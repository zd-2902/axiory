# ADR 0004: Optionale Parseradapter und überprüfbare Layoutartefakte

- Status: angenommen für synthetische Experimente; keine PyMuPDF-Produktionsfreigabe
- Datum: 2026-10-09
- Grundlage: ADR 0001–0003; PR #1 und #2 bleiben offen und ungemergt.
- Branchbasis: codex/layout-evaluation (Sprint 3).

## Entscheidung

ParserProtocol vereinheitlicht extract(original, version_sha256, limits), Konfiguration
und Parser-Version. PypdfAdapter kapselt den bestehenden plain-strict-Extraktor.
PyMuPDFAdapter ist ein explizites Experiment mit separatem Installations-Extra und
experimental=True. Import der Adaptermodule lädt PyMuPDF nicht implizit.

Schema 1 und DocumentStore bleiben unverändert. LayoutStore verwendet gemeinsame
Originale, logische Dokumente, Identitätsindex, Versionen und Acquisitions.
Neue layout_extractions und layout_receipts verwenden Schema 2. Gemeinsame
Dateispeicherprimitive und Evidence-/Claim-Prüfung werden geerbt; Orchestrierung wird
vorläufig getrennt gehalten, um alte Hashes und Parserreproduktion nicht umzudeuten.
Das bedeutet bewusst etwas duplizierte Ingest-/Load-Orchestrierung.

Ein LayoutArtifact bindet Original-SHA, Dokumentversions-SHA, Parser-Version,
ParserConfig (Parsername, Schema-/Adapterversion, Sortierung, Tabellenmodus),
Status und Seiten. Der SHA-256 seiner kanonischen JSON-Bytes ist der Extraktionshash
in Receipt/Dateiname; kein rekursives Hashfeld im Artefakt.
Physische Seiten und alle eingebetteten Strukturelemente erben diese Bindung.

## Layout und Text

PyMuPDF liefert unveränderten raw_text mit sort=False und separat den konfigurierten
text mit sort=True oder False. Keine nachträgliche Unicode-/Whitespacebereinigung.
PdfEvidence adressiert weiterhin text; RawSpan an Blöcken/Zeilen adressiert ausdrücklich
raw_text. Mehrdeutige/fehlende exakte Zuordnung ergibt null, keine erfundene Spanne.

Blöcke, Zeilen und Bounding Boxes sind parsergelieferte Geometrie; sie sind keine
verifizierten Versicherungsfakten. Koordinaten: unrotierte Cropbox, Ursprung links oben,
PDF-Punkte. Breite/Höhe und Rotation sind gespeichert. Negative, nichtendliche,
invertierte oder ausserhalb der Seite liegende Boxen werden abgelehnt.
Block-/Zeilenhierarchie, Lesereihenfolge-Permutation und Zellüberlappungen werden geprüft.

Sortierung und Tabellenrekonstruktion werden als heuristic ausgewiesen:
PyMuPDF find_tables erkennt geometrische Linien/Abstände; Axiory leitet Grid-Spans
aus den gelieferten Zellgrenzen ab. Tabellen werden pro Seite räumlich geordnet.
Header-Kandidaten des Parsers bleiben nur Kandidaten; zuverlässige Header-Wert-Kanten
und Klauselgrenzen sind unsupported. Keine aus Goldwerten erzeugte Struktur.

Fehlschläge der Layoutanalyse erhalten bereits vorhandenen Text samt layout_errors;
Tabellen sind dann null, nicht eine erfolgreiche leere Liste. Verschlüsselte PDFs
(auch mit leerem Passwort) werden nicht entschlüsselt. Reparierte PDFs werden
explizit als damaged abgelehnt. Grössen-/Seitenlimits gelten für beide Adapter.
Native Parserfehler, OCR-Bedarf, leere und nicht extrahierbare Seiten bleiben sichtbar.

## Provenienz und Migration

