import argparse

from content import generate_dynamic_post, make_client
from poster import post_content
from state import load_state, save_state, increment_post_count


def main():
    parser = argparse.ArgumentParser(description="Generate and publish one Wellcee dynamic post now.")
    parser.add_argument("--section", default="推荐")
    parser.add_argument("--time-slot", default="现在")
    parser.add_argument("--dry-run", action="store_true", help="Only print generated title/body.")
    args = parser.parse_args()

    state = load_state()
    client = make_client()
    post = generate_dynamic_post(
        client=client,
        time_slot=args.time_slot,
        section=args.section,
        posted_topics=state.get("posted_topics", []),
    )

    print(f"title: {post['title']}")
    print(post["body"])

    if args.dry_run:
        return

    screenshot = post_content(
        section=args.section,
        text=post["body"],
        title=post["title"],
    )
    state = increment_post_count(state)
    state.setdefault("posted_topics", []).append(f"{post['title']}:{post['body'][:20]}")
    save_state(state)
    print(f"Published. Screenshot: {screenshot}")


if __name__ == "__main__":
    main()
