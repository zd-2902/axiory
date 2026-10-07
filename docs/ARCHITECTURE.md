# Architektur

Installierbares Python-3.12+-Paket mit synchronen, deterministischen Funktionen.
Laufzeitabhängigkeiten: Pydantic für Datenverträge, pypdf für PDF-Textauslesung.
Keine Datenbank, Server, LLMs oder Agentenorchestrierung.

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
Die Ontologie bleibt 0.1.0.

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

Originale bleiben auch bei Parserfehlern erhalten. Ein Receipt kennzeichnet einen
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
