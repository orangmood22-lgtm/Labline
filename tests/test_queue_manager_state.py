#!/usr/bin/env python3
"""Targeted regression tests for experiment queue state persistence hardening."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools', 'experiment_queue'))

import queue_manager


class TestQueueManagerStatePersistence(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = Path(self.tmpdir) / 'queue_state.json'

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_state_writes_json_atomically(self):
        state = {
            'meta': {'project': 'demo', 'started': '2026-05-13T00:00:00Z'},
            'phases': [{'name': 'train', 'depends_on': [], 'status': 'pending'}],
            'jobs': [],
        }

        queue_manager.save_state(state, str(self.state_path))

        self.assertEqual(json.loads(self.state_path.read_text()), state)
        temp_files = list(Path(self.tmpdir).glob('.queue_state.json.*'))
        self.assertEqual(temp_files, [])

    def test_save_state_can_mirror_to_project_runtime_queue(self):
        project = Path(self.tmpdir) / 'project'
        state = {
            'meta': {'project': 'demo', 'started': '2026-05-13T00:00:00Z'},
            'phases': [{'name': 'train', 'depends_on': [], 'status': 'running'}],
            'jobs': [{'id': 'job1', 'status': 'running'}],
        }

        queue_manager.save_state(state, str(self.state_path), runtime_project=str(project), queue_id='formal-exp')

        mirror = project / '.labline' / 'runtime' / 'queues' / 'formal-exp.json'
        payload = json.loads(mirror.read_text())
        self.assertEqual(payload['schema_version'], '0.1')
        self.assertEqual(payload['queue_id'], 'formal-exp')
        self.assertEqual(payload['state_ref'], str(self.state_path))
        self.assertEqual(payload['state'], state)

    def test_load_state_initializes_default_shape(self):
        manifest = {
            '_path': '/tmp/manifest.json',
            'project': 'demo',
            'phases': [
                {'name': 'prep'},
                {'name': 'train', 'depends_on': ['prep']},
            ],
        }

        state = queue_manager.load_state(str(self.state_path), manifest)

        self.assertEqual(state['meta']['project'], 'demo')
        self.assertEqual(state['meta']['manifest_path'], '/tmp/manifest.json')
        self.assertIn('started', state['meta'])
        self.assertTrue(state['meta']['started'].endswith('Z'))
        self.assertEqual(state['jobs'], [])
        self.assertEqual(
            state['phases'],
            [
                {'name': 'prep', 'depends_on': [], 'status': 'pending'},
                {'name': 'train', 'depends_on': ['prep'], 'status': 'pending'},
            ],
        )

    def test_load_state_reads_existing_saved_state(self):
        expected = {
            'meta': {'project': 'resume', 'started': '2026-05-13T00:00:00Z'},
            'phases': [{'name': 'prep', 'depends_on': [], 'status': 'completed'}],
            'jobs': [{'id': 'job1', 'status': 'running'}],
        }
        self.state_path.write_text(json.dumps(expected))

        loaded = queue_manager.load_state(str(self.state_path), {'phases': []})

        self.assertEqual(loaded, expected)


if __name__ == '__main__':
    unittest.main()
