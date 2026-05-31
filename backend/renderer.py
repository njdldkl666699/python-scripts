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
