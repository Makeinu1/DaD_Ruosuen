#!/usr/bin/env python3
"""Byte-exact batch upload of original media to a GitHub PR branch.

Python 3.10+, stdlib + git; GitHub publishing needs authenticated GitHub CLI (gh).
No emails, token files, archive re-encoding, force push, or automatic merge.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote

MEDIA_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.tif', '.tiff', '.mp4', '.mov', '.wav', '.mp3', '.pdf'}
MAX_ARCHIVE_FILES = 2000
MAX_ARCHIVE_MEMBER = 200 * 1024 * 1024  # 200 MiB
MAX_ARCHIVE_TOTAL = 2 * 1024 * 1024 * 1024  # 2 GiB
CHUNK = 1024 * 1024


class TransferError(Exception):
    pass


def safe_rel(value: str) -> str:
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value or ':' in value:
        raise TransferError(f'Invalid file path: {value!r}')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('', '.', '..') for x in value.split('/')):
        raise TransferError(f'Unsafe file path: {value!r}')
    return p.as_posix()


def fingerprint(p: Path) -> tuple[int, str, str]:
    size = p.stat().st_size
    sha = hashlib.sha256()
    blob = hashlib.sha1(b'blob ' + str(size).encode('ascii') + b'\0')
    with p.open('rb') as fh:
        for buf in iter(lambda: fh.read(CHUNK), b''):
            sha.update(buf)
            blob.update(buf)
    return size, sha.hexdigest(), blob.hexdigest()


@dataclass(frozen=True)
class Media:
    relative: str
    bytes: int
    sha256: str
    git_blob_sha1: str


def is_media(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in MEDIA_EXTENSIONS


def check_signatures(path: Path) -> None:
    with path.open('rb') as f:
        head = f.read(16)
    ext = path.suffix.lower()
    if ext == '.png' and not head.startswith(b'\x89PNG\r\n\x1a\n'):
        raise TransferError(f'Invalid PNG signature: {path.name}')
    if ext in {'.jpg', '.jpeg'} and not head.startswith(b'\xff\xd8\xff'):
        raise TransferError(f'Invalid JPEG signature: {path.name}')
    if ext == '.webp' and not (head.startswith(b'RIFF') and head[8:12] == b'WEBP'):
        raise TransferError(f'Invalid WebP signature: {path.name}')


def extract_zip_safely(src: Path, dst: Path) -> None:
    with zipfile.ZipFile(src) as zf:
        infos = zf.infolist()
        if len(infos) > MAX_ARCHIVE_FILES:
            raise TransferError('Archive contains too many entries')
        if sum(i.file_size for i in infos) > MAX_ARCHIVE_TOTAL:
            raise TransferError('Archive expanded size exceeds safety limit')
        seen = set()
        for info in infos:
            name = info.filename.rstrip('/')
            rel = safe_rel(name)
            cf = rel.casefold()
            if cf in seen:
                raise TransferError(f'Duplicate archive member: {rel}')
            seen.add(cf)
            if stat.S_ISLNK((info.external_attr >> 16) & 0xffff):
                raise TransferError(f'Archive symlink rejected: {rel}')
            if info.file_size > MAX_ARCHIVE_MEMBER:
                raise TransferError(f'Archive member too large: {rel}')
            path = dst / rel
            if info.is_dir():
                path.mkdir(parents=True, exist_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            copied = 0
            with zf.open(info) as r, path.open('wb') as w:
                for chunk in iter(lambda: r.read(CHUNK), b''):
                    copied += len(chunk)
                    if copied > MAX_ARCHIVE_MEMBER or copied > info.file_size:
                        raise TransferError(f'Archive expansion limit exceeded: {rel}')
                    w.write(chunk)
            if copied != info.file_size:
                raise TransferError(f'Archive size differs: {rel}')


def find_source_root(folder: Path, hint: str | None) -> Path:
    if hint:
        root = folder / safe_rel(hint)
        if not root.is_dir():
            raise TransferError('Source root missing')
        return root
    if (folder / 'manifest.json').is_file():
        return folder
    manifests = list(folder.rglob('manifest.json'))
    if len(manifests) == 1:
        return manifests[0].parent
    if len(manifests) > 1:
        raise TransferError('Multiple manifests; supply --source-root')
    children = [p for p in folder.iterdir() if p.name != '__MACOSX']
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return folder


def manifest_entries(root: Path) -> list[tuple[str, int | None, str | None]]:
    mp = root / 'manifest.json'
    if not mp.is_file():
        return [(p.relative_to(root).as_posix(), None, None) for p in sorted(root.rglob('*'))
                if p.is_file() and is_media(p.name)]
    data = json.loads(mp.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('assets'), list) or not isinstance(data.get('variants'), list):
        raise TransferError('Source manifest must have assets[] and variants[] (source ZIP format)')
    entries = []
    for section in ('assets', 'variants'):
        for item in data[section]:
            if not isinstance(item, dict):
                raise TransferError('Invalid source manifest entry')
            rel = item.get('path') if section == 'assets' else 'variants/' + str(item.get('name', ''))
            rel = safe_rel(rel)
            expected_size, expected_sha = item.get('bytes'), item.get('sha256')
            if type(expected_size) is not int or expected_size < 0 or not re.fullmatch('[0-9a-f]{64}', str(expected_sha)):
                raise TransferError(f'Missing or malformed source hash for {rel}')
            entries.append((rel, expected_size, expected_sha))
    disk = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and is_media(p.name)}
    listed = {x[0] for x in entries}
    if disk != listed or len(listed) != len(entries):
        raise TransferError(f'Manifest/image set differs: missing={sorted(listed-disk)}, unlisted={sorted(disk-listed)}')
    return entries


@contextlib.contextmanager
def source_pack(src: Path, root_hint: str | None = None):
    if not src.exists():
        raise TransferError(f'Source does not exist: {src}')
    with tempfile.TemporaryDirectory(prefix='github-originals-src-') as tmp:
        folder = Path(tmp)
        if src.is_file():
            if not zipfile.is_zipfile(src):
                raise TransferError('Source must be directory or ZIP')
            extract_zip_safely(src, folder)
        elif src.is_dir():
            folder = src
        else:
            raise TransferError('Unsupported source')
        root = find_source_root(folder, root_hint)
        entries = manifest_entries(root)
        if not entries:
            raise TransferError('No media found')
        media = []
        seen = set()
        for rel, expected_size, expected_hash in entries:
            rel = safe_rel(rel)
            if rel.casefold() in seen or not is_media(rel):
                raise TransferError(f'Duplicate or unsupported media: {rel}')
            seen.add(rel.casefold())
            p = root / rel
            if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
                raise TransferError(f'Unsafe or missing original: {rel}')
            check_signatures(p)
            sz, sha, blob = fingerprint(p)
            if expected_size is not None and (sz != expected_size or sha != expected_hash):
                raise TransferError(f'Original hash/size differs from source manifest: {rel}')
            media.append(Media(rel, sz, sha, blob))
        yield root, media


def cmd(args: list[str], cwd: Path | None = None, *, binary: bool = False, allow_failure: bool = False):
    result = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode and not allow_failure:
        raise TransferError(f'Command failed ({args[0]}, exit={result.returncode}); inspect authentication, network, branch, or repository')
    if binary:
        return result.returncode, result.stdout
    return result.returncode, result.stdout.decode('utf-8', errors='replace').strip()


def git(*args: str, cwd: Path):
    return cmd(['git', *args], cwd=cwd)[1]


def gh(*args: str):
    if not shutil.which('gh'):
        raise TransferError('GitHub CLI (gh) is unavailable; install and authenticate with gh auth login')
    return cmd(['gh', *args])[1]


def check_pr(repo: str, number: int, branch: str, base: str) -> str:
    data = json.loads(gh('pr', 'view', str(number), '-R', repo, '--json', 'headRefName,baseRefName,isCrossRepository,state,url'))
    if data['state'] != 'OPEN' or data['headRefName'] != branch or data['baseRefName'] != base or data.get('isCrossRepository'):
        raise TransferError('PR is not open, or PR head/base differs, or head is from a fork')
    return data['url']


def ensure_within_repo(repo: Path, destination: str) -> None:
    base = repo.resolve()
    for parent in (base / destination).parents:
        if parent == base:
            break
        if parent.is_symlink():
            raise TransferError('Destination contains symlink')
    if not (base / destination).resolve().is_relative_to(base):
        raise TransferError('Destination escapes checkout')


def copy_verified(src: Path, dest: Path, item: Media, replace: bool) -> bool:
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink() or not dest.is_file():
            raise TransferError(f'Refusing to overwrite symlink/non-file: {item.relative}')
        if fingerprint(dest) == (item.bytes, item.sha256, item.git_blob_sha1):
            return False
        if not replace:
            raise TransferError(f'Existing file differs; use --replace only after review: {item.relative}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    if fingerprint(dest) != (item.bytes, item.sha256, item.git_blob_sha1):
        raise TransferError(f'Copy checksum mismatch: {item.relative}')
    return True


def independently_verify(repo: str | None, branch: str, paths: list[tuple[str, Media]], remote: str | None) -> None:
    """Fetch GitHub raw bytes, not just local pushed objects. For offline tests, re-clone remote."""
    if repo:
        for path, item in paths:
            target = 'repos/' + repo + '/contents/' + quote(path, safe='/') + '?ref=' + quote(branch, safe='')
            _, payload = cmd(['gh', 'api', target, '-H', 'Accept: application/vnd.github.raw+json'], binary=True)
            if len(payload) != item.bytes or hashlib.sha256(payload).hexdigest() != item.sha256:
                raise TransferError(f'Independent GitHub download checksum mismatch: {path}')
    else:
        assert remote
        with tempfile.TemporaryDirectory(prefix='github-originals-verify-') as td:
            checkout = Path(td) / 'verify'
            cmd(['git', 'clone', '--no-checkout', '--branch', branch, remote, str(checkout)])
            for path, item in paths:
                _, payload = cmd(['git', 'show', 'HEAD:' + path], cwd=checkout, binary=True)
                if len(payload) != item.bytes or hashlib.sha256(payload).hexdigest() != item.sha256:
                    raise TransferError(f'Independent remote-clone checksum mismatch: {path}')


def make_report(media: list[Media], destination: str, *, repo=None, branch=None, pr_url=None, status='local_verified') -> dict:
    return {
        'schema': 1, 'status': status, 'repository': repo, 'branch': branch, 'pull_request': pr_url,
        'verification': 'source_manifest_if_present + local_git_blob + independent_remote_bytes_sha256' if status == 'remote_verified' else 'local_bytes_sha256 + local_git_blob_sha1',
        'files': [dict(asdict(m), github_path=destination + '/' + m.relative) for m in media],
    }


def write_report(path: Path | None, report: dict) -> None:
    if path is None:
        return
    if path.exists():
        raise TransferError('Report already exists; choose another --report path (no overwrites)')
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temp.replace(path)


def upload(args, root: Path, media: list[Media]) -> dict:
    if not shutil.which('git'):
        raise TransferError('git is required')
    repo = args.repo
    remote = args.remote_url
    if not repo and not remote:
        raise TransferError('Provide --repo owner/name (GitHub) or --remote-url (local test)')
    if repo and not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise TransferError('Invalid GitHub repo name')
    branch, base = args.branch, args.base
    if not branch or branch == base or branch in {'main', 'master'} or not re.fullmatch(r'[\w./-]+', branch) or '..' in branch or branch.endswith('/'):
        raise TransferError('Refusing unsafe/protected upload branch')
    destination = safe_rel(args.destination)
    if repo:
        gh('auth', 'status')
    pr_url = check_pr(repo, args.pr, branch, base) if args.pr is not None else None
    with tempfile.TemporaryDirectory(prefix='github-originals-repo-') as td:
        checkout = Path(td) / 'repo'
        if repo:
            gh('repo', 'clone', repo, str(checkout), '--', '--filter=blob:none')
        else:
            cmd(['git', 'clone', remote, str(checkout)])
        _, lines = cmd(['git', 'ls-remote', '--heads', 'origin', 'refs/heads/' + branch], cwd=checkout)
        branch_exists = bool(lines)
        if args.pr is not None and not branch_exists:
            raise TransferError('PR branch does not exist remotely')
        if branch_exists:
            git('fetch', 'origin', branch, cwd=checkout)
            git('checkout', '-B', branch, 'FETCH_HEAD', cwd=checkout)
        else:
            git('fetch', 'origin', base, cwd=checkout)
            git('checkout', '-B', branch, 'FETCH_HEAD', cwd=checkout)
        changed = []
        paths = []
        for item in media:
            dest_path = destination + '/' + item.relative
            ensure_within_repo(checkout, dest_path)
            if copy_verified(root / item.relative, checkout / dest_path, item, args.replace):
                changed.append(dest_path)
            paths.append((dest_path, item))
        if changed:
            git('add', '--', *changed, cwd=checkout)
            _, staged = cmd(['git', 'diff', '--cached', '--name-only', '-z'], cwd=checkout, binary=True)
            actual = {x.decode('utf-8') for x in staged.split(b'\0') if x}
            if actual != set(changed):
                raise TransferError('Staged files differ from expected paths')
            git('commit', '-m', 'art: preserve original media with source SHA-256', cwd=checkout)
            # Fast-forward only: diverging branches require human review, never force.
            git('push', 'origin', 'HEAD:refs/heads/' + branch, cwd=checkout)
        elif not branch_exists:
            raise TransferError('Nothing changed on a new branch')
        remote_sha = git('ls-remote', 'origin', 'refs/heads/' + branch, cwd=checkout).split()[0]
        local_sha = git('rev-parse', 'HEAD', cwd=checkout)
        if remote_sha != local_sha:
            raise TransferError('Remote branch advanced concurrently; stop before claiming success')
        git('fetch', 'origin', branch, cwd=checkout)
        for path, item in paths:
            obj = git('rev-parse', 'FETCH_HEAD:' + path, cwd=checkout)
            if obj != item.git_blob_sha1:
                raise TransferError(f'Remote tree references different blob: {path}')
        independently_verify(repo, branch, paths, remote)
        if repo and not pr_url:
            existing = json.loads(gh('pr', 'list', '-R', repo, '--head', branch, '--state', 'open', '--json', 'number,url'))
            if len(existing) > 1:
                raise TransferError('Multiple open PRs for branch')
            if existing:
                pr_url = existing[0]['url']
            else:
                pr_url = gh('pr', 'create', '-R', repo, '--base', base, '--head', branch, '--draft',
                            '--title', 'art: add verified original media',
                            '--body', 'Original bytes uploaded to branch. Source SHA-256 and Git blob SHA-1 verified; independently re-downloaded each file. Review and merge manually.')
        return make_report(media, destination, repo=repo or remote, branch=branch, pr_url=pr_url, status='remote_verified')


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    for name in ('plan', 'upload'):
        sp = sub.add_parser(name)
        sp.add_argument('--source', type=Path, required=True, help='directory or original ZIP')
        sp.add_argument('--source-root', help='relative root inside ZIP or directory')
        sp.add_argument('--destination', required=True, help='target path prefix in repository')
        sp.add_argument('--report', type=Path, help='write JSON report; will never overwrite')
        if name == 'upload':
            sp.add_argument('--repo', help='GitHub owner/name; requires gh auth login')
            sp.add_argument('--remote-url', help='test-only Git remote path instead of GitHub')
            sp.add_argument('--branch', required=True, help='non-default branch; existing or new')
            sp.add_argument('--base', default='main')
            sp.add_argument('--pr', type=int, help='existing PR number; validate head/base before upload')
            sp.add_argument('--replace', action='store_true', help='explicitly allow different existing destination bytes')
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        destination = safe_rel(args.destination)
        with source_pack(args.source, args.source_root) as (root, media):
            if args.action == 'plan':
                report = make_report(media, destination)
            else:
                report = upload(args, root, media)
            write_report(args.report, report)
            print(json.dumps({'status': report['status'], 'count': len(media), 'bytes': sum(x.bytes for x in media),
                              'branch': report['branch'], 'pull_request': report['pull_request']}, ensure_ascii=False))
            return 0
    except (TransferError, OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as e:
        print('ERROR: ' + str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())