import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_repository_media import audit, AuditError, digests

PNG = b'\x89PNG\r\n\x1a\n' + b'minimal-fixture-bytes'

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        prefix = 'dm/example/'
        def put(path, data=PNG):
            full = self.root / path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(data)
            return digests(full)
        imgs = []
        for i in range(9):
            name = prefix + f'selected/C{i:02d}.png'
            d = put(name, PNG + bytes([i]))
            imgs.append({'github_path': name, 'bytes': d['size'], 'sha256': d['sha256'],
                         'github_git_blob_sha1': d['git_blob_sha1']})
        self.variants = prefix + 'variants/'
        for i in range(34):
            put(self.variants + f'trial_{i:02d}.png', PNG + bytes([i]))
        self.source = prefix+'original/C16.png'
        self.archive1 = prefix+'Old/C16_a.png'
        self.archive2 = prefix+'Old/C16_b.png'
        d = put(self.source)
        put(self.archive1)
        put(self.archive2)
        self.manifest = self.root / 'manifest.json'
        self.doc = {'images': imgs,
                    'variants': {'count': 34, 'github_directory': self.variants},
                    'legacy_C16': {'archive_copies': [
                        {'path': self.archive1,'blob_sha': d['git_blob_sha1'], 'source_path_kept': self.source},
                        {'path': self.archive2,'blob_sha': d['git_blob_sha1'], 'source_path_kept': self.source},
                    ]}}
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.doc), encoding='utf-8')

    def test_valid_fileset_passes_and_records_45(self):
        report = audit(self.root, self.manifest)
        self.assertEqual(report['result'], 'PASS')
        self.assertEqual(report['checks']['total_png'], 45)
        self.assertEqual(report['checks']['selected_candidate_sha256_anchored'], 9)
        self.assertEqual(report['checks']['variants_hashed_without_source_sha256'], 34)

    def test_bad_sha_rejected_before_counts(self):
        self.doc['images'][0]['sha256']='0'*64
        self.write_manifest()
        with self.assertRaisesRegex(AuditError, 'SHA-256 mismatch'):
            audit(self.root, self.manifest)

    def test_missing_variant_rejected(self):
        (self.root / (self.variants + 'trial_00.png')).unlink()
        with self.assertRaisesRegex(AuditError, 'Variant count differs'):
            audit(self.root, self.manifest)

    def test_corrupt_old_archive_rejected(self):
        (self.root / self.archive1).write_bytes(PNG+b'corrupt')
        with self.assertRaisesRegex(AuditError, 'Git blob SHA-1 mismatch'):
            audit(self.root, self.manifest)

    def test_unsafe_manifest_path_rejected(self):
        self.doc['images'][0]['github_path']='../../outside.png'
        self.write_manifest()
        with self.assertRaisesRegex(AuditError, 'Unsafe path'):
            audit(self.root, self.manifest)

if __name__ == '__main__':
    unittest.main()