# Architektur

Ein installierbares Python-Paket mit synchronen, deterministischen Funktionen.
Keine Server, Datenbank oder externen Laufzeitdienste. `models.py` definiert den
Datenvertrag, `provenance.py` prüft Quellenbezüge und `demo.py` erzeugt Fixtures und
JSON-Vergleichszeilen. Alle Laufzeitabhängigkeiten reduzieren sich auf Pydantic.

## Beziehungen und Semantik

Insurer → InsuranceProduct → Document. Claim bezeichnet eine analytische Aussage
(keinen Schadenfall), verweist auf ein Produkt und enthält normalisierte Coverage
sowie Evidence. Evidence verweist auf eine konkrete Dokument-ID und Textspanne.
Document enthält SHA-256 der Originalbytes, URI und Version. IDs sind lokale stabile
Bezeichner; eine persistente globale Identitätsstrategie ist noch offen.

Coverage verwendet versionierte Ontologiecodes und drei Zustände: covered, excluded,
unknown. Limite besteht immer aus positivem Decimal-Betrag, Währung und Bezugsgrösse.
Ohne Limite bleibt deren Höhe unbekannt. Bedingungen sind zunächst strukturierte
Textlisten. Mehrere Sublimiten, Selbstbehalte, territoriale Regeln und Konflikte sind
noch nicht modelliert; solche Inhalte dürfen später nicht verlustbehaftet eingepasst werden.

Die Pydantic-Modelle sind unveränderlich, verbieten zusätzliche Felder und prüfen
fachliche Minimalinvarianten. JSON-Arrays werden bewusst in Tupel und Geldstrings in
Decimal umgewandelt; Integer-Offsets und Boolean-Markierungen sind strikt.
JSON-Schemas sind über `Claim.model_json_schema()` verfügbar. Künftige LLM-Antworten
werden über `Claim.model_validate_json(payload)` validiert und dann separat geprüft.

## Provenienz und Vertrauensgrenzen

Die Demo besitzt UTF-8-Quellen im Code und gibt sie vollständig im Ergebnis aus.
Offsets sind halb offene Unicode-Zeichenintervalle `[start_char, end_char)` im
dekodierten Text. Hashes beziehen sich auf die exakten UTF-8-Bytes.
`verify_source` prüft Produkt-/Dokumentreferenzen, Hash und exakte Zitate. Die erste
Version unterstützt pro Prüfaufruf genau ein Dokument, keine Multi-Dokument-Claims.
Referenzintegrität zum Versicherer und Eindeutigkeit aller IDs sind noch keine
allgemeine Importfunktion; diese wird mit Ingestion ergänzt.

`unverified` → `source_matched` → `human_reviewed` beschreibt beabsichtigte Stufen.
Derzeit sind Statusfelder deklarativ; nur die Demo setzt `source_matched` nach Prüfung.
Importierte Statusangaben dürfen künftig nicht als vertrauenswürdig gelten. Exakte
Zitate beweisen keine semantische Unterstützung, Vollständigkeit oder Aktualität.
Ein Produktionsworkflow benötigt Review-Identität, Zeitpunkt und Prüfprotokoll.

PDF-Ingestion muss Originalbytes und separat versionierten extrahierten Text samt
Seiten-/Positionsabbildung erhalten. Abrufzeitpunkt, URL, Dokumentgültigkeit,
Extraktorversion und Konfliktbehandlung fehlen bewusst noch. Keine echten Daten vor
Implementierung und Tests dieses Pfads. Entscheidung: [ADR 0001](adr/0001-evidence-first-foundation.md).

Werkzeuggrundlagen: [uv Locking](https://docs.astral.sh/uv/concepts/projects/sync/),
[uv CI](https://docs.astral.sh/uv/guides/integration/github/),
[Pydantic](https://docs.pydantic.dev/latest/concepts/models/).
