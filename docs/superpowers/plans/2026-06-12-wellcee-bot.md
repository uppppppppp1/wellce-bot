# Wellcee Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully automated Wellcee community bot that posts 3 times daily, auto-replies to posts, and auto-replies to DMs using a consistent persona ("小林"), driven by GPT-4o and Android UI automation via uiautomator2.

**Architecture:** A Python APScheduler process runs on Windows, calls GPT-4o (via OpenAI-compatible API) to generate persona-consistent content, then drives a connected Android phone running the Wellcee app via uiautomator2/ADB. State is persisted in `state.json` to prevent duplicate posts/replies.

**Tech Stack:** Python 3.10+, uiautomator2, APScheduler 3.x, openai SDK 1.x, python-dotenv, ADB (Android Debug Bridge)

---

## File Map

| File | Responsibility |
|------|---------------|
| `.env` | Secrets and config (API key, base URL, model, ADB device ID) |
| `requirements.txt` | Python dependencies |
| `state.py` | Load/save `state.json`; track posted count, replied IDs, DM IDs |
| `content.py` | Call GPT-4o to generate post text and reply decisions |
| `poster.py` | uiautomator2 device connection, UI navigation, post/reply/DM actions |
| `scheduler.py` | APScheduler job definitions for posting, reply scanning, DM scanning |
| `main.py` | Entry point; initializes scheduler and blocks |
| `state.json` | Runtime state (auto-created on first run) |
| `screenshots/` | Auto-created directory; one PNG per action |

---

## Task 1: Project Scaffold and Dependencies

**Files:**
- Create: `C:/Users/25962/workspace/wellcee-bot/requirements.txt`
- Create: `C:/Users/25962/workspace/wellcee-bot/.env`
- Create: `C:/Users/25962/workspace/wellcee-bot/.gitignore`

- [ ] **Step 1: Create requirements.txt**

```
uiautomator2>=2.16.0
APScheduler>=3.10.4
openai>=1.0.0
python-dotenv>=1.0.0
```

- [ ] **Step 2: Create .env with your credentials**

```
OPENAI_API_KEY=sk-YRp4EKtR9o4wboT3YEHNSjQonhBzyJAraqCr3tA16WOR3q5Z
OPENAI_BASE_URL=https://api.innospark.cn/v1
MODEL_NAME=gpt-4o
DEVICE_ID=
```

Leave `DEVICE_ID` blank for now — filled after connecting phone in Task 5.

- [ ] **Step 3: Create .gitignore**

```
.env
state.json
screenshots/
__pycache__/
*.pyc
```

- [ ] **Step 4: Install dependencies**

```bash
cd C:/Users/25962/workspace/wellcee-bot
pip install -r requirements.txt
```

Expected: All packages install without error. uiautomator2 may print a note about `weditor`.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/25962/workspace/wellcee-bot
git init
git add requirements.txt .gitignore
git commit -m "feat: project scaffold"
```

---

## Task 2: State Management (`state.py`)

**Files:**
- Create: `C:/Users/25962/workspace/wellcee-bot/state.py`
- Create: `C:/Users/25962/workspace/wellcee-bot/tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/__init__.py` (empty), then `tests/test_state.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/25962/workspace/wellcee-bot
pytest tests/test_state.py -v
```

Expected: `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 3: Implement state.py**

```python
import json
import os
from datetime import date

DEFAULT_STATE = {
    "date": str(date.today()),
    "posts_today": 0,
    "replied_ids": [],
    "dm_replied_ids": [],
}

def load_state(path="state.json") -> dict:
    if not os.path.exists(path):
        return DEFAULT_STATE.copy()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state: dict, path="state.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def increment_post_count(state: dict) -> dict:
    state["posts_today"] = state.get("posts_today", 0) + 1
    return state

def mark_replied(state: dict, post_id: str) -> dict:
    if post_id not in state["replied_ids"]:
        state["replied_ids"].append(post_id)
    return state

def mark_dm_replied(state: dict, dm_id: str) -> dict:
    if dm_id not in state["dm_replied_ids"]:
        state["dm_replied_ids"].append(dm_id)
    return state

def reset_daily(state: dict) -> dict:
    state["date"] = str(date.today())
    state["posts_today"] = 0
    state["replied_ids"] = []
    return state
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_state.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add state.py tests/
git commit -m "feat: state management module"
```

---

## Task 3: Content Generation (`content.py`)

