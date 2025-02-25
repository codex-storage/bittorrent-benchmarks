import re
import sys


def increment_retry_counter(group_id: str) -> str:
    retry = re.match(r"(.+)-r(\d+)$", group_id)
    if not retry:
        return f"{group_id}-r1"

    return f"{retry.group(1)}-r{int(retry.group(2)) + 1}"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: increment_retry_counter.py <group_id>")
        sys.exit(1)

    print(increment_retry_counter(sys.argv[1]))
