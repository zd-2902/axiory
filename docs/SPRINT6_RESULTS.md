# Sprint 6 – Ergebnisbericht

## Stand

Offline-Infrastruktur und Goldstandard implementiert. **Kein echter LLM-Aufruf**,
keine API-Kosten durch diesen Sprintlauf, keine empirische Modellqualitätsbehauptung.
Der Live-Start wurde wegen fehlendem OPENAI_API_KEY vor der Providererzeugung abgebrochen.
Die explizite Freigabe des Nutzers gilt für 24 synthetische Fälle bis maximal 2 USD;
der vollständige 120-Fälle-Korpus wurde nur offline ausgeführt.

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
3. **Echte Aufrufe:** null. Secret fehlte in Prozess-, Benutzer- und Systemumgebung.
   Budgetfreigabe allein ist kein API-Zugang. Kein Schlüssel wurde gespeichert/geloggt.
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
   Complete-case-Sensitivität implementiert, aber für reale Modelle noch ungemessen.
8. **Kosten/Latenz:** A/B/C verwenden im Protokolllauf kumulativ 120/240/360 Calls,
   insgesamt 360 unterschiedliche simulierte Calls. Das ist keine API-Latenzprognose.
   Tatsächliche Token-/Kostenwerte und menschliche Reviewzeit bleiben dort null.
   Live-Plan: 72 Calls, maximal 144 Versuche mit Retry, konservativ 1.6128 USD bei
   konfiguriertem 2-USD-Limit. Preis-/Snapshotdetails im Benchmarkdokument.
9. **Statistik:** gepaarte Familienbootstrap-Intervalle sind implementiert und mit
   bekannten Testkonstellationen geprüft. Offlineintervalle sind Protokollwerte;
   es gibt keine statistisch belastbare Aussage zur realen Verbesserung von B/C.
10. **Grösster nächster Nutzen:** Secret bereitstellen, einmaligen Pilot ausführen,
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
- Live-Pilot: nicht ausgeführt; fehlendes Secret, keine bezahlten Versuche.

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

Offen: unabhängige Fachannotation, reale Pilotbeobachtungen, akzeptable Freigabeschwellen,
Ontologieverantwortung, Modellvielfalt und gemessener menschlicher Reviewaufwand.
Hashintegrität ist keine digitale Authentizität. Kein automatisches Crash-Resume oder
kontoweites Budget über fremde Prozesse; harte Workerlimits fehlen weiterhin.
Keine Freigabe für echte AVB, Produktion oder eine Weboberfläche.
