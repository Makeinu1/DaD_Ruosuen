#!/usr/bin/env python3
"""Verify committed original-media files from checked-out GitHub repository bytes.

This audit deliberately distinguishes original-source-anchored hashes from newly
calculated checksums of comparison variants without a recorded source hash.
No network, authentication, writes to the repository, or binary transformations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

PNG_MAGIC = b'\x89PNG\r\n\x1a\n'
HEXDIGEST = re.compile(r'^[0-9a-f]{40}$')
SHA256 = re.compile(r'^[0-9a-f]{64}$')
CHUNK = 1024 * 1024


class AuditError(ValueError):
    pass


def safe_file(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise AuditError('Invalid path in manifest')
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in ('', '.', '..') for part in value.split('/')):
        raise AuditError('Unsafe path in manifest: ' + value)
    dest = (root / value).resolve()
    if not dest.is_relative_to(root.resolve()):
        raise AuditError('Path escapes repo root: ' + value)
    if not dest.is_file() or dest.is_symlink():
        raise AuditError('Missing or unsafe file: ' + value)
    return dest


def digests(path: Path) -> dict:
    size = path.stat().st_size
    sha1 = hashlib.sha1(b'blob ' + str(size).encode('ascii') + b'\0')
    sha256 = hashlib.sha256()
    with path.open('rb') as f:
        if f.read(8) != PNG_MAGIC:
            raise AuditError('PNG signature mismatch: ' + path.name)
        f.seek(0)
        for block in iter(lambda: f.read(CHUNK), b''):
            sha1.update(block)
            sha256.update(block)
    return {'size': size, 'sha256': sha256.hexdigest(), 'git_blob_sha1': sha1.hexdigest()}


def require_sha(field: str, value: str, regex: re.Pattern) -> None:
    if not isinstance(value, str) or not regex.fullmatch(value):
        raise AuditError('Invalid ' + field)


def audit(root: Path, manifest_path: Path) -> dict:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_relative_to(root):
        raise AuditError('Manifest is outside repo')
    with manifest_path.open('r', encoding='utf-8') as f:
        manifest = json.load(f)
    images = manifest.get('images')
    variants = manifest.get('variants')
    legacy = manifest.get('legacy_C16')
    if not isinstance(images, list) or not isinstance(variants, dict) or not isinstance(legacy, dict):
        raise AuditError('Unrecognized project manifest schema')
    seen = set()
    records = []

    def register(value: str, kind: str, *, expected_sha256=None, expected_size=None, expected_blob=None, compare_path=None):
        if not value.lower().endswith('.png') or value in seen:
            raise AuditError('Duplicate or non-PNG path: ' + value)
        seen.add(value)
        info = digests(safe_file(root, value))
        if expected_size is not None and (type(expected_size) is not int or info['size'] != expected_size):
            raise AuditError('Byte count mismatch: ' + value)
        if expected_sha256 is not None:
            require_sha('SHA-256', expected_sha256, SHA256)
            if info['sha256'] != expected_sha256:
                raise AuditError('SHA-256 mismatch: ' + value)
        if expected_blob is not None:
            require_sha('Git blob SHA-1', expected_blob, HEXDIGEST)
            if info['git_blob_sha1'] != expected_blob:
                raise AuditError('Git blob SHA-1 mismatch: ' + value)
        if compare_path is not None:
            comparison = digests(safe_file(root, compare_path))
            if info != comparison:
                raise AuditError('Archived PNG bytes differ from retained source: ' + value)
        records.append({'path': value, 'category': kind, 'source_sha256_anchored': expected_sha256 is not None,
                        **info})

    for item in images:
        if not isinstance(item, dict):
            raise AuditError('Invalid images entry')
        register(item['github_path'], 'selected_or_candidate', expected_sha256=item['sha256'],
                 expected_size=item['bytes'], expected_blob=item['github_git_blob_sha1'])
    if len(images) != 9:
        raise AuditError('Expected exactly 9 selected/candidate PNGs, got ' + str(len(images)))

    var_dir = variants.get('github_directory')
    if not isinstance(var_dir, str):
        raise AuditError('Variant directory not declared')
    # Validate the directory path without requiring it to be a file.
    if var_dir.startswith('/') or '\\' in var_dir or any(p in ('', '..') for p in var_dir.rstrip('/').split('/')):
        raise AuditError('Unsafe variants directory')
    var_path = (root / var_dir).resolve()
    if not var_path.is_relative_to(root) or not var_path.is_dir():
        raise AuditError('Missing or unsafe variants directory')
    candidate_files = sorted(p for p in var_path.rglob('*') if p.is_file())
    if any(p.suffix.lower() != '.png' or p.is_symlink() for p in candidate_files):
        raise AuditError('Unexpected non-PNG or symlink in variants directory')
    expected_count = variants.get('count')
    if type(expected_count) is not int or len(candidate_files) != expected_count:
        raise AuditError(f'Variant count differs: actual={len(candidate_files)} expected={expected_count}')
    for path in candidate_files:
        register(path.relative_to(root).as_posix(), 'variant_unanchored')

    old_entries = legacy.get('archive_copies')
    if not isinstance(old_entries, list) or len(old_entries) != 2:
        raise AuditError('Expected two legacy archive files')
    for item in old_entries:
        if not isinstance(item, dict):
            raise AuditError('Invalid legacy entry')
        register(item['path'], 'legacy_C16', expected_blob=item['blob_sha'],
                 compare_path=item['source_path_kept'])
    if len(records) != 45:
        raise AuditError(f'Expected 45 original PNG entries, got {len(records)}')
    return {'schema_version': 1, 'result': 'PASS',
            'scope': 'committed checkout bytes (downloaded by GitHub Actions checkout)',
            'checks': {'total_png': len(records), 'selected_candidate_sha256_anchored': len(images),
                       'variants_hashed_without_source_sha256': len(candidate_files), 'legacy_archive_blob_and_source_identical': 2},
            'limitations': [
                'Variant SHA-256 values are calculated from the remote checkout, but no original-source SHA-256 per variant is stored in the project manifest.',
                'A successful repository-byte audit does not establish that comparison variants match originals that are no longer independently available.',
                'The source ZIP is not part of this verification.',
            ],
            'files': records}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path('.'))
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(args.repo_root, (args.repo_root / args.manifest))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'result': result['result'], 'checks': result['checks']}, ensure_ascii=False))
        return 0
    except (AuditError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print('AUDIT FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())