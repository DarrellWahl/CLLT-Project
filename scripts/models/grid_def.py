from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

Rectangle = Tuple[int, int, int, int]


@dataclass
class GridRegion:
    """A mathematical definition of a grid region on a page."""
    name: str
    left: int
    top: int
    columns: int
    rows: int
    column_width: Optional[int] = None
    row_height: Optional[int] = None
    horizontal_spacing: int = 0
    vertical_spacing: int = 0
    column_widths: Optional[List[int]] = None
    row_heights: Optional[List[int]] = None
    metadata: Dict[str, Union[str, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.column_widths is not None and len(self.column_widths) != self.columns:
            raise ValueError("column_widths length must equal columns")
        if self.row_heights is not None and len(self.row_heights) != self.rows:
            raise ValueError("row_heights length must equal rows")

    @property
    def total_width(self) -> int:
        if self.column_widths:
            return sum(self.column_widths) + self.horizontal_spacing * (self.columns - 1)
        if self.column_width is None:
            raise ValueError("column_width or column_widths must be defined")
        return self.column_width * self.columns + self.horizontal_spacing * (self.columns - 1)

    @property
    def total_height(self) -> int:
        if self.row_heights:
            return sum(self.row_heights) + self.vertical_spacing * (self.rows - 1)
        if self.row_height is None:
            raise ValueError("row_height or row_heights must be defined")
        return self.row_height * self.rows + self.vertical_spacing * (self.rows - 1)

    def cell_rect(self, row: int, column: int) -> Rectangle:
        if not (0 <= row < self.rows):
            raise IndexError("row index out of range")
        if not (0 <= column < self.columns):
            raise IndexError("column index out of range")

        x = self.left + sum(self.column_widths[:column] if self.column_widths else [self.column_width] * column)
        if self.column_widths:
            x += self.horizontal_spacing * column
        else:
            x += self.horizontal_spacing * column

        y = self.top + sum(self.row_heights[:row] if self.row_heights else [self.row_height] * row)
        if self.row_heights:
            y += self.vertical_spacing * row
        else:
            y += self.vertical_spacing * row

        width = self.column_widths[column] if self.column_widths else self.column_width
        height = self.row_heights[row] if self.row_heights else self.row_height
        assert width is not None and height is not None
        return int(x), int(y), int(width), int(height)

    def iter_cells(self) -> Iterable[Dict[str, Union[int, str, Rectangle]]]:
        for row in range(self.rows):
            for column in range(self.columns):
                yield {
                    "region": self.name,
                    "row": row,
                    "column": column,
                    "rect": self.cell_rect(row, column),
                }

    def to_dict(self) -> Dict[str, Union[str, int, List[int], Dict[str, Union[str, int]]]]:
        return {
            "name": self.name,
            "left": self.left,
            "top": self.top,
            "columns": self.columns,
            "rows": self.rows,
            "column_width": self.column_width,
            "row_height": self.row_height,
            "horizontal_spacing": self.horizontal_spacing,
            "vertical_spacing": self.vertical_spacing,
            "column_widths": self.column_widths,
            "row_heights": self.row_heights,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, int, List[int], Dict[str, Union[str, int]]]]) -> "GridRegion":
        return cls(
            name=data["name"],
            left=int(data["left"]),
            top=int(data["top"]),
            columns=int(data["columns"]),
            rows=int(data["rows"]),
            column_width=int(data["column_width"]) if data.get("column_width") is not None else None,
            row_height=int(data["row_height"]) if data.get("row_height") is not None else None,
            horizontal_spacing=int(data.get("horizontal_spacing", 0)),
            vertical_spacing=int(data.get("vertical_spacing", 0)),
            column_widths=[int(x) for x in data["column_widths"]] if data.get("column_widths") else None,
            row_heights=[int(x) for x in data["row_heights"]] if data.get("row_heights") else None,
            metadata={**data.get("metadata", {})},
        )


@dataclass
class PageLayout:
    page_name: str
    image_width: int
    image_height: int
    regions: List[GridRegion] = field(default_factory=list)

    def get_region(self, name: str) -> GridRegion:
        for region in self.regions:
            if region.name == name:
                return region
        raise KeyError(f"Region not found: {name}")

    def to_dict(self) -> Dict[str, Union[str, int, List[Dict[str, Union[str, int, List[int]]]]]]:
        return {
            "page_name": self.page_name,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "regions": [region.to_dict() for region in self.regions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, int, List[Dict[str, Union[str, int, List[int]]]]]]) -> "PageLayout":
        regions = [GridRegion.from_dict(region_data) for region_data in data.get("regions", [])]
        return cls(
            page_name=data["page_name"],
            image_width=int(data["image_width"]),
            image_height=int(data["image_height"]),
            regions=regions,
        )

    def section_report(self) -> List[Dict[str, Union[str, int]]]:
        report = []
        for region in self.regions:
            report.append({
                "name": region.name,
                "columns": region.columns,
                "rows": region.rows,
                "left": region.left,
                "top": region.top,
                "total_width": region.total_width,
                "total_height": region.total_height,
                "cell_width": region.column_width,
                "cell_height": region.row_height,
                "h_spacing": region.horizontal_spacing,
                "v_spacing": region.vertical_spacing,
            })
        return report
