from dataclasses import dataclass


@dataclass
class ManualEdition:
    edition_id: str
    source_pdf_path: str
    source_pdf_filename: str
    source_pdf_sha256: str
    publication_date: str
    status: str
    created_at: str
    model_version: str


@dataclass
class PageRecord:
    page_id: str
    edition_id: str
    page_number: int
    image_width: int
    image_height: int
    page_image_path: str
    page_image_sha256: str
    render_dpi: int
    normalization_profile: str
    created_at: str
