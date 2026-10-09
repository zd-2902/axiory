# Multi-Parser Benchmark – Sprint 4

## Reproduzieren

Standardinstallation und bestehende Demo/Evaluation bleiben ohne PyMuPDF:

```sh
uv sync --locked --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run axiory-demo
uv run axiory-eval
```

Explizites synthetisches Experiment (AGPL-/kommerzielle Lizenzstrategie noch offen):

```sh
uv sync --locked --dev --extra experimental-pymupdf
uv run --extra experimental-pymupdf pytest
uv run --extra experimental-pymupdf axiory-parser-benchmark --allow-experimental-pymupdf
```

Optional --output datasets/evaluation-parsers-next und --repeats 2 (2–10).
Ohne Opt-in verweigert die CLI den Lauf. Ohne installiertes Extra gibt es eine klare
Fehlermeldung. Standardtests überspringen nur explizit optionale PyMuPDF-Fälle;
der zusätzliche CI-Job muss diese Tests und den vollständigen Vergleich ausführen.

Output: comparison.json und comparison.md plus run-*/<fixture>/original.pdf,
gold.json und Stores je Parser/Wiederholung. Alle Originale sind synthetisch.
Schema-2-Artefakte enthalten Config/Parser/Version, Roh- und Ausgabetexte, Geometrie,
Tabellen und Hashreferenzen. Receipts erlauben reproduzierende Quellenprüfungen.

## Unveränderter Korpus und Fairness

24 Fälle / 29 Seiten aus Sprint 3, ohne neue Sollwerte oder Layoutvereinfachungen.
Die Gold-SHAs und normalisierten Quell-Dateihashes von Goldstandard und Renderer
werden im Regressionstest gegen Sprint 3 festgeschrieben. Der PDF-Corpus-SHA
bindet die konkret erzeugten Bytes und darf zwischen Plattformen abweichen.
Originalbytes werden einmal erzeugt und beiden Adaptern übergeben.
Keine Goldtexte gelangen in die Parser. Nur die ausdrücklich goldgestützte
Fundstellen-Lokalisierung und Bewertung verwenden Sollzitate.

pypdf: bestehender plain-strict-Text, keine behauptete Layoutstruktur.
PyMuPDF: raw_text bleibt erhalten; text verwendet sort=True, geometrische
Tabellenerkennung ist eingeschaltet. Textpräferenz bezieht sich genau auf diese
Konfiguration, nicht auf jede mögliche Verwendung der Bibliothek.

Die zusätzliche Struktur wird nicht automatisch positiv gewertet:
falsche/zusätzliche Zellen zählen als False Positives. Fehlende Strukturen sind
unsupported; fehlgeschlagene Strukturauslesung ist not_evaluable mit Diagnose.

## Neue Metriken

Textmetriken und Nenner aus [EVALUATION](EVALUATION.md) bleiben gültig.
Version 2 ergänzt:

- Table Cell Precision = exakt zugeordnete Zellen / ausgegebene Zellen.
- Table Cell Recall = exakt zugeordnete Zellen / annotierte Zellen.
- Header Association Precision = exakt korrekte Beziehungen / ausgegebene Beziehungen.
- Header Association Recall = exakt korrekte Beziehungen / annotierte Beziehungen.

Zellschlüssel: physische Seite, Tabellenordinal auf der Seite, Grid-Zeile/-Spalte,
Row-/Column-Span und unveränderter Zelltext. Table-IDs aus Gold werden nicht in
Parserausgaben kopiert. Ordinalzuordnung kann bei zusätzlichen Tabellen weitere
Zuordnungen verschieben: das ist konservativ und bleibt eine dokumentierte Grenze.
Headerflags gehören nicht zum neuen Zellscore, weil daraus keine verlässlichen
Header-Wert-Beziehungen folgen. Der alte strengere Headerflag-Zellscore bleibt
in den Reports separat unsupported.

