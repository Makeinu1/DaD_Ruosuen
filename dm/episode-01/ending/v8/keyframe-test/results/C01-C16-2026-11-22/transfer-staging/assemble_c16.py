#!/usr/bin/env python3
"""One-time, integrity-checked reconstruction of original C16 from Git blob chunks."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PREFIX = Path('dm/episode-01/ending/v8/keyframe-test/results/C01-C16-2026-11-22')
STAGING = ROOT / PREFIX / 'transfer-staging'
DEST = ROOT / PREFIX / 'originals' / 'C16.png'
MANIFEST = ROOT / PREFIX / 'manifest.json'
EXPECTED_CHUNKS = (
    ('C16.chunk01', 1200000, '51ede7da6a99727998a5f098d9d641a4ae8d08dd1755568f9a0a7eb7416b99c7'),
    ('C16.chunk02', 1200000, '21a1efcb4121ea5ae701672879120790ba20adc8f585556822d90c23d1bd5b54'),
    ('C16.chunk03', 1105211, '85eec55b514c77f9b6cca3679f72185a66dc17ac26787c6608d9184663ef0fbf'),
)
BRANCH = 'art/ending-originals-c01-c16-20261122'
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


def blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def assert_original(data, item):
    assert len(data) == item['bytes'], f"bytes differ: {item['filename']}"
    assert hashlib.sha256(data).hexdigest() == item['sha256'], f"sha256 differs: {item['filename']}"
    assert blob_sha(data) == item['git_blob_sha1'], f"git blob differs: {item['filename']}"
    assert data.startswith(PNG_MAGIC), f"invalid PNG: {item['filename']}"


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def main():
    doc = json.loads(MANIFEST.read_text(encoding='utf-8'))
    items = {item['filename']: item for item in doc['originals']}
    assert set(items) == {'C01.png','C02.png','C02.5.png','C09.png','C11.png','C16.png'}
    chunks = []
    for name, expected_size, expected_sha in EXPECTED_CHUNKS:
        raw = (STAGING / name).read_bytes()
        assert len(raw) == expected_size, f'chunk length differs: {name}'
        assert hashlib.sha256(raw).hexdigest() == expected_sha, f'chunk SHA differs: {name}'
        chunks.append(raw)
    source = b''.join(chunks)
    assert_original(source, items['C16.png'])
    for name, item in items.items():
        if name == 'C16.png':
            continue
        assert_original((ROOT / item['github_path']).read_bytes(), item)
    if DEST.exists():
        assert DEST.read_bytes() == source, 'existing C16 differs; refusing overwrite'
    else:
        DEST.parent.mkdir(parents=True, exist_ok=True)
        tmp = DEST.with_suffix('.png.tmp')
        tmp.write_bytes(source)
        os.replace(tmp, DEST)
    print(json.dumps({'result':'VERIFIED','files':6,'assembled':'C16.png','bytes':len(source),'sha256':items['C16.png']['sha256']},ensure_ascii=False))
    if os.getenv('RUOSUEN_VERIFY_ONLY') == '1':
        return
    assert os.getenv('GITHUB_REF_NAME') == BRANCH, 'ref mismatch: refuse push'
    run('git','config','user.name','github-actions[bot]')
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add','--',str(DEST.relative_to(ROOT)))
    run('git','rm','-r','--',str(STAGING.relative_to(ROOT)))
    run('git','commit','-m','art(dm): assemble original C16 PNG and remove transfer chunks')
    run('git','push','origin',f'HEAD:refs/heads/{BRANCH}')


if __name__ == '__main__':
    main()