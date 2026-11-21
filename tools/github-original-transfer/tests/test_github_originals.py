import hashlib
import io
import json
import os
import stat
import struct
import subprocess
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import github_originals as g


def png(pixel: bytes = b'\xff\x00\x00') -> bytes:
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00' + pixel)) + chunk(b'IEND', b'')


def pack_zip(p: Path, make_bad=False) -> tuple[list, list]:
    a = png()
    b = png(b'\x00\xff\x00')
    assets = [{'path': 'selected/C01.png', 'bytes': len(a), 'sha256': hashlib.sha256(a).hexdigest()}]
    variants = [{'name': 'take01.png', 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}]
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('bundle/selected/C01.png', a)
        if not make_bad:
            z.writestr('bundle/variants/take01.png', b)
        z.writestr('bundle/manifest.json', json.dumps({'assets': assets, 'variants': variants}))
    return assets, variants


def git(*a, cwd=None):
    return subprocess.run(['git', *a], cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()


class TestSource(unittest.TestCase):
    def test_manifest_and_fingerprints(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / 'bundle.zip'
            pack_zip(archive)
            with g.source_pack(archive) as (root, media):
                self.assertEqual([m.relative for m in media], ['selected/C01.png', 'variants/take01.png'])
                self.assertEqual(len(media), 2)
                self.assertEqual(media[0].git_blob_sha1, git('hash-object', str(root / media[0].relative)))

    def test_source_manifest_missing_member_fails(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / 'bundle.zip'
            pack_zip(archive, make_bad=True)
            with self.assertRaises(g.TransferError):
                with g.source_pack(archive):
                    pass

    def test_zip_traversal_and_symlink_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('../escape.png', png())
            with self.assertRaises(g.TransferError):
                with g.source_pack(archive):
                    pass
            with zipfile.ZipFile(archive, 'w') as z:
                info = zipfile.ZipInfo('symlink.png')
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, 'elsewhere')
            with self.assertRaises(g.TransferError):
                with g.source_pack(archive):
                    pass

    def test_reject_bad_png_and_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'x.png').write_bytes(b'not png')
            with self.assertRaises(g.TransferError):
                with g.source_pack(root):
                    pass
            (root / 'x.png').write_bytes(png())
            (root / 'manifest.json').write_text(json.dumps({'assets': [{'path': 'x.png','bytes':1234,'sha256':'a'*64}], 'variants': []}))
            with self.assertRaises(g.TransferError):
                with g.source_pack(root):
                    pass

    def test_cases_and_unsafe_dest(self):
        self.assertRaises(g.TransferError, g.safe_rel, 'a/../b')
        self.assertRaises(g.TransferError, g.safe_rel, '/absolute.png')
        self.assertRaises(g.TransferError, g.safe_rel, 'C:\\oops.png')


class TestLocalGitTransfer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.d = Path(self.temp.name)
        self.bare = self.d / 'remote.git'
        git('init', '--bare', '-b', 'main', str(self.bare))
        seed = self.d / 'seed'
        git('clone', str(self.bare), str(seed))
        (seed / 'README.md').write_text('# source repository\n')
        git('add', '.', cwd=seed)
        git('-c', 'user.name=Unit Test', '-c', 'user.email=unit@example.invalid', 'commit', '-m', 'seed', cwd=seed)
        git('push', 'origin', 'HEAD:main', cwd=seed)
        self.src = self.d / 'bundle.zip'
        pack_zip(self.src)
        self.env = {'GIT_AUTHOR_NAME': 'Unit Test', 'GIT_AUTHOR_EMAIL': 'unit@example.invalid',
                    'GIT_COMMITTER_NAME': 'Unit Test', 'GIT_COMMITTER_EMAIL': 'unit@example.invalid'}

    def tearDown(self):
        self.temp.cleanup()

    def call(self, *extra):
        args = ['upload', '--source', str(self.src), '--destination', 'dm/artwork',
                '--remote-url', str(self.bare), '--branch', 'art/new-originals', '--base', 'main', *extra]
        with patch.dict(os.environ, self.env):
            return g.main(args)

    def test_two_images_uploaded_verified_idempotent(self):
        self.assertEqual(self.call(), 0)
        self.assertEqual(self.call(), 0)  # does not introduce a redundant commit
        with tempfile.TemporaryDirectory() as d:
            git('clone', '--branch', 'art/new-originals', str(self.bare), d)
            self.assertEqual((Path(d)/'dm/artwork/selected/C01.png').read_bytes(), png())
            self.assertEqual((Path(d)/'dm/artwork/variants/take01.png').read_bytes(), png(b'\x00\xff\x00'))
            self.assertEqual(git('rev-list','--count','HEAD',cwd=Path(d)), '2')

    def test_conflict_not_overwritten_without_replace(self):
        self.assertEqual(self.call(), 0)
        # Replace source PNG but give correct new source hashes: refusing overwrite still required.
        with zipfile.ZipFile(self.src, 'w') as z:
            new = png(b'\x11\x22\x33')
            old = png(b'\x00\xff\x00')
            z.writestr('bundle/selected/C01.png', new)
            z.writestr('bundle/variants/take01.png', old)
            z.writestr('bundle/manifest.json', json.dumps({'assets':[{'path':'selected/C01.png','bytes':len(new),'sha256':hashlib.sha256(new).hexdigest()}],
                'variants':[{'name':'take01.png','bytes':len(old),'sha256':hashlib.sha256(old).hexdigest()}]}))
        self.assertEqual(self.call(), 1)
        self.assertEqual(self.call('--replace'), 0)

    def test_plan_does_not_need_network(self):
        report = self.d/'report.json'
        self.assertEqual(g.main(['plan','--source',str(self.src),'--destination','dm/artwork','--report',str(report)]),0)
        data=json.loads(report.read_text())
        self.assertEqual(data['status'], 'local_verified')
        self.assertEqual(len(data['files']),2)
        self.assertEqual(g.main(['plan','--source',str(self.src),'--destination','dm/artwork','--report',str(report)]),1)


if __name__ == '__main__':
    unittest.main()