#!/usr/bin/env python3
"""Targeted regression tests for experiment manifest persistence hardening."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools', 'experiment_queue'))

import build_manifest


class TestBuildManifestPersistence(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.output_path = Path(self.tmpdir) / 'manifest.json'

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_manifest_atomic_writes_json_without_temp_residue(self):
        manifest = {
            'project': 'demo',
            'cwd': '.',
            'conda': 'base',
            'gpus': [0],
            'max_parallel': 1,
            'oom_retry': {'delay': 120, 'max_attempts': 3},
            'phases': [],
        }

        build_manifest.write_manifest_atomic(self.output_path, manifest)

        self.assertEqual(json.loads(self.output_path.read_text()), manifest)
        temp_files = list(Path(self.tmpdir).glob('.manifest.json.*'))
        self.assertEqual(temp_files, [])

    def test_build_expands_grid_and_expected_output(self):
        config = {
            'project': 'grid-demo',
            'phases': [
                {
                    'name': 'train',
                    'grid': {'seed': [1, 2]},
                    'template': {
                        'id': 'job_${seed}',
                        'cmd': 'python train.py --seed ${seed}',
                        'expected_output': 'outputs/${seed}.json',
                    },
                }
            ],
        }

        manifest = build_manifest.build(config)

        self.assertEqual(manifest['project'], 'grid-demo')
        self.assertEqual(len(manifest['phases'][0]['jobs']), 2)
        self.assertEqual(manifest['phases'][0]['jobs'][0]['id'], 'job_1')
        self.assertEqual(manifest['phases'][0]['jobs'][1]['expected_output'], 'outputs/2.json')


if __name__ == '__main__':
    unittest.main()
