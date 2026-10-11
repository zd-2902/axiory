# Sprint-3-Baseline

sprint3-baseline.json und sprint3-baseline.md sind unveränderte Exporte eines sauberen
Checkouts des Implementierungscommits ce19b77. Dieser spätere Dokumentationscommit
fügt nur den Bericht und diese Einordnung hinzu. Der Datensatz ist rein synthetisch.

24 Fälle, 29 Seiten, zwei frische Wiederholungen je Fall; Windows/Python 3.12.14,
pypdf 6.19.0. Alle 168 Tests (111 bestehende + 57 neue) sowie Lint, Format und Demo
bestanden lokal. Alle 29 gerenderten PDF-Seiten wurden visuell kontrolliert.

Die angegebenen run-*-Stores liegen lokal unter datasets/evaluation; sie werden
nicht mit eingecheckt. Die CI erzeugt eigene Reports samt Stores als 14 Tage
aufbewahrtes Artefakt. Originale lassen sich aus dem versionierten Korpus neu erzeugen.

## Gemessene Ergebnisse

- CER 332/3503 = 9,48 %; WER 54/521 = 10,36 %.
- Zeichen-Vollständigkeit 2852/3005 = 94,91 %; Nicht-ASCII-Retention 37/37.
- Ankerreihenfolge 270/282 = 95,74 % bei Ankerabdeckung 105/111.
- Goldgestützte Fundstellen: 84/84 gültige Spannen und richtige Seiten;
  6/90 Sollzitate fehlen oder sind mehrdeutig.
- Extraktionsartefakte stimmen in 24/24 Wiederholungsvergleichen überein.
- 6/48 Läufe liefern keinen success/partial-Textstatus (3 erwartete Problemfälle);
  2/48 sind partial. Die leere Seite weicht vom Sollstatus empty ab (not_extractable).
- Klauselgrenzen sowie Tabellenzellen und Header/Wert-Verknüpfungen: unsupported.

Einfache digitale Texte, DE/FR/IT, kleine/grosse Schriften, Negationen, Fussnoten
und seitenübergreifende Texte haben in diesen Fällen CER=0. Das ist keine Aussage
über fachlich korrekt erkannte Klauseln oder reale AVB.

Probleme entstehen bei verschachtelter Paint-Reihenfolge in Spalten/Tabellen,
Kopf-/Fusszeilen sowie verlorenem Bild-/Vektortext. Dieselben sichtbaren Tabellen
können bei anderer Paint-Reihenfolge schlechteren Text liefern. Die Sollwerte wurden
nach diesen Beobachtungen nicht angepasst.

## Nächster Schritt und Risiken

Höchster erwarteter Lernnutzen: zweiter koordinatenbewusster Parser am eingefrorenen
Korpus, ergänzt um Struktur-Precision und ID-Zuordnung. Das ist eine Empfehlung,
kein bereits gemessener Vorteil eines anderen Parsers. Es fehlen repräsentative
Font-/Layoutvielfalt, autonome Evidence-Extraktion, Fachprüfung und harte Ressourcen-
grenzen eines isolierten Workers. Noch keine LLM-, OCR- oder UI-Erweiterung.

Definitionen und Nenner: [EVALUATION](../EVALUATION.md).

```sh
uv run axiory-eval --output datasets/evaluation-next --compare docs/benchmarks/sprint3-baseline.json
```

Andere Generatorbytes oder Konfigurationen führen zu nicht vergleichbaren Läufen;
Laufzeiten werden nicht automatisch zwischen Maschinen verglichen.

Sprint 6: `sprint6-offline-summary.json` records an OFFLINE_PROTOCOL_TEST of 120 DE/FR/IT cases. `live_quality` is null. All ratios and intervals are fixture statistics, not measured model quality. See ../REAL_LLM_BENCHMARK.md and ../SPRINT6_RESULTS.md.

`sprint6-live-attempt-summary.json` records eight API attempts across two pilot runs and a diagnosis: four model outputs, two DE/dev cases, only one complete A/B/C case, then credit_balance_exhausted. It includes partial observations, replay fingerprints and known usage/cost coverage; no general model-quality conclusion is justified. Raw CAS stores remain local and ignored.

`sprint6-live-pilot-24-summary.json` records the completed 11 October pilot: 24 cases, 64 model outputs, four extraction schema failures, verified replay and cumulative budget accounting. It includes all strata and case audits. See the current Sprint-6 report for model errors versus deterministic gate defects; earlier partial outputs are excluded from its quality metrics.
