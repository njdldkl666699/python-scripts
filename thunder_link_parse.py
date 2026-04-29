import argparse
import base64
import sys


def parse_thunder_link(thunder_link: str) -> str:
    """
    Parses a Thunder link and returns the original URL.

    Args:
        thunder_link (str): The Thunder link to be parsed.
    Returns:
        str: The original URL extracted from the Thunder link.
    """
    if not thunder_link.startswith("thunder://"):
        raise ValueError("Invalid Thunder link format")

    # Remove the 'thunder://' prefix
    encoded_part = thunder_link[len("thunder://") :]

    # Decode the base64 part
    decoded_bytes = base64.b64decode(encoded_part)
    decoded_str = decoded_bytes.decode("utf-8")

    # Remove the 'AA' prefix and 'ZZ' suffix
    if decoded_str.startswith("AA") and decoded_str.endswith("ZZ"):
        original_url = decoded_str[2:-2]
    else:
        raise ValueError("Decoded string does not have expected format")

    return original_url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse a Thunder link.")
    parser.add_argument("link", help="Thunder link to parse.")
    args = parser.parse_args(argv)

    try:
        original_url = parse_thunder_link(args.link)
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    sys.stdout.write(f"{original_url}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