PdfEvidence pdf-1 ist weiterhin ausreichend: der Extraktionshash bindet nun auch
Parser, Konfiguration und die konkrete Dokumentversion. Kein Austausch von Spannen
zwischen Parsern. LayoutStore.load verlangt exakt passende Config und Parser-Version,
prüft alle Hashes/Referenzen und reproduziert das gesamte Artefakt einschliesslich
Bounding Boxes, Blöcken und Tabellen. Selbst neu gehashte Manipulationen scheitern
an dieser Reproduktion. Importierte Verifikationsflags bleiben ohne Autorität.

Alte Receipts werden weiter mit DocumentStore geladen. Neue mit LayoutStore und
aufgezeichneter Config. Keine automatische Dateimigration oder Umschreibung.
Gleiche PDF-/Dokumentmetadaten ergeben dieselbe Dokumentversion in beiden Stores;
unterschiedliche Parser/Configs erzeugen eigene Extraktionsartefakte.

## Benchmark und Auswahlregel

Der Sprint-3-Goldstandard und Renderer bleiben unverändert; beide Adapter erhalten
dieselben einmal generierten PDF-Bytes. Neue Metrikversion 2 ergänzt Zell-Precision/
Recall und Relations-Precision/Recall. Exaktes Multiset-Matching bestraft zusätzliche
und doppelte Ausgaben; Tabellenzuordnung erfolgt über physische Seite und räumlichen
Ordinal, nicht anhand passender Solltexte. Historische Sprint-3-Metriken bleiben
separat erhalten; ihr strenger Zellscore verlangt zusätzlich Headerflags.

Keine Gesamtscores oder Signifikanztests. Textpräferenz wird fallweise über
Provenienz/Reproduzierbarkeit, Abwesenheit von Layoutfehlern und Pareto-Vergleich vorab definierter Textmetriken
bestimmt. Gewinne und Regressionen bleiben nebeneinander sichtbar.
Die Fähigkeit zur Tabellenerkennung ist eine zusätzliche, gesondert gemessene Dimension.
pypdf bleibt Default, PyMuPDF experimentell; keine automatische Produktionsumschaltung.

## Lizenz und Sicherheitsgrenzen

PyMuPDF wird unter AGPLv3 oder kommerzieller Lizenz angeboten.
Für proprietäre B2B-SaaS darf keine Lizenzkompatibilität vorausgesetzt werden.
Artifex beschreibt insbesondere Offenlegungspflichten bei Netzwerkprodukten.
Vor Produktion braucht es eine geprüfte Lizenzstrategie, gegebenenfalls einen
kommerziellen Vertrag; optionales Packaging ist keine Ausnahme von Lizenzpflichten.
Repositorylizenz und Distributionsmodell bleiben offen.

Offizielle Quellen, geprüft 2026-10-09:
- [PyMuPDF Licensing](https://pymupdf.io/licensing)
- [PyMuPDF Page API und Koordinaten](https://pymupdf.readthedocs.io/en/latest/page.html)
- [TextPage-Repräsentation](https://pymupdf.readthedocs.io/en/latest/app1.html)

Die Standardinstallation enthält PyMuPDF nicht. Ein separates CI-Experiment installiert
das Extra; der Benchmark verlangt zusätzlich --allow-experimental-pymupdf.
Keine Netzwerk-Ingestion, OCR oder LLMs. Beide Parser laufen weiterhin im Prozess:
Byte-/Seitenlimits sind keine CPU-/RAM-/Zeitlimits. Native Bibliotheken erhöhen die
Angriffsfläche; isolierter Worker und Freigabeprozess fehlen vor echten AVB.

## Bewusste Schulden

Keine automatische Parserversionsverwaltung, komplexe Rotation/Cropbox-Stichprobe
noch nicht repräsentativ, kein semantischer Headerbezug und kein unabhängiger
Struktur-Goldstandard für echte Dokumente. Textanker bleiben eine goldgestützte
Evaluationshilfe. Die optionale Abhängigkeit ist gelockt, aber noch keine langfristige
Lizenzentscheidung. Ein weiterer Parser ist nur bei gemessenem Nutzen sinnvoll.
