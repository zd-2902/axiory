# Architektur

Installierbares Python-3.12+-Paket mit synchronen, deterministischen Funktionen.
Laufzeitabhängigkeiten: Pydantic für Datenverträge, pypdf für PDF-Textauslesung,
ReportLab für synthetische Evaluations-PDFs (eingebetteter Vera-Font).
Keine Datenbank, Server oder Agentenorchestrierung. Sprint 5 ergänzt einen optionalen
LLM-Adapter hinter einer standardmässig offline ausgeführten Providergrenze.

## Fachmodell und Kompatibilität

Insurer → InsuranceProduct → Dokumentfamilie. Claim ist eine analytische Aussage,
kein Schadenfall. Coverage enthält versionierte Ontologiecodes, covered/excluded/unknown,
Decimal-Limiten samt CHF und Bezugsgrösse sowie Bedingungen. Fehlende Limite ist
unbekannt, nicht unbegrenzt. Sublimiten, Selbstbehalte, territoriale Regeln und
Konfliktauflösung sind weiterhin offen.

Das bisherige Document/Evidence-Modell und die Text-Demo (Schema 0.1.0) bleiben gültig.
provenance.verify_source prüft weiterhin deren UTF-8-Originalbytes. Claim akzeptiert
zusätzlich PdfEvidence (pdf-1); PDF-Fundstellen müssen über DocumentStore geprüft werden.
Es gibt keine automatische Umdeutung alter Text-Offsets in PDF-Positionen.
Die Legacy-Ontologie bleibt 0.1.0; additive Sprint-5-Claims verwenden travel-1.

## PDF-Datenfluss

1. LogicalDocument und optionale VersionMetadata strikt validieren.
2. Unveränderte Bytes unter Originalhash speichern, dann Dokument-/Versionsmanifest
   und Acquisition mit belegbaren Quellmetadaten ablegen.
3. Seiten mit pypdf extrahieren; Texte unverändert halten und Seitenfehler erfassen.
4. Separates ExtractionArtifact unter eigenem Hash speichern.
5. Receipt mit Referenzen zuletzt speichern und dessen Hash zurückgeben.

Logisches Dokument, Versionsmetadaten und Originalhash bestimmen eine unveränderliche
technische Version. Neue URL/Abrufzeit allein erzeugen keine neue Dokumentversion.
Korrigierte Versionsmetadaten erzeugen eine neue Version; Original/Extraktion bleiben
bei identischen Bytes und Parserergebnissen dedupliziert. Ein versionsübergreifender
Katalog oder veränderlicher Latest-Zeiger existiert noch nicht.

PDF-Modelle sind strikt, unveränderlich und verbieten zusätzliche Felder.
Unbekannte Metadaten sind null. Alle gespeicherten JSON-Objekte werden über
model_validate_json eingelesen und auf kanonische Byteform geprüft. Seiten-/Zitattext
wird nicht getrimmt oder normalisiert. Legacy-Modelle behalten ihre bisherigen Regeln.

## Integrität

Receipt → Version → Dokument/Original sowie Receipt → Acquisition/Extraktion bilden
eine hashgebundene Referenzkette. load prüft Dateihashes, Schemas, Referenzen und
reproduziert die Extraktion. PdfEvidence adressiert Dokument, Versionshash,
Extraktionshash, physische Seite und Unicode-Zeichenspanne. verify_claim prüft zusätzlich
Produktzuordnung und jede Evidenz; importierte Statusfelder haben keine Autorität.
Eine Prüfung ändert den Claim nicht und bedeutet keine fachliche Reviewfreigabe.

Zugelassene Originale bleiben auch bei Parserfehlern erhalten. Ein Receipt kennzeichnet einen
abgeschlossenen Lauf einschliesslich Fehlerergebnis. Bei Speicherfehlern wird abgebrochen;
bereits geschriebene Artefakte bleiben zur Diagnose/Wiederholung bestehen.
Das Dateisystem unterstützt atomare Veröffentlichung per Hardlink, keine
Multi-Datei-Transaktionen oder externe Schreibkonkurrenz.

## Grenzen und nächste Schnittstellen

Die Ingestion nimmt lokale Bytes entgegen, kein HTTP-Download. Originalseiten werden
über Reihenfolge referenziert, nicht über gedruckte Labels oder Pixelkoordinaten.
PDF-Textauslesung beweist keine Layouttreue, Vollständigkeit oder semantische Aussage.
Historische Verifikation benötigt die aufgezeichnete Parser-/Extraktorversion.
Hashes bieten keine Signaturen; Metadaten und die synthetische Deklaration kommen
vom Aufrufer. Ressourcenbegrenzung, Sandbox, fachliche Review-Audits und kontrollierte
Freigabe realer Quellen fehlen. Echte Daten bleiben gesperrt.

[API-Beispiel](INGESTION.md), [ADR 0001](adr/0001-evidence-first-foundation.md),
[ADR 0002: Format, Parser, Migration und Vertrauensgrenzen](adr/0002-versioned-pdf-ingestion.md).

## Review-Invarianten

IngestionLimits beschränkt PDF-Bytes und Seitenzahl, auch bei Reload/Verifikation.
ResourceLimitError mit pdf_size_exceeded/page_count_exceeded ist eine Ablehnung
vor Textauslesung; dabei wird kein neues Extraktionsartefakt/Receipt veröffentlicht.
Grössenablehnung erfolgt vor Speicherung, Seitenablehnung nach Original-/Metadaten-
speicherung. Die bestehenden Extraktionsschemas und Hashes bleiben unverändert.