**Files:**
- Create: `C:/Users/25962/workspace/wellcee-bot/content.py`
- Create: `C:/Users/25962/workspace/wellcee-bot/tests/test_content.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from unittest.mock import patch, MagicMock
from content import generate_post, generate_reply

MOCK_POST_TEXT = "今天通勤路上看到弄堂口奶奶喂猫 ☕ #上海生活 #打工人"
MOCK_REPLY_JSON = '{"should_reply": true, "reply": "哈哈同感，长宁的街道真的很治愈😊"}'
MOCK_SKIP_JSON = '{"should_reply": false, "reply": ""}'

def make_mock_client(content):
    mock_msg = MagicMock()
    mock_msg.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    return mock_client

def test_generate_post_returns_string():
    client = make_mock_client(MOCK_POST_TEXT)
    result = generate_post(client, "早晨", "推荐", [])
    assert isinstance(result, str)
    assert len(result) > 10

def test_generate_post_passes_context():
    client = make_mock_client(MOCK_POST_TEXT)
    generate_post(client, "午间", "蹲室友", ["早餐"])
    call_args = client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    user_msg = next(m["content"] for m in messages if m["role"] == "user")
    assert "蹲室友" in user_msg
    assert "早餐" in user_msg

def test_generate_reply_should_reply():
    client = make_mock_client(MOCK_REPLY_JSON)
    should_reply, reply_text = generate_reply(client, "今天在长宁看到个很可爱的猫")
    assert should_reply is True
    assert len(reply_text) > 0

def test_generate_reply_should_skip():
    client = make_mock_client(MOCK_SKIP_JSON)
    should_reply, reply_text = generate_reply(client, "出租房源中介联系")
    assert should_reply is False
    assert reply_text == ""
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_content.py -v
```

Expected: `ModuleNotFoundError: No module named 'content'`

- [ ] **Step 3: Implement content.py**

```python
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """你是"小林"，26岁互联网产品经理，广东人，在上海长宁区独自打拼2年。
性格随和、偶尔丧但不颓废，爱观察生活细节，不矫情。
熟悉上海长宁/静安/徐汇一带。

写作风格：
- 口语化中文，适量网络用语（属实、破防、整活）
- 每条帖子 2-4 个 emoji，不堆砌
- 结尾带 3-5 个 hashtag
- 内容真实，偶尔有点小丧，不永远正能量

禁止：推广产品、政治话题、回复中介帖。"""


def make_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )


def generate_post(client: OpenAI, time_slot: str, section: str, posted_topics: list[str]) -> str:
    topics_str = "、".join(posted_topics) if posted_topics else "无"
    roommate_note = "内容围绕找室友、合租经验、上海租房，真实具体。" if section == "蹲室友" else ""
    user_prompt = f"""现在是{time_slot}，发布板块：{section}。
今天已发的主题：{topics_str}。

请以小林的身份，写一条适合发在 Wellcee 社区{section}板块的帖子。
要求：
- 100-200 字，贴近真实上海打工人的生活感受
- 不要和今天已发内容重复
- {roommate_note}
- 结尾加 3-5 个相关 hashtag
- 只输出帖子正文，不要任何解释"""

    resp = client.chat.completions.create(
        model=os.getenv("MODEL_NAME", "gpt-4o"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
    )
    return resp.choices[0].message.content.strip()


def generate_reply(client: OpenAI, post_text: str) -> tuple[bool, str]:
    user_prompt = f"""以下是 Wellcee 社区的一条帖子：
---
{post_text}
---

首先判断是否适合小林回复。跳过条件（满足任意一条即跳过）：
- 中介广告或房源推广
- 出闲置/卖东西的帖子
- 无实质内容的水帖
- 内容与上海生活完全无关

如果适合回复，以小林身份写一条自然回复：
- 30-60 字，口语化，有实质内容
- 如果帖子明显是外国用户发的（英文或混合语言），可以用简单英文回复

输出格式（严格 JSON，不要其他内容）：
{{"should_reply": true/false, "reply": "回复内容或空字符串"}}"""

    resp = client.chat.completions.create(
        model=os.getenv("MODEL_NAME", "gpt-4o"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )
    raw = resp.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)
    return data["should_reply"], data.get("reply", "")


def generate_dm_reply(client: OpenAI, dm_text: str) -> str:
    user_prompt = f"""以下是一条发给小林的私信：
---
{dm_text}
---

以小林身份回复这条私信，要求：
- 40-80 字，友好自然，像真人聊天
- 如果是找室友咨询，给出真实建议
- 如果是无意义骚扰，礼貌结束对话
- 只输出回复内容，不要解释"""

    resp = client.chat.completions.create(
        model=os.getenv("MODEL_NAME", "gpt-4o"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
    )
    return resp.choices[0].message.content.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_content.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add content.py tests/test_content.py
git commit -m "feat: content generation with GPT-4o"
```

