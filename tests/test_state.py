import os, json, pytest
from state import load_state, save_state, mark_replied, mark_dm_replied, increment_post_count, reset_daily

STATE_FILE = "test_state_tmp.json"

@pytest.fixture(autouse=True)
def cleanup():
    yield
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

def test_load_state_creates_default():
    s = load_state(STATE_FILE)
    assert s["posts_today"] == 0
    assert s["replied_ids"] == []
    assert s["dm_replied_ids"] == []
    assert "date" in s

def test_increment_post_count():
    s = load_state(STATE_FILE)
    s = increment_post_count(s)
    save_state(s, STATE_FILE)
    s2 = load_state(STATE_FILE)
    assert s2["posts_today"] == 1

def test_mark_replied():
    s = load_state(STATE_FILE)
    s = mark_replied(s, "post_abc")
    save_state(s, STATE_FILE)
    s2 = load_state(STATE_FILE)
    assert "post_abc" in s2["replied_ids"]

def test_mark_dm_replied():
    s = load_state(STATE_FILE)
    s = mark_dm_replied(s, "dm_xyz")
    save_state(s, STATE_FILE)
    s2 = load_state(STATE_FILE)
    assert "dm_xyz" in s2["dm_replied_ids"]

def test_reset_daily_clears_posts():
    s = load_state(STATE_FILE)
    s = increment_post_count(s)
    s = increment_post_count(s)
    s = reset_daily(s)
    assert s["posts_today"] == 0
    assert s["replied_ids"] == []
