# Roadmap

1. **Fundament (erledigt):** Paket, Fachmodelle, synthetische Demo, Lockfile, CI und ADR.
2. **Synthetische Ingestion (Sprint 2):** logische Dokumente, unveränderliche Versionen,
   Originalbytes und Hashes, nullable Quellmetadaten, separate Parser-/Textartefakte,
   stabile Seiten-/Textspannen und verifizierter Reload. Fehlerzustände, Deduplikation,
   Manipulation und Rückwärtskompatibilität sind getestet. Review-Fixes ergänzen
   PDF-Grössen-/Seitenlimits sowie eine dauerhafte Dokument-ID-/Produktbindung.
3. **Layout-Evaluation (Sprint 3):** 24 synthetische Fälle, unabhängiger versionierter
   Goldstandard, CLI-Benchmark, explizite Nenner/Fähigkeitslücken und JSON-/Markdown-Reports.
   Kein fachlicher oder repräsentativer AVB-Qualitätsnachweis.
4. **Gate vor echten Daten (noch offen):** synthetische Encoding-/Layoutvielfalt erweitern, harte CPU-/RAM-/Zeitlimits im isolierten Worker implementieren, kontrollierte Aufnahme
   mit Abrufprotokoll implementieren. Nutzungs-/Speicherregeln und fachlichen Review
   dokumentieren. Freigabe erst nach bestandenen Integrationsprüfungen und explizit
   dokumentierter fachlicher Freigabe. Öffentlich zugänglich allein genügt nicht.
5. **Goldstandard und Ontologie:** nach Gate repräsentative Quellen doppelt annotieren,
   Differenzen klären, Sprachen/Versionen trennen, Bedingungen/Sublimiten ergänzen.
6. **Extraktion (später):** deterministische Baseline, dann optional LLM mit
   Schema-Validierung, Modell-/Promptversion und Evaluation. Nicht Teil von Sprint 3.
7. **Vergleich (später):** kompatible Bezugsgrössen/Gültigkeitsstände, Quellenansicht,
   fachlicher Review vor Produktivfreigabe. Noch keine Weboberfläche.

Nächste empfohlene Iteration: koordinatenbewusster Parservergleich am unveränderten
Goldstandard, insbesondere Spalten-/Tabellenreihenfolge und Header/Wert-Zuordnung.
Struktur-Precision und robuste ID-Zuordnung ergänzen. Isolierten Worker für harte
CPU-/RAM-/Zeitlimits spezifizieren; Quellenaufnahme bleibt hinter dem Gate.
Keine Erweiterung um LLMs oder Agenten, bevor diese Baseline verstanden ist.

Offen bleiben Lizenz, Ontologieverantwortung, Review-/Freigabeschwellen, Nutzungsregeln,
Mehrsprachigkeit und fachliche Dokumentpriorität bei Konflikten. Technische Versionen
sind implementiert, fachliche Gültigkeit und Echtheit sind damit nicht bewiesen.
