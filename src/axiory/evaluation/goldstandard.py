"""Authored synthetic source specifications. This module never imports a PDF parser."""

from axiory.evaluation.schemas import (
    GoldClause,
    GoldFixture,
    GoldTable,
    SourceBlock,
    TableCell,
    TextAnchor,
)

CORPUS_VERSION = "1"


def block(key, text, page=1, x=45.0, y=740.0, size=10.0, rendering="text"):
    return SourceBlock(id=key, text=text, page=page, x=x, y=y, font_size=size, rendering=rendering)


def fixture(
    key,
    layout,
    body,
    *,
    language="de",
    pages=1,
    paint=None,
    tables=(),
    clauses=None,
    status="success",
    marker=True,
):
    # Source ordering and source text are authored here, before PDF generation.
    heading = (
        [block("label", "SYNTHETISCH - KEINE ECHTEN AVB", y=805.0, size=9.0)] if marker else []
    )
    blocks = tuple(heading + body)
    reading = tuple(b.id for b in blocks)
    by_id = {b.id: b for b in blocks}
    texts = tuple(
        "\n".join(by_id[k].text for k in reading if by_id[k].page == page)
        for page in range(1, pages + 1)
    )
    anchors = tuple(TextAnchor(page=b.page, quote=b.text) for b in body)
    return GoldFixture(
        fixture_id=key,
        language=language,
        layout_type=layout,
        page_count=pages,
        blocks=blocks,
        expected_text=texts,
        expected_evidence=anchors,
        expected_reading_order=reading,
        expected_clauses=tuple(clauses)
        if clauses is not None
        else tuple(
            GoldClause(id=f"clause-{i}", parts=(anchor,)) for i, anchor in enumerate(anchors)
        ),
        expected_tables=tuple(tables),
        expected_extraction_status=status,
        paint_order=tuple(["label"] + paint) if paint is not None else reading,
    )


def table_fixture(key, merged=False, row_merged=False, column_paint=False):
    cells = []

    def cell(row, column, text, **kwargs):
        cells.append(TableCell(row=row, column=column, text=text, **kwargs))

    shift = 1 if merged else 0
    if merged:
        cell(0, 0, "Synthetische Deckungsgrenzen", column_span=3, header=True)
    for col, title in enumerate(("Leistung", "Limite", "Bezugsgrösse")):
        cell(shift, col, title, header=True)
    cell(shift + 1, 0, "Modul Alpha", row_span=2 if row_merged else 1)
    cell(shift + 1, 1, "CHF 1 200")
    cell(shift + 1, 2, "pro Reise")
    if not row_merged:
        cell(shift + 2, 0, "Modul Beta")
    cell(shift + 2, 1, "EUR 350")
    cell(shift + 2, 2, "pro Ereignis")
    table = GoldTable(
        id="table-a",
        page=1,
        cells=tuple(cells),
        associations=tuple(
            (shift, col, row, col) for row in (shift + 1, shift + 2) for col in (1, 2)
        ),
    )
    body = [
        block(
            f"cell-{c.row}-{c.column}",
            c.text,
            x=50.0 + c.column * 155.0,
            y=720.0 - c.row * 32.0,
            size=9.0,
        )
        for c in cells
    ]
    paint = None
    if column_paint:
        paint = [b.id for b in sorted(body, key=lambda b: (b.x, -b.y))]
    return fixture(
        key,
        "merged_cells" if merged or row_merged else "coverage_table",
        body,
        tables=(table,),
        paint=paint,
        clauses=(),
    )


