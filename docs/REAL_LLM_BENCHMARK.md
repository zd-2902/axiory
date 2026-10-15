# Real LLM Benchmark – Sprint 6

## Ergebnisstatus

Implementiert: gepaarte A/B/C-Pipeline, eingefrorener DE/FR/IT-Korpus, explizite
Freigabegates, gemeinsames Budgetjournal, Offline-Replay, Metriken und Familienbootstrap.
**Keine empirische Modellleistung aus Offline-Protokolltests ableiten.** `live_quality`
ist dort null; `fixture_metrics` testet nur die Auswertung. Der Offline-Provider liest
keine Goldlabels und antwortet absichtlich unknown/requires_human_review.

Der aktuelle Live-Pilot ist auf **24 Fälle und höchstens 2 USD** begrenzt. Alle 120 Fälle
kostenpflichtig auszuführen ist weder freigegeben noch über diese CLI möglich.
Am 11. Oktober 2026 wurde der Pilot vollständig ausgeführt: 24 Fälle, 64 Antworten,
vier fachlich ungültige Extraktionsantworten, keine HTTP-Fehler. Geschätzte Kosten
0.060195 USD; kumulativ mit früheren Läufen 0.8064 USD vorsorglich reserviert.
A/B/C-Claim-Precision: 13/17, 13/16, 13/15. Diese selektiven Quoten sind keine
Gesamterfolgsquote. Verifier-/Gatefehler und Grenzen stehen im
[Sprint-6-Bericht](SPRINT6_RESULTS.md), vollständige Strata im
[Live-Snapshot](benchmarks/sprint6-live-pilot-24-summary.json).
Weitere bezahlte Läufe erfordern eine bewusste Entscheidung; ein neuer Output-Pfad
setzt die nutzerseitige 2-USD-Gesamtfreigabe nicht zurück.

## Korrekturversion nach dem Pilot

Ab 15. Oktober ist `pilot-config-v2.json` der CLI-Standard: atomare Geldfelder,
explizites supported_unknown, korrigierte Zahlenprüfung und Prompts v2. Die ursprüngliche
Version bleibt über `--config datasets/multilingual/pilot-config.json` verfügbar.
[ADR 0007](adr/0007-versioned-pilot-fixes.md) beschreibt die Kompatibilitätsgrenzen.
Der diagnostische v2-Lauf ist abgeschlossen: [Vergleich und offene Fehler](PILOT_FIXES_RESULTS.md).
Das verbleibende konservative Gesamtbudget beträgt 0.3872 USD, kein neuer 2-USD-Topf.

Die rein deterministische [Quellennachprüfung](benchmarks/sprint6-source-reassessment-v2.json)
ändert genau einen von 20 gültigen Kandidaten: CHF 1875 vor Satzpunkt wird nun erkannt.
Vier ungültige Antworten bleiben ungültig; alte Reviewurteile und Live-Scores bleiben
unverändert. Reproduktion ohne Modellaufruf:

```sh
uv run python scripts/reassess_pilot_sources.py datasets/evaluation-real/live-pilot-24-20261011 --output datasets/evaluation-real/source-recheck-new.json
```

## Reproduzieren

```sh
uv sync --locked --dev
uv run axiory-real-eval --dry-run
uv run axiory-real-eval --all-offline --output datasets/evaluation-real/offline-120
uv run axiory-real-eval --replay datasets/evaluation-real/offline-120
```

Jeder Output-Pfad muss neu sein; keine stillschweigende Wiederaufnahme mit zurückgesetztem
Budget. Standard ohne Flags ist ein Offline-Protokolltest der 24 Pilotfälle. Alle
Läufe speichern Original-PDFs, Extraktionen und CAS-Artefakte im ignorierten
`datasets/evaluation-real/`. Ein Replay benötigt den passenden Code-/Parserstand und
unveränderten Freeze. Reports dürfen kopiert, lokale Stores nicht als echte Quellen
oder als signierte Messungen ausgegeben werden.

Nach Einrichtung von OPENAI_API_KEY über Secrets/Prozessumgebung, ohne Schlüssel in
CLI-Argumenten oder Dateien im Repository:

