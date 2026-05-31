from msgspec import Struct as BaseModel


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
