import math
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from .config import (
    BASE_DIR,
    FIXTURE_COLORS,
    ITEM_TEXTURES,
    RARE_ITEM,
    SCENE_CONFIGS,
    SUPER_RARE_ITEM,
    SceneConfig,
)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    )


# import 时预计算，避免渲染循环里重复解析 hex 字符串
FIXTURE_RGB: dict[int, tuple[int, int, int]] = {
    fixture_id: hex_to_rgb(color) for fixture_id, color in FIXTURE_COLORS.items()
}

# 稀有度查找表预转 frozenset，成员判断 O(1)
RARE_ITEM_SETS: dict[str, frozenset[int]] = {
    category: frozenset(int(i) for i in items) for category, items in RARE_ITEM.items()
}
SUPER_RARE_ITEM_SETS: dict[str, frozenset[int]] = {
    category: frozenset(int(i) for i in items) for category, items in SUPER_RARE_ITEM.items()
}


def check_reward_rarity(reward: dict) -> tuple[bool, bool]:
    """单次遍历 reward，同时判定 (has_rare, has_super)。"""
    has_rare = False
    has_super = False
    for category, items in reward.items():
        rare_set = RARE_ITEM_SETS.get(category)
        super_set = SUPER_RARE_ITEM_SETS.get(category)
        if rare_set is None and super_set is None:
            continue
        for item_id in items:
            if not has_rare and rare_set is not None and item_id in rare_set:
                has_rare = True
            if not has_super and super_set is not None and item_id in super_set:
                has_super = True
        if has_rare and has_super:
            break
    return has_rare, has_super


_ICON_PATH_CACHE: dict[tuple[str, int], Path | None] = {}


def resolve_icon_path(category: str, item_id: int) -> Path | None:
    """解析图标路径并缓存结果，避免每次查询都做磁盘 stat。"""
    key = (category, item_id)
    if key in _ICON_PATH_CACHE:
        return _ICON_PATH_CACHE[key]
    mapping = ITEM_TEXTURES.get(category, {})
    candidate = mapping.get(item_id)
    if candidate is None and category == "mysekai_music_record":
        candidate = mapping.get(0)
    resolved = BASE_DIR / candidate if candidate is not None else None
    if resolved is not None and not resolved.exists():
        resolved = None
    _ICON_PATH_CACHE[key] = resolved
    return resolved


_ICON_CACHE: dict[Path, Image.Image] = {}
_RESIZED_ICON_CACHE: dict[tuple[Path, int], Image.Image] = {}


def load_icon_image(path: Path | None, size: int) -> Image.Image | None:
    """返回缩放到 size 的图标；原图解码与缩放结果均缓存，避免重复解码/缩放。"""
    if path is None:
        return None
    icon = _ICON_CACHE.get(path)
    if icon is None:
        if not path.exists():
            return None
        icon = Image.open(path).convert("RGBA")
        _ICON_CACHE[path] = icon
    resized = _RESIZED_ICON_CACHE.get((path, size))
    if resized is None:
        resized = icon.resize((size, size))
        _RESIZED_ICON_CACHE[(path, size)] = resized
    return resized


_FONT_CACHE: dict[int, ImageFont.ImageFont] = {}


def resolve_quantity_font(size: int = 10) -> ImageFont.ImageFont:
    font = _FONT_CACHE.get(size)
    if font is not None:
        return font
    font_candidates = (
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf",
        "DejaVuSansMono.ttf",
        "LiberationSans-Regular.ttf",
    )
    for name in font_candidates:
        try:
            font = cast(ImageFont.ImageFont, ImageFont.truetype(name, size))
            break
        except OSError:
            continue
    else:
        font = cast(ImageFont.ImageFont, ImageFont.load_default())
    _FONT_CACHE[size] = font
    return font


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