---

## Task 4: UI Element Discovery (One-time Setup)

Before writing `poster.py`, you need the real resource-ids of Wellcee's UI elements. This task does that interactively.

**Files:**
- Create: `C:/Users/25962/workspace/wellcee-bot/discover_ui.py` (temporary helper, deleted after Task 5)

- [ ] **Step 1: Connect Android phone via USB**

On the phone:
1. Settings → About Phone → tap Build Number 7 times to enable Developer Mode
2. Settings → Developer Options → enable USB Debugging
3. Connect USB cable to PC

Verify ADB sees the device:
```bash
adb devices
```
Expected output (example):
```
List of devices attached
R58MA3LXNQE     device
```
Copy the device serial (e.g. `R58MA3LXNQE`) — you'll need it for `.env`.

- [ ] **Step 2: Install uiautomator2 server on phone**

```bash
python -m uiautomator2 init
```
Expected: "Successfully installed UIAutomator server"

- [ ] **Step 3: Update .env with DEVICE_ID**

Open `.env` and set:
```
DEVICE_ID=R58MA3LXNQE
```
(Replace with your actual device serial from Step 1)

- [ ] **Step 4: Create discover_ui.py**

```python
"""Run this script to discover Wellcee UI element resource-ids interactively.
Navigate the app to the screen you want to inspect, then press Enter."""
import uiautomator2 as u2
import os
from dotenv import load_dotenv

load_dotenv()
device_id = os.getenv("DEVICE_ID")
d = u2.connect(device_id) if device_id else u2.connect()

print("Connected to:", d.info["productName"])
print("\nNavigate Wellcee app to the screen you want to inspect, then press Enter.")

while True:
    input("\n[Enter] to dump UI hierarchy (Ctrl+C to quit): ")
    xml = d.dump_hierarchy()
    # Print all resource-ids and their text
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    for node in root.iter():
        rid = node.attrib.get("resource-id", "")
        text = node.attrib.get("text", "")
        desc = node.attrib.get("content-desc", "")
        cls = node.attrib.get("class", "")
        if rid or text or desc:
            print(f"  [{cls}] id={rid!r} text={text!r} desc={desc!r}")
```

- [ ] **Step 5: Run discover_ui.py and navigate Wellcee to each key screen**

```bash
python discover_ui.py
```

Navigate to each screen below and press Enter to dump. Record the resource-ids you find:

| Screen | What to look for |
|--------|-----------------|
| Community main tab | Tab bar buttons (推荐/蹲室友 tabs), "发布" FAB button |
| Post compose screen | Text input field, publish/send button |
| Individual post view | Comment input field, send comment button |
| Messages/DM list | Each DM conversation row |
| DM conversation | Message input field, send button |

Write down the resource-ids. You'll use them in Task 5.

- [ ] **Step 6: Note the app package name**

```bash
adb shell "dumpsys window | grep mCurrentFocus"
```
While Wellcee is open, this prints something like:
```
mCurrentFocus=Window{... com.wellcee.app/com.wellcee.MainActivity}
```
The package name is `com.wellcee.app` (or similar). Record it.

---

## Task 5: Mobile Automation (`poster.py`)

**Files:**
- Create: `C:/Users/25962/workspace/wellcee-bot/poster.py`

Replace all `RESOURCE_ID_*` constants below with the actual values discovered in Task 4.

- [ ] **Step 1: Create poster.py**

```python
import os
import time
import random
import datetime
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


def _screenshot(d: u2.Device, label: str):
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
    # Tap community tab in bottom nav
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
    Since Wellcee doesn't expose stable post IDs in UI, we use text hash as ID.
    """
    import hashlib
    d = _connect()
    navigate_to_section(d, section)
    _rand_sleep()

    posts = []
    seen_texts = set()

    # Scroll through feed collecting post text nodes
    for _ in range(4):
        xml = d.dump_hierarchy()
        import xml.etree.ElementTree as ET
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
    """
    Tap on a post matching post_text, type reply, submit.
    Returns screenshot path.
    """
    d = _connect()
    _rand_sleep()
    # Find and tap the post by its text
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
    """
    Navigate to DM inbox, scrape unread conversations.
    Returns list of {"id": str, "preview": str}.
    """
    import hashlib
    d = _connect()
    ensure_wellcee_open(d)
    _rand_sleep()
    # Navigate to messages — tap profile/message icon
    # Adjust selector to match actual UI
    d(description="消息").click()
    _rand_sleep()

    dms = []
    xml = d.dump_hierarchy()
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    for node in root.iter():
        text = node.attrib.get("text", "").strip()
        if len(text) > 5:
            dm_id = hashlib.md5(text.encode()).hexdigest()[:12]
            dms.append({"id": dm_id, "preview": text})
    return dms[:20]


def reply_to_dm(dm_preview: str, reply_text: str) -> str:
    """Open a DM thread matching dm_preview, send reply_text."""
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
```

