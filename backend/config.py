import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from msgspec import Struct as BaseModel

load_dotenv()

AES_KEY = os.getenv("AES_KEY", "").encode("utf-8")
AES_IV = os.getenv("AES_IV", "").encode("utf-8")
if not AES_KEY or not AES_IV:
    logger.error("必须在 .env 文件中设置 AES_KEY 和 AES_IV。")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent

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
        67: "icon/Texture2D/item_birthday_flower.png",
        68: "icon/Texture2D/item_birthday_flower.png",
        69: "icon/Texture2D/item_birthday_flower.png",
        70: "icon/Texture2D/item_birthday_flower.png",
        71: "icon/Texture2D/item_birthday_flower.png",
        72: "icon/Texture2D/item_birthday_flower.png",
        73: "icon/Texture2D/item_birthday_flower.png",
        74: "icon/Texture2D/item_birthday_flower.png",
        75: "icon/Texture2D/item_birthday_flower.png",
        77: "icon/Texture2D/item_birthday_flower.png",
        83: "icon/Texture2D/item_birthday_flower.png",
        84: "icon/Texture2D/item_birthday_flower.png",
        85: "icon/Texture2D/item_birthday_flower.png",
        88: "icon/Texture2D/item_birthday_flower.png",
        89: "icon/Texture2D/item_birthday_flower.png",
        90: "icon/Texture2D/item_birthday_flower.png",
        91: "icon/Texture2D/item_birthday_flower.png",
        92: "icon/Texture2D/item_birthday_flower.png",
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
    "material": {
        17: "icon/Texture2D/material17.png",  # 心愿种子
        170: "icon/Texture2D/material170.png",  # 世界碎片
    },
}


RARE_ITEM = {
    "mysekai_material": [5, 12, 20, 24, 32, 33, 61, 62, 63, 64, 65, 66, 93],
    "mysekai_item": [7],
    "mysekai_music_record": [],
    "mysekai_fixture": [118, 119, 120, 121],
}


SUPER_RARE_ITEM = {
    "mysekai_material": [5, 12, 20, 24, *range(67, 93)],
    "mysekai_item": [],
    "mysekai_fixture": [],
    "mysekai_music_record": [],
    "material": [17, 170],
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