```sh
uv sync --locked --dev --extra llm-openai
uv run --extra llm-openai axiory-real-eval --dry-run
uv run --extra llm-openai axiory-real-eval --live --output datasets/evaluation-real/live-pilot-24
uv run axiory-real-eval --replay datasets/evaluation-real/live-pilot-24
```

Ein Live-Lauf erfordert --live und akzeptiert nur den eingefrorenen Pilot, den geprüften
Snapshot und dessen Preisannahmen. Die Python-API verlangt zusätzlich allow_live=True.
Kein automatischer Übergang vom Pilot auf 120 Fälle. Vor einem weiteren bezahlten Lauf
Pilotfehler, tatsächliche Kosten, Annotation und explizite Freigabe prüfen.

## Daten und Annotation

`datasets/multilingual/gold-v1.json`: 120 zusätzliche Fälle, 40 je Sprache DE/FR/IT,
60 Dev und 60 Holdout, 30 Dokumentfamilien mit je vier Fällen. Zwölf Szenarien:
Deckung, Ausschluss, Negation, Ausnahme, Bedingung, Sublimit, Selbstbehalt,
Bezugsgrösse, Mehrdeutigkeit, Widerspruch, Tabelle und seitenübergreifende Klausel.
Fünf bestehende Deckungscodes bleiben kompatibel. Atomare Bedingungen/Ausschlüsse
und Selbstbehalte ergänzen travel-2/semantic-2; Legacy travel-1 bleibt erhalten.

Dev/Holdout verwenden unterschiedliche Formulierungen/Anordnungen und disjunkte
Familien-, Produkt- und Template-IDs. Zahlen-normalisierte identische Volltexttemplates
über die Splitgrenze werden abgelehnt. Wiederholungen innerhalb eines Splits und
sprachübergreifende semantische Verwandtschaft bleiben bestehen: dies ist kein
repräsentativer Markt- oder Generalisierungsnachweis. Die 24 festgeschriebenen
Pilot-IDs umfassen acht Fälle je Sprache, zwölf je Split, alle zwölf Szenarien und
24 Familien. Einzelne Strata bleiben sehr klein.

**0 Annotationen wurden unabhängig fachlich überprüft.** Ein Autor erzeugte Quellen
und erwartete strukturierte Antworten; das ist keine Doppelannotation. Erwartungswerte
wurden vor dem Live-Pilot als JSON und SHA-256-Freeze gespeichert, nicht aus getesteten
Modellantworten abgeleitet. `scripts/build_multilingual_gold.py` ist das Autorentool.
Nach Live-Beginn Änderungen als neue Korpus-/Freezeversion erstellen, nie v1 ersetzen.
Der aktuelle einfrierende Commit wird zusätzlich im Run-Manifest erfasst.

Provider sehen ausschliesslich blind gerenderte PDF-Textkontexte, Zielcode und bei B/C
die gespeicherte A-Antwort. Goldwerte, Szenario, Schwierigkeit und Split verlassen die
Evaluationsschicht nicht. Tests können eigene Oracle-Antworten konstruieren; diese sind
keine Produktionsprovider und kein Qualitätsbenchmark.

## A/B/C und Modellannahmen

| Modus | Verarbeitung | Aufrufe ohne Retry pro Fall |
| --- | --- | --- |
| A | Extractor, striktes Schema, deterministische Quellenprüfung | 1 |
| B | exakt dieselbe A-Antwort plus Originalkontext an Verifier | 2 kumulativ |
| C | B-Gate plus zusätzliches kritisches Urteil zur selben A-Antwort | 3 kumulativ |

C sieht nicht das Urteil von B. Beide sehen auch den Originalkontext, nicht nur das
Zitat. Separate Aufrufe sind keine statistisch unabhängigen Modelle. Der erste Pilot
verwendet bewusst denselben expliziten Snapshot für alle Rollen. Es gibt keine
Agentenorchestrierung, keine Selbstverbesserungsschleife und keine automatische Korrektur.
Promptversionen: multilingual-extract-1, multilingual-verify-1,
multilingual-adversarial-1. Alle Requestbytes und JSON-Schemas werden mitgespeichert.