def corpus() -> tuple[GoldFixture, ...]:
    cases = [
        fixture(
            "plain-de",
            "flowing_text",
            [
                block("a", "1. Fiktive Reisehilfe gilt ausschliesslich im Testgebiet.", y=750.0),
                block("b", "2. Die Musterleistung beträgt CHF 120 pro Testreise.", y=715.0),
                block(
                    "c", "3. Diese Angaben beschreiben kein reales Versicherungsprodukt.", y=680.0
                ),
            ],
        ),
        fixture(
            "multipage-de",
            "multipage",
            [
                block(
                    f"p{p}-{n}",
                    f"{p}.{n} Synthetische Klausel auf Seite {p}, Absatz {n}.",
                    page=p,
                    y=750.0 - n * 55.0,
                )
                for p in range(1, 4)
                for n in (1, 2)
            ],
            pages=3,
        ),
    ]
    columns = [
        block("left-a", "1. Linke Spalte: Musterleistung.", x=40.0, y=750.0, size=9.0),
        block("left-b", "2. Linke Spalte: Testausschluss.", x=40.0, y=700.0, size=9.0),
        block("right-a", "3. Rechte Spalte: Ausnahme.", x=310.0, y=750.0, size=9.0),
        block("right-b", "4. Rechte Spalte: Sublimite.", x=310.0, y=700.0, size=9.0),
    ]
    cases += [
        fixture("columns-column-order", "two_columns", columns),
        fixture(
            "columns-interleaved",
            "two_columns",
            columns,
            paint=["left-a", "right-a", "left-b", "right-b"],
        ),
        table_fixture("table-row-order"),
        table_fixture("table-column-order", column_paint=True),
        table_fixture("table-merged-header", merged=True),
        table_fixture("table-merged-row", row_merged=True),
        fixture(
            "footnote-de",
            "footnotes",
            [
                block(
                    "main",
                    "5. Testleistung bis CHF 900 [1], unter Vorbehalt von Ziffer 8.",
                    y=750.0,
                ),
                block("reference", "8. Die Testreise darf höchstens sieben Tage dauern.", y=700.0),
                block(
                    "note",
                    "[1] Nur bei dokumentiertem Testereignis; keine echte Deckung.",
                    y=90.0,
                    size=7.0,
                ),
            ],
        ),
        fixture(
            "clause-across-pages",
            "cross_page_clause",
            [
                block("start", "9. Die Musterleistung gilt bei Abbruch der Testreise,", y=100.0),
                block(
                    "end",
                    "sofern die Unterbrechung vor dem fiktiven Stichtag gemeldet wird.",
                    page=2,
                    y=750.0,
                ),
            ],
            pages=2,
            clauses=(
                GoldClause(
                    id="clause-9",
                    parts=(
                        TextAnchor(
                            page=1, quote="9. Die Musterleistung gilt bei Abbruch der Testreise,"
                        ),
                        TextAnchor(
                            page=2,
                            quote=(
                                "sofern die Unterbrechung vor dem fiktiven Stichtag gemeldet wird."
                            ),
                        ),
                    ),
                ),
            ),
        ),
        fixture(
            "negations-de",
            "negation",
            [
                block(
                    "a", "10. Nicht gedeckt sind absichtlich ausgelöste Testereignisse.", y=750.0
                ),
                block("b", "11. Keine Zahlung erfolgt bei fehlendem Musternachweis.", y=710.0),
            ],
        ),
        fixture(
            "exception-de",
            "exclusion_exception",
            [
                block("a", "12. Testschäden an Mustergeräten sind ausgeschlossen.", y=750.0),
                block(
                    "b",
                    "Ausnahme: Ein registriertes Ersatzgerät ist bis CHF 80 eingeschlossen.",
                    y=710.0,
                    size=9.0,
                ),
            ],
        ),
        fixture(
            "sublimits-de",
            "sublimits_deductibles",
            [
                block("a", "13. Gesamtlimite CHF 2 000 pro Testreise.", y=750.0),
                block("b", "Davon für Musterzubehör höchstens CHF 150.", y=710.0),
                block("c", "Selbstbehalt: CHF 25 je Testereignis.", y=670.0),
            ],
        ),
        fixture(
            "currencies-de",
            "currencies_units",
            [
                block("a", "14. CHF 500 pro Person und Testreise.", y=750.0),
                block("b", "15. EUR 300 pro Testereignis; USD 700 pro Testjahr.", y=710.0),
                block("c", "16. Währungen werden nicht umgerechnet.", y=670.0),
            ],
        ),
        fixture(
            "french-accents",
            "multilingual",
            [
                block("a", "17. Garantie fictive: frais à l'étranger, jusqu'à 240 EUR.", y=750.0),
                block("b", "Exclusion: séjour prolongé; exception après accord écrit.", y=710.0),
            ],
            language="fr",
        ),
        fixture(
            "italian-accents",
            "multilingual",
            [
                block(
                    "a", "18. Copertura fittizia: necessità di assistenza, fino a 180 EUR.", y=750.0
                ),
                block(
                    "b", "È escluso il ritardo volontario; validità per un solo viaggio.", y=710.0
                ),
            ],
            language="it",
        ),
        fixture(
            "german-unicode",
            "multilingual",
            [
                block(
                    "a", "19. Ärztliche Testhilfe: Übernachtung, Rückführung und Gepäck.", y=750.0
                ),
                block("b", "Fiktive Prüfgrenze: 95 €; zusätzliche Gebühr: 5 €.", y=710.0),
            ],
        ),
        fixture(
            "font-sizes",
            "font_sizes",
            [
                block("a", "20. MUSTERLEISTUNGEN", y=750.0, size=20.0),
                block("b", "Reguläre Klausel mit zwölf Punkten.", y=700.0, size=12.0),
                block("c", "Kleine Testbedingung: nur mit Nachweis.", y=650.0, size=6.0),
            ],
        ),
        fixture(
            "headers-footers",
            "headers_footers",
            [
                block("header", "SYNTHETISCHE PRODUKTINFORMATION - Testserie", y=780.0, size=8.0),
                block("body", "21. Die fiktive Deckung umfasst genau einen Testfall.", y=730.0),
                block("footer", "Dokumentversion 1 - Seite 1 von 1", y=40.0, size=8.0),
            ],
            paint=["footer", "header", "body"],
        ),
        fixture(
            "repeated-clause-numbers",
            "repeated_numbers",
            [
                block("a", "1. Teil A: Fiktive Annullierung bis CHF 101.", y=750.0),
                block("b", "1. Teil B: Fiktives Gepäck bis CHF 202.", y=710.0),
                block("c", "Nachweis erforderlich.", y=660.0),
                block("d", "Nachweis erforderlich.", y=620.0),
            ],
        ),
        fixture(
            "vector-text",
            "non_extractable",
            [
                block(
                    "a",
                    "SYNTHETISCH: 22. Sichtbar, aber nur als Vektorformen.",
                    rendering="outline",
                )
            ],
            marker=False,
            status="not_extractable",
        ),
        fixture(
            "image-only",
            "image_only",
            [block("a", "SYNTHETISCH: 23. Bildseite mit fiktiver Klausel.", rendering="image")],
            marker=False,
            status="needs_ocr",
        ),
        fixture(
            "mixed-text-image",
            "mixed_text_image",
            [
                block("a", "24. Digitaler Mustertext auf Seite eins.", y=740.0),
                block("b", "SYNTHETISCH: Bildklausel auf Seite zwei.", page=2, rendering="image"),
                block("c", "25. Digitaler Text mit bildbasierter Ausnahme.", page=3, y=750.0),
                block("d", "Ausnahme: CHF 30 nur am Testtag.", page=3, y=680.0, rendering="image"),
            ],
            pages=3,
            status="partial",
        ),
        fixture("empty-page", "empty", [], marker=False, status="empty"),
    ]
    if len(cases) != 24 or len({case.fixture_id for case in cases}) != 24:
        raise ValueError("Corpus must contain exactly 24 distinct authored fixtures")
    return tuple(cases)
