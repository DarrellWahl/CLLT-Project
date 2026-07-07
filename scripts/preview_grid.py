import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from scripts.models.grid_def import PageLayout


def load_layout(config_path: Path) -> PageLayout:
    config_text = config_path.read_text(encoding="utf-8")
    return PageLayout.from_dict(json.loads(config_text))


def load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except OSError:
            return ImageFont.load_default()


def draw_label(draw: ImageDraw.ImageDraw, position: Tuple[int, int], text: str, font: ImageFont.ImageFont, fill: Tuple[int, int, int, int], outline: Tuple[int, int, int, int]) -> None:
    x, y = position
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def draw_grid_preview(image_path: Path, config_path: Path, output_path: Path) -> None:
    layout = load_layout(config_path)
    with Image.open(image_path) as source:
        page_image = source.convert("RGBA")

    overlay = Image.new("RGBA", page_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    font_large = load_font(44)
    font_small = load_font(28)

    width, height = page_image.size
    draw.rectangle([0, 0, width - 1, height - 1], outline=(0, 255, 0, 255), width=10)
    draw_label(draw, (16, 16), f"Page boundary: {width}x{height}", font_large, fill=(0, 255, 0, 255), outline=(0, 0, 0, 255))

    region_colors = [
        ((0, 112, 255, 200), (0, 112, 255, 255)),
        ((255, 128, 0, 180), (255, 128, 0, 255)),
        ((255, 255, 0, 180), (255, 255, 0, 255)),
        ((0, 255, 255, 180), (0, 255, 255, 255)),
    ]

    for region_index, region in enumerate(layout.regions):
        fill_color, outline_color = region_colors[region_index % len(region_colors)]
        region_left = region.left
        region_top = region.top
        region_right = region.left + region.total_width - 1
        region_bottom = region.top + region.total_height - 1
        draw.rectangle([region_left, region_top, region_right, region_bottom], outline=outline_color, width=8)
        draw_label(draw, (region_left + 12, region_top + 12), f"Region: {region.name}", font_large, fill=outline_color, outline=(0, 0, 0, 255))
        draw_label(draw, (region_left + 12, region_top + 64), f"{region.columns} cols x {region.rows} rows", font_small, fill=outline_color, outline=(0, 0, 0, 255))

        for cell in region.iter_cells():
            x, y, w, h = cell["rect"]
            draw.rectangle([x, y, x + w - 1, y + h - 1], outline=(255, 255, 0, 180), width=4)

            label = f"{cell['row'] + 1},{cell['column'] + 1}"
            text_x = x + 10
            text_y = y + 10
            draw_label(draw, (text_x, text_y), label, font_small, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))

        for row in range(region.rows):
            x, y, w, h = region.cell_rect(row, 0)
            label = f"R{row + 1}"
            label_x = region_left - 110
            label_y = y + max(8, int(h * 0.1))
            draw_label(draw, (label_x, label_y), label, font_small, fill=outline_color, outline=(0, 0, 0, 255))

        for column in range(region.columns):
            x, y, w, h = region.cell_rect(0, column)
            label = f"C{column + 1}"
            label_x = x + max(8, int(w * 0.1))
            label_y = region_top - 48
            draw_label(draw, (label_x, label_y), label, font_small, fill=outline_color, outline=(0, 0, 0, 255))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = Image.alpha_composite(page_image, overlay)
    result.save(output_path)
    print(f"Saved preview overlay to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a visual grid preview for a page layout configuration.")
    parser.add_argument("--page", default="page_1.png", help="Page image file name to preview.")
    parser.add_argument("--image-dir", default="assets/png/pages", help="Directory containing PNG page images.")
    parser.add_argument("--config", default="assets/models/config/page_1_layout.json", help="Page layout configuration file.")
    parser.add_argument("--output", default="assets/png/previews/page_1_grid_preview.png", help="Preview output file path.")
    args = parser.parse_args()

    page_path = Path(args.image_dir) / args.page
    config_path = Path(args.config)
    output_path = Path(args.output)

    if not page_path.exists():
        raise FileNotFoundError(f"Page image not found: {page_path}")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    draw_grid_preview(page_path, config_path, output_path)


if __name__ == "__main__":
    main()
