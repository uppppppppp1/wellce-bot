import argparse

from poster import post_content


def main():
    parser = argparse.ArgumentParser(description="Publish one Wellcee dynamic post for testing.")
    parser.add_argument("--title", default="今天的小记录")
    parser.add_argument(
        "--body",
        default="今天在路上看到一点很日常的小风景，感觉还挺适合发在 Wellcee 试试水。#上海生活 #日常记录",
    )
    parser.add_argument("--section", default="推荐")
    parser.add_argument("--image-index", type=int, default=0)
    args = parser.parse_args()

    screenshot = post_content(
        section=args.section,
        text=args.body,
        title=args.title,
        image_index=args.image_index,
    )
    print(f"Published. Screenshot: {screenshot}")


if __name__ == "__main__":
    main()
