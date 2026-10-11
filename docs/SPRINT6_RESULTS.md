# Sprint 6 – Ergebnisbericht

## Stand: 24-Fälle-Pilot abgeschlossen

Am **11. Oktober 2026** wurden alle **24 synthetischen Pilotfälle** verarbeitet:
DE/FR/IT je acht, zwölf Dev und zwölf Holdout, zwölf Szenarien. **64 erfolgreiche
API-Antworten**, keine HTTP-Fehler oder Retries. Vier Extraktionsantworten verletzten
fachliche Schemainvarianten; ihre acht anschliessenden Reviews wurden ausgelassen.
complete=true bedeutet vollständige Abarbeitung, nicht 24 korrekte Ergebnisse.

Modell in allen Rollen: `gpt-4.1-mini-2025-04-14`, temperature=0. Code, Prompts und Gold
blieben unverändert. Run `run-b393e410c84941d58ce07be289e679e0`, Commit
`fb9ba677373a039fe1a1a16c4dc61c5afc04b41e`, git_dirty=false. Der Offline-Replay
rekonstruierte die Ergebnisse erfolgreich, Fingerprint:
`92f559870c3846c25265c46e7d88b587dbc9e6044354dd6a40268be7721a9b0f`.

[Live-Snapshot mit Manifest, allen Strata, Fallprüfungen und Intervallen](benchmarks/sprint6-live-pilot-24-summary.json).
Original-PDFs, Rohantworten und CAS-Stores liegen lokal unter
`datasets/evaluation-real/live-pilot-24-20261011/` und sind von Git ausgeschlossen.
Der Snapshot allein ersetzt diese Stores nicht und ermöglicht keinen eigenständigen Replay.
Frühere, wegen Guthaben abgebrochene Läufe bleiben separat erhalten:
[Historischer Stand vom 10. Oktober](benchmarks/sprint6-live-attempt-summary.json).
Ihre Antworten fliessen nicht in die Qualitätsmetriken des neuen Pilots ein.

Basis bleibt der offene PR #4, codex/structured-insurance-extraction,
4d4adabf1b06e55b375c5bf54bf0c8d5d06f4659. Featurebranch:
codex/real-llm-evaluation. main und PR #1 bis #4 wurden nicht gemergt.

## Beobachtete Ergebnisse

A: Extraktion plus deterministische Quellenprüfung. B: zusätzlich Verifier.
C: zusätzlich kritisch instruierter Review; kumulativ müssen beide Reviewgates bestehen.
Die Reviews ändern die A-Behauptung nicht. Werte gelten gegen den eingefrorenen,
bisher nicht unabhängig fachlich geprüften synthetischen Goldstandard.

| Messwert | A | B | C |
| --- | ---: | ---: | ---: |
| Freigegebene Kandidaten einschliesslich unknown | 19/24 | 16/24 | 15/24 |
| Korrekte freigegebene Deckungsbehauptungen / alle freigegebenen Deckungsbehauptungen | 13/17 (76.5%) | 13/16 (81.3%) | 13/15 (86.7%) |
| Claim-Recall: korrekte Behauptungen / 21 im Gold bekannte Deckungsstatus | 13/21 | 13/21 | 13/21 |
| Freigegebener korrekter Deckungsstatus / alle Fälle | 18/24 | 16/24 | 15/24 |
| Kritische Fehler: fehlerhafte freigegebene Behauptungen / alle Fälle | 4/24 | 3/24 | 2/24 |
| Freigegebene korrekte unknown / drei Gold-unknown | 2/3 | 0/3 | 0/3 |
| Geschätzte kumulative API-Kosten (USD) | 0.021608 | 0.041155 | 0.060195 |
| Kumulative API-Zeit (Sekunden) | 63.814 | 125.315 | 179.471 |

Claim-Precision schliesst unknown aus; sie ist keine Erfolgsquote über alle 24 Fälle.
A/B/C teilen dieselbe Extraktion: Kosten nicht addieren. Gates erhöhen hier die
Precision durch Zurückhalten, nicht durch Korrektur. Der zusätzliche Rückgang von
B auf C beruht auf einer formalen Reviewverletzung, nicht auf erkanntem Semantikfehler.

## Fehleranalyse und Vertrauensgrenzen

- **Vier Schemafehler:** `document-de-0-10` kombiniert unknown mit einem Betrag;
  `document-de-1-02`, `document-fr-1-03` und `document-it-0-02` nennen CHF ohne
  vollständige Betrags-/Bezugsgrössenangabe. Rohantworten bleiben gespeichert;
  Structured Outputs allein garantiert die Pydantic-Fachinvarianten nicht.
- **Ein semantisch erkannter Fehler:** Bei `document-fr-1-09` nennt A trotz
  gleichrangiger widersprüchlicher Klauseln covered. B erkennt den Widerspruch und
  lehnt ab. C urteilt fälschlich supported; das kumulative B-Gate verhindert Freigabe.