Matching verwendet Multisets; doppelte Ausgaben erzeugen zusätzliche False Positives.
Nenner 0 = not_evaluable. Keine Tabellen in der Referenz, aber ausgegebene Zellen:
Precision=0, Recall=not_evaluable. Keine Erkennungsfähigkeit: unsupported.
Relationsschlüssel müssen im späteren Adapter beide Endpunkte samt Text, Tabellen-,
Seiten- und Zellidentität enthalten. Der aktuelle Adapter liefert bewusst keine Kanten;
beide Relationsmetriken bleiben unsupported. Der reine Scorer wird mit zusätzlichen,
falschen und doppelten Beziehungen getestet.

Klauselgrenzen bleiben unsupported. Die Reading-Order-Metrik misst auffindbare
Textanker im ausgegebenen text, nicht die semantische Wahrheit geometrischer Reihenfolgen.
Evidence-Validity prüft Rohspannen zusätzlich über den reproduzierenden Store;
der goldgestützte Locator bleibt keine autonome Claims-Extraktion.

## Entscheidungsregel und Relevanz

Vorab festgelegte Regel, keine gewichtete Rangliste:
Nur Fälle ohne Layoutfehler mit bestandener Provenienzprüfung und identischen Wiederholungshashes
kommen für eine Textpräferenz infrage. Vergleich von CER, WER, Vollständigkeit,
Ankerreihenfolge/-abdeckung, Spanvalidität, Seitenrichtigkeit und fehlender Evidenz:
mindestens eine Verbesserung ohne Regression bevorzugt diesen Parser für diesen
Fall. Gegensätzliche Verbesserungen ergeben tradeoff; Gleichstand no_clear_advantage.
Nicht messbare Dimensionen werden aufgelistet und nicht als Erfolg gewertet.

Das ist eine deskriptive Regel, keine automatische Produktionsauswahl.
Strukturbedarf wird daneben über gemessene Precision/Recall beurteilt.
Schon eine Spalten-Regression ist praktisch relevant, wenn Klauselteile vertauscht
werden; geringe aggregierte Unterschiede erlauben keine Populationsaussage.
24 kontrollierte Fälle, nur eine Fontfamilie und wenige Beispiele je Layout
rechtfertigen keine Signifikanztests oder Konfidenzbehauptung.

## Performance und Reproduzierbarkeit

parser_runtime_ms misst einen separaten vollständigen Adapteraufruf inklusive
Layout-/Tabellendetektion, ohne Rendering, Store oder Metrikberechnung.
runtime_per_document_ms misst Ingestion, verifizierten Reload und Spanprüfung.
Der zusätzliche zeitgemessene Aufruf muss dasselbe Artefakt ergeben.
Mittelwerte enthalten Summe und Anzahl; rohe Einzelzeiten stehen im JSON.
Parserspezifische Ergebnisse werden je Wiederholung in frischen Stores gespeichert.

Die erste Parserreihenfolge wechselt zwischen Fällen. Dennoch ist dies ein kleiner
Warm-Process-Benchmark, kein kontrollierter Leistungsnachweis: Dateisystem,
Virenscanner, Caches und Messrauschen beeinflussen Zeiten. PyMuPDF führt mehr Arbeit
aus als die reine pypdf-Textbaseline. Kein pauschaler Geschwindigkeitsvergleich
der Bibliotheken und keine maschinenübergreifenden Zeitdeltas.

quality_sha256 schliesst Zeiten und volatile Metadaten aus, bindet aber Originale,
Sollwerte, Artefakte, Configs, Versionen und Ergebnisse. Wiederholte vollständige
Läufe müssen denselben Fingerprint liefern. Unterschiedliche Parserstände erzeugen
absichtlich andere Artefakthashes. Kein Hash ist eine Signatur.

## Lizenz, Sicherheit und nächster Schritt

