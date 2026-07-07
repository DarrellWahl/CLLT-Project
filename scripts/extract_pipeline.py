import csv
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import pytesseract
    try:
        _ = pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
    except Exception:
        pytesseract = None  # type: ignore
        TESSERACT_AVAILABLE = False
except ImportError:
    pytesseract = None  # type: ignore
    TESSERACT_AVAILABLE = False

root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

CONFIG_PATH = root_path / "assets" / "config" / "extraction_config.json"
BoundingBox = Tuple[int, int, int, int]

@dataclass
class CropMetadata:
    filename: str
    page: int
    code: str
    status: str
    confidence: float
    x: int
    y: int
    w: int
    h: int
    padded_x: int
    padded_y: int
    padded_w: int
    padded_h: int
    timestamp: str
    retries: int = 0
    warnings: List[str] = field(default_factory=list)


@dataclass
class SignCandidate:
    id: int
    bounding_box: BoundingBox
    contour_boxes: List[BoundingBox]
    page: int
    status: str = 'candidate'
    confidence: float = 0.0
    code: str = ''
    description: str = ''
    warnings: List[str] = field(default_factory=list)

    def area(self) -> int:
        return self.bounding_box[2] * self.bounding_box[3]

    def to_metadata(self, timestamp: str) -> CropMetadata:
        x, y, w, h = self.bounding_box
        padded_x, padded_y, padded_w, padded_h = self.bounding_box
        return CropMetadata(
            filename=f"page{self.page:01d}_{self.code or 'unknown'}_{self.id:03}.png",
            page=self.page,
            code=self.code,
            status=self.status,
            confidence=self.confidence,
            x=x,
            y=y,
            w=w,
            h=h,
            padded_x=padded_x,
            padded_y=padded_y,
            padded_w=padded_w,
            padded_h=padded_h,
            timestamp=timestamp,
            retries=0,
            warnings=list(self.warnings),
        )


@dataclass
class ExtractionStats:
    page: int
    total_contours: int = 0
    contours_rejected: int = 0
    contours_merged: int = 0
    candidates: int = 0
    rejected_candidates: int = 0
    duplicate_removed: int = 0
    exported_signs: int = 0
    avg_crop_area: float = 0.0
    avg_padding: float = 0.0
    avg_confidence: float = 0.0
    ocr_enabled: bool = False
    ocr_success_rate: float = 0.0
    missing_codes: int = 0
    missing_descriptions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    with path.open(encoding='utf-8') as f:
        return json.load(f)


def make_dirs(config: Dict[str, Any]) -> None:
    for key in ["signs_output_dir", "verification_dir", "metadata_dir", "logs_dir"]:
        Path(root_path / config[key]).mkdir(parents=True, exist_ok=True)


def deterministic_sort(boxes: List[BoundingBox]) -> List[BoundingBox]:
    return sorted(boxes, key=lambda b: (b[1], b[0], b[2], b[3]))


def box_iou(a: BoundingBox, b: BoundingBox) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = aw * ah + bw * bh - inter
    return inter / union


def clamp_box(box: BoundingBox, width: int, height: int) -> BoundingBox:
    x, y, w, h = box
    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    w = max(1, min(w, width - x))
    h = max(1, min(h, height - y))
    return x, y, w, h


def pad_box(box: BoundingBox, image_size: Tuple[int, int], padding: Dict[str, Any]) -> BoundingBox:
    x, y, w, h = box
    page_w, page_h = image_size
    left = max(int(round(w * padding["left"])), padding["min_pixels"])
    right = max(int(round(w * padding["right"])), padding["min_pixels"])
    top = max(int(round(h * padding["top"])), padding["min_pixels"])
    bottom = max(int(round(h * padding["bottom"])), padding["min_pixels"])
    x = max(0, x - left)
    y = max(0, y - top)
    w = min(page_w - x, w + left + right)
    h = min(page_h - y, h + top + bottom)
    return x, y, w, h


def expand_to_enclose(box: BoundingBox, image_size: Tuple[int, int], step: int, max_expand: int) -> BoundingBox:
    x, y, w, h = box
    page_w, page_h = image_size
    x = max(0, x - step)
    y = max(0, y - step)
    w = min(page_w - x, w + 2 * step)
    h = min(page_h - y, h + 2 * step)
    if (w - box[2]) > max_expand or (h - box[3]) > max_expand:
        return box
    return x, y, w, h


