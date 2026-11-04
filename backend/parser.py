import base64
import json

import msgspec
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from loguru import logger

from .config import SITE_ID
from .structs import (
    Map,
    UserMysekaiSiteHarvestFixture,
    UserMysekaiSiteHarvestResourceDrop,
)


def _coerce_map(raw) -> Map:
    """新版响应把 harvest map 压缩成了位置数组，这里直接还原成 Map 对象。

    新版格式（按字段顺序 positional 编码）：
      [mysekaiSiteId, fixtures, drops]
      fixture: [id, posX, posZ, hp, status, ...新增未知字段]
      drop:    [resourceType, resourceId, posX, posZ, hp, seq, status, quantity, ...新增未知字段]
    旧版 dict 响应仍走 msgspec.convert；新版位置数组按字段顺序直接构造 Struct，
    省去中间 dict 的分配与二次校验。
    """
    if isinstance(raw, dict):
        return msgspec.convert(raw, type=Map)

    site_id, fixtures, drops = raw
    return Map(
        mysekaiSiteId=site_id,
        userMysekaiSiteHarvestFixtures=[
            UserMysekaiSiteHarvestFixture(f[0], f[1], f[2], f[3], f[4]) for f in fixtures or []
        ],
        userMysekaiSiteHarvestResourceDrops=[
            UserMysekaiSiteHarvestResourceDrop(d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7])
            for d in drops or []
        ],
    )


def parse_map(user_data: dict):
    assert user_data["updatedResources"]["userMysekaiHarvestMaps"]

    harvest_maps: list[Map] = [
        _coerce_map(mp) for mp in user_data["updatedResources"]["userMysekaiHarvestMaps"]
    ]

    for mp in harvest_maps:
        mp.siteName = SITE_ID[mp.mysekaiSiteId]

    processed_map = {}
    for mp in harvest_maps:
        logger.debug("正在处理场景：{}", mp.siteName)
        mp_detail = []
        # 位置 -> 首个 spawned fixture 在 mp_detail 中的索引，drop 匹配 O(1) 命中
        index_by_pos: dict[tuple[int, int], int] = {}
        for fixture in mp.userMysekaiSiteHarvestFixtures:
            #  spawned
            #  harvested
            if fixture.userMysekaiSiteHarvestFixtureStatus == "spawned":
                index_by_pos.setdefault((fixture.positionX, fixture.positionZ), len(mp_detail))
                mp_detail.append(
                    {
                        "location": (fixture.positionX, fixture.positionZ),
                        "fixtureId": fixture.mysekaiSiteHarvestFixtureId,
                        "reward": {},
                    }
                )

        for drop in mp.userMysekaiSiteHarvestResourceDrops:
            idx = index_by_pos.get((drop.positionX, drop.positionZ))
            if idx is None:
                continue

            # mysekai_material
            # mysekai_item
            # mysekai_fixture
            # mysekai_music_record
            detail = mp_detail[idx]
            by_type = detail["reward"].setdefault(drop.resourceType, {})
            by_type[drop.resourceId] = by_type.get(drop.resourceId, 0) + drop.quantity

        processed_map[mp.siteName] = mp_detail

    return processed_map


def unmsgpack(data: bytes) -> dict:
    # msgspec 的 Rust 解码器（实测真实响应可直接解码，无需 python-msgpack 兜底）
    return msgspec.msgpack.decode(data) if len(data) > 0 else {}


def decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    plaintext: bytes = unpad(cipher.decrypt(ciphertext), 16)
    return plaintext


def encrypt(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    ciphertext: bytes = cipher.encrypt(pad(plaintext, 16))
    return ciphertext


def _json_default(obj):
    if isinstance(obj, (bytes, bytearray)):
        return base64.b64encode(obj).decode()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def dumps_json(data: dict, *, indent: int | None) -> str:
    if indent is None:
        # 紧凑输出走 msgspec（Rust 实现），bytes 值经 enc_hook 转 base64
        return msgspec.json.encode(data, enc_hook=_json_default).decode("utf-8")
    return json.dumps(data, ensure_ascii=False, indent=indent, default=_json_default)
