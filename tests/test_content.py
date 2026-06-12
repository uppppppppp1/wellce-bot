import pytest
from unittest.mock import MagicMock
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
