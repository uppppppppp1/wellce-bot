import os
import time
import random
import datetime
import hashlib
import xml.etree.ElementTree as ET
import uiautomator2 as u2
from dotenv import load_dotenv

load_dotenv()

# ── Replace these with real resource-ids found via discover_ui.py ──
APP_PACKAGE = "com.wellcee.app"          # replace with actual package name
RID_COMMUNITY_TAB = ""                   # resource-id of community tab in nav bar
RID_RECOMMEND_TAB = ""                   # resource-id of 推荐 tab
RID_ROOMMATE_TAB = ""                    # resource-id of 蹲室友 tab
RID_POST_FAB = ""                        # resource-id of 发布 floating button
RID_POST_INPUT = ""                      # resource-id of post text input
RID_POST_SUBMIT = ""                     # resource-id of post submit/publish button
RID_COMMENT_INPUT = ""                   # resource-id of comment text input
RID_COMMENT_SUBMIT = ""                  # resource-id of comment send button
RID_DM_INPUT = ""                        # resource-id of DM message input
RID_DM_SEND = ""                         # resource-id of DM send button
# ──────────────────────────────────────────────────────────────────


def _connect() -> u2.Device:
    device_id = os.getenv("DEVICE_ID")
    return u2.connect(device_id) if device_id else u2.connect()


def _rand_sleep(lo=1.5, hi=4.0):
    time.sleep(random.uniform(lo, hi))


def _type_text(d: u2.Device, rid: str, text: str):
    """Type text character by character to mimic human input."""
    el = d(resourceId=rid)
    el.click()
    time.sleep(0.5)
    for char in text:
        d.send_keys(char, clear=False)
        time.sleep(random.uniform(0.05, 0.15))


def _screenshot(d: u2.Device, label: str) -> str:
    os.makedirs("screenshots", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"screenshots/{ts}_{label}.png"
    d.screenshot(path)
    print(f"[screenshot] {path}")
    return path


def ensure_wellcee_open(d: u2.Device):
    """Launch Wellcee if not already in foreground."""
    current = d.app_current()
    if current.get("package") != APP_PACKAGE:
        d.app_start(APP_PACKAGE)
        time.sleep(3)


def navigate_to_section(d: u2.Device, section: str):
    """Navigate to 推荐 or 蹲室友 tab inside community."""
    ensure_wellcee_open(d)
    _rand_sleep()
    d(resourceId=RID_COMMUNITY_TAB).click()
    _rand_sleep()
    if section == "蹲室友":
        d(resourceId=RID_ROOMMATE_TAB).click()
    else:
        d(resourceId=RID_RECOMMEND_TAB).click()
    _rand_sleep()


def post_content(section: str, text: str) -> str:
    """Post a new community post. Returns screenshot path."""
    d = _connect()
    navigate_to_section(d, section)
    d(resourceId=RID_POST_FAB).click()
    _rand_sleep()
    _type_text(d, RID_POST_INPUT, text)
    _rand_sleep()
    d(resourceId=RID_POST_SUBMIT).click()
    _rand_sleep(2, 5)
    path = _screenshot(d, f"post_{section}")
    return path


def scrape_post_texts(section: str, limit: int = 20) -> list[dict]:
    """
    Scrape visible post texts from the feed.
    Returns list of {"id": str, "text": str}.
    Uses text hash as stable ID since Wellcee doesn't expose post IDs in UI.
    """
    d = _connect()
    navigate_to_section(d, section)
    _rand_sleep()

    posts = []
    seen_texts = set()

    for _ in range(4):
        xml = d.dump_hierarchy()
        root = ET.fromstring(xml)
        for node in root.iter():
            text = node.attrib.get("text", "").strip()
            if len(text) > 20 and text not in seen_texts:
                seen_texts.add(text)
                post_id = hashlib.md5(text.encode()).hexdigest()[:12]
                posts.append({"id": post_id, "text": text})
                if len(posts) >= limit:
                    return posts
        d.swipe(0.5, 0.7, 0.5, 0.3, duration=0.5)
        _rand_sleep(1.5, 3.0)

    return posts


def reply_to_post(post_text: str, reply_text: str) -> str:
    """Tap on a post matching post_text, type reply, submit. Returns screenshot path."""
    d = _connect()
    _rand_sleep()
    d(text=post_text[:30]).click()
    _rand_sleep()
    _type_text(d, RID_COMMENT_INPUT, reply_text)
    _rand_sleep()
    d(resourceId=RID_COMMENT_SUBMIT).click()
    _rand_sleep(2, 4)
    path = _screenshot(d, "reply")
    d.press("back")
    _rand_sleep()
    return path


def scrape_unread_dms() -> list[dict]:
    """Navigate to DM inbox, scrape unread conversations. Returns list of {"id": str, "preview": str}."""
    d = _connect()
    ensure_wellcee_open(d)
    _rand_sleep()
    d(description="消息").click()
    _rand_sleep()

    dms = []
    xml = d.dump_hierarchy()
    root = ET.fromstring(xml)
    for node in root.iter():
        text = node.attrib.get("text", "").strip()
        if len(text) > 5:
            dm_id = hashlib.md5(text.encode()).hexdigest()[:12]
            dms.append({"id": dm_id, "preview": text})
    return dms[:20]


def reply_to_dm(dm_preview: str, reply_text: str) -> str:
    """Open a DM thread matching dm_preview, send reply_text. Returns screenshot path."""
    d = _connect()
    _rand_sleep()
    d(text=dm_preview[:20]).click()
    _rand_sleep()
    _type_text(d, RID_DM_INPUT, reply_text)
    _rand_sleep()
    d(resourceId=RID_DM_SEND).click()
    _rand_sleep(2, 4)
    path = _screenshot(d, "dm_reply")
    d.press("back")
    _rand_sleep()
    return path
