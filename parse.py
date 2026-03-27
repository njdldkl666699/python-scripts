import argparse
import base64
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import msgspec
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from dotenv import load_dotenv
from loguru import logger
from msgpack import unpackb
from msgspec import Struct as BaseModel
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
AES_KEY = os.getenv("AES_KEY", "").encode("utf-8")
AES_IV = os.getenv("AES_IV", "").encode("utf-8")
if not AES_KEY or not AES_IV:
    logger.error("必须在 .env 文件中设置 AES_KEY 和 AES_IV。")
    sys.exit(1)


class GridSize(BaseModel):
    width: int
    depth: int
    height: int


class MysekaiFixtureTagGroup(BaseModel):
    id: int
    mysekaiFixtureTagId1: int
    mysekaiFixtureTagId2: int | None = None
    mysekaiFixtureTagId3: int | None = None


class ModelItem(BaseModel, kw_only=True):
    id: int
    mysekaiFixtureType: str
    name: str
    pronunciation: str
    flavorText: str
    seq: int
    gridSize: GridSize
    mysekaiFixtureMainGenreId: int | None = None
    mysekaiFixtureSubGenreId: int | None = None
    mysekaiFixtureHandleType: str
    mysekaiSettableSiteType: str
    mysekaiSettableLayoutType: str
    mysekaiFixturePutType: str
    mysekaiFixtureAnotherColors: list
    mysekaiFixturePutSoundId: int
    mysekaiFixtureFootstepId: int | None = None
    mysekaiFixtureTagGroup: MysekaiFixtureTagGroup | None = None
    isAssembled: bool
    isDisassembled: bool
    mysekaiFixturePlayerActionType: str
    isGameCharacterAction: bool
    assetbundleName: str


class UserMysekaiSiteHarvestFixture(BaseModel):
    mysekaiSiteHarvestFixtureId: int
    positionX: int
    positionZ: int
    hp: int
    userMysekaiSiteHarvestFixtureStatus: str


class UserMysekaiSiteHarvestResourceDrop(BaseModel):
    resourceType: str
    resourceId: int
    positionX: int
    positionZ: int
    hp: int
    seq: int
    mysekaiSiteHarvestResourceDropStatus: str
    quantity: int


class Map(BaseModel, kw_only=True):
    mysekaiSiteId: int
    siteName: str | None = None
    userMysekaiSiteHarvestFixtures: list[UserMysekaiSiteHarvestFixture]
    userMysekaiSiteHarvestResourceDrops: list[UserMysekaiSiteHarvestResourceDrop]


SITE_ID = {
    1: "マイホーム",
    2: "1F",
    3: "2F",
    4: "3F",
    5: "さいしょの原っぱ",
    6: "願いの砂浜",
    7: "彩りの花畑",
    8: "忘れ去られた場所",
}

BASE_DIR = Path(__file__).resolve().parent


FIXTURE_COLORS = {
    112: "#f9f9f9",
    #
    1001: "#da6d42",  # wood
    1002: "#da6d42",
    1003: "#da6d42",
    1004: "#da6d42",
    #
    2001: "#878685",  # iron
    2002: "#d5750a",  # copper
    2003: "#d5d5d5",  # stone
    2004: "#a7c7cb",
    2005: "#9933cc",
    #
    3001: "#c95a49",
    #
    4001: "#f8729a",  # flower
    4002: "#f8729a",
    4003: "#f8729a",
    4004: "#f8729a",
    4005: "#f8729a",
    4006: "#f8729a",
    4007: "#f8729a",
    4008: "#f8729a",
    4009: "#f8729a",  # cotton
    4010: "#f8729a",
    4011: "#f8729a",
    4012: "#f8729a",
    4013: "#f8729a",
    4014: "#f8729a",
    4015: "#f8729a",
    4016: "#f8729a",
    4017: "#f8729a",
    4018: "#f8729a",
    4019: "#f8729a",
    4020: "#f8729a",
    #
    5001: "#f6f5f2",
    5002: "#f6f5f2",
    5003: "#f6f5f2",
    5004: "#f6f5f2",
    5101: "#f6f5f2",
    5102: "#f6f5f2",
    5103: "#f6f5f2",
    5104: "#f6f5f2",
    #
    6001: "#6f4e37",
    #
    7001: "#a5d9ff",
}