Pilotprofil: gpt-4.1-mini-2025-04-14, temperature=0, Responses API, striktes JSON-Schema,
service_tier=default, store=false. Temperatur kann bei nicht unterstützten Modellen
weggelassen werden; Null wird nicht als Temperaturwert gesendet. Das ist kein Anspruch,
dieses Modell sei das neueste oder beste. Modellantworten bleiben nichtdeterministisch.

Preisannahmen, am 9. Oktober 2026 anhand der
[offiziellen Modellseite](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
und [Preisliste](https://developers.openai.com/api/docs/pricing) geprüft: 0.40 USD pro
Million Inputtoken, 1.60 USD pro Million Outputtoken. Keine Cache-Rabatte eingerechnet.
Andere Live-Modelle/Preise benötigen eine neue geprüfte Pilotkonfiguration und Anpassung
der Zulassungsprüfung; unpassende Preis-/Snapshotkombinationen werden abgewiesen.

## Budget und Fehler

Pilot: 72 geplante Aufrufe, höchstens 144 Versuche bei einem Retry, 20 000 Input- und
2 000 Outputtoken pro Versuch, 3 168 000 reservierte Token insgesamt. Die konservative
Preisobergrenze beträgt **1.6128 USD**, unter dem genehmigten Limit von 2 USD.
Ein Kontext muss zusätzlich in die UTF-8-Bytegrenze einschliesslich Framingreserve
passen. Das ist eine konservative Zulassungsschätzung, kein exakter Tokenizer.
Maximal 45 Sekunden Transporttimeout pro Versuch, 1 800 Sekunden Gesamtzulassung.

Jeder Versuch wird **vor dem Versand** in einem append-only Hashjournal reserviert.
Retries teilen Kosten-, Token-, Aufruf- und Zeitbudget mit allen Fällen und Rollen.
Timeoutreservierungen werden nicht freigegeben; serverseitiger Verbrauch kann unbekannt
bleiben. Keine versteckten SDK-Retries. Unbekannte Usage/Kosten bleiben null plus
Messabdeckungsnenner; bekannte Teilkosten und reservierte Obergrenzen sind getrennt.
Preisänderungen, Providerabrechnung und fremde Verbraucher desselben Kontos sind keine
lokal garantierbare Rechnungsobergrenze; ein serverseitiges Kontolimit bleibt getrennt.

Fehlerklassen: Eingabe-/Outputbudget, Kostenbudget, Tokenbudget, Aufruf-/Zeitbudget,
Timeout/Verbindung/API-Status, Refusal, unvollständige Ausgabe, Antwortgrösse,
gemeldete Token-/Kostenüberschreitung und invalid_response. Rohantworten bleiben vor
Schemaauswertung erhalten. Ausgeschöpfte Transportfehler stoppen den Gesamtlauf.
Nicht angegangene Fälle bleiben im Nenner; keine stille Auswahl erfolgreicher Fälle.
`complete` bedeutet vollständig abgearbeiteter Versuchplan, nicht fachliche Korrektheit;
Fallfehler und zurückgehaltene Ergebnisse werden separat ausgewiesen.

Offline --all-offline erweitert nur simulierte Reservierungen auf 720 Versuche und
8.064 USD rechnerische Obergrenze. Es entstehen keine API-Kosten und diese Konfiguration
kann nicht für den Live-Pilot verwendet werden. Harte CPU-/RAM-/Zeitlimits benötigen
einen isolierten Worker. Ein Prozessabbruch kann ein offenes Journal hinterlassen:
Originale und bereits gespeicherte Rohantworten bleiben erhalten, automatisches Resume
ist verboten; unvollständige Runs ohne Abschlussmanifest sind forensisch zu prüfen.

## Metrikvertrag

Jede Ratio enthält numerator, denominator, case_count und value; value=null bei leerem
Nenner. Geldbeträge werden als Decimal verglichen, Sublimiten ungeordnet nach Inhalt.
Ein Fall verlangt genau einen konsolidierten Claim zum Zielcode und Produkt. Vollständig
korrekt bedeutet passender Status, alle Geldfelder, Bedingungen und Ausschlüsse.
Quellenunterstützung verlangt zusätzlich auflösbare Spannen und Goldanker. Zum Scoring
wird nur Whitespace normalisiert; die Provenienzauflösung bleibt exakt.

| Metrik | Zähler / Nenner |
| --- | --- |
| Claim Precision | vollständig korrekte, belegte freigegebene covered/excluded / freigegebene covered/excluded |
| Claim Recall | dieselben korrekten Aussagen / alle Gold-covered/excluded |
| Status Accuracy | freigegebene richtige Status / alle ausgewählten Fälle |
| Limit Accuracy | freigegebene vollständig richtige Geldfelder / Goldfälle mit Limit oder Sublimit |
| Deductible Accuracy | freigegebene vollständig richtige Geldfelder / Goldfälle mit Selbstbehalt |
| Evidence Support Accuracy | vollständige korrekte belegte Aussagen / alle freigegebenen Claims |
| Unknown Recall | freigegebene richtige unknown / alle Gold-unknown |
| False Exclusion Rate | falsche freigegebene excluded / alle Gold-nicht-excluded |
| Unsupported Claim Rate | falsche oder nicht belegte freigegebene covered/excluded / freigegebene covered/excluded |
| Critical Error Rate | dieselben fehlerhaften freigegebenen Aussagen / alle ausgewählten Fälle |
| Hallucinated Evidence Rate | A-Claims mit falscher Quelle/Seite, fehlendem, mehrdeutigem oder ausserhalb liegendem Zitat / alle schema-validen A-Claims |
| Verifier False Rejection Rate | vollständig korrekte belegte A-Claims, die das B/C-Gate zurückhält / alle vollständig korrekten belegten A-Claims |
| Verifier Missed Error Rate | fehlerhafte/nicht belegte A-Claims, die B/C freigibt / alle fehlerhaften/nicht belegten A-Claims |
| Withheld Claim Rate | zurückgehaltene schema-valide A-Claims / alle schema-validen A-Claims |

Die Verifier-Raten sind **End-to-End-Gateraten** inklusive Format-, Quellen- und
Transportfehlern, keine isolierten semantischen Urteilsraten. Fehlercodes pro Fall
und die Sensitivitätsanalyse vollständiger Fälle machen diese Grenze sichtbar.
Halluzinationsrate ist ein konservativer gemeinsamer A-Quellenfehlerindikator, kein
behaupteter psychologischer Zustand und kein nur freigegebene Claims zählender Wert.
Critical Error umfasst hier jede falsche bekannte Aussage; keine fachlich gewichtete
Schadenschwere. Unknown, fehlende Ausgabe und Zurückhalten sind unterschiedliche Dinge.
All-withhold senkt Risikoraten, verschlechtert aber Recall/Status und muss gemeinsam
bewertet werden. Kein zusammengesetzter Score kaschiert diesen Trade-off.

Bericht nach Sprache, Deckungscode, Szenario/Fehlertyp, Schwierigkeit und Split.
API-Latenz pro angegangenem Dokument enthält alle Versuche; PDF-Vorbereitung ist
separat nicht als LLM-Latenz behauptet. Token und geschätzte Kosten zeigen ihre
Messabdeckung. B/C enthalten A kumulativ; Armkosten nie addieren. Zusatzkosten/-latenz
für Verifikation sind gesondert. Menschliche Reviewzeit wurde nicht gemessen (null).

## Statistik und Aussagegrenzen

Gepaarte Differenzen B-A und C-A für kritische Fehler, richtigen Status und Withholding;
95%-Perzentilbootstrap mit 1 000 Replikaten und Seed 1729. Ganze Dokumentfamilien werden
mit Zurücklegen gezogen, innerhalb der Familien bleiben A/B/C gepaart. Getrennte
Auswertung für Dev/Holdout, zusätzlich vollständige Fälle ohne Laufzeit-/Schemafehler.
Weniger als zwei Familien: kein Intervall. Unter zehn Familien: small_sample=true.
Auch darüber sind Pilotintervalle explorativ; verwandte Templates, nur 24 Pilotfälle
und ungeprüftes Gold erlauben keine Signifikanz-/Populationsbehauptung. Die eigentliche
Verbesserung von A zu B/C und ihre Wirtschaftlichkeit sind erst nach realen Beobachtungen
und fachlicher Nachprüfung diskutierbar. Offlineintervalle sind reine Protokolltests.