class OccupancyGrid:
    """空间哈希网格，用于面板碰撞检测。

    旧实现对所有已放置面板线性扫描（每个新面板 O(P)、整体 O(P²)）；
    网格把已占用矩形登记到其覆盖的单元中，查询只与候选矩形所覆盖单元里的
    少量矩形做精确重叠判断。凡与候选矩形有实际重叠的已放置矩形，必然与它
    共享至少一个单元，因此结果与线性扫描完全一致，密集场景下接近 O(1) 均摊。
    """

    def __init__(self, width: int, height: int, cell_size: int = 128):
        self.cell_size = cell_size
        self.cols = max(1, math.ceil(width / cell_size))
        self.rows = max(1, math.ceil(height / cell_size))
        self.cells: list[set[int]] = [set() for _ in range(self.cols * self.rows)]
        self.boxes: list[tuple[int, int, int, int]] = []

    def _cell_range(self, rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        lx, ty, rx, by = rect
        c0 = max(0, lx // self.cell_size)
        c1 = min(self.cols - 1, rx // self.cell_size)
        r0 = max(0, ty // self.cell_size)
        r1 = min(self.rows - 1, by // self.cell_size)
        return c0, c1, r0, r1

    def collides(self, rect: tuple[int, int, int, int]) -> bool:
        c0, c1, r0, r1 = self._cell_range(rect)
        for row in range(r0, r1 + 1):
            base = row * self.cols
            for col in range(c0, c1 + 1):
                for idx in self.cells[base + col]:
                    if has_significant_overlap(rect, self.boxes[idx]):
                        return True
        return False

    def add(self, rect: tuple[int, int, int, int]) -> None:
        idx = len(self.boxes)
        self.boxes.append(rect)
        c0, c1, r0, r1 = self._cell_range(rect)
        for row in range(r0, r1 + 1):
            base = row * self.cols
            for col in range(c0, c1 + 1):
                self.cells[base + col].add(idx)


_BACKGROUND_CACHE: dict[Path, Image.Image] = {}


def load_background_image(image_path: Path) -> Image.Image:
    """缓存解码后的底图，每次渲染用内存拷贝代替完整 PNG 解码。"""
    background = _BACKGROUND_CACHE.get(image_path)
    if background is None:
        background = Image.open(image_path).convert("RGBA")
        _BACKGROUND_CACHE[image_path] = background
    return background.copy()


_OVERLAY_CACHE: dict[tuple[int, int, int, int, int, int], Image.Image] = {}


def get_panel_overlay(width: int, height: int, color: tuple[int, int, int, int]) -> Image.Image:
    """面板底色只有 3 种、宽度离散，按 (尺寸, 颜色) 缓存，避免高频小对象分配。"""
    key = (width, height, *color)
    overlay = _OVERLAY_CACHE.get(key)
    if overlay is None:
        overlay = Image.new("RGBA", (width, height), color)
        _OVERLAY_CACHE[key] = overlay
    return overlay


def draw_reward_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    reward: dict,
    origin_x: float,
    origin_y: float,
    has_rare: bool,
    has_super: bool,
    font: Any,
    occupied: OccupancyGrid,
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
        if not occupied.collides(rect):
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

    overlay = get_panel_overlay(panel_width, panel_height, panel_color)
    image.paste(overlay, (selected_rect[0], selected_rect[1]), overlay)

    for index, (category, item_id, quantity) in enumerate(entries):
        icon_x = selected_rect[0] + padding + index * (icon_size + spacing)
        icon_y = selected_rect[1] + padding
        icon_image = load_icon_image(resolve_icon_path(category, item_id), icon_size)
        if icon_image is not None:
            image.paste(icon_image, (icon_x, icon_y), icon_image)

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

    occupied.add(selected_rect)
    return selected_rect


def draw_points_on_scene(image: Image.Image, points: list[dict], config: SceneConfig) -> None:
    draw = ImageDraw.Draw(image)
    font = resolve_quantity_font()
    origin_x = image.width / 2 + config.offset_x
    origin_y = image.height / 2 + config.offset_y
    grid_width = config.physical_width
    occupied = OccupancyGrid(image.width, image.height)

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

        fill_color = FIXTURE_RGB.get(point["fixtureId"], (0, 0, 0))
        has_rare, has_super = check_reward_rarity(point["reward"])
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
            occupied,
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


def _render_scene(
    harvest: dict, site_name: str, config: SceneConfig
) -> tuple[str, Image.Image] | None:
    points = harvest.get(site_name)
    if not points:
        logger.warning("场景 '{}' 没有采集数据，跳过渲染。", site_name)
        return None

    if not config.image_path.exists():
        logger.error("场景 '{}' 的底图不存在：{}", site_name, config.image_path)
        return None

    image = load_background_image(config.image_path)
    draw_points_on_scene(image, points, config)
    return config.output_stub, image


def _render_scene_to_file(
    harvest: dict, site_name: str, config: SceneConfig, output_dir: Path
) -> Path | None:
    result = _render_scene(harvest, site_name, config)
    if result is None:
        return None
    stub, image = result
    # compress_level=1：编码时间大幅下降，文件略大（本地传输场景可接受）
    output_path = output_dir / f"{stub}.png"
    image.save(output_path, compress_level=1)
    logger.info("已输出场景图片：{}", output_path)
    return output_path


def _render_scene_to_bytes(
    harvest: dict,
    site_name: str,
    config: SceneConfig,
    *,
    quality: int,
    method: int,
) -> tuple[str, bytes] | None:
    result = _render_scene(harvest, site_name, config)
    if result is None:
        return None
    stub, image = result
    buffer = BytesIO()
    # 有损 WebP：体积约为 PNG compress_level=1 的 1/10，编码耗时不升反降
    image.save(buffer, format="WEBP", quality=quality, method=method)
    logger.info("已渲染场景图片：{}", stub)
    return stub, buffer.getvalue()


def render_scene_images(harvest: dict, output_dir: Path) -> list[Path]:
    """渲染所有场景并保存为 PNG 文件（CLI 用）。

    场景间互不依赖，渲染与 PNG 编码全部在工作线程内并行完成
    （PIL 编解码会释放 GIL，多核下接近线性加速）。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    with ThreadPoolExecutor(max_workers=len(SCENE_CONFIGS) or 1) as executor:
        futures = [
            executor.submit(_render_scene_to_file, harvest, site_name, config, output_dir)
            for site_name, config in SCENE_CONFIGS.items()
        ]
        for future in futures:
            output_path = future.result()
            if output_path is not None:
                saved_paths.append(output_path)

    return saved_paths


def render_scene_images_webp(
    harvest: dict, *, quality: int = 90, method: int = 4
) -> dict[str, bytes]:
    """渲染所有场景到内存的有损 WebP，返回 {output_stub: WebP 字节}（mitm 插件推送用）。

    1920x1080 实测：quality=90/method=4 总体积约 1.2MB（PNG compress_level=1
    约 11.5MB），base64 后的 WebSocket 载荷约缩小 10 倍。
    注意：无损 WebP 对这类截图内容编码极慢（~10s），不要用。
    """
    outputs: dict[str, bytes] = {}

    with ThreadPoolExecutor(max_workers=len(SCENE_CONFIGS) or 1) as executor:
        futures = [
            executor.submit(
                _render_scene_to_bytes,
                harvest,
                site_name,
                config,
                quality=quality,
                method=method,
            )
            for site_name, config in SCENE_CONFIGS.items()
        ]
        for future in futures:
            result = future.result()
            if result is not None:
                stub, webp_bytes = result
                outputs[stub] = webp_bytes

    return outputs
