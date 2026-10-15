"""Frozen gold loading and blind synthetic document rendering."""

import re
from collections import Counter
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from axiory.experiments.models import Corpus, Freeze, Source
from axiory.extraction.context import build_context
from axiory.ingestion import IntegrityError, artifact_id
from axiory.ingestion_models import LogicalDocument

ROOT = Path("datasets/multilingual")


def load_corpus(root=ROOT):
    raw = (root / "gold-v1.json").read_bytes()
    corpus = Corpus.model_validate_json(raw)
    freeze = Freeze.model_validate_json((root / "freeze-v1.json").read_bytes())
    if sha256(raw).hexdigest() != freeze.file_sha256 or artifact_id(corpus) != freeze.corpus_sha256:
        raise IntegrityError("Frozen gold was modified")
    if len(corpus.cases) != freeze.case_count or len(corpus.cases) < 120:
        raise IntegrityError("Incomplete corpus")
    ids = {c.source.id for c in corpus.cases}
    if len(ids) != len(corpus.cases) or not set(freeze.pilot_ids) <= ids:
        raise IntegrityError("Duplicate/unknown corpus IDs")
    if len(freeze.pilot_ids) != 24 or len(set(freeze.pilot_ids)) != 24:
        raise IntegrityError("Pilot must contain 24 distinct frozen cases")
    if Counter(c.source.language for c in corpus.cases) != {"de": 40, "fr": 40, "it": 40}:
        raise IntegrityError("Language imbalance")
    for key in (lambda c: c.family, lambda c: c.template, lambda c: c.source.product_id):
        dev = {key(c) for c in corpus.cases if c.split == "dev"}
        holdout = {key(c) for c in corpus.cases if c.split == "holdout"}
        if dev & holdout:
            raise IntegrityError("Family, template or product leakage")

    def normalized(case):
        text = " ".join(line for page in case.source.pages for line in page).casefold()
        return re.sub(r"\d+", "#", " ".join(text.split()))

    dev = {normalized(c) for c in corpus.cases if c.split == "dev"}
    if dev & {normalized(c) for c in corpus.cases if c.split == "holdout"}:
        raise IntegrityError("Identical source template across splits")
    return corpus, freeze


def render(source: Source):
    """Receives ONLY Source; labels/expected outcomes cannot enter the PDF payload."""
    source = Source.model_validate_json(source.model_dump_json())
    font = "AxiorySemanticVera"
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont(font, str(Path(reportlab.__file__).parent / "fonts/Vera.ttf"))
        )
    output = BytesIO()
    canvas = Canvas(output, pagesize=(595, 842), invariant=1, pageCompression=0)
    for paragraphs in source.pages:
        canvas.setFont(font, 8)
        canvas.drawString(40, 805, "SYNTHETIC / SYNTHETISCH / SYNTHETIQUE / SINTETICO")
        y = 770
        for paragraph in paragraphs:
            if "|" in paragraph:
                columns = [part.strip() for part in paragraph.split("|")]
                if len(columns) != 3:
                    raise ValueError("Synthetic table requires three columns")
                widths = (260, 145, 110)
                x = 40
                for text, width in zip(columns, widths, strict=True):
                    if pdfmetrics.stringWidth(text, font, 8) > width - 8:
                        raise ValueError("Table cell does not fit")
                    canvas.rect(x, y - 7, width, 22)
                    canvas.drawString(x + 4, y, text)
                    x += width
                y -= 22
            else:
                line = ""
                for word in paragraph.split(" "):
                    trial = (line + " " + word).lstrip()
                    if pdfmetrics.stringWidth(trial, font, 8) > 510:
                        canvas.drawString(40, y, line)
                        y -= 13
                        line = word
                    else:
                        line = trial
                canvas.drawString(40, y, line)
                y -= 24
        if y < 40:
            raise ValueError("Synthetic content exceeds physical page")
        canvas.showPage()
    canvas.save()
    return output.getvalue()


def prepare(store, source: Source, *, max_chars):
    receipt = store.ingest(
        render(source),
        LogicalDocument(
            id=source.id,
            product_id=source.product_id,
            title="Synthetic multilingual evaluation",
            kind="policy_conditions",
            language=source.language,
            synthetic=True,
        ),
    )
    return build_context(store, receipt, (source.coverage_code,), max_chars=max_chars)
