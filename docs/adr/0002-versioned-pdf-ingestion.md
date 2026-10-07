# ADR 0002: Versionierte, dateibasierte PDF-Ingestion

Status: angenommen. Datum: 2026-10-07.

## Kontext

Original-PDFs, extrahierter Text und fachliche Aussagen sind unterschiedliche Artefakte.
Ein Text-Hash allein beweist weder PDF-Zuordnung noch Extraktionsqualität. Fehlerhafte
oder teilweise Extraktionen dürfen nicht als vollständige Dokumente erscheinen.

## Entscheidung

Ein synchroner Python-Datenfluss mit genau einer neuen Laufzeitabhängigkeit: pypdf,
über uv.lock fixiert. pypdf benötigt für Text-/Strukturverarbeitung keine native
PDF-Laufzeit. strict=True und extract_text(extraction_mode="plain") bilden
Extraktorversion 1. Parsername, Paketversion, Modus und unsere Extraktorversion
werden gespeichert. PyMuPDF hätte native Laufzeit und zusätzliche Lizenzabwägungen;
pdfplumber bietet Layoutfunktionen, die seitenbezogene Textspannen noch nicht benötigen.
OCR und automatische Reparatur bleiben ausserhalb des Sprints.

LogicalDocument identifiziert eine Dokumentfamilie innerhalb eines Produkts und wird
als unveränderlicher Metadaten-Snapshot gespeichert. DocumentVersion verbindet diesen
Snapshot mit Originalhash und optionaler publizierter Versionsbezeichnung/Gültigkeit.
Die technische Version ist der Hash des Versionsmanifests, keine erfundene
Versionsnummer. Metadatenkorrekturen erzeugen eine neue technische Version; identische
Originalbytes werden trotzdem nur einmal gespeichert.

Acquisition hält Quell-URL und Abrufzeit separat. Erneute Abrufe identischer Bytes
mit gleichen Versionsmetadaten behalten dieselbe Version/Extraktion und können eigene
Acquisition-/Receipt-Artefakte erzeugen. Unbekannte URL, Zeit, Sprache, Versionslabel
und Gültigkeit bleiben null. Die API übernimmt Bytes und belegbare Metadaten vom
Aufrufer; sie lädt keine URLs herunter. Zeitangaben brauchen eine Zeitzone.
synthetic=True ist eine ausdrückliche Deklaration, keine Inhaltsprüfung.

## Speicher und Identität

Dateinamen enthalten SHA-256 über exakte Bytes. JSON ist kanonisches UTF-8 mit
sortierten Schlüsseln, kompakten Separatoren, unescaped Unicode und ohne Newline.

- documents/<hash>.json: LogicalDocument-Snapshot.
- originals/<hash>.pdf: unveränderte Eingangsbytes, auch kaputte/leere Dateien.
- versions/<hash>.json: DocumentVersion mit Original-/Dokumentreferenz.
- acquisitions/<hash>.json: Quellmetadaten einer Version.
- extractions/<hash>.json: Parserkonfiguration, Seiten, vollständige Texte, Fehlerstatus.
- receipts/<hash>.json: Verbindung von Version, Acquisition und Extraktion.

Das zuletzt geschriebene Receipt markiert einen abgeschlossenen Lauf, nicht eine
erfolgreiche Extraktion. Bestehende Dateien werden bytegenau verglichen und nie
überschrieben. Temporäre Dateien werden nach fsync per exklusivem Hardlink atomar
veröffentlicht; ein lokales Dateisystem mit Hardlinks (z.B. NTFS/ext4) ist erforderlich.
Kein unsicherer Überschreib-Fallback und keine Multi-Datei-Transaktion: Bei I/O-Fehler
oder Abbruch bleiben gespeicherte Originale/Manifeste erhalten, Fehler werden
weitergereicht. Wiederholung derselben Eingaben vervollständigt den Lauf.
Keine automatische Bereinigung verwaister Artefakte. Volle Stromausfall-Durabilität
ist nicht zugesichert; Netzlaufwerke und konkurrierende externe Schreiber werden
nicht unterstützt.

