# Multi-Parser-Benchmark (synthetisch)

Git: 365d29a369d2fa61a0db45c84829c3bab69fd14b; Dirty: False.
Corpus: e050f9872587a6845b4d163a2116f5b43db635fdbe0b5d12e8249e51d70e7069.
Quality: 0b75bc44ddd0e119b2e81af1149ec67f72581b49c43fdf80abe0f902ce5a51eb.

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
| parser_runtime_ms | 15.898775 (763.141/48.000) | 25.083146 (1203.991/48.000) |
| partial_extraction_rate | 0.041667 (2.000/48.000) | 0.041667 (2.000/48.000) |
| reading_order_accuracy | 0.957447 (270.000/282.000) | 0.992908 (280.000/282.000) |
| reading_order_anchor_coverage | 0.945946 (105.000/111.000) | 0.945946 (105.000/111.000) |
| reproducibility | 1.000000 (24.000/24.000) | 1.000000 (24.000/24.000) |
| runtime_per_document_ms | 154.475719 (7414.834/48.000) | 181.972269 (8734.669/48.000) |
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
| plain-de | flowing_text | no_clear_advantage | — | — | 1.3516513766694656 |
| multipage-de | multipage | no_clear_advantage | — | — | 2.347446302092471 |
| columns-column-order | two_columns | pypdf | — | character_error_rate, word_error_rate, reading_order_accuracy | 1.7709486296098678 |
| columns-interleaved | two_columns | no_clear_advantage | — | — | 2.052384532509241 |
| table-row-order | coverage_table | no_clear_advantage | — | — | 2.6713149188708654 |
| table-column-order | coverage_table | pymupdf | character_error_rate, word_error_rate, reading_order_accuracy | — | 2.016015773463255 |
| table-merged-header | merged_cells | no_clear_advantage | — | — | 3.031213789911497 |
| table-merged-row | merged_cells | no_clear_advantage | — | — | 2.1114695762008515 |
| footnote-de | footnotes | no_clear_advantage | — | — | 2.3626281680847736 |
| clause-across-pages | cross_page_clause | no_clear_advantage | — | — | 1.6371888860330133 |
| negations-de | negation | no_clear_advantage | — | — | 1.4398884598287673 |
| exception-de | exclusion_exception | no_clear_advantage | — | — | 1.6290280372165562 |
| sublimits-de | sublimits_deductibles | no_clear_advantage | — | — | 1.625054012960129 |
| currencies-de | currencies_units | no_clear_advantage | — | — | 1.7368910695895807 |
| french-accents | multilingual | no_clear_advantage | — | — | 1.8027026868100813 |
| italian-accents | multilingual | no_clear_advantage | — | — | 1.8747374882393257 |
| german-unicode | multilingual | no_clear_advantage | — | — | 2.195943128536179 |
| font-sizes | font_sizes | no_clear_advantage | — | — | 1.674293986322969 |
| headers-footers | headers_footers | pymupdf | character_error_rate, word_error_rate, reading_order_accuracy | — | 2.0467589676932882 |
| repeated-clause-numbers | repeated_numbers | no_clear_advantage | — | — | 2.091828083152748 |
| vector-text | non_extractable | no_clear_advantage | — | — | 1.2678345963096298 |
| image-only | image_only | no_clear_advantage | — | — | 1.937412568150184 |
| mixed-text-image | mixed_text_image | no_clear_advantage | — | — | 0.7768318438159935 |
| empty-page | empty | no_clear_advantage | — | — | 0.598141096652304 |

## Diagnosen

- pypdf/empty-page: Expected empty; actual not_extractable

## Grenzen

Nur 24 kontrollierte Fälle; eine Fontfamilie. Kleine Unterschiede sind deskriptiv,
nicht statistisch abgesichert. Laufzeiten umfassen verschiedene Fähigkeitsumfänge;
parser_runtime_ms misst Parsing inklusive Layout/Tabellen, separat von Store/Reload.
Keine harten CPU-/RAM-/Zeitlimits, kein OCR, keine fachliche Versicherungsprüfung.
Klauseln und verlässliche Header/Wert-Relationen bleiben unsupported.
Vollständige Nenner, Parserkonfigurationen, Artefakte und Fähigkeiten stehen im JSON.
