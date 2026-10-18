"""Offline integrity regressions for both preserved manifest formats."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import verify_results as verifier


class ArchiveManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'results').mkdir()
        self.patch = patch.object(verifier, 'REPO_ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.entry = {'path': 'results/example.zip',
                      'member_manifest': 'results/members.json', 'members': 1}
        self.payload = b'preserved failed result\n'
        self.members = {'report.txt': {'bytes': len(self.payload),
                        'sha256': hashlib.sha256(self.payload).hexdigest()}}

    def check_archive(self, manifest, members=None):
        (self.root / self.entry['member_manifest']).write_text(json.dumps(manifest))
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            for name, data in (members or {'report.txt': self.payload}).items():
                z.writestr(name, data)
        stream.seek(0)
        return verifier.verify_members(self.entry, stream)

    def test_legacy_wrapper_and_modern_flat_map_verify_identical_bytes(self):
        self.assertEqual(1, self.check_archive(self.members))
        self.assertEqual(1, self.check_archive({'archive': self.entry['path'],
                                              'members': self.members}))

    def test_legacy_wrapper_rejects_wrong_archive_binding(self):
        with self.assertRaisesRegex(verifier.VerificationError, 'binding mismatch'):
            self.check_archive({'archive': 'results/different.zip', 'members': self.members})

    def test_legacy_wrapper_rejects_malformed_members(self):
        with self.assertRaisesRegex(verifier.VerificationError, 'Invalid wrapped members'):
            self.check_archive({'archive': self.entry['path'], 'members': []})

    def test_unknown_wrapper_fields_rejected(self):
        with self.assertRaisesRegex(verifier.VerificationError, 'Invalid wrapped member manifest'):
            self.check_archive({'archive': self.entry['path'], 'members': self.members, 'extra': 1})

    def test_hash_mismatch_fails_in_both_formats(self):
        for manifest in [self.members, {'archive': self.entry['path'], 'members': self.members}]:
            with self.subTest(manifest=manifest), self.assertRaises(verifier.VerificationError):
                self.check_archive(manifest, {'report.txt': b'changed'})

    def test_missing_or_unlisted_members_fail(self):
        for manifest in [self.members, {'archive': self.entry['path'], 'members': self.members}]:
            with self.subTest(manifest=manifest), self.assertRaisesRegex(verifier.VerificationError, 'Unlisted'):
                self.check_archive(manifest, {'other.txt': self.payload})

    def test_path_traversal_still_rejected(self):
        with self.assertRaisesRegex(verifier.VerificationError, 'Parent traversal'):
            self.check_archive(self.members, {'../report.txt': self.payload})

    def test_flat_map_can_contain_a_file_named_archive(self):
        metadata = self.members['report.txt']
        self.assertEqual(1, self.check_archive({'archive': metadata}, {'archive': self.payload}))


if __name__ == '__main__':
    unittest.main()