## Seiten und Evidence

Seiten sind physische, einsbasierte PDF-Seiten in unveränderter Reihenfolge.
(original_sha256, page_number) identifiziert die Originalseite;
(extraction_sha256, page_number) deren konkrete Textdarstellung. Gedruckte Seitennummern
und PDF-PageLabels spielen dabei keine Rolle. PdfEvidence speichert zusätzlich Version,
logische Dokument-ID, Zitat und halb offene Unicode-Zeichenspanne [start_char, end_char)
innerhalb genau einer Seite. Text wird weder getrimmt noch normalisiert. Spannen sind
keine UTF-8-Bytepositionen oder PDF-Koordinaten. Zitate über Seitengrenzen brauchen
mehrere Evidenzen.

## Integrität und Vertrauen

Beim Laden werden alle Dateihashes, strikten Schemas und Referenzen geprüft. Danach
wird mit der aufgezeichneten pypdf-Version erneut aus Originalbytes extrahiert.
Nur identische Ergebnisse sind zulässig; eine abweichende installierte Parser-Version
führt zu ParserVersionError. Upgrades erzeugen neue Artefakte, ohne alte Referenzen
umzuschreiben. Historische Verifikation braucht die damalige Parser-/Extraktorversion.

Auch neu gehashte, erfundene Extraktionstexte werden abgelehnt. Der Austausch des
gesamten Stores samt externer Receipt-ID ist jedoch kein authentischer Herkunftsnachweis:
Hashes sind keine Signaturen. URL, Datum und Versionslabel werden nicht unabhängig
bestätigt. Der Parser ist nicht sandboxed; harte Ressourcen-/Zeitlimits fehlen.
Deshalb bleibt der Einsatz auf kontrollierte synthetische Fixtures beschränkt.

Ergebniszustände: success, partial, empty, needs_ocr, not_extractable, encrypted,
damaged. Jede erreichbare Seite bleibt erhalten, auch leere und fehlerhafte.
Ein Bild ohne Text ist ein OCR-Bedarfsindikator, kein gesicherter Scan-Nachweis.
Bild-/Form-XObjects und Inline-Bilder werden berücksichtigt; Vektorgrafik ohne Text
wird not_extractable. OCR-Textschichten, Fonts, Tabellen, Lesereihenfolge und stille
Parserungenauigkeiten brauchen spätere Layout-/Fachprüfung. Nichtleerer Text beweist
keine vollständige Extraktion.

Evidence-/Claim-Prüfung liest und reproduziert die Quellen. Importierte verification-
Flags werden nicht als Prüfnachweis akzeptiert oder automatisch hochgestuft.
Einzelne Textseiten eines partial-Dokuments können belegt werden; der Dokumentstatus
bleibt partial. Quellenabgleich bestätigt keine semantische oder juristische Aussage.

## Kompatibilität

Document, Evidence und Text-Demo (Schema 0.1.0) bleiben unverändert. Claim akzeptiert
zusätzlich PdfEvidence (schema_version pdf-1). Neue Manifeste verwenden Schema 1;
die Versicherungsontologie bleibt 0.1.0. Der bisherige UTF-8-Prüfer lehnt PDF-Evidenz ab.
Keine automatische Migration: Legacy-Textdokumente sind keine PDF-Versionen.
Tatsächliche PDF-Originalbytes müssen neu ingestiert und deren Evidence-Spannen neu
erstellt werden. Fehlende Metadaten bleiben null.

## Referenzen

[pypdf-Textauslesung und Grenzen](https://pypdf.readthedocs.io/en/stable/user/extract-text.html),
[pypdf strict-Modus](https://pypdf.readthedocs.io/en/stable/user/robustness.html).
