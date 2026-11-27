#!/usr/bin/env python3
"""Encode one original into a numbered ASCII CSV for a binary-capable connector.

No network, no image conversion, and no base64 in stdout. Keep packets transient.
"""
import argparse
import base64
import csv
import hashlib
import json
from pathlib import Path

ROW_WIDTH = 8192
MAX_BYTES = 10 * 1024 * 1024  # conservative local bound, not a connector guarantee


def prepare(source: Path, packet: Path) -> dict:
    if not source.is_file() or source.is_symlink():
        raise ValueError('source must be an original regular file')
    if packet.suffix.lower() != '.csv' or packet.exists() or packet.is_symlink():
        raise ValueError('packet must be a new .csv file')
    size = source.stat().st_size
    if not 0 < size <= MAX_BYTES:
        raise ValueError('unsupported file size; use a direct Git environment')
    raw = source.read_bytes()
    if len(raw) != size:
        raise ValueError('source changed while reading')
    if source.suffix.lower() == '.png' and not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('invalid PNG signature')
    encoded = base64.b64encode(raw).decode('ascii')
    rows = (len(encoded) + ROW_WIDTH - 1) // ROW_WIDTH
    with packet.open('x', encoding='ascii', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['index', 'encoded'])
        writer.writerows((i, encoded[i*ROW_WIDTH:(i+1)*ROW_WIDTH]) for i in range(rows))
    with packet.open(encoding='ascii', newline='') as f:
        reader = csv.reader(f)
        if next(reader) != ['index', 'encoded']:
            raise ValueError('packet header mismatch')
        parts = []
        for i, row in enumerate(reader):
            if len(row) != 2 or row[0] != str(i):
                raise ValueError('packet sequence mismatch')
            parts.append(row[1])
    if len(parts) != rows or base64.b64decode(''.join(parts), validate=True) != raw:
        raise ValueError('packet roundtrip mismatch')
    return {'name': source.name, 'bytes': size, 'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob_sha1': hashlib.sha1(b'blob ' + str(size).encode('ascii') + b'\0' + raw).hexdigest(),
            'base64_length': len(encoded), 'row_width': ROW_WIDTH, 'rows': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('packet', type=Path)
    args = p.parse_args()
    print(json.dumps(prepare(args.source, args.packet), ensure_ascii=False))


if __name__ == '__main__':
    main()
