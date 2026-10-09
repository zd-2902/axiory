# Axiory: synthetischer Layout-Benchmark

**Kein Benchmark realer AVB und keine semantische Versicherungsbewertung.**

Parser: pypdf 6.19.0; Git: ce19b7795a12666d1a2d633311ddd7ac3ad263b0.
Gold-/Evaluationsschema: 1; Corpus: e050f9872587a6845b4d163a2116f5b43db635fdbe0b5d12e8249e51d70e7069.
Zeitpunkt: 2026-10-09T20:02:44.620801+00:00; Dirty: False.
Stabiler Qualitätsfingerprint: f6a854948483cccde0c42e237e9963c3ad9843100b172bbd218dd3205f3e932d.

CER/WER verwenden ausschliesslich Whitespace-Normalisierung. Reading Order misst
eindeutige Textanker im serialisierten Text, keine rekonstruierte Layoutstruktur.
Evidence nutzt einen goldgestützten exakten Zitat-Locator, keine autonome Extraktion.
unsupported ist keine gemessene Null. Capability gaps sind getrennt von Messfehlern.

| Metrik | Wert/Status | Zähler | Nenner | messbar / unsupported / n.a. |
| --- | --- | --- | --- | --- |
| character_error_rate | 0.094776 | 332.0 | 3503.0 | 23 / 0 / 1 |
| clause_boundary_accuracy | unsupported | None | None | 0 / 19 / 5 |
| evidence_span_validity | 1.000000 | 84.0 | 84.0 | 21 / 0 / 3 |
| expected_status_match | 0.958333 | 23.0 | 24.0 | 24 / 0 / 0 |
| extraction_failure_rate | 0.125000 | 6.0 | 48.0 | 24 / 0 / 0 |
| missing_evidence_rate | 0.066667 | 6.0 | 90.0 | 23 / 0 / 1 |
| page_reference_accuracy | 1.000000 | 84.0 | 84.0 | 21 / 0 / 3 |
| partial_extraction_rate | 0.041667 | 2.0 | 48.0 | 24 / 0 / 0 |
| reading_order_accuracy | 0.957447 | 270.0 | 282.0 | 21 / 0 / 3 |
| reading_order_anchor_coverage | 0.945946 | 105.0 | 111.0 | 23 / 0 / 1 |
| reproducibility | 1.000000 | 24.0 | 24.0 | 24 / 0 / 0 |
| runtime_per_document_ms | 117.233756 | 5627.22029996803 | 48.0 | 24 / 0 / 0 |
| table_cell_extraction_accuracy | unsupported | None | None | 0 / 4 / 20 |
| table_header_value_association | unsupported | None | None | 0 / 4 / 20 |
| text_completeness | 0.949085 | 2852.0 | 3005.0 | 23 / 0 / 1 |
| unicode_integrity | 1.000000 | 37.0 | 37.0 | 15 / 0 / 9 |
| word_error_rate | 0.103647 | 54.0 | 521.0 | 23 / 0 / 1 |

## Layoutvergleich

| Layout | Fälle | CER | Completeness | Reading Order |
| --- | --- | --- | --- | --- |
| coverage_table | 2 | 0.2236 | 1.0000 | 0.9000 |
| cross_page_clause | 1 | 0.0000 | 1.0000 | 1.0000 |
| currencies_units | 1 | 0.0000 | 1.0000 | 1.0000 |
| empty | 1 | not_evaluable | not_evaluable | not_evaluable |
| exclusion_exception | 1 | 0.0000 | 1.0000 | 1.0000 |
| flowing_text | 1 | 0.0000 | 1.0000 | 1.0000 |
| font_sizes | 1 | 0.0000 | 1.0000 | 1.0000 |
| footnotes | 1 | 0.0000 | 1.0000 | 1.0000 |
| headers_footers | 1 | 0.4198 | 1.0000 | 0.6667 |
| image_only | 1 | 1.0000 | 0.0000 | not_evaluable |
| merged_cells | 2 | 0.0000 | 1.0000 | 1.0000 |
| mixed_text_image | 1 | 0.3854 | 0.6182 | 1.0000 |
| multilingual | 3 | 0.0000 | 1.0000 | 1.0000 |
| multipage | 1 | 0.0000 | 1.0000 | 1.0000 |
| negation | 1 | 0.0000 | 1.0000 | 1.0000 |
| non_extractable | 1 | 1.0000 | 0.0000 | not_evaluable |
| repeated_numbers | 1 | 0.0000 | 1.0000 | 1.0000 |
| sublimits_deductibles | 1 | 0.0000 | 1.0000 | 1.0000 |
| two_columns | 2 | 0.1111 | 1.0000 | 0.9500 |

## Fälle und Fehleranalyse

