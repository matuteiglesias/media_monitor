from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from apps.media_watch.monitor import write_wp04_live_proof
from apps.media_watch.store import MediaWatchStore,safe_name

class WP04MediaMaterializationTests(unittest.TestCase):
    def test_real_source_manifest_binds_workflow_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=MediaWatchStore(Path(tmp))
            rid='media-run:abc'
            path=store.runs_dir/safe_name(rid)/'run_manifest.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'schema_name':'media_materialization_run.m1.v1',
                                        'run_id':rid,'failures':0}))
            p=write_wp04_live_proof(store=store,run_id=rid,
                 started_at='2026-10-25T01:00:00Z',finished_at='2026-10-25T01:01:00Z',
                 workflow_run_id=123456)
            content=json.loads(p.read_text())
            self.assertEqual(content['source_kind'],'github_actions')
            self.assertEqual(content['workflow_run_id'],123456)
            self.assertIn('manifest_sha256',content)
            self.assertNotIn('api_key',p.read_text())
            self.assertEqual(p,write_wp04_live_proof(store=store,run_id=rid,
                 started_at='2026-10-25T01:00:00Z',finished_at='2026-10-25T01:01:00Z',
                 workflow_run_id=123456))
    def test_no_missing_or_wrong_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=MediaWatchStore(Path(tmp))
            rid='media-run:abc'
            p=store.runs_dir/safe_name(rid)/'run_manifest.json'
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'schema_name':'media_materialization_run.m1.v1',
                                     'run_id':'unrelated','failures':0}))
            with self.assertRaises(ValueError):
                write_wp04_live_proof(store=store,run_id=rid,
                     started_at='2026-10-25T01:00:00Z',finished_at='2026-10-25T01:01:00Z',
                     workflow_run_id=12345)
