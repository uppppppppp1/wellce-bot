from poster import _connect, _submit_comment


def main():
    d = _connect()
    _submit_comment(d)
    print("Submit attempted.")


if __name__ == "__main__":
    main()