def detect_page_layout(image: np.ndarray, page_number: int, config: Dict[str, Any]) -> Tuple[BoundingBox, str]:
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (15, 15), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    row_density = (binary > 0).sum(axis=1).astype(float) / width
    candidate_rows = [i for i, v in enumerate(row_density) if v > config["page_analysis"]["content_threshold"]]
    if not candidate_rows:
        return (0, 0, width, height), 'default'
    top = max(0, min(candidate_rows) - int(height * config["page_analysis"]["header_ignore_ratio"]))
    bottom = min(height, max(candidate_rows) + int(height * config["page_analysis"]["footer_ignore_ratio"]))
    page_type = 'page5' if page_number == 5 else 'page_standard'
    return (0, top, width, bottom - top), page_type


def build_sign_mask(image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    masks = []
    masks.append(cv2.inRange(hsv, np.array([0, 40, 40]), np.array([12, 255, 255])))
    masks.append(cv2.inRange(hsv, np.array([160, 40, 40]), np.array([179, 255, 255])))
    masks.append(cv2.inRange(hsv, np.array([90, 40, 40]), np.array([140, 255, 255])))
    masks.append(cv2.inRange(hsv, np.array([15, 70, 70]), np.array([40, 255, 255])))
    masks.append(cv2.inRange(hsv, np.array([100, 4, 0]), np.array([179, 255, 255])))
    color_mask = masks[0]
    for m in masks[1:]:
        color_mask = cv2.bitwise_or(color_mask, m)
    mask = cv2.bitwise_or(bw, color_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)
    return opened


def detect_contour_boxes(mask: np.ndarray, config: Dict[str, Any]) -> List[BoundingBox]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < config["detection"]["min_area"] or area > config["detection"]["max_area"]:
            continue
        if w < config["detection"]["min_side"] or h < config["detection"]["min_side"]:
            continue
        aspect_ratio = max(w / float(h), h / float(w))
        if aspect_ratio > config["detection"]["max_aspect_ratio"]:
            continue
        boxes.append((x, y, w, h))
    return boxes, len(contours)


def detect_edge_boxes(image: np.ndarray, config: Dict[str, Any]) -> Tuple[List[BoundingBox], int]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < config["detection"]["min_area"] or area > config["detection"]["max_area"]:
            continue
        if w < config["detection"]["min_side"] or h < config["detection"]["min_side"]:
            continue
        aspect_ratio = max(w / float(h), h / float(w))
        if aspect_ratio > config["detection"]["max_aspect_ratio"]:
            continue
        boxes.append((x, y, w, h))
    return boxes, len(contours)


def merge_boxes(boxes: List[BoundingBox], config: Dict[str, Any]) -> List[BoundingBox]:
    if not boxes:
        return []
    boxes = deterministic_sort(boxes)
    merged = []
    while boxes:
        base = boxes.pop(0)
        bx, by, bw, bh = base
        changed = True
        while changed:
            changed = False
            for idx, other in enumerate(boxes):
                iou = box_iou(base, other)
                if iou >= config["detection"]["merge_iou"] or _distance_between(base, other) <= config["detection"]["merge_distance"]:
                    ox, oy, ow, oh = other
                    nx = min(bx, ox)
                    ny = min(by, oy)
                    nx2 = max(bx + bw, ox + ow)
                    ny2 = max(by + bh, oy + oh)
                    base = (nx, ny, nx2 - nx, ny2 - ny)
                    bx, by, bw, bh = base
                    boxes.pop(idx)
                    changed = True
                    break
        merged.append(base)
    return deterministic_sort(merged)


def _distance_between(a: BoundingBox, b: BoundingBox) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    a_cx, a_cy = ax + aw / 2.0, ay + ah / 2.0
    b_cx, b_cy = bx + bw / 2.0, by + bh / 2.0
    return math.hypot(a_cx - b_cx, a_cy - b_cy)


def reject_false_positives(candidates: List[BoundingBox], page_box: BoundingBox, config: Dict[str, Any]) -> List[BoundingBox]:
    x0, y0, w0, h0 = page_box
    filtered = []
    for box in candidates:
        x, y, w, h = box
        if y < y0 + int(h0 * 0.08):
            continue
        if y + h > y0 + h0 - int(h0 * 0.04):
            continue
        if w < config["detection"]["min_side"] * 1.2 or h < config["detection"]["min_side"] * 1.2:
            continue
        area = w * h
        if area < config["validation"]["min_crop_area"]:
            continue
        if w < config["detection"]["min_side"] * 2 and h < config["detection"]["min_side"] * 2:
            continue
        if w / float(h) > 4.0 or h / float(w) > 4.0:
            continue
        filtered.append(box)
    return deterministic_sort(filtered)


def build_candidates(image: np.ndarray, page_box: BoundingBox, config: Dict[str, Any], stats: ExtractionStats, page_number: int) -> List[SignCandidate]:
    x0, y0, w0, h0 = page_box
    region = image[y0:y0 + h0, x0:x0 + w0]
    sign_mask = build_sign_mask(region, config)
    color_boxes, color_contours = detect_contour_boxes(sign_mask, config)
    edge_boxes, edge_contours = detect_edge_boxes(region, config)
    stats.total_contours = color_contours + edge_contours
    all_boxes = list({(x, y, w, h) for x, y, w, h in color_boxes + edge_boxes})
    merged = merge_boxes(all_boxes, config)
    stats.contours_merged = max(0, len(all_boxes) - len(merged))
    filtered = reject_false_positives(merged, page_box, config)
    stats.candidates = len(filtered)
    return [SignCandidate(id=idx + 1, bounding_box=(x0 + x, y0 + y, w, h), contour_boxes=[(x0 + x, y0 + y, w, h)], page=page_number)
            for idx, (x, y, w, h) in enumerate(filtered)]


def detect_text_blocks(image: np.ndarray, config: Dict[str, Any]) -> List[BoundingBox]:
    if not TESSERACT_AVAILABLE or not config["ocr"]["enabled"]:
        return []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    d = pytesseract.image_to_data(gray, config=config["ocr"]["config"], output_type=pytesseract.Output.DICT)
    boxes = []
    for i, text in enumerate(d["text"]):
        text = str(text).strip()
        conf = int(d["conf"][i]) if d["conf"][i].isdigit() else -1
        if not text or conf < config["ocr"]["confidence_threshold"]:
            continue
        if re.search(config["ocr"]["code_pattern"], text):
            x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
            boxes.append((x, y, w, h))
    return deterministic_sort(boxes)


def merge_text_boxes(boxes: List[BoundingBox], max_gap: int = 16) -> List[BoundingBox]:
    if not boxes:
        return []
    merged = []
    boxes = deterministic_sort(boxes)
    current = list(boxes[0])
    for x, y, w, h in boxes[1:]:
        cx, cy, cw, ch = current
        if y <= cy + ch + max_gap and x <= cx + cw + max_gap:
            nx = min(cx, x)
            ny = min(cy, y)
            nx2 = max(cx + cw, x + w)
            ny2 = max(cy + ch, y + h)
            current = [nx, ny, nx2 - nx, ny2 - ny]
        else:
            merged.append(tuple(current))
            current = [x, y, w, h]
    merged.append(tuple(current))
    return merged


def nearest_text_to_box(box: BoundingBox, text_boxes: List[BoundingBox]) -> Optional[BoundingBox]:
    if not text_boxes:
        return None
    x, y, w, h = box
    cx, cy = x + w / 2.0, y + h / 2.0
    best = None
    best_dist = float('inf')
    for tx, ty, tw, th in text_boxes:
        tcx, tcy = tx + tw / 2.0, ty + th / 2.0
        dist = math.hypot(cx - tcx, cy - tcy)
        if dist < best_dist:
            best_dist = dist
            best = (tx, ty, tw, th)
    return best


def extract_code_from_text(image: np.ndarray, text_box: BoundingBox, config: Dict[str, Any]) -> str:
    if not TESSERACT_AVAILABLE or text_box is None:
        return ""
    x, y, w, h = text_box
    roi = image[y:y + h, x:x + w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray, config=config["ocr"]["config"], lang=config["ocr"]["language"])
    matches = re.findall(config["ocr"]["code_pattern"], text)
    return matches[0].strip() if matches else ""


def border_touching_edge(mask: np.ndarray) -> bool:
    if mask.shape[0] == 0 or mask.shape[1] == 0:
        return True
    if np.any(mask[0, :]) or np.any(mask[-1, :]) or np.any(mask[:, 0]) or np.any(mask[:, -1]):
        return True
    return False


def validate_candidate(candidate: SignCandidate, image: np.ndarray, text_box: Optional[BoundingBox], config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    warnings: List[str] = []
    x, y, w, h = candidate.bounding_box
    height, width = image.shape[:2]
    if x <= 0 or y <= 0 or x + w >= width - 1 or y + h >= height - 1:
        warnings.append('crop_touches_image_edge')
    crop = image[y:y + h, x:x + w]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if border_touching_edge(mask):
        warnings.append('object_touches_crop_edge')
    if text_box is not None:
        tx, ty, tw, th = text_box
        if tx < x or ty < y or tx + tw > x + w or ty + th > y + h:
            warnings.append('code_outside_crop')
    if w * h < config["validation"]["min_crop_area"]:
        warnings.append('crop_too_small')
    return (len(warnings) == 0), warnings


def refine_candidate(candidate: SignCandidate, image: np.ndarray, text_box: Optional[BoundingBox], config: Dict[str, Any]) -> SignCandidate:
    padded = pad_box(candidate.bounding_box, (image.shape[1], image.shape[0]), config["padding"])
    retries = 0
    valid, warnings = validate_candidate(candidate, image, text_box, config)
    while not valid and retries < config["validation"]["max_retries"]:
        padded = expand_to_enclose(padded, (image.shape[1], image.shape[0]), config["padding"]["expand_step"], config["padding"]["max_expansion"])
        candidate.bounding_box = clamp_box(padded, image.shape[1], image.shape[0])
        valid, warnings = validate_candidate(candidate, image, text_box, config)
        retries += 1
    candidate.warnings.extend(warnings)
    candidate.status = 'ok' if valid else 'warning'
    candidate.bounding_box = padded
    return candidate


def compute_confidence(candidate: SignCandidate, code_box: Optional[BoundingBox], config: Dict[str, Any]) -> float:
    score = 100.0
    if candidate.status != 'ok':
        score -= 20.0
    if candidate.warnings:
        score -= min(30.0, 10.0 * len(candidate.warnings))
    if code_box is None and config["ocr"]["enabled"]:
        score -= 25.0
    if candidate.area() < 10000:
        score -= 5.0
    return max(0.0, min(100.0, score))


def remove_duplicate_candidates(candidates: List[SignCandidate], config: Dict[str, Any], stats: ExtractionStats) -> List[SignCandidate]:
    if not candidates:
        return []
    sorted_candidates = sorted(candidates, key=lambda c: (-c.area(), -c.confidence, c.id))
    keep: List[SignCandidate] = []
    for candidate in sorted_candidates:
        if any(box_iou(candidate.bounding_box, kept.bounding_box) >= config["detection"]["duplicate_iou"] for kept in keep):
            stats.duplicate_removed += 1
            continue
        keep.append(candidate)
    return keep


def load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except OSError:
            return ImageFont.load_default()


def draw_verification_image(page_path: Path, candidates: List[SignCandidate], output_path: Path, config: Dict[str, Any]) -> None:
    image = Image.open(page_path).convert('RGBA')
    draw = ImageDraw.Draw(image)
    font = load_font(24)
    for candidate in candidates:
        x, y, w, h = candidate.bounding_box
        color = (0, 255, 0, 255) if candidate.status == 'ok' else (255, 128, 0, 255)
        draw.rectangle([x, y, x + w - 1, y + h - 1], outline=color, width=4)
        cx, cy = x + w // 2, y + h // 2
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=color)
        label = f"#{candidate.id} {candidate.code or 'unknown'} {int(candidate.confidence)}%"
        draw.text((x + 6, y + 6), label, font=font, fill=color)
        pad = pad_box(candidate.bounding_box, image.size, config["padding"])
        px, py, pw, ph = pad
        draw.rectangle([px, py, px + pw - 1, py + ph - 1], outline=(0, 128, 255, 180), width=2)
    image.save(output_path)


def build_contact_sheet(crops: List[Path], output_path: Path, columns: int = 6, thumb_size: Tuple[int, int] = (320, 320)) -> None:
    images = [Image.open(p).convert('RGB') for p in crops]
    if not images:
        return
    rows = math.ceil(len(images) / columns)
    sheet_w = columns * thumb_size[0]
    sheet_h = rows * thumb_size[1]
    sheet = Image.new('RGB', (sheet_w, sheet_h), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    font = load_font(18)
    for idx, img in enumerate(images):
        thumb = img.copy()
        thumb.thumbnail(thumb_size, Image.LANCZOS)
        col = idx % columns
        row = idx // columns
        x = col * thumb_size[0]
        y = row * thumb_size[1]
        sheet.paste(thumb, (x, y))
        draw.text((x + 4, y + 4), crops[idx].name, fill=(0, 0, 0), font=font)
    sheet.save(output_path)


def crop_image(image: np.ndarray, bounding_box: BoundingBox, filename: str, output_dir: Path) -> Path:
    x, y, w, h = clamp_box(bounding_box, image.shape[1], image.shape[0])
    crop = image[y:y + h, x:x + w]
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)).save(path)
    return path


