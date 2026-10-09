# Sprint 6 – Ergebnisbericht

## Stand

Offline-Infrastruktur und Goldstandard implementiert. Am **10. Oktober 2026** wurde
nach Einrichtung des API-Schlüssels der genehmigte 24-Fälle-Pilot gestartet. Nach zwei
abgewiesenen Pilotversuchen und einer Diagnose wurde auf Nutzerwunsch erneut geprüft:
**vier Modellantworten**, danach erneut **HTTP 429, credit_balance_exhausted,
insufficient_quota**. Der zweite Lauf stoppte nach zwei von 24 Fällen. Insgesamt
acht API-Versuche; kein weiterer kostenpflichtiger Versuch läuft.

Beobachtet wurden ausschliesslich zwei deutsche Dev-Fälle:

- `document-de-0-00`: Annullierung, CHF 1200 pro Ereignis. A stimmt mit Gold überein;
  B und C melden supported, Quellenprüfung erfolgreich, alle drei Gates geben frei.
- `document-de-0-05`: Reisegepäck CHF 1325 pro Ereignis, Elektronik-Sublimite CHF 200
  pro Gegenstand. A stimmt mit Gold überein; B scheitert am API-Guthaben, C wird nicht
  aufgerufen. B/C halten daher operativ zurück; dies ist keine Modellablehnung.

Nur **ein vollständig gepaarter A/B/C-Fall**; keine FR-/IT-/Holdout-Antworten und keine
belastbare Aussage zur Verifierwirkung. Die geplanten 24 Fälle sind nicht abgeschlossen.
Der kostenpflichtige 120-Fälle-Lauf wurde nicht gestartet.

Erfasst: 5081 Input- und 919 Output-Token für vier Antworten. Bei den dokumentierten
Preisen ergibt dies aufgerundet je Aufruf **0.003505 USD geschätzte bekannte Kosten**.
Für vier fehlgeschlagene Versuche fehlen Usage-Werte; Gesamtkosten/Rechnungsbetrag
bleiben unbekannt. Vorsorglich bleiben **0.0896 USD** reserviert, sodass **1.9104 USD**
des genehmigten 2-USD-Budgets für weitere Zulassung verbleiben. Reservierung ist keine
Abrechnung. Der erneute Lauf verwendete max_retries=0 und berücksichtigte frühere
Reservierungen. Kein automatischer weiterer Versuch bei fehlendem Guthaben.

Beide Pilot-Stores und die Diagnose bleiben lokal unter `datasets/evaluation-real/`
erhalten und von Git ausgeschlossen. Offline-Replay beider Pilotläufe ist erfolgreich.
Der erneute Lauf protokolliert git_dirty=true wegen laufender Berichtsedits; Code,
Prompts und Gold blieben unverändert. Der
[sanitisierte Versuchsbericht](benchmarks/sprint6-live-attempt-summary.json) enthält
Run-IDs, Konfigurationen, Fingerprints, beobachtete Fälle und Kostenabdeckung. Er allein
ersetzt die lokalen CAS-Stores nicht und erlaubt keine unabhängige Live-Reproduktion.

Basis: offener, getesteter PR #4, codex/structured-insurance-extraction,
4d4adabf1b06e55b375c5bf54bf0c8d5d06f4659. Featurebranch:
codex/real-llm-evaluation. main und PR #1 bis #4 wurden nicht gemergt.

## Antworten auf die Forschungsfragen

1. **Architektur:** additive experiments-Pipeline mit blindem PDF-Kontext, strikten
   semantic-2/travel-2-Schemas, CAS, gemeinsamem Budgetjournal und Quellen-/Reviewgates.
   Keine neuen Laufzeitabhängigkeiten oder Agentenframeworks.
2. **Fälle:** 120 neue synthetische Fälle, DE/FR/IT je 40, zwölf Szenarien, fünf Codes,
   60 Dev/60 Holdout und disjunkte Familien/Templates. Pilot: 24 vorab festgelegte Fälle,
   acht je Sprache, zwölf je Split, alle Szenarien. Keine unabhängige Fachannotation.
3. **Echte Aufrufe:** acht API-Versuche, vier Antworten, zwei deutsche Dev-Fälle;
   nur ein Fall vollständig A/B/C. Secret funktioniert, API meldet erneut fehlendes
   Guthaben. Kein Schlüssel wurde im Repository oder in Logs gespeichert.
