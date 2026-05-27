#!/usr/bin/env python3
"""Targeted regression tests for recent recovery hardening."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

import semantic_scholar_fetch as s2_fetch
import watchdog


class _FakeResponse:
    def __init__(self, body: str, status: int = 200):
        self._body = body.encode("utf-8")
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestSemanticScholarRetryHardening(unittest.TestCase):
    def test_json_decode_error_retries_on_empty_200_then_succeeds(self):
        responses = [
            _FakeResponse("", 200),
            _FakeResponse('{"ok": true}', 200),
        ]

        def fake_urlopen(_req, timeout=30):
            return responses.pop(0)

        with patch('semantic_scholar_fetch.urllib.request.urlopen', side_effect=fake_urlopen), \
             patch('semantic_scholar_fetch.time.sleep') as mock_sleep:
            result = s2_fetch._request_json('https://example.test/api', retries=2)

        self.assertEqual(result, {"ok": True})
        mock_sleep.assert_called_once()

    @patch('semantic_scholar_fetch.time.sleep')
    def test_retry_delay_doubles_with_cap(self, _mock_sleep):
        self.assertEqual(s2_fetch._retry_delay_seconds(0), 1.5)
        self.assertEqual(s2_fetch._retry_delay_seconds(1), 3.0)
        self.assertEqual(s2_fetch._retry_delay_seconds(10), 20.0)


    def test_json_decode_error_raises_after_retry_budget_exhausted(self):
        responses = [
            _FakeResponse('', 200),
            _FakeResponse('', 200),
        ]

        def fake_urlopen(_req, timeout=30):
            return responses.pop(0)

        with patch('semantic_scholar_fetch.urllib.request.urlopen', side_effect=fake_urlopen), \
             patch('semantic_scholar_fetch.time.sleep') as mock_sleep:
            with self.assertRaises(RuntimeError):
                s2_fetch._request_json('https://example.test/api', retries=1)

        self.assertEqual(mock_sleep.call_count, 1)

    @patch('semantic_scholar_fetch.time.sleep')
    def test_url_error_retries_then_raises_network_error(self, _mock_sleep):
        err = s2_fetch.urllib.error.URLError('temporary failure')
        with patch('semantic_scholar_fetch.urllib.request.urlopen', side_effect=err):
            with self.assertRaises(RuntimeError) as ctx:
                s2_fetch._request_json('https://example.test/api', retries=1)

        self.assertIn('Network error', str(ctx.exception))

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.status_dir = Path(self.tmpdir) / 'status'
        self.status_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_status_persists_json_atomically(self):
        status_file = self.status_dir / 'exp01.json'
        data = {"status": "OK", "task": "exp01", "type": "training", "ts": "2026-05-13T00:00:00"}
        watchdog.write_status(status_file, data)
        self.assertEqual(json.loads(status_file.read_text()), data)
        temp_files = list(self.status_dir.glob('.exp01.json.*'))
        self.assertEqual(temp_files, [])

    def test_register_task_writes_tasks_json(self):
        payload = json.dumps({"name": "exp01", "type": "training", "session": "exp01"})
        watchdog.register_task(self.tmpdir, payload)
        tasks_path = Path(self.tmpdir) / 'tasks.json'
        tasks = json.loads(tasks_path.read_text())
        self.assertEqual(tasks[0]['name'], 'exp01')
        self.assertIn('registered_at', tasks[0])
        temp_files = list(Path(self.tmpdir).glob('.tasks.json.*'))
        self.assertEqual(temp_files, [])


if __name__ == '__main__':
    unittest.main()
