import os
import random
import logging
from datetime import date
from apscheduler.schedulers.blocking import BlockingScheduler
from content import make_client, generate_dynamic_post, generate_reply, generate_dm_reply
from poster import post_content, scrape_post_texts, reply_to_post, scrape_unread_dms, reply_to_dm
from state import load_state, save_state, increment_post_count, mark_replied, mark_dm_replied, reset_daily

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

POST_SCHEDULE = [
    (17,  37,  "推荐",   "下班"),
    (12, 30, "蹲室友", "午间"),
    (20, 0,  "推荐",   "晚间"),
]

MAX_REPLIES_PER_DAY = 10
MAX_DM_REPLIES_PER_HOUR = 20


def _jitter_minutes() -> int:
    return random.randint(-10, 10)


def job_post(section: str, time_slot: str):
    state = load_state()
    if state.get("date") != str(date.today()):
        state = reset_daily(state)
        save_state(state)

    if state["posts_today"] >= 3:
        log.info("Already posted 3 times today, skipping.")
        return

    client = make_client()
    posted_topics = state.get("posted_topics", [])
    post = generate_dynamic_post(client, time_slot, section, posted_topics)
    title = post["title"]
    body = post["body"]
    log.info(f"[POST] section={section}\ntitle={title}\n{body}")

    path = post_content(section=section, text=body, title=title)
    log.info(f"[POST] Screenshot: {path}")

    state = increment_post_count(state)
    state.setdefault("posted_topics", []).append(f"{title}:{body[:20]}")
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
    posts = scrape_post_texts("首页", limit=5)
    for post in posts:
        if post["id"] in state["replied_ids"]:
            continue
        should_reply, reply_text = generate_reply(client, post["text"])
        if not should_reply or not reply_text:
            continue
        log.info(f"[REPLY] post_id={post['id']}\npost={post['text']}\nreply={reply_text}")
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
    enable_reply_scan = os.getenv("ENABLE_REPLY_SCAN", "false").lower() == "true"
    enable_dm_scan = os.getenv("ENABLE_DM_SCAN", "false").lower() == "true"

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

    if enable_reply_scan:
        scheduler.add_job(job_scan_replies, "interval", minutes=30, id="scan_replies")
    else:
        log.info("Reply scan disabled. Set ENABLE_REPLY_SCAN=true to enable it.")

    if enable_dm_scan:
        scheduler.add_job(job_scan_dms, "interval", hours=1, id="scan_dms")
    else:
        log.info("DM scan disabled. Set ENABLE_DM_SCAN=true to enable it.")

    return scheduler
