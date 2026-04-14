"""Tests for figwatch.ack_updater — AckUpdater background worker.

These tests stub out the real Figma API (post_ack / delete_ack) by
monkeypatching the ack_updater module so no network calls happen.
"""

import threading
import time
from types import SimpleNamespace

import pytest

from figwatch.ack_updater import AckUpdater, PendingUpdate, _position_message
from figwatch.queue_stats import InstrumentedQueue, QueuedItem


# ── Helpers ───────────────────────────────────────────────────────────

def _make_item(trigger='@ux', node_id='1:2', file_key='abc'):
    return SimpleNamespace(
        trigger=trigger,
        node_id=node_id,
        file_key=file_key,
        reply_to_id='111',
        pat='figd_test',
    )


def _queued(audit_id, ack_id='ack-0'):
    return QueuedItem(
        item=_make_item(),
        ack_id=ack_id,
        audit_id=audit_id,
    )


class _AckStub:
    """Monkeypatch target that records delete/post calls and hands out
    predictable ack ids.
    """

    def __init__(self):
        self.posts = []
        self.deletes = []
        self._counter = 0

    def post_ack(self, item, message):
        self._counter += 1
        new_id = f'ack-{self._counter}'
        self.posts.append({'item': item, 'message': message, 'ack_id': new_id})
        return new_id

    def delete_ack(self, item, ack_id):
        if ack_id is not None:
            self.deletes.append({'item': item, 'ack_id': ack_id})


@pytest.fixture
def stub(monkeypatch):
    s = _AckStub()
    monkeypatch.setattr('figwatch.ack_updater.post_ack', s.post_ack)
    monkeypatch.setattr('figwatch.ack_updater.delete_ack', s.delete_ack)
    return s


# ── _position_message formatting ─────────────────────────────────────

def test_position_message_zero():
    msg = _position_message('@ux', 0)
    assert 'starting shortly' in msg
    assert 'ux' in msg


def test_position_message_one():
    assert '1 ahead of you' in _position_message('@ux', 1)


def test_position_message_many():
    assert '5 ahead of you' in _position_message('@tone', 5)
    assert 'tone' in _position_message('@tone', 5)


def test_position_message_strips_trigger_prefix():
    assert '@ux' not in _position_message('@ux', 2)


# ── Public API surface ───────────────────────────────────────────────

def test_track_initial_records_position():
    q = InstrumentedQueue()
    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater.track_initial('abc', position=3)
    assert updater._displayed['abc'] == 3


def test_cancel_removes_tracking():
    q = InstrumentedQueue()
    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater.track_initial('abc', position=2)
    updater.cancel('abc')
    assert 'abc' not in updater._displayed
    assert 'abc' not in updater._pending


def test_rate_zero_disables_thread():
    q = InstrumentedQueue()
    updater = AckUpdater(q, rate_per_minute=0)
    updater.start()
    assert updater._thread is None
    updater.stop()


# ── _refresh_pending (position change detection) ─────────────────────

def test_refresh_skips_items_at_their_displayed_position(stub):
    q = InstrumentedQueue()
    q.put(_queued('a'))
    q.put(_queued('b'))
    q.put(_queued('c'))

    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater.track_initial('a', position=0)
    updater.track_initial('b', position=1)
    updater.track_initial('c', position=2)

    updater._refresh_pending()
    assert updater._pending == {}


def test_refresh_schedules_update_when_position_moves(stub):
    q = InstrumentedQueue()
    q.put(_queued('a'))
    q.put(_queued('b'))
    q.put(_queued('c'))

    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater.track_initial('a', position=0)
    updater.track_initial('b', position=1)
    updater.track_initial('c', position=2)

    # Remove 'a' — positions shift: b is now 0, c is now 1
    q.get(timeout=1)
    updater._refresh_pending()

    assert 'b' in updater._pending
    assert 'c' in updater._pending
    assert updater._pending['b'].new_position == 0
    assert updater._pending['c'].new_position == 1