- **Formales Zurückhalten statt semantischer Erkennung:** Bei `document-fr-0-01`
  erfindet A den Ausschlussatom unattended_items. B und C sagen beide supported.
  C wird nur wegen incomplete_checks blockiert. Dies ist kein Nachweis, dass der
  Kritiker die erfundene Einschränkung verstanden hat.
- **Zwei Fehler bleiben bis C freigegeben:** `document-it-1-10` ordnet CHF 9000 pro
  Jahr aus der Tabellenzeile Prestazione accessoria fälschlich dem Gepäck zu; korrekt
  wären CHF 2125 pro Ereignis. Beide Reviews bestätigen den Fehler. Bei
  `document-it-1-15` fehlt der kanonische Bedingungsatom emergency; beide Reviews
  akzeptieren medical_certificate plus non_emergency als Ausschluss. Die formale
  Goldabweichung ist eindeutig; fachliche semantische Äquivalenz separat prüfen.
- **Zwei korrekte unknown werden zurückgehalten:** `document-de-1-08` und
  `document-it-0-08`. Die Reviewer antworten insufficient_evidence, obwohl der
  unknown-Kandidat die Quellenlage korrekt wiedergibt. Das supported-only-Gate
  behandelt dies als Ablehnung. Unknown bleibt unbekannt und wird nie excluded.
- **Ein deterministischer Prüfungsfehler:** `document-it-1-00` ist inhaltlich korrekt,
  wird aber bereits von A mit amount_not_literal zurückgehalten. Die Zahlenregex
  verwirft `1875.` vor einem Satzpunkt. Beide Reviews sagen supported. Der Fehler
  bleibt im eingefrorenen Ergebnis sichtbar; keine nachträgliche Scorekorrektur.
  Die derzeitige Metrik baseline_error enthält diesen Quellenprüfungsfehler und darf
  daher nicht durchgehend als Fehler des Extraktionsmodells interpretiert werden.

Keine erfundenen Fundstellen unter 20 validen Kandidaten gemessen; das schliesst
falsch interpretierte, exakt zitierte Tabellen oder Bedingungen nicht aus.

## Kosten und Budget

