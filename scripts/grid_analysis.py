import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image
import numpy as np

root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))
from scripts.models.grid_def import PageLayout


CoordinateSegment = Tuple[int, int]


def load_layout(config_path: Path) -> PageLayout:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return PageLayout.from_dict(data)


def print_layout_report(layout: PageLayout) -> None:
    print(f"Page layout report for '{layout.page_name}'")
    print(f"Image size: {layout.image_width} x {layout.image_height}")
    print(f"Regions: {len(layout.regions)}")
    print()

    for region in layout.regions:
        print(f"Region: {region.name}")
        print(f"  origin: ({region.left}, {region.top})")
        print(f"  size: {region.total_width} x {region.total_height}")
        print(f"  columns: {region.columns}")
        print(f"  rows: {region.rows}")
        print(f"  cell size: {region.column_width} x {region.row_height}")
        print(f"  spacing: h={region.horizontal_spacing} v={region.vertical_spacing}")
        print(f"  total cells: {region.columns * region.rows}")
        print()


def report_image_size(image_path: Path) -> Dict[str, Any]:
    with Image.open(image_path) as image:
        return {"width": image.width, "height": image.height, "mode": image.mode}


def threshold_image(image: Image.Image, threshold: int = 245) -> np.ndarray:
    grayscale = np.array(image.convert("L"))
    return grayscale < threshold


def project_segments(mask: np.ndarray, axis: int, min_width: int = 8) -> List[CoordinateSegment]:
    projection = mask.sum(axis=axis)
    segments: List[CoordinateSegment] = []
    start: int = -1
    for index, value in enumerate(projection):
        if value > 0 and start < 0:
            start = index
        elif value == 0 and start >= 0:
            if index - start >= min_width:
                segments.append((start, index - 1))
            start = -1
    if start >= 0 and len(projection) - start >= min_width:
        segments.append((start, len(projection) - 1))
    return segments


def analyze_page_layout(image_path: Path) -> Dict[str, Any]:
    with Image.open(image_path) as image:
        mask = threshold_image(image)

    row_segments = project_segments(mask, axis=1, min_width=10)
    col_segments = project_segments(mask, axis=0, min_width=10)
    row_heights = [end - start + 1 for start, end in row_segments]
    col_widths = [end - start + 1 for start, end in col_segments]

    return {
        "row_segments": row_segments,
        "col_segments": col_segments,
        "row_heights": row_heights,
        "col_widths": col_widths,
        "row_count": len(row_segments),
        "col_count": len(col_segments),
    }


def print_analysis_report(image_path: Path) -> None:
    analysis = analyze_page_layout(image_path)
    print("Automatic page grid analysis")
    print("-----------------------------")
    print(f"Detected row groups: {analysis['row_count']}")
    print(f"Detected column groups: {analysis['col_count']}")
    print(f"Row heights: {analysis['row_heights'][:10]}{'...' if len(analysis['row_heights']) > 10 else ''}")
    print(f"Column widths: {analysis['col_widths'][:10]}{'...' if len(analysis['col_widths']) > 10 else ''}")
    print()
    print("Row segments:")
    for start, end in analysis["row_segments"]:
        print(f"  {start}-{end} ({end - start + 1})")
    print()
    print("Column segments:")
    for start, end in analysis["col_segments"][:20]:
        print(f"  {start}-{end} ({end - start + 1})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze page grid models for CLLT sign extraction.")
    parser.add_argument("--page", required=True, help="Page image name, e.g. page_1.png")
    parser.add_argument("--image-dir", default="assets/png/pages", help="Directory containing exported page PNGs.")
    parser.add_argument("--config", default="assets/models/config/page_1_layout.json", help="Path to page layout config.")
    parser.add_argument("--auto", action="store_true", help="Run automatic layout analysis from the page image.")
    args = parser.parse_args()

    image_path = Path(args.image_dir) / args.page
    if not image_path.exists():
        raise FileNotFoundError(f"Page image not found: {image_path}")

    size_info = report_image_size(image_path)
    print("Image analysis")
    print("--------------")
    print(f"Image: {image_path}")
    print(f"Size: {size_info['width']} x {size_info['height']}")
    print(f"Mode: {size_info['mode']}")
    print()

    if args.auto:
        print_analysis_report(image_path)
    else:
        config_path = Path(args.config)
        if config_path.exists():
            layout = load_layout(config_path)
            print_layout_report(layout)
        else:
            print(f"No layout config found at {config_path}")
            print("Create a layout config with the page dimensions and one or more grid regions.")
            print("Example config: assets/models/config/page_1_layout.json")
            print("Use scripts/calibrate_grid.py to generate or update that config.")


if __name__ == "__main__":
    main()
