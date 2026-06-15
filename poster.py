import os
import time
import random
import datetime
import hashlib
import re
import xml.etree.ElementTree as ET
import uiautomator2 as u2
from dotenv import load_dotenv

load_dotenv()

# ── Replace these with real resource-ids found via discover_ui.py ──
APP_PACKAGE = os.getenv("WELLCEE_APP_PACKAGE", "com.wellcee.app")
RID_HOME_POST_FAB = os.getenv("RID_HOME_POST_FAB", "")
RID_DYNAMIC_POST_ENTRY = os.getenv("RID_DYNAMIC_POST_ENTRY", "")
RID_GALLERY_IMAGE = os.getenv("RID_GALLERY_IMAGE", "")
RID_GALLERY_NEXT = os.getenv("RID_GALLERY_NEXT", "")
RID_POST_TITLE_INPUT = os.getenv("RID_POST_TITLE_INPUT", "")
RID_POST_BODY_INPUT = os.getenv("RID_POST_BODY_INPUT", "")
RID_COMMUNITY_TAB = ""                   # resource-id of community tab in nav bar
RID_RECOMMEND_TAB = ""                   # resource-id of 推荐 tab
RID_ROOMMATE_TAB = ""                    # resource-id of 蹲室友 tab
RID_POST_FAB = ""                        # resource-id of 发布 floating button
RID_POST_INPUT = ""                      # resource-id of post text input
RID_POST_SUBMIT = ""                     # resource-id of post submit/publish button
RID_COMMENT_INPUT = os.getenv("RID_COMMENT_INPUT", "")
RID_COMMENT_SUBMIT = os.getenv("RID_COMMENT_SUBMIT", "")
RID_DM_INPUT = ""                        # resource-id of DM message input
RID_DM_SEND = ""                         # resource-id of DM send button
# ──────────────────────────────────────────────────────────────────


def _connect() -> u2.Device:
    device_id = os.getenv("DEVICE_ID")
    return u2.connect(device_id) if device_id else u2.connect()


def _rand_sleep(lo=1.5, hi=4.0):
    time.sleep(random.uniform(lo, hi))


def _type_text(d: u2.Device, rid: str, text: str, clear: bool = True):
    """Type text into a known resource-id."""
    if not rid:
        raise ValueError("resource-id is empty; fill it in .env or poster.py first")
    el = d(resourceId=rid)
    el.click()
    time.sleep(0.5)
    d.send_keys(text, clear=clear)


def _parse_bounds(bounds: str) -> tuple[int, int, int, int]:
    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
    if not match:
        raise ValueError(f"invalid bounds: {bounds!r}")
    return tuple(int(v) for v in match.groups())


