"""Deterministic ReportLab PDFs with embedded, package-shipped Bitstream Vera."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path

import reportlab
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from axiory.evaluation.schemas import GoldFixture

GENERATOR_VERSION = "1"
FONT_NAME = "AxioryVera"


def font_path() -> Path:
    return Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"


def generator_metadata() -> dict:
    return {
        "generator": "reportlab",
        "version": reportlab.Version,
        "generator_version": GENERATOR_VERSION,
        "font": "Bitstream Vera",
        "font_sha256": sha256(font_path().read_bytes()).hexdigest(),
    }


def render_pdf(fixture: GoldFixture) -> bytes:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path())))
    face = pdfmetrics.getFont(FONT_NAME).face
    output = BytesIO()
    canvas = Canvas(output, pagesize=(595, 842), invariant=1, pageCompression=0)
    canvas.setTitle(f"SYNTHETIC Axiory fixture {fixture.fixture_id}")
    canvas.setAuthor("Axiory synthetic evaluation")
    by_id = {block.id: block for block in fixture.blocks}
    for page in range(1, fixture.page_count + 1):
        for table in fixture.expected_tables:
            if table.page == page:
                for cell in table.cells:
                    canvas.rect(
                        45 + cell.column * 155,
                        710 - (cell.row + cell.row_span - 1) * 32,
                        cell.column_span * 155,
                        cell.row_span * 32,
                    )
        for key in fixture.paint_order:
            block = by_id[key]
            if block.page != page:
                continue
            if any(ord(char) not in face.charToGlyph for char in block.text):
                raise ValueError(f"Fixture {fixture.fixture_id}: glyph not in embedded font")
            width = pdfmetrics.stringWidth(block.text, FONT_NAME, block.font_size)
            if block.x + width > 580:
                raise ValueError(f"Fixture {fixture.fixture_id}: text exceeds page width")
            if block.rendering == "text":
                canvas.setFont(FONT_NAME, block.font_size)
                canvas.drawString(block.x, block.y, block.text)
            else:
                scale = 3
                font = ImageFont.truetype(str(font_path()), round(block.font_size * scale))
                box = font.getbbox(block.text)
                raster = Image.new("RGB", (box[2] - box[0] + 4, box[3] - box[1] + 4), "white")
                ImageDraw.Draw(raster).text(
                    (2 - box[0], 2 - box[1]), block.text, font=font, fill="black"
                )
                w, h = raster.size
                if block.rendering == "image":
                    canvas.drawImage(
                        ImageReader(raster), block.x, block.y, width=w / scale, height=h / scale
                    )
                else:
                    # Vector outlines from raster runs: visible glyph shapes, no PDF text objects.
                    pixels = raster.convert("L")
                    for row in range(h):
                        start = None
                        for col in range(w + 1):
                            ink = col < w and pixels.getpixel((col, row)) < 128
                            if ink and start is None:
                                start = col
                            if not ink and start is not None:
                                canvas.rect(
                                    block.x + start / scale,
                                    block.y + (h - row) / scale,
                                    (col - start) / scale,
                                    1 / scale,
                                    stroke=0,
                                    fill=1,
                                )
                                start = None
        canvas.showPage()
    canvas.save()
    return output.getvalue()
