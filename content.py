import json
import os
import re
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


def _strip_json_fence(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def _fallback_title(body: str, max_len: int = 24) -> str:
    clean = re.sub(r"#\S+", "", body).strip()
    first_line = clean.splitlines()[0].strip() if clean else ""
    title = re.split(r"[。！？!?]", first_line)[0].strip() or "今天的小记录"
    if len(title) > max_len:
        title = title[:max_len].rstrip() + "..."
    return title


def generate_dynamic_post(client: OpenAI, time_slot: str, section: str, posted_topics: list[str]) -> dict:
    topics_str = "、".join(posted_topics) if posted_topics else "无"
    roommate_note = "如果写租房/室友相关，避免像中介广告，要像个人真实经验或观察。" if section == "蹲室友" else ""
    user_prompt = f"""现在是{time_slot}，准备发一条 Wellcee 社区动态。
今天已发的主题：{topics_str}。

请以小林的身份生成一条真实自然的动态，适合 Wellcee 社区氛围。
要求：
- 标题 8-20 个中文字符，像真人随手写的标题，不要标题党
- 正文 100-180 字，贴近上海打工人/租房/通勤/周末生活观察
- 不要和今天已发内容重复
- {roommate_note}
- 正文结尾加 3-5 个相关 hashtag
- 不要推广、不要政治、不要像营销号

输出严格 JSON，不要解释：
{{"title": "标题", "body": "正文"}}"""

    resp = client.chat.completions.create(
        model=os.getenv("MODEL_NAME", "gpt-4o"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
    )
    raw = _strip_json_fence(resp.choices[0].message.content)
    try:
        data = json.loads(raw)
        title = str(data.get("title", "")).strip()
        body = str(data.get("body", "")).strip()
    except json.JSONDecodeError:
        body = raw
        title = ""

    if not body:
        raise ValueError("AI returned an empty post body")
    if not title:
        title = _fallback_title(body)

    return {"title": title[:30], "body": body}


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
- 20-45 字，口语化，有实质内容
- 不要加 hashtag，不要写成小作文
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
    raw = _strip_json_fence(resp.choices[0].message.content)
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