4. **A/B/C:** A extrahiert einmal; B prüft exakt dieselbe gespeicherte A-Antwort;
   C ergänzt einen kritisch instruierten Aufruf und kombiniert beide Gates. Alle
   nutzen Originalkontext; C sieht Bs Urteil nicht. Ein Modell in drei Rollen
   liefert keine statistisch unabhängigen Fehler.
5. **Erkannte Verifierfehler:** technisch prüfbar sind ungültige Quellen/Checks sowie
   fünf explizite Reviewentscheidungen. Welche semantischen Fehler ein echtes Modell
   erkennt, ist noch nicht gemessen. Test-Oracles sind kein Wirksamkeitsnachweis.
6. **Übersehene Fehler:** noch nicht empirisch bekannt. Insbesondere exakt zitierte,
   falsch interpretierte Ausnahmen, Tabellenbeträge und Bezugsgrössen bleiben möglich.
7. **Falsch zurückgehaltene Claims:** als End-to-End-Gaterate samt Zähler/Nenner und
   Complete-case-Sensitivität implementiert, bei den zwei beobachteten Fällen nur transportbedingt aufgetreten.
   Daraus folgt keine Aussage über die semantische Fehlerrate eines Verifiers.
8. **Kosten/Latenz:** A/B/C verwenden im Protokolllauf kumulativ 120/240/360 Calls,
   insgesamt 360 unterschiedliche simulierte Calls. Das ist keine API-Latenzprognose.
   Tatsächliche Token-/Kostenwerte und menschliche Reviewzeit bleiben dort null.
   Standard-Live-Plan: 72 Calls, maximal 144 Versuche mit Retry, konservativ 1.6128 USD.
   Der erneute Lauf deaktivierte Retries (max_calls=72) und senkte das Run-Budget um
   frühere Reservierungen. Fünf Versuche dauerten zusammen rund 21.986 Sekunden API-Zeit;
   bekannte Kosten und Messlücken siehe oben. Preis-/Snapshotdetails im Benchmarkdokument.
9. **Statistik:** gepaarte Familienbootstrap-Intervalle sind implementiert und mit
   bekannten Testkonstellationen geprüft. Offlineintervalle sind Protokollwerte;
   es gibt keine statistisch belastbare Aussage zur realen Verbesserung von B/C.
10. **Grösster nächster Nutzen:** API-Guthaben klären, begrenzten Pilot abschliessen,
    falsch freigegebene und falsch abgelehnte Fälle blind fachlich prüfen und Gold
    unabhängig validieren. Danach Reviewzeit, praktische Fehlerrisiken und Mehrkosten
    abwägen, bevor ein grösserer bezahlter Lauf oder weiteres Modell gewählt wird.

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

- uv sync --locked --dev: erfolgreich.
- Vollständige Suite mit OpenAI- und PyMuPDF-Extras: **353 Tests bestanden**.
  Darunter 39 neue Sprint-6-Tests und sieben SDK-Vertragstests. Standardinstallation
  und isolierte CI prüfen dieselben Regressionen; 40 Tests benötigen optionale Extras.
- Ruff Lint, Formatcheck und git diff --check: erfolgreich.
- axiory-demo, axiory-eval, axiory-semantic-eval: erfolgreich.
- axiory-real-eval --dry-run: 24 Fälle innerhalb des 2-USD-Limits.
- Vollkorpus offline und Replay: erfolgreich.
- Aktueller lokaler Lauf mit OpenAI-Extra: **320 bestanden, 33 PyMuPDF-Skips**.
- Live-Pilot unvollständig: vier Antworten, dann Guthabenfehler. Nur ein vollständiger
  A/B/C-Fall; keine belastbare Aussage über Modell- oder Verifierqualität.
- Offline-Replay beider abgebrochener Pilotläufe: erfolgreich. Technische Scores
  unerledigter Fälle sind keine Messung der Modellgenauigkeit.

SDK-Vertragstests verwenden nur In-Memory-HTTP. Standard-CI isoliert Runtime-Netzwerk
über Linux-Netzwerknamespace; pytest blockiert zusätzlich Socketverbindungen. Setup
und Artefaktupload benötigen weiterhin Netzwerkzugang ausserhalb dieser Runtime.

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

Offen: unabhängige Fachannotation, vollständiger Pilot, akzeptable Freigabeschwellen,
Ontologieverantwortung, Modellvielfalt und gemessener menschlicher Reviewaufwand.
Hashintegrität ist keine digitale Authentizität. Kein automatisches Crash-Resume oder
kontoweites Budget über fremde Prozesse; harte Workerlimits fehlen weiterhin.
Keine Freigabe für echte AVB, Produktion oder eine Weboberfläche.
