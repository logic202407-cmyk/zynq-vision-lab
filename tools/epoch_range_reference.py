"""Offline two-journal QID reservation reference; no hardware/serial access.

SQLite FULL is not proof of physical power-loss durability or anti-rollback.
Restoring/cloning both journals together is undetectable here: never certify a
motion epoch provider from this module's successful tests.
"""
from pathlib import Path
from contextlib import closing
import sqlite3


class AllocationError(RuntimeError):
    pass


def initialize(primary, witness, namespace, registration):
    """Explicit provisioning, never automatic recovery of missing journals."""
    if not 0 < namespace < 2**64 or not registration.strip():
        raise AllocationError('Registered nonzero namespace and provenance required')
    primary, witness = Path(primary).resolve(), Path(witness).resolve()
    if primary == witness or primary.exists() or witness.exists():
        raise AllocationError('Two distinct fresh journals required')
    # Partial provisioning deliberately remains visible and blocks reserve().
    for path in (primary, witness):
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE epoch(namespace TEXT NOT NULL, reservation INTEGER NOT NULL, registration TEXT NOT NULL)')
            db.execute('INSERT INTO epoch VALUES(?,?,?)', (f'{namespace:016x}', 0, registration))


def reserve(primary, witness, crash_at=None):
    """Burn one complete 2^32-ID range, persist both journals before return.

    crash_at is exception injection for tests, not a power-failure emulator.
    A split commit locks future allocation; no ACK-driven recycling exists.
    """
    paths = [Path(primary).resolve(), Path(witness).resolve()]
    if paths[0] == paths[1] or not all(p.is_file() for p in paths):
        raise AllocationError('Missing or identical journal; no automatic initialize')
    databases = []
    try:
        # Fixed order avoids lock inversion for concurrent callers of one pair.
        for path in sorted(paths):
            db = sqlite3.connect(path, timeout=15, isolation_level=None)
            databases.append(db)
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
        rows = [db.execute('SELECT namespace,reservation,registration FROM epoch').fetchall() for db in databases]
        if len(rows[0]) != 1 or rows[0] != rows[1]:
            raise AllocationError('Journal mismatch/corruption: recovery requires external review')
        namespace, current, registration = rows[0][0]
        if (len(namespace) != 16 or not 0 < int(namespace, 16) < 2**64 or
                type(current) is not int or not 0 <= current < 2**32-1 or not registration.strip()):
            raise AllocationError('Invalid/exhausted reservation')
        following = current+1
        for db in databases:
            db.execute('UPDATE epoch SET reservation=?', (following,))
        if crash_at == 'before_commit':
            raise AllocationError('Injected crash before durable return')
        databases[0].commit()
        if crash_at == 'split_commit':
            raise AllocationError('Injected crash between journal commits')
        databases[1].commit()
        if crash_at == 'after_commit':
            raise AllocationError('Injected loss after commit; interval remains burned')
        start = (int(namespace, 16) << 64) | (following << 32)
        return dict(start=start, end=start+2**32-1, reservation=following,
                    scope='offline_reference', production_ready=False,
                    blockers=['registered namespace uniqueness unproven',
                              'actual media power-loss durability unproven',
                              'simultaneous rollback/clone of both journals undetectable',
                              'trusted atomic PL handoff and reset-generation binding missing'])
    except (sqlite3.Error, ValueError, TypeError) as error:
        raise AllocationError('Invalid journal: '+type(error).__name__) from error
    finally:
        for db in databases:
            db.close()  # Uncommitted transactions roll back; committed ranges never recycle.