ITEM_TEXTURES = {
    "mysekai_material": {
        1: "icon/Texture2D/item_wood_1.png",
        2: "icon/Texture2D/item_wood_2.png",
        3: "icon/Texture2D/item_wood_3.png",
        4: "icon/Texture2D/item_wood_4.png",
        5: "icon/Texture2D/item_wood_5.png",
        6: "icon/Texture2D/item_mineral_1.png",
        7: "icon/Texture2D/item_mineral_2.png",
        8: "icon/Texture2D/item_mineral_3.png",
        9: "icon/Texture2D/item_mineral_4.png",
        10: "icon/Texture2D/item_mineral_5.png",
        11: "icon/Texture2D/item_mineral_6.png",
        12: "icon/Texture2D/item_mineral_7.png",
        13: "icon/Texture2D/item_junk_1.png",
        14: "icon/Texture2D/item_junk_2.png",
        15: "icon/Texture2D/item_junk_3.png",
        16: "icon/Texture2D/item_junk_4.png",
        17: "icon/Texture2D/item_junk_5.png",
        18: "icon/Texture2D/item_junk_6.png",
        19: "icon/Texture2D/item_junk_7.png",
        20: "icon/Texture2D/item_plant_1.png",
        21: "icon/Texture2D/item_plant_2.png",
        22: "icon/Texture2D/item_plant_3.png",
        23: "icon/Texture2D/item_plant_4.png",
        24: "icon/Texture2D/item_tone_8.png",
        32: "icon/Texture2D/item_junk_8.png",
        33: "icon/Texture2D/item_mineral_8.png",
        34: "icon/Texture2D/item_junk_9.png",
        61: "icon/Texture2D/item_junk_10.png",
        62: "icon/Texture2D/item_junk_11.png",
        63: "icon/Texture2D/item_junk_12.png",
        64: "icon/Texture2D/item_mineral_9.png",
        65: "icon/Texture2D/item_mineral_10.png",
        66: "icon/Texture2D/item_junk_13.png",
        93: "icon/Texture2D/item_junk_14.png",
    },
    "mysekai_item": {
        7: "icon/Texture2D/item_blueprint_fragment.png",
    },
    "mysekai_fixture": {
        118: "icon/Texture2D/mdl_non1001_before_sapling1_118.png",
        119: "icon/Texture2D/mdl_non1001_before_sapling1_119.png",
        120: "icon/Texture2D/mdl_non1001_before_sapling1_120.png",
        121: "icon/Texture2D/mdl_non1001_before_sapling1_121.png",
        126: "icon/Texture2D/mdl_non1001_before_sprout1_126.png",
        127: "icon/Texture2D/mdl_non1001_before_sprout1_127.png",
        128: "icon/Texture2D/mdl_non1001_before_sprout1_128.png",
        129: "icon/Texture2D/mdl_non1001_before_sprout1_129.png",
        130: "icon/Texture2D/mdl_non1001_before_sprout1_130.png",
        474: "icon/Texture2D/mdl_non1001_before_sprout1_474.png",
        475: "icon/Texture2D/mdl_non1001_before_sprout1_475.png",
        476: "icon/Texture2D/mdl_non1001_before_sprout1_476.png",
        477: "icon/Texture2D/mdl_non1001_before_sprout1_477.png",
        478: "icon/Texture2D/mdl_non1001_before_sprout1_478.png",
        479: "icon/Texture2D/mdl_non1001_before_sprout1_479.png",
        480: "icon/Texture2D/mdl_non1001_before_sprout1_480.png",
        481: "icon/Texture2D/mdl_non1001_before_sprout1_481.png",
        482: "icon/Texture2D/mdl_non1001_before_sprout1_482.png",
        483: "icon/Texture2D/mdl_non1001_before_sprout1_483.png",
    },
    "mysekai_music_record": {
        0: "icon/Texture2D/item_surplus_music_record.png",
    },
}