### plain-de

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 6c224f52c06f98193e69facb74af20d3ceb1390e3bc5f94de27548e341417fb9; Receipt: bfda0a6d90f8183acc616940fe58685def16b6bb1422f95d3284c5b8d78a62b2.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### multipage-de

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: d6d70396e1b92268bcadf0bc73c2ebfe5a2db6a654995c514d83b72a508c8cc8; Receipt: e3a4a452f2b3446a5d88be94e76ce133e2f1e2a724740183ff78edcb895a8b56.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### columns-column-order

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 696a62192e163b3477f8b757a3fb1fe9495655c3f16cf90c0f9d83559aff7ef9; Receipt: f3b4c436b3b56622b5dcae096981e89222efdd79f2da0bfd579ee8bd135e5e9d.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### columns-interleaved

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 6e5de01e6e6f082854cc5e99605b4dda0f70d74b2704e7871d0784237e6235ec; Receipt: 57842d7a94239439064531a8bbdaea3e87484cac7eddafb577424d073651ba3a.

- incorrect_reading_order (measured): reading_order_accuracy=0.900000
- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### table-row-order

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 09925b2abea604ff52412f5e6d022aea6c124445c67ee9375025415ec2e93cf8; Receipt: c0b23c92d51b1ff78c5901b5b2b2613a27534c48d4147f07d585aa74ec53e4dc.

- table_structure_lost (capability_gap): pypdf adapter outputs no table structure
- incorrect_value_association (capability_gap): pypdf adapter outputs no table structure

### table-column-order

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 4921d28b8e89a727ddae90b110159b63156df82f8f4e33b0dde3f79685ef9ebf; Receipt: 932c8331b7f3ba7875cef0296b84fdaf2dcf15824c83457f9885b07c8d01ed5e.

- incorrect_reading_order (measured): reading_order_accuracy=0.800000
- table_structure_lost (capability_gap): pypdf adapter outputs no table structure
- incorrect_value_association (capability_gap): pypdf adapter outputs no table structure

### table-merged-header

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: e5a1e9d089c093f10071691a53db8c43133b5d1e31528edf4d16e883798c27bd; Receipt: c1fa98bdef91d5ed433400a48419bbed156e9bd68278abf7a45c65f3fed77830.

- table_structure_lost (capability_gap): pypdf adapter outputs no table structure
- incorrect_value_association (capability_gap): pypdf adapter outputs no table structure

### table-merged-row

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 843026186d3dc71accc96c4302ca991fa18fcdc561dc43f81e1f148cb05cc52f; Receipt: 91352d008f00f308228b8cc9c171928907485751e606612495c0835108c5b607.

- table_structure_lost (capability_gap): pypdf adapter outputs no table structure
- incorrect_value_association (capability_gap): pypdf adapter outputs no table structure

### footnote-de

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: acf23b4af9e2cfd68189f9ca78b0609a3998391f48752845f4604b992e11d2a9; Receipt: 528ecefdcb436965d5382dbdf78adaf60cecc229ff18348745c4365b3a6d6a4d.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### clause-across-pages

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: aa14282492c67f1683e65c6f6345e3354011d7b61841bdbd69fcd1dc4d5f343f; Receipt: 4777454ebe433e0384797bad53e7857d3ddd9c124c87887ccff616061fed253d.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### negations-de

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: e179cf3f62f80787ba9c14418babf2178d113fa2f5f027a400525eb23e401e60; Receipt: c5ebdd3bc9dc9060d4b46ace96717c2fe7abb32d6ba6ccc83b78c9f07ed46cdc.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### exception-de

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: a42741f5fc13a2a29229054d787652595c4ba078933a08ed99abafef624ad53a; Receipt: 5b6e4bfa9d2e82158af824ffdb924df7a167700171d7832ccd9dfd3dcf852308.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### sublimits-de

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: f58371ea3eebdbfbf7afa051aa86123a2840738dc18cf8d7ef344d217724d998; Receipt: f2ec09d758df633d098920301bab65660aa3514b62a2597250eb4ab5c3c447f3.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### currencies-de

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: acdddbcb4e644d3e021c3f65581aca9a3b85fc0e506c793c7a4df4236a119e64; Receipt: 6c645b99dcc4d456f2a692ae6ec832e7654b9dbdbed4bfa671fcf73fa7dd4afd.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### french-accents

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 27c75dd59b6dd58d02f859fe857c3132fd0fac200e483bdfbb983c35cab65d4c; Receipt: 7acee3463f86837e9cba4088c16de31cb4645bf5bad8aa133312623462f98e0b.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### italian-accents

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 884f859b6398e43a88cf004e3c63c2a65ade90bc83fba7b7f02fa661ce524078; Receipt: 6b6e5726b940a86cc5f9f7d98937a09e724a1cb0b4f15098cc5c18bf5e51cd3e.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### german-unicode

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 72030c0dc7648e384a552e9cea0dd5a375e58819e6e9488d00f8636f87d9ba0e; Receipt: 4c03aeff8ea52d4c7a520ba88d7d1cef3cfbdfdcf533509087f7ce2ea7f1b2cc.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### font-sizes

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: f1f78380ade9e6f8983f9e12f3e10ab1623fed53436da1e59b4c5b716c6c06df; Receipt: 124eb2c115d2c6a21af34e89cd355ee37e8e1579bc88400d4de75f9446a95a6c.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### headers-footers

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 3b5f4613673eac0f7279e29bd2064a19f04bc86c3000b9675b255e66a359f24c; Receipt: a8c25270c2e598c4477177d28fe117495ff110d55ebc4a02b6335e88c5e53c92.

