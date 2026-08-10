#!/usr/bin/env python3
"""合并 Minecraft 客户端 JAR 与散列资源文件。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

SHA1_RE = re.compile(r"^[0-9a-fA-F]{40}$")
COPY_BUFFER_SIZE = 1024 * 1024
PROGRESS_INTERVAL = 250


class MergeError(Exception):
    """可以直接显示给命令行用户的错误。"""


class ChineseArgumentParser(argparse.ArgumentParser):
    """使用中文标题和错误前缀的命令行参数解析器。"""

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法：", 1)

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "用法：", 1)
            .replace("positional arguments:", "位置参数：", 1)
            .replace("options:", "选项：", 1)
        )

    def error(self, message: str):
        required_prefix = "the following arguments are required:"
        unrecognized_prefix = "unrecognized arguments:"
        missing_value_suffix = ": expected one argument"
        if message.startswith(required_prefix):
            message = f"缺少以下必需参数：{message.removeprefix(required_prefix).strip()}"
        elif message.startswith(unrecognized_prefix):
            message = f"无法识别的参数：{message.removeprefix(unrecognized_prefix).strip()}"
        elif message.startswith("argument ") and message.endswith(missing_value_suffix):
            argument = message.removeprefix("argument ").removesuffix(missing_value_suffix)
            message = f"参数 {argument} 需要一个值"
        else:
            message = "命令行参数无效，请使用 --help 查看用法"
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}：参数错误：{message}\n")


@dataclass(frozen=True)
class Asset:
    resource_path: PurePosixPath
    hash: str
    size: int
    object_path: Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = ChineseArgumentParser(
        description="解压 Minecraft 客户端 JAR，并合并对应的散列资源文件。",
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="help", help="显示此帮助信息并退出")
    parser.add_argument(
        "minecraft_root", type=Path, metavar="MINECRAFT根目录", help=".minecraft 根目录路径"
    )
    parser.add_argument(
        "asset_index",
        metavar="资源索引",
        help="散列资源索引文件名（例如 32.json）或显式路径",
    )
    parser.add_argument("version_jar", metavar="版本JAR", help="版本 JAR 路径")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="输出目录",
        help="输出目录（默认：根据 JAR 文件名推断为 ./<版本号>）",
    )
    return parser.parse_args(argv)


def resolve_input(value: str | Path, root: Path, fallback: Path | None = None) -> Path:
    supplied = Path(value).expanduser()
    if supplied.is_absolute():
        return supplied.resolve()

    candidates = [Path.cwd() / supplied, root / supplied]
    if fallback is not None:
        candidates.append(fallback / supplied)

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    if fallback is not None and supplied.parent == Path("."):
        return (fallback / supplied).resolve()
    return (root / supplied).resolve()


def safe_relative_path(raw_path: str, source: str) -> PurePosixPath:
    if not raw_path or "\\" in raw_path:
        raise MergeError(f"{source} 中包含不安全的路径：{raw_path!r}")

    path = PurePosixPath(raw_path)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise MergeError(f"{source} 中包含不安全的路径：{raw_path!r}")
    return path


def load_assets(index_path: Path, objects_root: Path) -> list[Asset]:
    try:
        with index_path.open("r", encoding="utf-8") as file:
            index: Any = json.load(file)
    except FileNotFoundError as exc:
        raise MergeError(f"散列资源索引不存在：{index_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise MergeError(f"无法读取散列资源索引 {index_path}：{exc}") from exc

    if not isinstance(index, dict) or not isinstance(index.get("objects"), dict):
        raise MergeError(f"散列资源索引不包含有效的 'objects' 映射：{index_path}")

    assets: list[Asset] = []
    for raw_resource_path, metadata in index["objects"].items():
        if not isinstance(raw_resource_path, str) or not isinstance(metadata, dict):
            raise MergeError("散列资源索引包含无效的资源条目")

        resource_path = safe_relative_path(raw_resource_path, str(index_path))
        object_hash = metadata.get("hash")
        size = metadata.get("size")
        if not isinstance(object_hash, str) or not SHA1_RE.fullmatch(object_hash):
            raise MergeError(f"资源 {raw_resource_path!r} 的 SHA-1 无效")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise MergeError(f"资源 {raw_resource_path!r} 的文件大小无效")

        object_hash = object_hash.lower()
        assets.append(
            Asset(
                resource_path=resource_path,
                hash=object_hash,
                size=size,
                object_path=objects_root / object_hash[:2] / object_hash,
            )
        )
    return assets


def preflight_assets(assets: Iterable[Asset]) -> None:
    missing: list[Asset] = []
    wrong_size: list[tuple[Asset, int]] = []

    for asset in assets:
        try:
            actual_size = asset.object_path.stat().st_size
        except FileNotFoundError:
            missing.append(asset)
            continue
        except OSError as exc:
            raise MergeError(f"无法检查散列资源文件 {asset.object_path}：{exc}") from exc
        if not asset.object_path.is_file():
            missing.append(asset)
        elif actual_size != asset.size:
            wrong_size.append((asset, actual_size))

    if not missing and not wrong_size:
        return

    details: list[str] = []
    if missing:
        details.append(f"缺少 {len(missing)} 个散列资源文件")
        details.extend(f"  {asset.resource_path} -> {asset.object_path}" for asset in missing[:10])
        if len(missing) > 10:
            details.append(f"  ……以及另外 {len(missing) - 10} 个")
    if wrong_size:
        details.append(f"{len(wrong_size)} 个散列资源文件的大小不匹配")
        details.extend(
            f"  {asset.resource_path}：应为 {asset.size}，实际为 {actual_size}"
            for asset, actual_size in wrong_size[:10]
        )
        if len(wrong_size) > 10:
            details.append(f"  ……以及另外 {len(wrong_size) - 10} 个")
    raise MergeError("\n".join(details))


def extract_jar(jar_path: Path, output_dir: Path) -> int:
    try:
        archive = zipfile.ZipFile(jar_path)
    except FileNotFoundError as exc:
        raise MergeError(f"版本 JAR 不存在：{jar_path}") from exc
    except (OSError, zipfile.BadZipFile) as exc:
        raise MergeError(f"无法打开版本 JAR {jar_path}：{exc}") from exc

    extracted = 0
    try:
        for entry in archive.infolist():
            raw_name = entry.filename.rstrip("/")
            if not raw_name:
                continue
            relative_path = safe_relative_path(raw_name, str(jar_path))
            destination = output_dir.joinpath(*relative_path.parts)

            unix_mode = entry.external_attr >> 16
            if unix_mode and stat.S_ISLNK(unix_mode):
                raise MergeError(f"不支持 JAR 中的符号链接条目：{entry.filename!r}")
            try:
                if entry.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target, COPY_BUFFER_SIZE)
            except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                raise MergeError(f"无法解压条目 {entry.filename!r}：{exc}") from exc
            extracted += 1
    finally:
        archive.close()
    return extracted


def copy_asset(asset: Asset, destination: Path) -> None:
    temp_path: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as target:
            temp_path = Path(target.name)
            digest = hashlib.sha1()
            with asset.object_path.open("rb") as source:
                while chunk := source.read(COPY_BUFFER_SIZE):
                    target.write(chunk)
                    digest.update(chunk)

        actual_hash = digest.hexdigest()
        if actual_hash != asset.hash:
            raise MergeError(
                f"资源 {asset.resource_path} 的 SHA-1 不匹配：应为 {asset.hash}，实际为 {actual_hash}"
            )
        os.replace(temp_path, destination)
        temp_path = None
    except MergeError:
        raise
    except OSError as exc:
        raise MergeError(f"无法复制资源 {asset.resource_path}：{exc}") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def merge_assets(assets: list[Asset], output_dir: Path) -> tuple[int, int]:
    copied = 0
    overwritten = 0
    for asset in assets:
        destination = output_dir / "assets" / Path(*asset.resource_path.parts)
        if destination.exists():
            overwritten += 1
        copy_asset(asset, destination)
        copied += 1
        if copied % PROGRESS_INTERVAL == 0 or copied == len(assets):
            print(f"已合并散列资源：{copied}/{len(assets)}", file=sys.stderr)
    return copied, overwritten


def run(args: argparse.Namespace) -> None:
    root = args.minecraft_root.expanduser().resolve()
    if not root.is_dir():
        raise MergeError(f"Minecraft 根目录不存在或不是目录：{root}")

    index_path = resolve_input(args.asset_index, root, root / "assets" / "indexes")
    jar_path = resolve_input(args.version_jar, root)
    output_dir = (
        args.output.expanduser().resolve()
        if args.output is not None
        else (Path.cwd() / jar_path.stem).resolve()
    )

    if not jar_path.is_file():
        raise MergeError(f"版本 JAR 不存在：{jar_path}")
    if output_dir == jar_path or output_dir == index_path:
        raise MergeError("输出路径必须是与输入文件分离的目录")

    assets = load_assets(index_path, root / "assets" / "objects")
    preflight_assets(assets)
    if output_dir.exists() and not output_dir.is_dir():
        raise MergeError(f"输出路径已存在但不是目录：{output_dir}")
    try:
        output_has_entries = output_dir.exists() and next(output_dir.iterdir(), None) is not None
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise MergeError(f"无法创建或检查输出目录 {output_dir}：{exc}") from exc

    print(f"散列资源索引：{index_path}")
    print(f"版本 JAR：{jar_path}")
    print(f"输出目录：{output_dir}")
    print(f"散列资源数量：{len(assets)}")
    if output_has_entries:
        print("警告：输出目录不为空，已有文件可能被覆盖。", file=sys.stderr)
    print("正在解压版本 JAR……", file=sys.stderr)
    extracted = extract_jar(jar_path, output_dir)
    print("正在合并散列资源……", file=sys.stderr)
    copied, overwritten = merge_assets(assets, output_dir)
    print(
        f"完成：解压 {extracted} 个 JAR 文件，合并 {copied} 个散列资源 "
        f"（覆盖了 {overwritten} 个已有文件）。"
    )


def main(argv: list[str] | None = None) -> int:
    try:
        run(parse_args(argv))
    except MergeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("操作已中断。", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