def _click_bounds_center(d: u2.Device, bounds: str):
    x1, y1, x2, y2 = _parse_bounds(bounds)
    d.click((x1 + x2) // 2, (y1 + y2) // 2)


def _raw_tap(d: u2.Device, x: int, y: int):
    d.shell(f"input tap {x} {y}")


def _click_if_exists(d: u2.Device, selector: dict, timeout: float = 1.0) -> bool:
    el = d(**selector)
    if el.exists(timeout=timeout):
        el.click()
        return True
    return False


def _click_first_available(d: u2.Device, candidates: list[dict], label: str, timeout: float = 2.0):
    for selector in candidates:
        if selector.get("resourceId") == "":
            continue
        if _click_if_exists(d, selector, timeout=timeout):
            return
    raise RuntimeError(f"Could not find UI element: {label}")


def _click_text_node(d: u2.Device, text: str):
    snippets = _text_match_snippets(text)
    if _click_text_node_once(d, text, snippets):
        return

    # The feed scraper may have scrolled after seeing this post. Search nearby
    # screen positions before giving up.
    for start_y, end_y in [(0.3, 0.7), (0.3, 0.7), (0.7, 0.3), (0.7, 0.3), (0.7, 0.3)]:
        d.swipe(0.5, start_y, 0.5, end_y, duration=0.4)
        _rand_sleep(0.8, 1.4)
        if _click_text_node_once(d, text, snippets):
            return

    raise RuntimeError("Could not find the target post text on screen")


def _text_match_snippets(text: str) -> list[str]:
    clean = re.sub(r"^[\s.。·…]+", "", text).strip()
    clean = re.sub(r"\s+", " ", clean)
    snippets = []

    for size in (24, 18, 12):
        if len(clean) >= size:
            snippets.append(clean[:size])

    for part in re.split(r"[，。！？!?、\n]", clean):
        part = part.strip()
        if len(part) >= 8:
            snippets.append(part[:18])

    result = []
    for snippet in snippets:
        if snippet and snippet not in result:
            result.append(snippet)
    return result


def _click_text_node_once(d: u2.Device, text: str, snippets: list[str]) -> bool:
    if _click_if_exists(d, {"text": text}, timeout=0.5):
        return True

    for snippet in snippets:
        if _click_if_exists(d, {"textContains": snippet}, timeout=0.5):
            return True

    root = ET.fromstring(d.dump_hierarchy())
    for node in root.iter():
        node_text = node.attrib.get("text", "").strip()
        bounds = node.attrib.get("bounds", "")
        if not bounds:
            continue
        if node_text == text or any(snippet in node_text for snippet in snippets):
            _click_bounds_center(d, bounds)
            return True

    return False


def _feed_text_candidates(d: u2.Device) -> list[str]:
    ignored_texts = {
        "推荐",
        "关注",
        "附近",
        "发布",
        "发布动态",
        "发布房源",
        "消息",
        "我的",
        "首页",
        "社区",
        "说点好听的",
    }
    ignored_keywords = [
        "广告",
        "置顶",
        "赞",
        "评论",
        "分享",
        "分钟前",
        "小时前",
        "天前",
    ]

    root = ET.fromstring(d.dump_hierarchy())
    candidates = []
    for node in root.iter():
        text = node.attrib.get("text", "").strip()
        bounds = node.attrib.get("bounds", "")
        if not text or not bounds:
            continue
        if text in ignored_texts:
            continue
        if any(keyword == text or text.endswith(keyword) for keyword in ignored_keywords):
            continue
        if len(text) < 18 or len(text) > 500:
            continue
        if re.fullmatch(r"[\d\s:./-]+", text):
            continue

        try:
            x1, y1, x2, y2 = _parse_bounds(bounds)
        except ValueError:
            continue
        if y1 < 120 or y2 > 2200:
            continue
        candidates.append((y1, x1, text))

    candidates.sort()
    return [text for _, _, text in candidates]


def _click_bottom_right_action(d: u2.Device, label: str, require_visible_name: bool = True) -> bool:
    root = ET.fromstring(d.dump_hierarchy())
    candidates = []
    for node in root.iter():
        text = node.attrib.get("text", "").strip()
        desc = node.attrib.get("content-desc", "").strip()
        bounds = node.attrib.get("bounds", "")
        clickable = node.attrib.get("clickable") == "true"
        enabled = node.attrib.get("enabled", "true") == "true"
        if not bounds or not enabled:
            continue

        try:
            x1, y1, x2, y2 = _parse_bounds(bounds)
        except ValueError:
            continue

        visible_name = text or desc
        looks_like_send = visible_name in {"发送", "Send", "确定", "发布"} or "发送" in visible_name
        bottom_right = x1 > 500 and y1 > 1100
        if clickable and (looks_like_send or (bottom_right and not require_visible_name)):
            candidates.append((looks_like_send, y1, x1, bounds, visible_name))

    if not candidates:
        return False

    candidates.sort(reverse=True)
    _, _, _, bounds, visible_name = candidates[0]
    print(f"[click] {label}: {visible_name or bounds}")
    _click_bounds_center(d, bounds)
    return True


def _find_node_bounds_by_id_or_text(d: u2.Device, resource_id: str, texts: set[str]) -> tuple[str, str, str, str] | None:
    root = ET.fromstring(d.dump_hierarchy())
    matches = []
    for node in root.iter():
        rid = node.attrib.get("resource-id", "")
        text = node.attrib.get("text", "").strip()
        desc = node.attrib.get("content-desc", "").strip()
        bounds = node.attrib.get("bounds", "")
        enabled = node.attrib.get("enabled", "true") == "true"
        if not bounds or not enabled:
            continue
        if (resource_id and rid == resource_id) or text in texts or desc in texts:
            try:
                x1, y1, x2, y2 = _parse_bounds(bounds)
            except ValueError:
                continue
            matches.append((y1, x1, bounds, rid, text, desc))

    if not matches:
        return None

    matches.sort(reverse=True)
    _, _, bounds, rid, text, desc = matches[0]
    return bounds, rid, text, desc


def _click_node_by_id_or_text(d: u2.Device, resource_id: str, texts: set[str]) -> bool:
    match = _find_node_bounds_by_id_or_text(d, resource_id, texts)
    if not match:
        return False

    bounds, rid, text, desc = match
    print(f"[click] exact submit: id={rid!r} text={text!r} desc={desc!r} bounds={bounds!r}")
    _tap_bounds_points(d, bounds)
    return True


def _tap_bounds_points(d: u2.Device, bounds: str):
    x1, y1, x2, y2 = _parse_bounds(bounds)
    points = [
        ((x1 + x2) // 2, (y1 + y2) // 2),
        (x1 + max(8, (x2 - x1) // 4), (y1 + y2) // 2),
        (x2 - max(8, (x2 - x1) // 4), (y1 + y2) // 2),
    ]
    for x, y in points:
        print(f"[tap] submit point=({x},{y})")
        _raw_tap(d, x, y)
        _rand_sleep(0.4, 0.8)


def _tap_comment_send_region(d: u2.Device):
    width, height = d.window_size()
    points = [
        (int(width * 0.91), int(height * 0.69)),
        (int(width * 0.92), int(height * 0.66)),
        (int(width * 0.88), int(height * 0.69)),
    ]
    for x, y in points:
        print(f"[tap] fallback send region=({x},{y})")
        _raw_tap(d, x, y)
        _rand_sleep(0.5, 0.9)


def _comment_input_text(d: u2.Device) -> str:
    root = ET.fromstring(d.dump_hierarchy())
    for node in root.iter():
        if RID_COMMENT_INPUT and node.attrib.get("resource-id") == RID_COMMENT_INPUT:
            return node.attrib.get("text", "") or ""
    return ""


def _comment_sheet_visible(d: u2.Device) -> bool:
    root = ET.fromstring(d.dump_hierarchy())
    for node in root.iter():
        rid = node.attrib.get("resource-id", "")
        text = node.attrib.get("text", "").strip()
        if RID_COMMENT_SUBMIT and rid == RID_COMMENT_SUBMIT:
            return True
        if RID_COMMENT_INPUT and rid == RID_COMMENT_INPUT:
            return True
        if text in {"评论", "发送", "取消"}:
            return True
    return False


def _wait_comment_sent(d: u2.Device, before_text: str, timeout: float = 4.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _comment_sheet_visible(d):
            return True
        after_text = _comment_input_text(d)
        if before_text and after_text and after_text != before_text:
            return True
        time.sleep(0.4)
    return False


def _debug_print_send_candidates(d: u2.Device):
    root = ET.fromstring(d.dump_hierarchy())
    print("[debug] visible send/action candidates:")
    for node in root.iter():
        text = node.attrib.get("text", "").strip()
        desc = node.attrib.get("content-desc", "").strip()
        rid = node.attrib.get("resource-id", "")
        cls = node.attrib.get("class", "")
        bounds = node.attrib.get("bounds", "")
        clickable = node.attrib.get("clickable", "")
        if text in {"发送", "Send", "确定", "发布"} or desc in {"发送", "Send", "确定", "发布"} or "confirm" in rid.lower():
            print(f"  class={cls!r} id={rid!r} text={text!r} desc={desc!r} clickable={clickable!r} bounds={bounds!r}")


def _submit_comment(d: u2.Device):
    before_text = _comment_input_text(d)

    match = _find_node_bounds_by_id_or_text(d, RID_COMMENT_SUBMIT, {"发送", "Send"})
    if match:
        bounds, rid, text, desc = match
        print(f"[click] exact submit: id={rid!r} text={text!r} desc={desc!r} bounds={bounds!r}")
        _tap_bounds_points(d, bounds)
        if _wait_comment_sent(d, before_text):
            return
        print("[debug] comment text still present after submit taps, trying fallback region")

    _tap_comment_send_region(d)
    if _wait_comment_sent(d, before_text):
        return

    for _ in range(2):
        if _click_bottom_right_action(d, "comment submit", require_visible_name=True):
            if _wait_comment_sent(d, before_text):
                return

    d.press("enter")
    _rand_sleep(0.8, 1.2)
    if _wait_comment_sent(d, before_text):
        return

    d.press("back")
    _rand_sleep(0.5, 1.0)

    if _click_node_by_id_or_text(d, RID_COMMENT_SUBMIT, {"发送", "Send"}):
        if _wait_comment_sent(d, before_text):
            return

    _debug_print_send_candidates(d)
    raise RuntimeError("Comment submit button was tapped, but the comment sheet did not close")


def _allow_photo_permission_if_needed(d: u2.Device):
    permission_texts = [
        "允许",
        "始终允许",
        "仅在使用中允许",
        "允许访问所有照片",
        "Allow",
        "ALLOW",
    ]
    for text in permission_texts:
        if _click_if_exists(d, {"text": text}, timeout=0.5):
            _rand_sleep(0.5, 1.0)
            return


def _click_gallery_image(d: u2.Device, image_index: int = 0):
    if RID_GALLERY_IMAGE:
        d(resourceId=RID_GALLERY_IMAGE)[image_index].click()
        return

    root = ET.fromstring(d.dump_hierarchy())
    candidates = []
    for node in root.iter():
        cls = node.attrib.get("class", "")
        bounds = node.attrib.get("bounds", "")
        clickable = node.attrib.get("clickable") == "true"
        if cls not in {"android.widget.ImageView", "android.view.ViewGroup", "android.widget.FrameLayout"}:
            continue
        if not clickable or not bounds:
            continue
        x1, y1, x2, y2 = _parse_bounds(bounds)
        width, height = x2 - x1, y2 - y1
        if y1 < 120 or width < 80 or height < 80:
            continue
        candidates.append((y1, x1, bounds))

    if not candidates:
        raise RuntimeError("Could not find a selectable image in the system gallery")

    candidates.sort()
    safe_index = min(max(image_index, 0), len(candidates) - 1)
    _click_bounds_center(d, candidates[safe_index][2])


def _click_gallery_next_if_needed(d: u2.Device):
    candidates = [
        {"resourceId": RID_GALLERY_NEXT},
        {"text": "下一步"},
        {"text": "完成"},
        {"text": "确定"},
        {"text": "添加"},
        {"text": "Next"},
        {"text": "Done"},
        {"description": "下一步"},
        {"description": "完成"},
    ]
    for selector in candidates:
        if selector.get("resourceId") == "":
            continue
        if _click_if_exists(d, selector, timeout=1.0):
            _rand_sleep(1.0, 2.0)
            return True
    return False


def _edit_text_bounds(d: u2.Device) -> list[str]:
    root = ET.fromstring(d.dump_hierarchy())
    bounds_list = []
    for node in root.iter():
        if node.attrib.get("class") != "android.widget.EditText":
            continue
        if node.attrib.get("enabled") == "false":
            continue
        bounds = node.attrib.get("bounds", "")
        if bounds:
            bounds_list.append(bounds)
    return bounds_list


def _type_edit_text_by_index(d: u2.Device, index: int, text: str):
    bounds_list = _edit_text_bounds(d)
    if index >= len(bounds_list):
        raise RuntimeError(f"Could not find EditText index {index}; found {len(bounds_list)} inputs")
    _click_bounds_center(d, bounds_list[index])
    time.sleep(0.5)
    d.send_keys(text, clear=True)


def _derive_title(text: str, max_len: int = 24) -> str:
    clean = re.sub(r"#\S+", "", text).strip()
    first_line = clean.splitlines()[0].strip() if clean else ""
    first_sentence = re.split(r"[。！？!?]", first_line)[0].strip()
    title = first_sentence or "今天的小记录"
    if len(title) > max_len:
        title = title[:max_len].rstrip() + "..."
    return title


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


def post_content(
    section: str,
    text: str,
    title: str | None = None,
    image_index: int | None = None,
) -> str:
    """
    Publish a Wellcee dynamic post from the home-page plus button.

    Flow:
    home + button -> 发布动态 -> system gallery -> select one image ->
    edit title/body -> 发布.
    """
    d = _connect()
    ensure_wellcee_open(d)
    _rand_sleep()

    _click_first_available(
        d,
        [
            {"resourceId": RID_HOME_POST_FAB},
            {"resourceId": RID_POST_FAB},
            {"description": "发布"},
            {"description": "加号"},
            {"description": "plus"},
            {"text": "+"},
        ],
        "home plus/post button",
    )
    _rand_sleep()

    _click_first_available(
        d,
        [
            {"resourceId": RID_DYNAMIC_POST_ENTRY},
            {"text": "发布动态"},
            {"description": "发布动态"},
        ],
        "发布动态 entry",
    )
    _rand_sleep(1.0, 2.0)

    _allow_photo_permission_if_needed(d)
    _click_gallery_image(d, image_index if image_index is not None else int(os.getenv("POST_IMAGE_INDEX", "0")))
    _rand_sleep(0.8, 1.5)
    _click_gallery_next_if_needed(d)
    _rand_sleep(1.5, 3.0)

    post_title = title or _derive_title(text)
    if RID_POST_TITLE_INPUT:
        _type_text(d, RID_POST_TITLE_INPUT, post_title)
    else:
        _type_edit_text_by_index(d, 0, post_title)
    _rand_sleep(0.5, 1.0)

    if RID_POST_BODY_INPUT:
        _type_text(d, RID_POST_BODY_INPUT, text)
    elif RID_POST_INPUT:
        _type_text(d, RID_POST_INPUT, text)
    else:
        _type_edit_text_by_index(d, 1, text)
    _rand_sleep()

    _click_first_available(
        d,
        [
            {"resourceId": RID_POST_SUBMIT},
            {"text": "发布"},
            {"description": "发布"},
            {"text": "提交"},
            {"description": "提交"},
        ],
        "post submit button",
    )
    _rand_sleep(2, 5)
    path = _screenshot(d, f"post_{section}")
    return path


def scrape_post_texts(section: str, limit: int = 20) -> list[dict]:
    """
    Scrape visible post texts from the home feed.
    Returns list of {"id": str, "text": str}.
    Uses text hash as stable ID since Wellcee doesn't expose post IDs in UI.
    """
    d = _connect()
    ensure_wellcee_open(d)
    _rand_sleep()

    posts = []
    seen_texts = set()

    for _ in range(4):
        for text in _feed_text_candidates(d):
            if text in seen_texts:
                continue
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
    ensure_wellcee_open(d)
    _rand_sleep()
    _click_text_node(d, post_text)
    _rand_sleep()

    if RID_COMMENT_INPUT:
        _type_text(d, RID_COMMENT_INPUT, reply_text)
    else:
        _click_first_available(
            d,
            [
                {"text": "说点好听的"},
                {"textContains": "说点好听"},
                {"description": "说点好听的"},
                {"className": "android.widget.EditText"},
            ],
            "comment input",
        )
        time.sleep(0.5)
        d.send_keys(reply_text, clear=False)

    _rand_sleep()
    _submit_comment(d)
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
