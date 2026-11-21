#!/usr/bin/env python3
"""Independently hash each checked-out PNG against its recorded source manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

CHUNK = 1024 * 1024
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'
SHA256 = re.compile(r'^[0-9a-f]{64}$')
GIT_SHA1 = re.compile(r'^[0-9a-f]{40}$')


def verify(repo_root: Path, manifest_path: Path) -> dict:
    root = repo_root.resolve()
    source = manifest_path.resolve()
    if not source.is_relative_to(root):
        raise ValueError('Manifest is outside repository')
    manifest = json.loads(source.read_text('utf-8'))
    entries = manifest.get('originals')
    if not isinstance(entries, list) or len(entries) != 6:
        raise ValueError('Expected exactly 6 original PNG files')
    expected_names = {'C01.png','C02.png','C02.5.png','C09.png','C11.png','C16.png'}
    records = []
    seen = set()
    for entry in entries:
        rel = entry['github_path']
        if not isinstance(rel, str) or '\\' in rel or ':' in rel or not rel:
            raise ValueError('Invalid path')
        path = PurePosixPath(rel)
        if path.is_absolute() or any(part in ('', '.', '..') for part in rel.split('/')):
            raise ValueError('Unsafe path: ' + rel)
        name = entry['filename']
        if name not in expected_names or name != path.name or name in seen:
            raise ValueError('Missing, duplicated, or unexpected original: ' + str(name))
        seen.add(name)
        full = root / rel
        if not full.resolve().is_relative_to(root) or not full.is_file() or full.is_symlink():
            raise ValueError('Missing or unsafe original: ' + rel)
        count = full.stat().st_size
        sha = hashlib.sha256()
        blob = hashlib.sha1(b'blob ' + str(count).encode('ascii') + b'\0')
        with full.open('rb') as file:
            if file.read(8) != PNG_MAGIC:
                raise ValueError('Invalid PNG signature: ' + rel)
            file.seek(0)
            for block in iter(lambda: file.read(CHUNK), b''):
                sha.update(block)
                blob.update(block)
        expected_size = entry['bytes']
        expected_sha = entry['sha256']
        expected_blob = entry['git_blob_sha1']
        if type(expected_size) is not int or not SHA256.fullmatch(expected_sha) or not GIT_SHA1.fullmatch(expected_blob):
            raise ValueError('Invalid source manifest: ' + rel)
        if (count, sha.hexdigest(), blob.hexdigest()) != (expected_size, expected_sha, expected_blob):
            raise ValueError('Source checksum mismatch: ' + rel)
        records.append({'name':name,'bytes':count,'sha256':expected_sha,'git_blob_sha1':expected_blob})
    if seen != expected_names:
        raise ValueError('Original set differs: ' + ', '.join(sorted(expected_names-seen)))
    return {'result':'PASS','count':len(records),'source':'GitHub checkout bytes compared with user-uploaded original SHA-256 and Git blob SHA-1','files':records}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', type=Path, default=Path('.'))
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path)
    args = p.parse_args(argv)
    try:
        report = verify(args.repo_root, args.repo_root / args.manifest)
        if args.output:
            args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n', encoding='utf-8')
        print(json.dumps({'result':report['result'],'count':report['count']},ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print('VERIFY FAILED: '+str(exc),file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())