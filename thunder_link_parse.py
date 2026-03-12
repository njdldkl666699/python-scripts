import base64


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


if __name__ == "__main__":
    # Example usage
    thunder_link = "thunder://QUFodHRwczovL2l0MzY1LmdpdGxhYi5pby96aC1jbi94dW5sZWktemgvWlo="
    try:
        original_url = parse_thunder_link(thunder_link)
        print("Original URL:", original_url)
    except ValueError as e:
        print("Error:", e)
