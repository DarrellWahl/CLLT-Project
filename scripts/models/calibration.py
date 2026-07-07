from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .grid_def import GridRegion, PageLayout

Point = Tuple[int, int]


@dataclass
class CalibrationPoint:
    name: str
    x: int
    y: int

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "CalibrationPoint":
        return cls(name=data["name"], x=int(data["x"]), y=int(data["y"]))


@dataclass
class GridCalibration:
    page_name: str
    image_width: int
    image_height: int
    reference_points: List[CalibrationPoint] = field(default_factory=list)
    layout: Optional[PageLayout] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "page_name": self.page_name,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "reference_points": [p.to_dict() for p in self.reference_points],
            "layout": self.layout.to_dict() if self.layout else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "GridCalibration":
        points = [CalibrationPoint(name=p["name"], x=int(p["x"]), y=int(p["y"])) for p in data.get("reference_points", [])]
        layout = PageLayout.from_dict(data["layout"]) if data.get("layout") else None
        return cls(
            page_name=data["page_name"],
            image_width=int(data["image_width"]),
            image_height=int(data["image_height"]),
            reference_points=points,
            layout=layout,
            metadata={**data.get("metadata", {})},
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        path.write_text(__import__("json").dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "GridCalibration":
        data = path.read_text(encoding="utf-8")
        return cls.from_dict(__import__("json").loads(data))

    def add_reference_point(self, name: str, x: int, y: int) -> None:
        self.reference_points.append(CalibrationPoint(name=name, x=x, y=y))

    def is_calibrated(self) -> bool:
        return self.layout is not None

    @staticmethod
    def build_region_from_corners(
        name: str,
        left_top: Point,
        right_bottom: Point,
        columns: int,
        rows: int,
        horizontal_spacing: int = 0,
        vertical_spacing: int = 0,
    ) -> GridRegion:
        total_width = right_bottom[0] - left_top[0]
        total_height = right_bottom[1] - left_top[1]

        if columns <= 0 or rows <= 0:
            raise ValueError("columns and rows must be positive")

        if columns == 1:
            column_width = total_width
        else:
            column_width = (total_width - horizontal_spacing * (columns - 1)) / columns
        if rows == 1:
            row_height = total_height
        else:
            row_height = (total_height - vertical_spacing * (rows - 1)) / rows

        return GridRegion(
            name=name,
            left=int(left_top[0]),
            top=int(left_top[1]),
            columns=columns,
            rows=rows,
            column_width=int(round(column_width)),
            row_height=int(round(row_height)),
            horizontal_spacing=horizontal_spacing,
            vertical_spacing=vertical_spacing,
        )

    def add_layout(self, page_layout: PageLayout) -> None:
        self.layout = page_layout
