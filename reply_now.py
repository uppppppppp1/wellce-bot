from content import generate_reply, make_client
from poster import reply_to_post, scrape_post_texts
from state import load_state, mark_replied, save_state


def main():
    state = load_state()
    client = make_client()
    posts = scrape_post_texts(section="首页", limit=3)

    for post in posts:
        if post["id"] in state.get("replied_ids", []):
            continue

        should_reply, reply_text = generate_reply(client, post["text"])
        print(f"post_id: {post['id']}")
        print(f"post: {post['text']}")
        print(f"should_reply: {should_reply}")
        print(f"reply: {reply_text}")

        if not should_reply or not reply_text:
            continue

        screenshot = reply_to_post(post["text"], reply_text)
        state = mark_replied(state, post["id"])
        save_state(state)
        print(f"Replied. Screenshot: {screenshot}")
        return

    print("No suitable post found to reply.")


if __name__ == "__main__":
    main()