[Artifex beschreibt AGPLv3 und kommerzielle Lizenzierung](https://pymupdf.io/licensing),
einschliesslich Quelloffenlegung für Netzwerkprodukte. Eine proprietäre SaaS-Freigabe
wird daraus nicht abgeleitet. PyMuPDF bleibt opt-in und experimentell; vor Produktion
sind Lizenz-/Vertragsprüfung und Distributionsstrategie erforderlich.
Eine optionale Abhängigkeit beseitigt keine Pflichten bei tatsächlicher Nutzung.

Echte AVB erfordern weiterhin isolierten Worker mit harten Ressourcenlimits,
kontrollierte Quellenaufnahme samt Abrufnachweisen, Nutzungs-/Speicherregeln,
grössere unabhängige Annotationen und fachliche Review-/Freigabeschwellen.
Hashes beweisen weder Quellenechtheit noch versicherungsfachliche Richtigkeit.

Ein späterer LLM-Extraktor kann die versionierten Texte und Fundstellen als
Schnittstelle nutzen. Für verlässliche fachliche Extraktion fehlen aber ein
semantischer Goldstandard, geprüfte Header-/Wert-/Ausnahmezuordnung und die
Betriebs-/Lizenzfreigaben. Noch keinen produktiven LLM-Agenten darauf freigeben.

Nächste Experimente: sort=False gegen sort=True als explizite Ablation;
spaltenbewusste Ordnung ohne Goldhilfen; unabhängige Tabellen mit Fehl-/Mehrzellen;
weitere Fonts/Rotationen und isolierter Worker. Kein Parserwechsel allein wegen
zusätzlicher Felder oder niedrigerer aggregierter CER.

## Schema-2-API (synthetisches Beispiel)

```python
from pathlib import Path
from axiory.evaluation.fixtures import render_pdf
from axiory.evaluation.goldstandard import corpus
from axiory.ingestion_models import LogicalDocument
from axiory.parsers.models import ParserConfig
from axiory.parsers.store import LayoutStore

config = ParserConfig(parser="pymupdf", sort_text=True, tables=True)
store = LayoutStore(Path("datasets/evaluation-api"), config=config, experimental=True)
receipt = store.ingest(
    render_pdf(corpus()[0]),
    LogicalDocument(
        id="synthetic-layout",
        product_id="synthetic-product",
        title="SYNTHETIC",
        kind="policy_conditions",
        synthetic=True,
    ),
)
verified = store.load(receipt)  # Hashprüfung und vollständige Re-Extraktion
```

Für Schema 1 weiterhin DocumentStore verwenden. Die gespeicherte Config und
Parser-Version sind für spätere Verifikation verbindlich; unbekannte Konfigurationen
werden nicht stillschweigend auf aktuelle Defaults umgesetzt.

## Gemessene Baseline (sauberer Commit df4f45c)

[Menschenlesbarer Export](benchmarks/sprint4-comparison.md) und
[maschinenlesbare Zusammenfassung](benchmarks/sprint4-summary.json).
Die Zusammenfassung lässt Rohtexte/Boxen weg; der vollständige Report und alle
Original-/Store-Artefakte liegen lokal unter datasets/evaluation-parsers und im
CI-Artefakt. Die Zusammenfassung bezeichnet den Quellfingerprint ausdrücklich als
source_quality_sha256, nicht als Hash ihrer verkürzten eigenen Inhalte.
Dieser nachfolgende Dokumentationscommit ändert keine Implementierung/Sollwerte.

Windows, Python 3.12.14; pypdf 6.19.0, PyMuPDF 1.28.2; zwei Wiederholungen pro Fall.
Zwei vollständige Läufe ergeben denselben Qualitätsfingerprint
649c62251741506a839036c8473a3c597292dfe589831adf65f43b1e5b676bc8.

| Messung | pypdf | PyMuPDF |
| --- | --- | --- |
| CER | 332/3503 = 9,48 % | 243/3503 = 6,94 % |
| WER | 54/521 = 10,36 % | 36/521 = 6,91 % |
| Ankerreihenfolge | 270/282 = 95,74 % | 280/282 = 99,29 % |
| Ankerabdeckung | 105/111 | 105/111 |
| Zell-Precision / Recall | unsupported | jeweils 36/36 |
| Parserlaufzeit, Mittel | 15,94 ms | 26,19 ms |
| Store + Reload + Evidence, Mittel | 156,20 ms | 183,36 ms |

PyMuPDF ist in dieser Konfiguration inklusive Tabellen/Layout im Parseraufruf etwa
1,64-mal so langsam; im vollständigen Storepfad etwa 1,17-mal. Keine allgemeine
Geschwindigkeitsbehauptung und kein kontrollierter Vergleich gleicher Fähigkeiten.

Fallweise Textregel: PyMuPDF gewinnt bei table-column-order und headers-footers;
pypdf gewinnt bei columns-column-order. Die übrigen 21 Fälle ergeben keinen klaren
Textvorteil. Beide verlieren Bild-/Vektortext. PyMuPDF erkennt die vier geometrischen
Tabellen einschliesslich verbundener Zellen mit 36 richtigen Zellen und ohne zusätzliche
Zellen in diesem Korpus. Das beweist keine korrekte semantische Header-/Wertzuordnung.
Klauselgrenzen und zuverlässige Header-Kanten bleiben bei beiden unsupported.

Die leere ReportLab-Seite bleibt im Gold empty: PyMuPDF meldet empty, pypdf weiterhin
not_extractable. Das ist eine beobachtete Zustandsabweichung, keine Änderung des Solls.
Keine globale Umschaltung: pypdf bleibt Standard, PyMuPDF ein gezieltes Layout-Experiment.
Ein Vorteil auf realen AVB oder anderer Sortierkonfiguration ist bislang unbewiesen.

Qualität: 227/227 Tests mit Extra; ohne Extra 194 bestanden und 33 ausdrücklich
optionale PyMuPDF-Tests übersprungen. 168 bisherige Tests bleiben erhalten.
Lint, Formatprüfung, Demo und bestehende Evaluation sind erfolgreich.
Der Sprint-3-Fingerprint bleibt unverändert. GitHub-CI-Status steht im zugehörigen PR.

## Beobachtete Plattformgrenze in der CI

Der erste Linux-Lauf bestand 226/227 Tests; eine unzulässige Annahme gleicher
Windows-/Linux-PDF-Bytes im neuen Freeze-Test scheiterte. Der Standard-CI-Job war grün.
Vergleich des heruntergeladenen Linux-Artefakts mit der Windows-Baseline zeigte:
Nur vector-text, image-only und mixed-text-image haben andere PDF-Hashes. Diese
Fixtures verwenden Pillow-Rasterdaten (Vektortext wird daraus gezeichnet).
Alle Gold-Hashes, extrahierten Seitentexte und Qualitätsaggregate sind identisch.
Die genaue native Rendering-Build-Ursache wurde nicht weiter isoliert.

Windows-Corpus: e050f9872587a6845b4d163a2116f5b43db635fdbe0b5d12e8249e51d70e7069.
Linux-Corpus: da7172f10b9d81e6c2d93d05e0e22ca1b1d5742640fe7efe0f7d29b899848067.

Der korrigierte Test friert stattdessen Gold-Hashes und Quell-Dateihashes aus PR #2
ein, prüft den tatsächlichen Corpus-SHA und identische Originalbytes beider Parser
je Lauf. Wiederholte Läufe müssen weiterhin identische Qualitätsfingerprints liefern.
Keine Änderung am Goldstandard, Renderer oder an den Parserergebnissen.
Plattformübergreifende Läufe mit verschiedenen PDF-Hashes dürfen nicht als derselbe
Byte-Korpus aggregiert werden; die gespeicherte Windows-Messung bleibt so gekennzeichnet.

Die endgültige Diagnose unterscheidet geometrisch erkannte Zellen von fehlenden
Headerflags: Letztere führen beim Legacy-Score zu unsupported, nicht pauschal zu
Strukturverlust. Gemessene Zellfehler verwenden die neuen Precision-/Recall-Werte.
Diese Präzisierung ändert keine Sollwerte oder numerischen Qualitätsmetriken.