- incorrect_reading_order (measured): reading_order_accuracy=0.666667
- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries

### repeated-clause-numbers

Status: success; Status-Erwartung erfüllt: 1.0.
Originalhash: 9dc672aa38f0bd556863ef06f5c84b525bb553639b486ecaf4ccea406d459d51; Receipt: 2ebd5aeb6b8da3281434a7a0736b4933160dca832f528bd41f520980ce22833a.

- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries
- Diagnose: Evidence quote 'Nachweis erforderlich.': 2 exact occurrences
- Diagnose: Evidence quote 'Nachweis erforderlich.': 2 exact occurrences

### vector-text

Status: not_extractable; Status-Erwartung erfüllt: 1.0.
Originalhash: 588c6a56474fa37d9d9646265698cd0ba468d45c1114b6b6b7d4dc4ae67fea40; Receipt: 37181f64a50e1bad8cbfd250e78bfab6293393f7e73465d50c1068bf4cc9a371.

- missing_text (measured): text_completeness=0.000000
- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries
- extraction_failure (measured): First extraction state: not_extractable; failure rate=1.000000
- Diagnose: Evidence quote 'SYNTHETISCH: 22. Sichtbar, aber nur als Vektorformen.': 0 exact occurrences
- Diagnose: Page 1: not_extractable; error_type=None

### image-only

Status: needs_ocr; Status-Erwartung erfüllt: 1.0.
Originalhash: fe262fe023967a7e73e78d58bdfd8a5c799589b62debac64700c6411b0f3801f; Receipt: 2108cfb31e3a294cd106a5031c8ef76a2532bdb5220fd52c532a239e65376a61.

- missing_text (measured): text_completeness=0.000000
- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries
- extraction_failure (measured): First extraction state: needs_ocr; failure rate=1.000000
- Diagnose: Evidence quote 'SYNTHETISCH: 23. Bildseite mit fiktiver Klausel.': 0 exact occurrences
- Diagnose: Page 1: needs_ocr; error_type=None

### mixed-text-image

Status: partial; Status-Erwartung erfüllt: 1.0.
Originalhash: c7e15502a7a0b3d246e8f0088b94f2c29596bf725767751d84a339c3ab9763b3; Receipt: 81f070cc82c0490654f090b320c8726253a6f18843a550be4220557d629d3bec.

- missing_text (measured): text_completeness=0.618182
- broken_clause_boundary (capability_gap): pypdf adapter does not output clause boundaries
- Diagnose: Evidence quote 'SYNTHETISCH: Bildklausel auf Seite zwei.': 0 exact occurrences
- Diagnose: Evidence quote 'Ausnahme: CHF 30 nur am Testtag.': 0 exact occurrences
- Diagnose: Page 2: needs_ocr; error_type=None

### empty-page

Status: not_extractable; Status-Erwartung erfüllt: 0.0.
Originalhash: 9edce9d49e659114f039a49bef928fd39c4237957c60b4f468ed5895b525d342; Receipt: 34aa446ed73269f05ede0b297f59c5900dd9087ce4c3d0e3b2934dbe2b91d445.

- extraction_failure (measured): First extraction state: not_extractable; failure rate=1.000000
- Diagnose: Expected status empty, observed not_extractable
- Diagnose: Page 1: not_extractable; error_type=None

## Grenzen

24 kontrollierte Fälle sind keine repräsentative Stichprobe. Fehlende OCR und
fehlende Tabellen-/Klauselstruktur werden sichtbar, nicht nachträglich repariert.
Zeiten umfassen Ingestion und verifizierten Reload, nicht PDF-Erzeugung/Metriken.
Keine harten CPU-/RAM-/Zeitlimits; dafür ist ein isolierter Worker erforderlich.
Rohtexte, Evidenzkandidaten, Goldstandard, Konfiguration und Laufzeitumgebung
stehen in den JSON-Artefakten. Fehlende/mehrdeutige Anker werden ausgewiesen.
