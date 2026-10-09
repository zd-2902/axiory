# Multi-Parser-Benchmark (synthetisch)

Git: df4f45c0b487a252500b447cef493080a8f52eef; Dirty: False.
Corpus: e050f9872587a6845b4d163a2116f5b43db635fdbe0b5d12e8249e51d70e7069.
Quality: 649c62251741506a839036c8473a3c597292dfe589831adf65f43b1e5b676bc8.

Keine Signifikanzbehauptung; kein Gesamtscore. Tabellen sind geometrische Heuristiken.
Fundstellen nutzen bekannte Goldzitate. pypdf bleibt Produktionsdefault;
PyMuPDF bleibt wegen offener Lizenzstrategie experimentell.

| Metrik | pypdf (Z/N) | PyMuPDF (Z/N) |
| --- | --- | --- |
| character_error_rate | 0.094776 (332.000/3503.000) | 0.069369 (243.000/3503.000) |
| clause_boundary_accuracy | unsupported | unsupported |
| evidence_span_validity | 1.000000 (84.000/84.000) | 1.000000 (84.000/84.000) |
| expected_status_match | 0.958333 (23.000/24.000) | 1.000000 (24.000/24.000) |
| extraction_failure_rate | 0.125000 (6.000/48.000) | 0.125000 (6.000/48.000) |
| header_association_precision | unsupported | unsupported |
| header_association_recall | unsupported | unsupported |
| missing_evidence_rate | 0.066667 (6.000/90.000) | 0.066667 (6.000/90.000) |
| page_reference_accuracy | 1.000000 (84.000/84.000) | 1.000000 (84.000/84.000) |
| parser_runtime_ms | 15.939979 (765.119/48.000) | 26.187981 (1257.023/48.000) |
| partial_extraction_rate | 0.041667 (2.000/48.000) | 0.041667 (2.000/48.000) |
| reading_order_accuracy | 0.957447 (270.000/282.000) | 0.992908 (280.000/282.000) |
| reading_order_anchor_coverage | 0.945946 (105.000/111.000) | 0.945946 (105.000/111.000) |
| reproducibility | 1.000000 (24.000/24.000) | 1.000000 (24.000/24.000) |
| runtime_per_document_ms | 156.204894 (7497.835/48.000) | 183.361175 (8801.336/48.000) |
| table_cell_extraction_accuracy | unsupported | unsupported |
| table_cell_precision | unsupported | 1.000000 (36.000/36.000) |
| table_cell_recall | unsupported | 1.000000 (36.000/36.000) |
| table_header_value_association | unsupported | unsupported |
| text_completeness | 0.949085 (2852.000/3005.000) | 0.949085 (2852.000/3005.000) |
| unicode_integrity | 1.000000 (37.000/37.000) | 1.000000 (37.000/37.000) |
| word_error_rate | 0.103647 (54.000/521.000) | 0.069098 (36.000/521.000) |

## Fähigkeiten

| Fähigkeit | pypdf | PyMuPDF |
| --- | --- | --- |
| blocks | unsupported | parser |
| lines | unsupported | parser |
| coordinates | unsupported | parser |
| reading_order | unsupported | heuristic |
| tables | unsupported | heuristic |
| header_associations | unsupported | unsupported |
| clauses | unsupported | unsupported |

## Fälle und Layouts

| Fall | Layout | Textpräferenz | verbessert | verschlechtert | Zeitverhältnis |
| --- | --- | --- | --- | --- | --- |
| plain-de | flowing_text | no_clear_advantage | — | — | 1.723068570102389 |
| multipage-de | multipage | no_clear_advantage | — | — | 2.068638062778949 |
| columns-column-order | two_columns | pypdf | — | character_error_rate, word_error_rate, reading_order_accuracy | 1.5307642864570756 |
| columns-interleaved | two_columns | no_clear_advantage | — | — | 1.239952353971266 |
| table-row-order | coverage_table | no_clear_advantage | — | — | 1.924917484029715 |
| table-column-order | coverage_table | pymupdf | character_error_rate, word_error_rate, reading_order_accuracy | — | 2.3031355651352676 |
| table-merged-header | merged_cells | no_clear_advantage | — | — | 2.5050910580845414 |
| table-merged-row | merged_cells | no_clear_advantage | — | — | 2.388114248544384 |
| footnote-de | footnotes | no_clear_advantage | — | — | 2.3909282383003068 |
| clause-across-pages | cross_page_clause | no_clear_advantage | — | — | 1.4089435641202086 |
| negations-de | negation | no_clear_advantage | — | — | 1.8843650035002177 |
| exception-de | exclusion_exception | no_clear_advantage | — | — | 2.5082362057652157 |
| sublimits-de | sublimits_deductibles | no_clear_advantage | — | — | 1.611663200306541 |
| currencies-de | currencies_units | no_clear_advantage | — | — | 1.7106745335274378 |
| french-accents | multilingual | no_clear_advantage | — | — | 2.027829400345221 |
| italian-accents | multilingual | no_clear_advantage | — | — | 3.1939729160015466 |
| german-unicode | multilingual | no_clear_advantage | — | — | 1.4278613898307133 |
| font-sizes | font_sizes | no_clear_advantage | — | — | 1.8404988914271427 |
| headers-footers | headers_footers | pymupdf | character_error_rate, word_error_rate, reading_order_accuracy | — | 1.9293125858848057 |
| repeated-clause-numbers | repeated_numbers | no_clear_advantage | — | — | 1.8131333587243386 |
| vector-text | non_extractable | no_clear_advantage | — | — | 1.2265489235400358 |
| image-only | image_only | no_clear_advantage | — | — | 1.5523963544840687 |
| mixed-text-image | mixed_text_image | no_clear_advantage | — | — | 2.2216509655373917 |
| empty-page | empty | no_clear_advantage | — | — | 1.1500985148763085 |

## Diagnosen

- pypdf/empty-page: Expected empty; actual not_extractable

## Grenzen

Nur 24 kontrollierte Fälle; eine Fontfamilie. Kleine Unterschiede sind deskriptiv,
nicht statistisch abgesichert. Laufzeiten umfassen verschiedene Fähigkeitsumfänge;
parser_runtime_ms misst Parsing inklusive Layout/Tabellen, separat von Store/Reload.
Keine harten CPU-/RAM-/Zeitlimits, kein OCR, keine fachliche Versicherungsprüfung.
Klauseln und verlässliche Header/Wert-Relationen bleiben unsupported.
Vollständige Nenner, Parserkonfigurationen, Artefakte und Fähigkeiten stehen im JSON.