RARE_ITEM = {
    "mysekai_material": [5, 12, 20, 24, 32, 33, 61, 62, 63, 64, 65, 66, 93],
    "mysekai_item": [7],
    "mysekai_music_record": [],
    "mysekai_fixture": [118, 119, 120, 121],
}


SUPER_RARE_ITEM = {
    "mysekai_material": [5, 12, 20, 24],
    "mysekai_item": [],
    "mysekai_fixture": [],
    "mysekai_music_record": [],
}


@dataclass(frozen=True)
class SceneConfig:
    site_name: str
    output_stub: str
    image_path: Path
    physical_width: float
    offset_x: float
    offset_y: float
    x_direction: str
    y_direction: str
    reverse_xy: bool


SCENE_CONFIGS = {
    "さいしょの原っぱ": SceneConfig(
        site_name="さいしょの原っぱ",
        output_stub="scene_grassland",
        image_path=BASE_DIR / "img/grassland.png",
        physical_width=33.333,
        offset_x=0,
        offset_y=-40,
        x_direction="x-",
        y_direction="y-",
        reverse_xy=True,
    ),
    "彩りの花畑": SceneConfig(
        site_name="彩りの花畑",
        output_stub="scene_flowergarden",
        image_path=BASE_DIR / "img/flowergarden.png",
        physical_width=24.806,
        offset_x=-62.015,
        offset_y=20.672,
        x_direction="x-",
        y_direction="y-",
        reverse_xy=True,
    ),
    "願いの砂浜": SceneConfig(
        site_name="願いの砂浜",
        output_stub="scene_beach",
        image_path=BASE_DIR / "img/beach.png",
        physical_width=20.513,
        offset_x=0,
        offset_y=80,
        x_direction="x+",
        y_direction="y-",
        reverse_xy=False,
    ),
    "忘れ去られた場所": SceneConfig(
        site_name="忘れ去られた場所",
        output_stub="scene_memorial",
        image_path=BASE_DIR / "img/memorialplace.png",
        physical_width=21.333,
        offset_x=0,
        offset_y=-106.667,
        x_direction="x+",
        y_direction="y-",
        reverse_xy=False,
    ),
}


class ItemDetail(BaseModel):
    id: int
    seq: int
    mysekaiItemType: str
    name: str
    pronunciation: str
    description: str
    iconAssetbundleName: str


class MaterialDetail(BaseModel, kw_only=True):
    id: int
    seq: int
    mysekaiMaterialType: str
    name: str
    pronunciation: str
    description: str
    mysekaiMaterialRarityType: str
    iconAssetbundleName: str
    modelAssetbundleName: str | None = None
    mysekaiSiteIds: list[int]
    mysekaiPhenomenaGroupId: int | None = None


class HarvestObjectDetail(BaseModel):
    id: int
    mysekaiSiteHarvestFixtureType: str
    hp: int
    lastAttackStamina: int
    mysekaiSiteHarvestFixtureRarityType: str
    assetbundleName: str


