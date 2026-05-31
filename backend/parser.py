import base64
import json

import msgspec
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from loguru import logger
from msgpack import unpackb

from .config import SITE_ID
from .structs import Map


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
