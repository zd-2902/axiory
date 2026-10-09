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
6. **Extraktion (Sprint 5, synthetisch):** deterministische Baseline, optionaler LLM-Adapter,
   Schema-/Evidence-Prüfung, Modell-/Promptversion, Replay und separate Semantik-Evaluation.
7. **Vergleich (später):** kompatible Bezugsgrössen/Gültigkeitsstände, Quellenansicht,
   fachlicher Review vor Produktivfreigabe. Noch keine Weboberfläche.

Empfehlung nach Sprint 3 (Parservergleich in Sprint 4 umgesetzt): am unveränderten
Goldstandard, insbesondere Spalten-/Tabellenreihenfolge und Header/Wert-Zuordnung.
Struktur-Precision und robuste ID-Zuordnung ergänzen. Isolierten Worker für harte
CPU-/RAM-/Zeitlimits spezifizieren; Quellenaufnahme bleibt hinter dem Gate.
Die Parserbaseline bleibt erhalten; Sprint 5 nutzt sie für ein abgegrenztes synthetisches
LLM-Experiment ohne Agentenorchestrierung.

Offen bleiben Lizenz, Ontologieverantwortung, Review-/Freigabeschwellen, Nutzungsregeln,
Mehrsprachigkeit und fachliche Dokumentpriorität bei Konflikten. Technische Versionen
sind implementiert, fachliche Gültigkeit und Echtheit sind damit nicht bewiesen.

## Sprint 4 und nächste Iteration

Zwei austauschbare Parser, optionale Layoutrepräsentation, Schema-2-Provenienz und
gepaarter Benchmark am unveränderten Korpus sind implementiert. PyMuPDF bleibt
experimentell und lizenzseitig ungeklärt für proprietäre SaaS. Die Standardbaseline
bleibt pypdf; Vorteile und Regressionen werden je Fall ausgewiesen.

Weiterhin offene Parserarbeit: Sortier-Ablation und spaltenbewusste Ordnung, mehr
unabhängige Strukturannotation (insbesondere zusätzliche/falsche Zellen und
Header-/Wert-Zuordnung), weitere Fonts/Rotationen sowie isolierter Worker.
Echte AVB benötigen zusätzlich kontrollierte Aufnahme, Lizenz-/Nutzungsfreigaben
und fachlichen Review. Die versionierte Schnittstelle erlaubt spätere LLM-Experimente,
ist aber noch keine verlässliche fachliche Extraktions- oder Produktionsfreigabe.

## Sprint 5 und nächste Iteration

Einzelner strukturierter Extraktor, optionaler unabhängiger Verifier-Aufruf, Mock,
kontrollierter OpenAI-Adapter, Quellspannenauflösung und Replay sind implementiert.
120 Semantikfälle bilden eine technische Foundation; die Templateverwandtschaft und
fehlende fachliche Zweitannotation begrenzen ihre Aussagekraft. Live-LLM-Qualität,
Kosten/Nutzen des Verifiers und menschlicher Reviewaufwand sind noch ungemessen.

Priorität: unabhängige synthetische DE/FR/IT-Annotation mit neuen Klauselfamilien,
Konflikt-/Sublimitregeln und Tabellen; festgeschriebener Holdout. Danach ein budgetierter
Live-Pilot mit Fehleranalyse, echten Token-/Kostenmessungen und Vergleich des Verifier-
Nutzens gegen zusätzlichen Reviewaufwand. Keine automatische Produktausgabe.
Quellenaufnahme, Worker-Isolation, Lizenzklärung und fachliche Freigabe vor echten AVB
bleiben offen. Keine UI oder zusätzlichen Agenten im aktuellen Sprint.

## Sprint 6 und nächste Iteration

Implementiert: zusätzlicher DE/FR/IT-Korpus, gepaarte A/B/C-Pipeline, gemeinsames
Budgetjournal, fünf Reviewentscheidungen, Familienbootstrap und unabhängiges Replay
von Rohantworten. Alle 120 Fälle zunächst nur offline; kostenpflichtiger Pilot auf
24 Fälle und 2 USD begrenzt. Kein behaupteter Live-Nutzen ohne echte Beobachtungen.

Priorität: Pilot mit Secret ausführen, korrekte und falsche Gateentscheidungen blind
fachlich reviewen, Annotation korrigieren und als neue Version einfrieren. Danach
Reviewzeit und praktische Wirkung gegen Zusatzkosten messen. Erst darauf gestützt über
grösseren bezahlten Korpus oder anderes Verifiermodell entscheiden. Harte Workerlimits,
Quellenaufnahme und Freigabe echter Dokumente bleiben separate offene Gates. Keine UI.