def parse_map(user_data: dict):
    assert user_data["updatedResources"]["userMysekaiHarvestMaps"]

    harvest_maps: list[Map] = [
        msgspec.json.decode(msgspec.json.encode(mp), type=Map)
        for mp in user_data["updatedResources"]["userMysekaiHarvestMaps"]
    ]

    for mp in harvest_maps:
        mp.siteName = SITE_ID[mp.mysekaiSiteId]

    processed_map = {}
    for mp in harvest_maps:
        logger.debug("正在处理场景：{}", mp.siteName)
        mp_detail = []
        for fixture in mp.userMysekaiSiteHarvestFixtures:
            #  spawned
            #  harvested
            if fixture.userMysekaiSiteHarvestFixtureStatus == "spawned":
                mp_detail.append(
                    {
                        "location": (fixture.positionX, fixture.positionZ),
                        "fixtureId": fixture.mysekaiSiteHarvestFixtureId,
                        "reward": {},
                    }
                )

        for drop in mp.userMysekaiSiteHarvestResourceDrops:
            pos = (drop.positionX, drop.positionZ)
            for i in range(0, len(mp_detail)):
                if mp_detail[i]["location"] != pos:
                    continue

                # mysekai_material
                # mysekai_item
                # mysekai_fixture
                # mysekai_music_record
                mp_detail[i]["reward"].setdefault(drop.resourceType, {})
                mp_detail[i]["reward"][drop.resourceType][drop.resourceId] = (
                    mp_detail[i]["reward"][drop.resourceType].get(drop.resourceId, 0)
                    + drop.quantity
                )
                break

        processed_map[mp.siteName] = mp_detail

    return processed_map


def unmsgpack(data: bytes) -> dict:
    return unpackb(data, strict_map_key=False) if len(data) > 0 else {}


def decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    plaintext: bytes = unpad(cipher.decrypt(ciphertext), 16)
    return plaintext


def encrypt(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    ciphertext: bytes = cipher.encrypt(pad(plaintext, 16))
    return ciphertext


def dumps_json(data: dict, *, indent: int | None) -> str:
    def _default(obj):
        if isinstance(obj, (bytes, bytearray)):
            return base64.b64encode(obj).decode()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(data, ensure_ascii=False, indent=indent, default=_default)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    )


def reward_matches(reward: dict, lookup: dict[str, list[int]]) -> bool:
    for category, items in reward.items():
        candidates = lookup.get(category)
        if not candidates:
            continue
        for item_id in items.keys():
            try:
                if int(item_id) in candidates:
                    return True
            except ValueError:
                continue
    return False


def resolve_icon_path(category: str, item_id: int) -> Path | None:
    mapping = ITEM_TEXTURES.get(category, {})
    candidate = mapping.get(item_id)
    if candidate is None and category == "mysekai_music_record":
        candidate = mapping.get(0)
    if candidate is None:
        return None
    candidate_path = BASE_DIR / candidate
    return candidate_path if candidate_path.exists() else None


_ICON_CACHE: dict[Path, Image.Image] = {}


def load_icon_image(path: Path | None) -> Image.Image | None:
    if path is None:
        return None
    if path not in _ICON_CACHE:
        if not path.exists():
            return None
        _ICON_CACHE[path] = Image.open(path).convert("RGBA")
    return _ICON_CACHE[path]


def resolve_quantity_font(size: int = 10) -> ImageFont.ImageFont:
    font_candidates = (
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf",
        "DejaVuSansMono.ttf",
        "LiberationSans-Regular.ttf",
    )
    for name in font_candidates:
        try:
            return cast(ImageFont.ImageFont, ImageFont.truetype(name, size))
        except OSError:
            continue
    return cast(ImageFont.ImageFont, ImageFont.load_default())


def has_significant_overlap(
    rect: tuple[int, int, int, int],
    other: tuple[int, int, int, int],
    threshold: int = 4,
) -> bool:
    lx = max(rect[0], other[0])
    rx = min(rect[2], other[2])
    ty = max(rect[1], other[1])
    by = min(rect[3], other[3])
    overlap_w = rx - lx
    overlap_h = by - ty
    if overlap_w <= 0 or overlap_h <= 0:
        return False
    return overlap_w > threshold or overlap_h > threshold


