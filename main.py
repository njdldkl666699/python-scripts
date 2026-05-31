import argparse
import sys
from pathlib import Path

from loguru import logger

from backend.config import AES_IV, AES_KEY
from backend.parser import decrypt, dumps_json, parse_map, unmsgpack
from backend.renderer import render_scene_images


def configure_logger(verbose: bool) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        colorize=True,
        level="DEBUG" if verbose else "INFO",
        format="<green>{time:HH:mm:ss}</green> <level>{message}</level>",
    )


def read_payload_bytes(response_file: Path | None) -> bytes:
    if response_file:
        data = response_file.read_bytes()
    else:
        if sys.stdin.isatty():
            raise ValueError(
                "未提供 payload。请使用 --response-file，或通过标准输入传入二进制数据。"
            )
        data = sys.stdin.buffer.read()
        if not data:
            raise ValueError("未从标准输入读取到任何数据。")

    return data


def inspect_response(payload: bytes) -> dict:
    decrypted = decrypt(payload, AES_KEY, AES_IV)
    decoded = unmsgpack(decrypted)
    logger.info("解密成功，响应包含这些顶级键：{}", list(decoded.keys()))
    return decoded


def extract_harvest_maps(decoded_response: dict) -> dict:
    try:
        harvest = parse_map(decoded_response)
    except AssertionError as exc:
        raise ValueError("响应中不包含 harvest map 数据。") from exc
    logger.info("共发现 {} 个采集场景。", len(harvest))
    return harvest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="在命令行中解密并解析 Mysekai 响应 payload。支持通过 --response-file 传入文件，或直接通过标准输入（管道）传入二进制数据。"
    )
    parser.add_argument(
        "--response-file",
        type=Path,
        help="包含加密响应 payload 的二进制文件路径。如果不指定此参数，则默认从标准输入读取。",
    )
    parser.add_argument(
        "--dump-decrypted",
        action="store_true",
        help="在解析 harvest map 之前，先输出完整的解密后 JSON。",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="以紧凑格式输出 harvest map 数据，不进行美化排版。",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出更详细的日志，便于排查问题。",
    )
    parser.add_argument(
        "--render-scenes",
        type=Path,
        metavar="DIR",
        help="将标注后的场景图片输出到目标目录，而不是打印 JSON。",
    )

    args = parser.parse_args(argv)
    configure_logger(args.verbose)

    try:
        payload = read_payload_bytes(args.response_file)
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(2)

    try:
        decoded_response = inspect_response(payload)
    except Exception as exc:
        logger.error("解密或解码响应失败：{}", exc)
        sys.exit(1)

    if args.dump_decrypted:
        print(dumps_json(decoded_response, indent=None if args.compact else 2))

    try:
        harvest = extract_harvest_maps(decoded_response)
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)

    if args.render_scenes:
        rendered = render_scene_images(harvest, args.render_scenes)
        if not rendered:
            logger.warning("没有生成任何场景图片。")
    else:
        indent = None if args.compact else 2
        print(dumps_json(harvest, indent=indent))


if __name__ == "__main__":
    main()