def test_refresh_coalesces_multiple_updates_for_same_audit(stub):
    q = InstrumentedQueue()
    q.put(_queued('a'))
    q.put(_queued('b'))
    q.put(_queued('c'))
    q.put(_queued('d'))

    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater.track_initial('a', position=0)
    updater.track_initial('b', position=1)
    updater.track_initial('c', position=2)
    updater.track_initial('d', position=3)

    # First refresh: nothing pending
    updater._refresh_pending()
    assert updater._pending == {}

    # Remove 'a' — d moves from position 3 to 2
    q.get(timeout=1)
    updater._refresh_pending()
    assert updater._pending['d'].new_position == 2

    # Remove 'b' — d moves from 2 to 1 BEFORE the previous update fires
    q.get(timeout=1)
    updater._refresh_pending()
    # Only one entry for 'd', and it holds the latest position (1)
    assert updater._pending['d'].new_position == 1


def test_refresh_cleans_up_stale_displayed_entries(stub):
    q = InstrumentedQueue()
    q.put(_queued('a'))

    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater.track_initial('a', position=0)
    # Simulate a stale entry for an item that's already gone from the queue
    updater._displayed['ghost'] = 2
    updater._pending['ghost'] = PendingUpdate(
        audit_id='ghost', new_position=1, queued=_queued('ghost'),
    )

    updater._refresh_pending()
    assert 'ghost' not in updater._displayed
    assert 'ghost' not in updater._pending


# ── _post_one (actual ack update posting) ────────────────────────────

def test_post_one_posts_pending_update(stub):
    q = InstrumentedQueue()
    queued = _queued('a', ack_id='ack-0')
    q.put(queued)

    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater._pending['a'] = PendingUpdate(
        audit_id='a', new_position=2, queued=queued,
    )

    updater._post_one()
    assert len(stub.posts) == 1
    assert len(stub.deletes) == 1
    assert stub.deletes[0]['ack_id'] == 'ack-0'
    assert '2 ahead' in stub.posts[0]['message']
    # ack_id rewritten on the QueuedItem
    assert queued.ack_id == 'ack-1'
    # displayed position updated
    assert updater._displayed['a'] == 2


def test_post_one_skips_if_audit_no_longer_queued(stub):
    q = InstrumentedQueue()
    queued = _queued('a')
    # Don't put it in the queue — find('a') will return None

    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater._pending['a'] = PendingUpdate(
        audit_id='a', new_position=1, queued=queued,
    )

    updater._post_one()
    assert stub.posts == []
    assert stub.deletes == []


def test_post_one_noops_when_pending_empty(stub):
    q = InstrumentedQueue()
    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater._post_one()
    assert stub.posts == []


def test_post_one_respects_rate_limit(stub):
    q = InstrumentedQueue()
    for audit_id in ('a', 'b', 'c'):
        q.put(_queued(audit_id))

    # Rate = 1 per minute, capacity = 1. First post consumes the token,
    # second post should be throttled (re-queued).
    updater = AckUpdater(q, rate_per_minute=1, poll_seconds=0.01)
    updater._pending['a'] = PendingUpdate(
        audit_id='a', new_position=1, queued=q.find('a'),
    )
    updater._pending['b'] = PendingUpdate(
        audit_id='b', new_position=2, queued=q.find('b'),
    )

    updater._post_one()
    assert len(stub.posts) == 1

    updater._post_one()
    assert len(stub.posts) == 1  # throttled
    assert 'b' in updater._pending  # re-queued


# ── End-to-end: start / stop thread ──────────────────────────────────

def test_start_stop_thread_runs_cleanly(stub):
    q = InstrumentedQueue()
    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater.start()
    assert updater._thread is not None
    assert updater._thread.is_alive()
    updater.stop()
    assert updater._thread is None


def test_thread_posts_updates_when_queue_moves(stub):
    q = InstrumentedQueue()
    q.put(_queued('a'))
    q.put(_queued('b'))
    q.put(_queued('c'))

    updater = AckUpdater(q, rate_per_minute=60, poll_seconds=0.01)
    updater.track_initial('a', position=0)
    updater.track_initial('b', position=1)
    updater.track_initial('c', position=2)
    updater.start()

    try:
        # Remove 'a' — positions shift
        q.get(timeout=1)
        # Wait for the updater to notice and post updates
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if len(stub.posts) >= 2:
                break
            time.sleep(0.02)
    finally:
        updater.stop()

    assert len(stub.posts) >= 2
    positions = [p['message'] for p in stub.posts]
    # Expect one post for b (position 0 → 'starting shortly') and one for c
    # (position 1 → '1 ahead of you')
    assert any('starting shortly' in m for m in positions)
    assert any('1 ahead of you' in m for m in positions)