def draw_reward_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    reward: dict,
    origin_x: float,
    origin_y: float,
    has_rare: bool,
    has_super: bool,
    font: Any,
    occupied_boxes: list[tuple[int, int, int, int]],
) -> tuple[int, int, int, int] | None:
    entries: list[tuple[str, int, int]] = []
    for category, items in reward.items():
        for item_id, quantity in items.items():
            try:
                entries.append((category, int(item_id), int(quantity)))
            except ValueError:
                continue

    if not entries:
        return None

    padding = 4
    spacing = 2
    icon_size = 24
    panel_width = padding * 2 + len(entries) * icon_size + max(len(entries) - 1, 0) * spacing
    panel_height = padding * 2 + icon_size

    origin_x = max(0, min(int(origin_x), image.width - panel_width))
    origin_y = max(0, min(int(origin_y), image.height - panel_height))

    if has_super:
        panel_color = (255, 0, 0, 160)
    elif has_rare:
        panel_color = (0, 0, 180, 160)
    else:
        panel_color = (138, 138, 138, 180)

    base_x = int(origin_x)
    base_y = int(origin_y)
    offsets = [
        (0, 0),
        (panel_width + 8, 0),
        (0, panel_height + 8),
        (-panel_width - 8, 0),
        (0, -panel_height - 8),
        (panel_width + 8, panel_height + 8),
        (-panel_width - 8, panel_height + 8),
        (panel_width + 8, -panel_height - 8),
        (-panel_width - 8, -panel_height - 8),
    ]

    selected_rect = None
    for dx, dy in offsets:
        candidate_x = max(0, min(base_x + dx, image.width - panel_width))
        candidate_y = max(0, min(base_y + dy, image.height - panel_height))
        rect = (
            candidate_x,
            candidate_y,
            candidate_x + panel_width,
            candidate_y + panel_height,
        )
        if not any(has_significant_overlap(rect, other) for other in occupied_boxes):
            selected_rect = rect
            break

    if selected_rect is None:
        candidate_x = max(0, min(base_x, image.width - panel_width))
        candidate_y = max(0, min(base_y, image.height - panel_height))
        selected_rect = (
            candidate_x,
            candidate_y,
            candidate_x + panel_width,
            candidate_y + panel_height,
        )

    overlay = Image.new("RGBA", (panel_width, panel_height), panel_color)
    image.paste(overlay, (selected_rect[0], selected_rect[1]), overlay)

    for index, (category, item_id, quantity) in enumerate(entries):
        icon_x = selected_rect[0] + padding + index * (icon_size + spacing)
        icon_y = selected_rect[1] + padding
        icon_image = load_icon_image(resolve_icon_path(category, item_id))
        if icon_image is not None:
            resized = icon_image.resize((icon_size, icon_size))
            image.paste(resized, (icon_x, icon_y), resized)

        quantity_text = str(quantity)
        try:
            text_bbox = font.getbbox(quantity_text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except AttributeError:
            text_width, text_height = font.getsize(quantity_text)
        badge_padding = 1
        badge_rect = [
            icon_x + icon_size - text_width - badge_padding * 2,
            icon_y + icon_size - text_height - badge_padding * 2,
            icon_x + icon_size,
            icon_y + icon_size,
        ]
        draw.rectangle(badge_rect, fill=(255, 255, 255, 220))
        text_x = badge_rect[0] + badge_padding
        text_y = badge_rect[1] + badge_padding
        draw.text((text_x, text_y), quantity_text, fill=(0, 0, 0), font=font)

    occupied_boxes.append(selected_rect)
    return selected_rect


def draw_points_on_scene(image: Image.Image, points: list[dict], config: SceneConfig) -> None:
    draw = ImageDraw.Draw(image)
    font = resolve_quantity_font()
    origin_x = image.width / 2 + config.offset_x
    origin_y = image.height / 2 + config.offset_y
    grid_width = config.physical_width
    occupied_boxes: list[tuple[int, int, int, int]] = []

    for point in points:
        x_coord, y_coord = point["location"]
        if config.reverse_xy:
            x_coord, y_coord = y_coord, x_coord

        display_x = (
            origin_x + x_coord * grid_width
            if config.x_direction == "x+"
            else origin_x - x_coord * grid_width
        )
        display_y = (
            origin_y + y_coord * grid_width
            if config.y_direction == "y+"
            else origin_y - y_coord * grid_width
        )

        fill_color = hex_to_rgb(FIXTURE_COLORS.get(point["fixtureId"], "#000000"))
        has_rare = reward_matches(point["reward"], RARE_ITEM)
        has_super = reward_matches(point["reward"], SUPER_RARE_ITEM)
        outline_color = (255, 0, 0) if has_rare else (0, 0, 0)
        radius = 6
        bbox = [
            display_x - radius,
            display_y - radius,
            display_x + radius,
            display_y + radius,
        ]
        draw.ellipse(bbox, fill=fill_color)
        draw.ellipse(bbox, outline=outline_color, width=2)

        label_x = display_x + 6
        label_y = display_y + 6

        panel_rect = draw_reward_panel(
            image,
            draw,
            point["reward"],
            label_x,
            label_y,
            has_rare,
            has_super,
            font,
            occupied_boxes,
        )
        if panel_rect is not None:
            panel_cx = panel_rect[0]
            panel_cy = panel_rect[1]
            draw.line(
                [
                    (int(display_x), int(display_y)),
                    (int(panel_cx), int(panel_cy)),
                ],
                fill=outline_color,
                width=1,
            )


def render_scene_images(harvest: dict, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    for site_name, config in SCENE_CONFIGS.items():
        points = harvest.get(site_name)
        if not points:
            logger.warning("场景 '{}' 没有采集数据，跳过渲染。", site_name)
            continue

        if not config.image_path.exists():
            logger.error("场景 '{}' 的底图不存在：{}", site_name, config.image_path)
            continue

        image = Image.open(config.image_path).convert("RGBA")
        draw_points_on_scene(image, points, config)
        output_path = output_dir / f"{config.output_stub}.png"
        image.save(output_path)
        saved_paths.append(output_path)
        logger.info("已输出场景图片：{}", output_path)

    return saved_paths


def configure_logger(verbose: bool) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        colorize=True,
        level="DEBUG" if verbose else "INFO",
        format="<green>{time:HH:mm:ss}</green> <level>{message}</level>",
    )


def read_payload_bytes(
    *,
    response_file: Path | None,
    response_base64: str | None,
    treat_as_base64: bool,
) -> bytes:
    sources = [bool(response_file), bool(response_base64)]
    if sum(sources) > 1:
        raise ValueError("--response-file 和 --response-base64 只能二选一。")

    if response_file:
        data = response_file.read_bytes()
    elif response_base64 is not None:
        data = response_base64.encode("utf-8")
    else:
        if sys.stdin.isatty():
            raise ValueError(
                "未提供 payload。请使用 --response-file、--response-base64，或通过标准输入传入数据。"
            )
        data = sys.stdin.buffer.read()
        if not data:
            raise ValueError("未从标准输入读取到任何数据。")

    if treat_as_base64:
        try:
            data = base64.b64decode(data, validate=True)
        except Exception as exc:
            raise ValueError("base64 payload 解码失败。") from exc

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
    parser = argparse.ArgumentParser(description="在命令行中解密并解析 Mysekai 响应 payload。")
    parser.add_argument(
        "--response-file",
        type=Path,
        help="包含加密响应 payload 的二进制文件路径。",
    )
    parser.add_argument(
        "--response-base64",
        help="直接通过命令行传入的 base64 编码加密 payload。",
    )
    parser.add_argument(
        "--base64",
        action="store_true",
        help="将输入内容按 base64 处理后再解码，可用于文件内容、命令行输入或标准输入。",
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
        payload = read_payload_bytes(
            response_file=args.response_file,
            response_base64=args.response_base64,
            treat_as_base64=args.base64,
        )
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