- [ ] **Step 2: Fill in all RESOURCE_ID constants**

Open `poster.py` and replace every `""` constant with the real resource-id strings you recorded in Task 4. For example:
```python
APP_PACKAGE = "com.wellcee.app"
RID_COMMUNITY_TAB = "com.wellcee.app:id/tab_community"
RID_POST_FAB = "com.wellcee.app:id/fab_post"
# ... etc
```

- [ ] **Step 3: Smoke test post_content manually**

```bash
python -c "
from poster import post_content
path = post_content('推荐', '测试帖子，请忽略 🙏 #测试')
print('Screenshot saved:', path)
"
```

Expected: Wellcee app opens, post compose screen appears, text is typed, post is submitted, screenshot saved to `screenshots/`.

**If a resource-id is wrong:** Re-run `discover_ui.py` on that specific screen and update the constant.

- [ ] **Step 4: Commit**

```bash
git add poster.py
git commit -m "feat: uiautomator2 mobile automation layer"
```

---

## Task 6: Scheduler (`scheduler.py` + `main.py`)

**Files:**
- Create: `C:/Users/25962/workspace/wellcee-bot/scheduler.py`
- Create: `C:/Users/25962/workspace/wellcee-bot/main.py`

- [ ] **Step 1: Create scheduler.py**

```python
import random
import logging
from datetime import datetime, date
from apscheduler.schedulers.blocking import BlockingScheduler
from content import make_client, generate_post, generate_reply, generate_dm_reply
from poster import post_content, scrape_post_texts, reply_to_post, scrape_unread_dms, reply_to_dm
from state import load_state, save_state, increment_post_count, mark_replied, mark_dm_replied, reset_daily

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Post schedule: (hour, minute, section, time_slot_label)
POST_SCHEDULE = [
    (9,  0,  "推荐",  "早晨"),
    (12, 30, "蹲室友", "午间"),
    (20, 0,  "推荐",  "晚间"),
]

MAX_REPLIES_PER_DAY = 10
MAX_DM_REPLIES_PER_HOUR = 20


def _jitter_minutes() -> int:
    return random.randint(-10, 10)


def job_post(section: str, time_slot: str):
    state = load_state()
    # Reset if new day
    if state.get("date") != str(date.today()):
        state = reset_daily(state)
        save_state(state)

    if state["posts_today"] >= 3:
        log.info("Already posted 3 times today, skipping.")
        return

    client = make_client()
    posted_topics = state.get("posted_topics", [])
    text = generate_post(client, time_slot, section, posted_topics)
    log.info(f"[POST] section={section}\n{text}")

    path = post_content(section, text)
    log.info(f"[POST] Screenshot: {path}")

    state = increment_post_count(state)
    # Track topic summary (first 20 chars) to avoid repetition
    state.setdefault("posted_topics", []).append(text[:20])
    save_state(state)


def job_scan_replies():
    state = load_state()
    if state.get("date") != str(date.today()):
        state = reset_daily(state)
        save_state(state)

    replied_today = len(state.get("replied_ids", []))
    if replied_today >= MAX_REPLIES_PER_DAY:
        log.info("Reply limit reached for today.")
        return

    client = make_client()
    for section in ["推荐", "蹲室友"]:
        posts = scrape_post_texts(section, limit=20)
        for post in posts:
            if post["id"] in state["replied_ids"]:
                continue
            should_reply, reply_text = generate_reply(client, post["text"])
            if not should_reply or not reply_text:
                continue
            log.info(f"[REPLY] post_id={post['id']}\nreply: {reply_text}")
            reply_to_post(post["text"], reply_text)
            state = mark_replied(state, post["id"])
            save_state(state)
            replied_today += 1
            if replied_today >= MAX_REPLIES_PER_DAY:
                return


def job_scan_dms():
    state = load_state()
    client = make_client()
    dms = scrape_unread_dms()
    replied_count = 0

    for dm in dms:
        if dm["id"] in state.get("dm_replied_ids", []):
            continue
        reply_text = generate_dm_reply(client, dm["preview"])
        log.info(f"[DM] dm_id={dm['id']}\nreply: {reply_text}")
        reply_to_dm(dm["preview"], reply_text)
        state = mark_dm_replied(state, dm["id"])
        save_state(state)
        replied_count += 1
        if replied_count >= MAX_DM_REPLIES_PER_HOUR:
            break


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler()

    for hour, minute, section, time_slot in POST_SCHEDULE:
        jitter = _jitter_minutes()
        adj_minute = (minute + jitter) % 60
        adj_hour = hour + ((minute + jitter) // 60)
        scheduler.add_job(
            job_post,
            "cron",
            hour=adj_hour,
            minute=adj_minute,
            args=[section, time_slot],
            id=f"post_{section}_{hour}",
        )
        log.info(f"Scheduled post: section={section} at {adj_hour:02d}:{adj_minute:02d}")

    # Reply scan every 30 minutes, DM scan every hour
    scheduler.add_job(job_scan_replies, "interval", minutes=30, id="scan_replies")
    scheduler.add_job(job_scan_dms, "interval", hours=1, id="scan_dms")

    return scheduler
```

