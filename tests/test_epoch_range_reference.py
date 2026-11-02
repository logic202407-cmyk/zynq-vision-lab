from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from tools.epoch_range_reference import AllocationError, initialize, reserve


class EpochRangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.a = Path(self.temp.name)/'a.db'
        self.b = Path(self.temp.name)/'b.db'
        initialize(self.a, self.b, 0x1234, 'synthetic registry fixture; NOT a device assignment')

    def test_monotonic_disjoint_and_never_production_certificate(self):
        first, second = reserve(self.a,self.b), reserve(self.a,self.b)
        self.assertLess(first['end'], second['start'])
        self.assertEqual(first['end']-first['start']+1, 2**32)
        self.assertFalse(first['production_ready'])

    def test_concurrent_nonoverlapping(self):
        with ThreadPoolExecutor(max_workers=4) as workers:
            grants = sorted(workers.map(lambda _: reserve(self.a,self.b)['start'], range(8)))
        self.assertEqual(len(set(grants)),8)
        self.assertTrue(all(b-a==2**32 for a,b in zip(grants,grants[1:])))

    def test_before_commit_no_delivery_no_reservation(self):
        with self.assertRaises(AllocationError): reserve(self.a,self.b,'before_commit')
        self.assertEqual(reserve(self.a,self.b)['reservation'],1)

    def test_split_commit_fail_closed(self):
        with self.assertRaises(AllocationError): reserve(self.a,self.b,'split_commit')
        with self.assertRaises(AllocationError): reserve(self.a,self.b)

    def test_after_commit_or_lost_ack_burns_range(self):
        with self.assertRaises(AllocationError): reserve(self.a,self.b,'after_commit')
        self.assertEqual(reserve(self.a,self.b)['reservation'],2)

    def test_single_journal_rollback_detected(self):
        backup=self.a.with_suffix('.old');shutil.copy2(self.a,backup)
        reserve(self.a,self.b);shutil.copy2(backup,self.a)
        with self.assertRaises(AllocationError):reserve(self.a,self.b)

    def test_double_rollback_is_explicit_unresolved_blocker(self):
        old_a=self.a.with_suffix('.old');old_b=self.b.with_suffix('.old')
        shutil.copy2(self.a,old_a);shutil.copy2(self.b,old_b)
        prior=reserve(self.a,self.b)
        shutil.copy2(old_a,self.a);shutil.copy2(old_b,self.b)
        replay=reserve(self.a,self.b)
        self.assertEqual(prior['start'],replay['start'])
        self.assertFalse(replay['production_ready'])
        self.assertTrue(any('undetectable' in b for b in replay['blockers']))

    def test_missing_and_corrupt_never_auto_reinitialized(self):
        self.a.unlink()
        with self.assertRaises(AllocationError):reserve(self.a,self.b)
        self.assertFalse(self.a.exists())
        self.a.write_bytes(b'not a database')
        with self.assertRaises(AllocationError):reserve(self.a,self.b)

    def test_exhaustion_never_wraps(self):
        for path in (self.a,self.b):
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('UPDATE epoch SET reservation=?',(2**32-1,))
        with self.assertRaises(AllocationError):reserve(self.a,self.b)

    def test_provisioning_cannot_overwrite(self):
        with self.assertRaises(AllocationError):initialize(self.a,self.b,0x9999,'fixture')