def write_metadata(crops: List[CropMetadata], config: Dict[str, Any], page: int) -> None:
    json_path = root_path / config["metadata_dir"] / f"page_{page}_signs.json"
    csv_path = root_path / config["metadata_dir"] / f"page_{page}_signs.csv"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open('w', encoding='utf-8') as f:
        json.dump([asdict(c) for c in crops], f, indent=2, ensure_ascii=False)
    with csv_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(crops[0]).keys()))
        writer.writeheader()
        for crop in crops:
            writer.writerow(asdict(crop))


def write_stats(stats: ExtractionStats, config: Dict[str, Any]) -> None:
    stats_path = root_path / config["logs_dir"] / f"page_{stats.page}_stats.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with stats_path.open('w', encoding='utf-8') as f:
        json.dump(stats.to_dict(), f, indent=2, ensure_ascii=False)


def get_run_timestamp() -> str:
    fixed = os.environ.get('CLLT_FIXED_TIMESTAMP', '').strip()
    if fixed:
        return fixed
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def process_page(page_number: int, config: Dict[str, Any]) -> None:
    page_path = root_path / config["pages_dir"] / f"page_{page_number}.png"
    if not page_path.exists():
        print(f"Page missing: {page_path}")
        return
    image = cv2.imread(str(page_path))
    if image is None:
        raise FileNotFoundError(f"Unable to read page {page_path}")
    page_h, page_w = image.shape[:2]
    make_dirs(config)
    stats = ExtractionStats(page=page_number, ocr_enabled=config["ocr"]["enabled"] and TESSERACT_AVAILABLE)
    page_box, page_type = detect_page_layout(image, page_number, config)
    if page_type == 'page5':
        print(f"Page 5 layout analysis only. No sign extraction for page {page_number}.")
        write_stats(stats, config)
        return
    candidates = build_candidates(image, page_box, config, stats, page_number)
    text_boxes = detect_text_blocks(image, config)
    text_boxes = merge_text_boxes(text_boxes)
    exports: List[Path] = []
    metadata: List[CropMetadata] = []
    timestamp = get_run_timestamp()
    for candidate in candidates:
        code_box = nearest_text_to_box(candidate.bounding_box, text_boxes)
        candidate.code = extract_code_from_text(image, code_box, config) if code_box else ''
        if config["ocr"]["enabled"] and not candidate.code:
            candidate.warnings.append('missing_code')
            stats.missing_codes += 1
        candidate = refine_candidate(candidate, image, code_box, config)
        candidate.confidence = compute_confidence(candidate, code_box, config)
        if candidate.status != 'ok':
            stats.rejected_candidates += 1
        exports.append(candidate)
    exports = remove_duplicate_candidates(exports, config, stats)
    final_crops: List[Path] = []
    for candidate in exports:
        output_dir = root_path / config["signs_output_dir"]
        filename = re.sub(r'[^A-Za-z0-9_\-.]', '_', f"page{page_number:01d}_{candidate.code or 'unknown'}_{candidate.id:03}.png")
        crop_path = crop_image(image, candidate.bounding_box, filename, output_dir)
        final_crops.append(crop_path)
        metadata.append(candidate.to_metadata(timestamp))
    if metadata:
        write_metadata(metadata, config, page_number)
    verification_path = root_path / config["verification_dir"] / f"page_{page_number}_verification.png"
    draw_verification_image(page_path, exports, verification_path, config)
    contact_sheet_path = root_path / config["verification_dir"] / f"page_{page_number}_contact_sheet.png"
    build_contact_sheet(final_crops, contact_sheet_path)
    stats.exported_signs = len(final_crops)
    stats.avg_crop_area = float(np.mean([c.bounding_box[2] * c.bounding_box[3] for c in exports])) if exports else 0.0
    stats.avg_padding = float(np.mean([pad_box(c.bounding_box, (page_w, page_h), config["padding"])[2] * pad_box(c.bounding_box, (page_w, page_h), config["padding"])[3] - c.bounding_box[2] * c.bounding_box[3] for c in exports])) if exports else 0.0
    stats.avg_confidence = float(np.mean([c.confidence for c in exports])) if exports else 0.0
    if exports:
        ocr_count = sum(1 for c in exports if c.code)
        stats.ocr_success_rate = float(ocr_count) / len(exports) * 100.0 if config["ocr"]["enabled"] else 0.0
    write_stats(stats, config)
    print(f"Page {page_number}: extracted {stats.exported_signs} logical sign objects")


def main() -> None:
    config = load_config()
    for page_number in range(1, 6):
        process_page(page_number, config)


if __name__ == '__main__':
    main()
