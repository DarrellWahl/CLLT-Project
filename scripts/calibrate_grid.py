import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Ensure the repository root is importable when running as a script
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from PIL import Image
from scripts.models.calibration import GridCalibration
from scripts.models.grid_def import GridRegion, PageLayout


def load_image_size(image_path: Path) -> Dict[str, int]:
    with Image.open(image_path) as image:
        return {"width": image.width, "height": image.height}


def load_config(config_path: Path) -> Optional[Dict]:
    if not config_path.exists():
        return None
    return json.loads(config_path.read_text(encoding="utf-8"))


def save_config(config_path: Path, data: Dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a page grid calibration config.")
    parser.add_argument("--page", required=True, help="Page image name, e.g. page_1.png")
    parser.add_argument("--image-dir", default="assets/png/pages", help="Directory containing exported page PNGs.")
    parser.add_argument("--config", default="assets/models/config/page_1_layout.json", help="Layout config path.")
    parser.add_argument("--region-name", required=True, help="Logical region name for the grid section.")
    parser.add_argument("--left", type=int, required=True, help="Left X coordinate of the region in pixels.")
    parser.add_argument("--top", type=int, required=True, help="Top Y coordinate of the region in pixels.")
    parser.add_argument("--right", type=int, required=True, help="Right X coordinate of the region in pixels.")
    parser.add_argument("--bottom", type=int, required=True, help="Bottom Y coordinate of the region in pixels.")
    parser.add_argument("--columns", type=int, required=True, help="Number of columns in the region.")
    parser.add_argument("--rows", type=int, required=True, help="Number of rows in the region.")
    parser.add_argument("--horizontal-spacing", type=int, default=0, help="Horizontal spacing between cells.")
    parser.add_argument("--vertical-spacing", type=int, default=0, help="Vertical spacing between cells.")
    args = parser.parse_args()

    image_path = Path(args.image_dir) / args.page
    if not image_path.exists():
        raise FileNotFoundError(f"Page image not found: {image_path}")

    image_size = load_image_size(image_path)
    if image_size["width"] != 6736 or image_size["height"] != 9536:
        print("Warning: image dimensions do not match the currently expected 6736x9536.")

    config_path = Path(args.config)
    config_data = load_config(config_path) or {
        "page_name": args.page.replace('.png', ''),
        "image_width": image_size["width"],
        "image_height": image_size["height"],
        "regions": [],
    }

    left_top = (args.left, args.top)
    right_bottom = (args.right, args.bottom)
    region = GridRegion(
        name=args.region_name,
        left=args.left,
        top=args.top,
        columns=args.columns,
        rows=args.rows,
        column_width=int(round((args.right - args.left - args.horizontal_spacing * (args.columns - 1)) / args.columns)),
        row_height=int(round((args.bottom - args.top - args.vertical_spacing * (args.rows - 1)) / args.rows)),
        horizontal_spacing=args.horizontal_spacing,
        vertical_spacing=args.vertical_spacing,
    )

    config_data["regions"] = [region.to_dict() if region_data.get("name") == args.region_name else region_data for region_data in config_data.get("regions", [])]
    if not any(region_data.get("name") == args.region_name for region_data in config_data.get("regions", [])):
        config_data["regions"].append(region.to_dict())

    save_config(config_path, config_data)
    print(f"Saved region '{args.region_name}' to {config_path}")
    print(f"Page size: {image_size['width']} x {image_size['height']}")
    print(f"Computed cell size: {region.column_width} x {region.row_height}")


if __name__ == "__main__":
    main()