Dieser Lauf: 83'119 Input- und 16'827 Output-Token, Usage-Abdeckung 64/64.
Geschätzte Kosten **0.060195 USD**, je Aufruf auf Mikro-USD aufgerundet, ohne
Cacherabatt; kein bestätigter Rechnungsbetrag. Die Preisannahmen 0.40 USD/M Input und
1.60 USD/M Output wurden am 11. Oktober anhand der
[offiziellen Modellseite](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
erneut geprüft. Das eingefrorene Konfigurationsschema behält sein ursprüngliches
pricing_checked_on=2026-10-09; die erneute Prüfung steht separat im Snapshot.

Der Run hatte max_retries=0, max_calls=72 und ein Kostenlimit von 1.9104 USD nach
Abzug früherer Reservierungen. Geplante konservative Obergrenze: 0.8064 USD.
Tatsächlich reserviert: 0.7168 USD für 64 Aufrufe. Mit früheren 0.0896 USD sind
**0.8064 USD von 2 USD reserviert**, verbleibend **1.1936 USD**. Bekannte geschätzte
Kosten aller Läufe: 0.063700 USD; Usage der vier früher fehlgeschlagenen Versuche
fehlt, weshalb tatsächliche Gesamtkosten unbekannt bleiben. Reservierung ist keine
Abrechnung. Insgesamt 72 API-Versuche und 68 Antworten über alle Läufe.

## Antworten auf die Forschungsfragen

1. **Architektur:** additive experiments-Pipeline mit blindem PDF-Kontext, strikten
   semantic-2/travel-2-Schemas, CAS, Budgetjournal und Quellen-/Reviewgates.
2. **Fälle:** 120 eingefrorene synthetische Fälle; ausschliesslich der vorab festgelegte
   24-Fälle-Pilot wurde vollständig live ausgeführt. Keine unabhängige Fachannotation.
3. **Echte Aufrufe:** 64 im vollständigen Pilot, 24 Extraktionen und je 20 Reviews;
   vier fachlich ungültige Extraktionsantworten. Frühere Versuche separat dokumentiert.
4. **A/B/C:** identische gespeicherte A-Antwort, gleicher Originalkontext, verschiedene
   Reviewprompts. C sieht B nicht. Gleiches Modell bedeutet korrelierte Fehler.
5. **Erkannte Fehler:** B erkennt einen Widerspruch; C blockiert zusätzlich einen
   fehlerhaften Claim wegen unvollständiger Checks, nicht wegen fachlicher Einsicht.
6. **Übersehene Fehler:** italienische Tabellenzuordnung und fehlender Bedingungsatom
   passieren alle Gates. Quellenintegrität beweist keine semantische Richtigkeit.
7. **Falsch zurückgehalten:** B/C jeweils zwei von 15 laut Metrik korrekten,
   quellengestützten Kandidaten (beide unknown). Zusätzlich blockiert ein Regexfehler
   einen korrekten Betrag bereits in A, ausserhalb dieses Nenners.
8. **Kosten/Latenz:** oben gemessen; C kostet kumulativ rund 2.79-mal so viel wie A.
   API-Zeiten schliessen PDF-Vorbereitung aus. Menschliche Reviewzeit nicht gemessen.
9. **Statistik:** explorative Familienbootstrap-Intervalle der kritischen Fehlerrate:
   B-A -4.17 Prozentpunkte, 95%-Intervall [-12.5; 0]; C-A -8.33 Punkte,
   [-20.83; 0]. Beide enthalten null. Kleine Stichprobe, ein Modell, ein Goldautor:
   kein statistisch belastbarer Wirksamkeits- oder Produktionsnachweis.
10. **Nächster Nutzen:** zuerst deterministische Zahlenprüfung, unknown-Reviewsemantik
    und nullable Geldfelder mit Regressionen prüfen; Tabellenzuordnung und fehlende
    Bedingungsatome gezielt evaluieren. Kritische Fälle unabhängig fachlich annotieren,
    danach eine versionierte Vergleichsiteration planen. Holdoutbeobachtungen sind
    nun bekannt; für spätere Optimierung frischen unabhängigen Holdout reservieren.

## Offline-Nachweise

120/120 Fälle erfolgreich abgearbeitet, 360 gespeicherte simulierte Calls.
Offline-Replay rekonstruierte den vollständigen Bericht einschliesslich Quellen,
Rohantworten, Budgetkette und erneut berechneter Gates.

Qualitätsfingerprint des Protokolltests:
`e97f58730476048653c21c67e743ac6de81fb6bb31e513ed815e62a0d3526309`.
Dies ist ein Reproduzierbarkeitsfingerprint, keine Modellqualitätszahl.
[JSON-Snapshot](benchmarks/sprint6-offline-summary.json) enthält alle Strata,
Zähler/Nenner und explorativen Fixtureintervalle; live_quality=null.
Vollständige Quellen/Antworten/Fallberichte werden von der CI als Artefakt veröffentlicht
und lassen sich mit den dokumentierten CLI-Befehlen neu erstellen.

Unveränderte lokale Windows-Referenzen:
- Sprint 3: `f6a854948483cccde0c42e237e9963c3ad9843100b172bbd218dd3205f3e932d`
- Sprint 5: `5ed116194207ccb6105c831ce1e383066bfdd09d28570b2189a6da2817d7789f`

Sprint-3-/4-Generatorbytes können wie bisher plattformabhängig sein. Der neue Freeze
erzwingt LF-Dateibytes auch unter Windows, damit Checkout-Zeilenenden keinen Hash ändern.

## Qualitätsprüfungen

- Aktueller lokaler Lauf `uv run --extra llm-openai pytest`: **320 bestanden,
  33 erwartete PyMuPDF-Skips**. Frühere Gesamtsuite mit beiden Extras: 353 bestanden.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run axiory-demo`: erfolgreich.
- Offline-Replay des vollständigen Live-Pilots: erfolgreich; Fingerprint unverändert.
- Kein Code, kein Prompt und kein Gold nach Beobachtung der Ergebnisse geändert.
- Kein bezahlter 120-Fälle-Lauf. SDK-/Standardtests bleiben offline.

## Geänderte Bereiche und offene Entscheidungen

- src/axiory/experiments: Schemas, Korpus/Renderer, Prompts, Quellen-/Reviewgates,
  Budgetjournal, feste Pipeline, Metriken/Bootstrap, CLI/Runner, Replay und Bericht.
- src/axiory/extraction/providers.py: additive RequestV2-Temperatur-/Tieroptionen;
  Legacy-Schemas und Hashsemantik unverändert.
- datasets/multilingual und scripts/build_multilingual_gold.py: Korpus, Freeze,
  Pilotkonfiguration und Autorentool; keine echten PDFs in Git.
- tests/test_experiments.py, tests/conftest.py, tests/test_openai_adapter.py:
  Regressionen, Angriffs-/Budget-/Replayfälle, SDK-Vertrag, Netzwerksperre.
- pyproject.toml, .gitattributes, CI: neuer CLI-Einstieg, stabile Freeze-Bytes,
  Offline-Benchmark und Netzwerkisolation. uv.lock unverändert: keine neue Abhängigkeit.
- README, Architektur, Evaluation, Roadmap, Benchmarkbericht, Verifikationsstrategie
  und ADR 0006: Datenmodell, Preisannahmen, Metriken, Grenzen und nächster Schritt.

Offen: unabhängige Fachannotation, Fehlerbehebung aus dem Pilot, akzeptable Freigabeschwellen,
Ontologieverantwortung, Modellvielfalt und gemessener menschlicher Reviewaufwand.
Hashintegrität ist keine digitale Authentizität. Kein automatisches Crash-Resume oder
kontoweites Budget über fremde Prozesse; harte Workerlimits fehlen weiterhin.
Keine Freigabe für echte AVB, Produktion oder eine Weboberfläche.
