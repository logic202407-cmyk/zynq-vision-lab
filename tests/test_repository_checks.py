"""Tests for repository tooling only; no hardware or vision functionality."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.check_repository import (
    ROOT, check_repository, contains_secret, markdown_link_errors,
    safe_relative_path, status_errors,
)


class RepositoryCheckTests(unittest.TestCase):
    def test_safe_ascii_path(self) -> None:
        self.assertTrue(safe_relative_path('src/rtl/module_v1.sv'))

    def test_reject_traversal_absolute_and_non_ascii(self) -> None:
        for name in ('../x', '/x', 'a/../b', 'a\\b', 'a//b', '中文.md', '', None):
            with self.subTest(name=name):
                self.assertFalse(safe_relative_path(name))

    def test_secret_token_detected(self) -> None:
        self.assertTrue(contains_secret('gh' + 'p_' + 'A' * 40))
        self.assertTrue(contains_secret('github_' + 'pat_' + 'B' * 50))

    def test_private_key_detected(self) -> None:
        self.assertTrue(contains_secret('-----BEGIN ' + 'OPENSSH PRIVATE KEY-----'))

    def test_normal_document_not_secret(self) -> None:
        self.assertFalse(contains_secret('Use browser login. No token is stored in this project.'))

    def test_existing_relative_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'README.md').touch()
            self.assertEqual(markdown_link_errors(root, root / 'index.md', '[ok](README.md)'), [])

    def test_missing_and_escaping_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(len(markdown_link_errors(root, root / 'README.md', '[x](missing.md) [y](../escape.md)')), 2)

    def test_external_links_are_not_fetched(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(markdown_link_errors(root, root / 'README.md', '[external](https://example.org/no-fetch) [heading](#heading)'), [])

    def test_planned_status_needs_no_fabricated_evidence(self) -> None:
        data = {'schema_version': 1, 'components': [{'id': 'camera', 'status': 'planned', 'evidence': []}]}
        self.assertEqual(status_errors(ROOT, data), [])

    def test_verified_status_requires_evidence_and_provenance(self) -> None:
        data = {'schema_version': 1, 'components': [{'id': 'camera', 'status': 'board_verified', 'evidence': []}]}
        self.assertGreaterEqual(len(status_errors(ROOT, data)), 3)

    def test_invalid_and_duplicate_status(self) -> None:
        data = {'schema_version': 1, 'components': [
            {'id': 'x', 'status': 'magic_success', 'evidence': []},
            {'id': 'x', 'status': 'planned', 'evidence': ['../secret']},
        ]}
        self.assertGreaterEqual(len(status_errors(ROOT, data)), 3)

    def test_current_repository_foundations(self) -> None:
        self.assertEqual(check_repository(ROOT), [])


if __name__ == '__main__':
    unittest.main()
