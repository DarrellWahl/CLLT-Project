import re
import json
import numpy as np
from pathlib import Path

import cv2
from PIL import Image
import pytesseract
import csv


def load_image(path: Path):
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Unable to read image: {path}")
    return img


def find_sign_boxes(image, min_area=1200, max_area=250000, min_dim=24):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect colored sign areas and dark text/shapes together.
    _, gray_thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    red_lower1 = np.array([0, 60, 50])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([160, 60, 50])
    red_upper2 = np.array([179, 255, 255])
    blue_lower = np.array([90, 50, 50])
    blue_upper = np.array([140, 255, 255])

    red_mask = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
    color_mask = cv2.bitwise_or(red_mask, red_mask2)
    color_mask = cv2.bitwise_or(color_mask, blue_mask)

    mask = cv2.bitwise_or(gray_thresh, color_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < min_area or area > max_area:
            continue
        if w < min_dim or h < min_dim:
            continue
        aspect_ratio = max(w / h, h / w)
        if aspect_ratio > 5:
            continue
        boxes.append((x, y, w, h))

    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    return boxes


def normalize_boxes(boxes, row_tol=40):
    rows = []
    for b in boxes:
        x, y, w, h = b
        placed = False
        for row in rows:
            if abs(row[0][1] - y) < row_tol:
                row.append(b)
                placed = True
                break
        if not placed:
            rows.append([b])

    normalized = []
    for row in rows:
        row_sorted = sorted(row, key=lambda b: b[0])
        normalized.extend(row_sorted)

    return normalized


def crop_and_save_boxes(image, boxes, output_dir: Path, page_number: int):
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = normalize_boxes(boxes)
    metadata = []
    for idx, (x, y, w, h) in enumerate(rows, start=1):
        pad = 6
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(image.shape[1], x + w + pad)
        y1 = min(image.shape[0], y + h + pad)
        crop = image[y0:y1, x0:x1]
        filename = f"page{page_number:01d}_sign_{idx:03}.png"
        out_path = output_dir / filename
        cv2.imwrite(str(out_path), crop)
        metadata.append({
            "page": page_number,
            "index": idx,
            "filename": filename,
            "x": int(x),
            "y": int(y),
            "w": int(w),
            "h": int(h),
        })
    return metadata


def save_metadata_csv(metadata, csv_path: Path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["page", "index", "filename", "x", "y", "w", "h"])
        writer.writeheader()
        writer.writerows(metadata)


def ocr_legend_page(legend_image_path: Path, lang="eng"):
    img = Image.open(legend_image_path)
    text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
    return text


def parse_legend_text(text):
    pattern = re.compile(r"([A-Z]{1,2}\d{3})\s*[–-]?\s*(.+)")
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            code = match.group(1).strip()
            description = match.group(2).strip()
            entries.append({"code": code, "description": description})
    return entries


def save_json(data, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    source_dir = Path("assets/png/pages")
    output_dir = Path("output/signs")
    metadata_csv = Path("output/signs_metadata.csv")
    legend_json = Path("output/legend.json")

    metadata = []
    for page_num in range(1, 5):
        path = source_dir / f"page_{page_num}.png"
        if not path.exists():
            print(f"Skipping missing page: {path}")
            continue
        image = load_image(path)
        boxes = find_sign_boxes(image)
        print(f"Page {page_num}: found {len(boxes)} candidate boxes")
        page_meta = crop_and_save_boxes(image, boxes, output_dir, page_num)
        metadata.extend(page_meta)

    save_metadata_csv(metadata, metadata_csv)
    print(f"Saved metadata CSV with {len(metadata)} entries to {metadata_csv}")

    legend_path = source_dir / "page_5.png"
    if legend_path.exists():
        text = ocr_legend_page(legend_path)
        entries = parse_legend_text(text)
        save_json(entries, legend_json)
        print(f"Saved legend JSON with {len(entries)} entries to {legend_json}")
    else:
        print("Legend page not found; skipping OCR.")


if __name__ == "__main__":
    main()