- [ ] **Step 2: Create main.py**

```python
import logging
from scheduler import build_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if __name__ == "__main__":
    print("Wellcee Bot starting...")
    scheduler = build_scheduler()
    print("Scheduler running. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("Bot stopped.")
```

- [ ] **Step 3: Verify scheduler builds without error**

```bash
python -c "from scheduler import build_scheduler; s = build_scheduler(); print('Jobs:', [j.id for j in s.get_jobs()])"
```

Expected output:
```
Jobs: ['post_推荐_9', 'post_蹲室友_12', 'post_推荐_20', 'scan_replies', 'scan_dms']
```

- [ ] **Step 4: Commit**

```bash
git add scheduler.py main.py
git commit -m "feat: APScheduler job definitions"
```

---

## Task 7: End-to-End Smoke Test

- [ ] **Step 1: Run a manual post job to verify full pipeline**

```bash
python -c "
from scheduler import job_post
job_post('推荐', '早晨')
"
```

Watch the phone screen. Expected sequence:
1. Wellcee app comes to foreground
2. Community tab is tapped
3. 推荐 tab is selected
4. 发布 button is tapped
5. Text is typed character by character
6. Post is submitted
7. Screenshot appears in `screenshots/`

- [ ] **Step 2: Run a manual reply scan**

```bash
python -c "
from scheduler import job_scan_replies
job_scan_replies()
"
```

Expected: Logs show posts scraped, AI decisions made, replies sent (or "Reply limit reached").

- [ ] **Step 3: Verify state.json is updated correctly**

```bash
python -c "
import json
with open('state.json') as f:
    print(json.dumps(json.load(f), ensure_ascii=False, indent=2))
"
```

Expected: `posts_today` incremented, `replied_ids` populated.

- [ ] **Step 4: Commit**

```bash
git add state.json
git commit -m "chore: initial state after smoke test"
```

---

## Task 8: Start the Bot

- [ ] **Step 1: Run the full bot**

```bash
python main.py
```

Expected:
```
Wellcee Bot starting...
Scheduled post: section=推荐 at 09:07
Scheduled post: section=蹲室友 at 12:23
Scheduled post: section=推荐 at 20:05
Scheduler running. Press Ctrl+C to stop.
```

The bot now runs continuously. Posts will fire at the scheduled times, reply scan every 30 minutes, DM scan every hour.

- [ ] **Step 2: Keep the bot running in the background (optional)**

To keep the bot running after closing the terminal on Windows:

```bash
start /B python main.py > bot.log 2>&1
```

Or use Task Scheduler (Windows) to run `python main.py` on login.

- [ ] **Step 3: Collect screenshots for assignment submission**

After the bot runs for a day, collect evidence:

```bash
dir screenshots\
```

Screenshots are named `YYYYMMDD_HHMMSS_post_推荐.png`, `_reply.png`, `_dm_reply.png` etc.

---

## Resource-ID Quick Reference (fill in during Task 4)

| Constant | Screen | Description |
|----------|--------|-------------|
| `APP_PACKAGE` | Any | Wellcee app package name |
| `RID_COMMUNITY_TAB` | Bottom nav | 社区 tab |
| `RID_RECOMMEND_TAB` | Community | 推荐 sub-tab |
| `RID_ROOMMATE_TAB` | Community | 蹲室友 sub-tab |
| `RID_POST_FAB` | Community | Floating 发布 button |
| `RID_POST_INPUT` | Compose | Text input area |
| `RID_POST_SUBMIT` | Compose | Submit/publish button |
| `RID_COMMENT_INPUT` | Post detail | Comment input |
| `RID_COMMENT_SUBMIT` | Post detail | Send comment button |
| `RID_DM_INPUT` | DM thread | Message input |
| `RID_DM_SEND` | DM thread | Send DM button |
