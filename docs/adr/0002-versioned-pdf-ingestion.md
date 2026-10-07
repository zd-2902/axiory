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

Inhaltsartefakte tragen SHA-256 über exakte Bytes im Dateinamen. Der unten
beschriebene Identitätsindex ist die einzige Ausnahme. JSON ist kanonisches UTF-8 mit
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

## Review-Ergänzung: Ressourcen-Zulassung und dauerhafte Identität

Die Zulassung ist von Extraktionsinhalt/Parserkonfiguration getrennt. IngestionLimits
definiert strikt positive ganze Zahlen: max_pdf_bytes (Standard 20 MiB = 20 * 1024 * 1024)
und max_pages (Standard 200). Exakte Grenzwerte sind erlaubt. DocumentStore akzeptiert
limits=IngestionLimits(...); der Parseradapter dieselbe optionale Konfiguration.

Eine Überschreitung löst ResourceLimitError mit code, actual und limit aus:
pdf_size_exceeded oder page_count_exceeded. Das ist eine **Ablehnung**, kein
Extraktionsstatus success/partial/damaged und kein neu veröffentlichtes Receipt.
Die API fängt diese Ausnahme nicht als Parserfehler ab. Eine Grössenüberschreitung
wird vor Hashberechnung, Speichern und PdfReader geprüft; es entsteht kein Original-
artefakt. Die aufrufende Anwendung behält ihre Eingangsbytes und muss die Ablehnung
anzeigen/protokollieren. Eine Seitenüberschreitung wird nach Ermittlung der Seitenzahl,
aber vor der ersten Textauslesung geprüft. Bereits gespeicherte Originalbytes,
Versions-/Abrufmetadaten und Identitätsbindung bleiben erhalten; kein Extraktions-
artefakt oder neues Receipt entsteht. Ein früher erfolgreiches Receipt bleibt gültig,
wird aber unter nun strengeren Limits nicht verifiziert.

Reloads unterliegen derselben aktuellen Zulassung: Dateigrösse vor dem Lesen prüfen,
höchstens max_pdf_bytes + 1 Bytes lesen und die Seitenzahl vor Re-Extraktion prüfen.
Limits werden nicht ins Extraktionsartefakt eingebettet. Deshalb bleiben bestehende
Hashes, Evidence-Referenzen, Schema 1 und Extraktorversion 1 für akzeptierte PDFs
unverändert. Bei bewusster Lockerung der Limits kann derselbe Aufruf wiederholt werden.

Das sind keine harten CPU-/RAM-/Zeitgarantien. Die Bytes liegen beim API-Aufruf bereits
im Speicher; PdfReader muss vor der Seitenzahlprüfung den Seitenbaum analysieren.
Komprimierte Streams, feindliche PDFs, JSON-Artefakte und Indexscans können weiterhin
Ressourcen verbrauchen. Echte CPU-/Speicher-/Zeitlimits erfordern einen späteren
isolierten Worker mit Prozessgrenzen/Abbruchmechanismus. Keine realen Dokumente freigegeben.

Eine logische Dokument-ID ist innerhalb eines Stores dauerhaft an genau ein Produkt
gebunden. identities/<sha256(document_id UTF-8)>.json enthält eine kanonische
DocumentIdentity (Schema 1, document_id, product_id). Dieser unveränderliche Index ist
nach dem Schlüssel gehasht, **nicht** nach seinem Inhalt; er ersetzt keine bestehenden
Hashreferenzen. Seine Bytes müssen exakt der erwarteten kanonischen Bindung entsprechen.
Publikation erfolgt exklusiv/atomar wie bei Inhaltsartefakten. Zwei konkurrierende
Erstschreiber verschiedener Produkte können deshalb nicht beide gewinnen.

Ingestion und Reload prüfen zusätzlich die validierten documents-Snapshots für die
angefragte ID. Damit werden Konflikte auch in älteren Stores ohne Index erkannt;
bereits widersprüchliche Historien führen zu IdentityConflictError statt automatischer
Umdeutung. Reload alter Stores bleibt lesend; die nächste konfliktfreie Ingestion legt
die Bindung an, ohne alte Artefakte umzuschreiben. Metadatenrevisionen und neue PDF-
Versionen desselben Produkts bleiben erlaubt. Verschiedene Dokument-IDs dürfen auf
verschiedene Produkte zeigen und dieselben Originalbytes deduplizieren.

Die Reservierung erfolgt vor den übrigen Schreibvorgängen. Nach Abbruch kann daher
eine Bindung ohne abgeschlossenen Lauf existieren; sie wird absichtlich nicht entfernt.
Ein Produktwechsel benötigt eine neue logische Dokument-ID. Eine manuelle Änderung
oder Löschung des gesamten Stores bleibt ausserhalb der Authentizitätsgarantien.
Die Prüfung älterer Snapshots ist O(Anzahl gespeicherter Dokument-Snapshots); ein
skalierbarer Katalog ist weiterhin nicht implementiert.