Ein atomar angelegter unveränderlicher Identitätsindex bindet Dokument-ID an Produkt.
Validierte Dokument-Snapshots bleiben die zusätzliche Referenz für ältere Stores.
IdentityConflictError verhindert Produktwechsel bei gleicher ID; Titel-/Versions-
revisionen bleiben möglich. Details einschliesslich Migration und Schlüsselhash:
[ADR 0002](adr/0002-versioned-pdf-ingestion.md).

Grössen-/Seitenlimits sind keine CPU-/RAM-/Zeitlimits. Ein späterer isolierter Worker
muss Parser-Laufzeit und Speicher unabhängig vom aufrufenden Prozess begrenzen.

## Evaluation (Sprint 3)

Additive Module unter src/axiory/evaluation; keine Änderung an produktiven Schemas:

1. goldstandard.py verfasst den versionierten Sollinhalt unabhängig vom Parser.
2. fixtures.py rendert deterministische PDFs mit eingebetteter Schrift.
3. runner.py führt je Wiederholung Ingestion und verifizierten Reload in frischen Stores aus.
4. metrics.py bewertet Rohtext, begrenzte Ankerreihenfolge und goldgestützte Fundstellen.
5. reporting.py exportiert JSON/Markdown, Mikromittel, Diagnosen und Vergleichsfingerprints.

schemas.py trennt GoldFixture, Observation und Ergebnisse; Fachinterpretation bleibt
not_evaluated. Fehlende Klausel-/Tabellenfähigkeit ist unsupported. Strukturmetriken
existieren für spätere Adapter, ohne Struktur aus flachem Text zu erfinden.
PDF-/Gold-/Extraktionshashes, Versionen und Konfiguration binden die Ergebnisse.
Zeitpunkt, Maschine und Laufzeiten werden gespeichert, aber nicht in den stabilen
Qualitätsfingerprint eingerechnet. Keine automatischen maschinenübergreifenden Zeitdeltas.

Das CLI schreibt in ignorierte datasets/evaluation-Verzeichnisse; CI lädt synthetische
Ergebnisse als kurzlebige Artefakte hoch. Goldstandard und Generator werden als Code
versioniert. Alle Eingabeannotation und historische Falldaten durchlaufen strikte
Pydantic-Validierung. Hashes authentifizieren keinen externen Bericht.

Die 24 Fälle zeigen nur kontrollierte Layoutphänomene, keine reale Produktqualität.
Ein späterer Parseradapter muss seine Struktur-/Koordinatenfähigkeiten offenlegen;
produktive Provenienz darf dabei nicht stillschweigend auf neue Text-Offsets wechseln.
[ADR 0003](adr/0003-layout-evaluation.md) und [Metrikvertrag](EVALUATION.md).

## Multi-Parser-Schnittstelle (Sprint 4)

parsers/models.py definiert versionierte ParserConfig und LayoutArtifact (Schema 2),
parsers/adapters.py das ParserProtocol und zwei Implementierungen. PyMuPDF wird nur
nach explizitem Opt-in importiert; Standardinstallation und Legacy-Verifikation
benötigen es nicht. parsers/store.py ergänzt LayoutStore mit neuen Collections.
DocumentStore und seine Hash-/Identitätssemantik bleiben unverändert.

Ein neues Artefakt bindet Parser/Version/Config und Dokumentversion direkt.
PdfEvidence bleibt pdf-1: dessen Extraktionshash bindet alle zusätzlichen Angaben.
Reload reproduziert auch Geometrie und Struktur. raw_text wird neben sortiertem
text gespeichert; RawSpan gehört zu raw_text, PdfEvidence zu text. Kein Offset wird
zwischen diesen Repräsentationen automatisch übertragen.

Parsergelieferte Blöcke/Zeilen/Boxen sind von heuristischer Sortierung und geometrischer
Tabellenrekonstruktion getrennt. Header-Kandidaten werden nicht zu Fakten oder Kanten.
Layoutfehler erhalten Text und explizite Diagnosen. Tabellen sind bei Fehlschlag null.
Alte Receipts bleiben über DocumentStore lesbar, neue über LayoutStore mit exakter Config.

Die neue Vergleichs-CLI nutzt beide Adapter an identischen Bytes und unverändertem
Goldstandard. Keine Produktionsumschaltung aufgrund eines pauschalen Scores.
[ADR 0004](adr/0004-multi-parser-architecture.md) dokumentiert Migration, Lizenz und Schulden.

## Semantische Pipeline (Sprint 5)

LayoutStore.load → build_context → Provider/Caller → model_outputs → strikte DTOs →
resolve/check_candidate → optionaler Verifier → semantic_runs. Die alte Demo und
Quellenprüfung bleiben getrennt erhalten. Neue Collections ergänzen den CAS;
keine stillschweigende Migration. `replay` revalidiert Rohantworten und Herkunft,
nicht importierte Flags. Quelle, semantische Bewertung und fachlicher Review sind
verschiedene Vertrauensstufen. Kostenreservationen und Timeout-Prüfungen ersetzen
keinen isolierten Prozess. Details und Datenmodelle: [LLM_EXTRACTION](LLM_EXTRACTION.md),
[ADR 0005](adr/0005-llm-extraction-architecture.md).
