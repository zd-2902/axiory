# Strukturierte Extraktion (Sprint 5)

Die Pipeline verarbeitet ausschliesslich deklarierte synthetische Dokumente. Sie
liefert analytische Claims, keine rechtliche Deckungsentscheidung. `source_matched`
ist ein technischer Quellenabgleich, keine fachliche Freigabe.

## Datenfluss und Vertrauensgrenzen

PDF → LayoutStore → verifizierter Reload → Context Builder → Provider → gespeicherte
Rohantwort → Pydantic → Evidence Resolver → konservative Prüfungen → optionaler
Verifier → unveränderliches Ergebnis → separate semantische Evaluation.

- Ingestion-/Parser-Schemas 1/2, pdf-1 und die Legacy-Demo bleiben unverändert.
- Neue Verträge: context-1, semantic-1, semantic-run-1, llm-call-1 und travel-1.
- travel-1 umfasst cancellation, interruption, baggage, medical_assistance und
  rental_car_deductible. CHF-Limiten verwenden dezimale Strings, intern Decimal.
  Amount, currency und basis sind gemeinsam vorhanden oder gemeinsam unbekannt.
  Sublimiten haben eigenes Subjekt, Betrag, Währung und Bezugsgrösse.
- covered/excluded/unknown bleiben drei Statuswerte. Bedingte Deckung ist covered
  mit conditions; kein vierter Status, der Bedingungen und Deckung vermischt.
- Bedingungen/Ausschlüsse sind noch freie Texte. Leere Listen bedeuten nur, dass
  keine entsprechenden Angaben extrahiert wurden, nicht deren fachliche Abwesenheit.
- DTOs erlauben keine vom Modell gesetzten Verifikationsflags. Externe JSON-Daten
  werden mit model_validate_json und extra=forbid validiert.

Context Builder: reproduziert zuerst das Layoutartefakt aus Originalbytes. Er übernimmt
Absätze inklusive Leerzeichen und Unicode-Offsets in Seitenreihenfolge, ohne Header
zu löschen. Passt ein Absatz nicht vollständig in max_chars, endet das Präfix dort;
truncated/omitted_chars dokumentieren den Rest. Ein übergrosser erster Absatz kann
leeren Kontext ergeben. Kein stilles Kürzen, Ergänzen oder automatisches Verfolgen
externer Verweise. Seitenübergreifende Einschränkungen bleiben bei ausreichendem
Budget enthalten. Die Schnittstelle bewahrt Parserkonfiguration/-version und
Dokument-/Original-/Extraktionshash. Sie nutzt derzeit Text, nicht Tabellengeometrie.

Evidence Resolver: Zitate müssen exakt und genau einmal auf der angegebenen Seite
vorkommen und vollständig innerhalb eines gelieferten Abschnitts liegen. Angegebene
Seite und Hashes sind ebenfalls zu prüfen; ein gleiches Zitat auf einer anderen Seite
ist durch die Seitenreferenz disambiguiert. Mehrfache Treffer auf derselben Seite
werden abgelehnt. Daraus entstehen pdf-1-Offsets [start_char, end_char).

Eine falsche Produkt-ID, erfundene/mehrdeutige Fundstelle, unvollständiger Kontext oder
nicht wörtlich belegbare Limite erzeugt review_required. Der Originalclaim bleibt
zur Diagnose erhalten. Die englische synthetische Limitprüfung erkennt Betrag,
CHF und einfache Bezugsgrössen; sie beweist **keine korrekte Zuordnung** einer im Zitat
vorhandenen Zahl. Negationen, implizite Regeln, Übersetzungen und alle fachlichen
Schlüsse brauchen zusätzliche Evaluation und menschlichen Review.

## Provider und Prompts

Genau ein realer Adapter: OpenAI Responses API über das optionale offizielle
openai-SDK (Lockfile: 2.54.0). `responses.create` nutzt JSON Schema mit strict=true;
beide Rollen, alle DTO-Felder und zusätzliche Eigenschaften sind explizit definiert.
Rohtext wird vor fachlicher Validierung gespeichert. Refusal/incomplete werden
separat gespeichert und nie als erfolgreiche Extraktion gewertet. SDK-Retries sind
abgeschaltet; ausschliesslich Caller entscheidet über begrenzte Wiederholungen.
Keine Tools, Websuche, Agentenschleifen oder zusätzlichen Provider.

Quellen: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
und [Responses create](https://developers.openai.com/api/reference/python/resources/responses/methods/create).
Structured Outputs erzwingen Struktur, nicht Wahrheit. SDK-Vertragstests laufen mit
In-Memory-HTTP-Transport. Es wurde kein Live-Modell als Qualitätsbaseline vermessen.

MockProvider liefert deterministische vorgegebene Antworten. Der Benchmark verwendet
rules(..., simulated=True) für absichtlich fehlerhafte Antworten; er greift nicht auf
Goldannotation zu. ReplayProvider liest gespeicherte Antworten und macht keine
Netzwerkaufrufe. Ein erneuter echter Modellaufruf ist nicht deterministisch zugesichert.

Die versionierten Prompts travel-extract-1 und travel-verify-1 liegen in
src/axiory/extraction/prompts.py. Systeminstruktionen verbieten Ergänzungen aus
Weltwissen und behandeln Dokumente/Claims als untrusted DATA im User-Payload.
Prompt-Injection bleibt ein offenes Modellrisiko: Rollentrennung und Schemas sind
keine Garantie für semantischen Gehorsam. Fabrications können trotz korrektem
Quellzitat entstehen. Keine Geheimnisse werden in Prompts benötigt.

## Modus A/B und Korrekturen

A: Extraktor, Schema, Quellenprüfung. B: derselbe Extraktor plus separater Verifier-
Aufruf mit Originalkontext und Kandidaten, ohne Extraktor-Chain-of-Thought. Er muss
support, omissions, limits, negation, overclaim und unknown prüfen, begründen und
zitieren. Seine Zitate werden ebenfalls deterministisch geprüft. Dass ein Feld in
checks vorkommt, beweist nicht, dass die fachliche Prüfung korrekt ausgeführt wurde.

Der Verifier ändert keinen Claim. Ein optionales experimentelles review_gate gibt
nur source_matched-Claims mit vollständig zitiertem supported-Verdict zurück.
Zurückgehaltene Claims sind **keine Ausschlüsse** und werden im Recall als fehlend
bewertet. Alle ursprünglichen Claims bleiben im Run. Das Gate ist keine Produktfreigabe.
Der gleiche Modellname wird für beide Aufrufe verwendet: getrennte Aufrufe sind
keine statistische Unabhängigkeit der Modellfehler.

Explizite Neuläufe mit predecessor=<vorheriger Runhash> speichern Korrekturen als
neue, verkettete Runs für denselben Kontext; kein Überschreiben und keine automatische
Übernahme von Verifier-Vorschlägen. Neue Dokumentversionen sind eigenständige Runs.

## Installation und Nutzung

```sh
uv sync --locked --dev
uv run axiory-semantic-eval
```

Alle 120 Fälle werden offline mit pypdf eingelesen. Pro Fall entstehen isolierte
Stores unter datasets/evaluation-semantic/cases/<case>/store; report.json enthält
Fallresultate, Nenner, Messlücken und Run-IDs. Keine echten Daten hinzufügen.

Ein späterer Live-Pilot muss ausdrücklich aktiviert werden. Es gibt keinen
Standard-Live-Modellnamen: einen verfügbaren, Structured-Outputs-fähigen Modellnamen
bzw. Snapshot bewusst wählen und dokumentieren. --model wird im Request aufgezeichnet;
response.model zusätzlich in der Rohantwort und im Claim. Beispiel einer dokumentierten
Modellfamilie: [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
Dies ist keine aktuelle Qualitäts-/Preisempfehlung. API-Schlüssel ausschliesslich als
OPENAI_API_KEY setzen, niemals in Budgetdateien oder Git.

```sh
uv sync --locked --dev --extra llm-openai
uv run --extra llm-openai axiory-semantic-eval --live --case family-0-clear_coverage --model YOUR_MODEL_SNAPSHOT --budget .cache/live-budget.json --verify
```

Die Budgetdatei wird als Budget-Modell strikt validiert. Explizit aktuelle Preise
input_usd_per_million und output_usd_per_million setzen; keine Preise sind fest
hinterlegt. Zusätzlich max_cost_usd, max_total_tokens, max_input_tokens,
max_output_tokens, max_calls, max_retries, timeout_seconds, total_seconds und
max_response_bytes konfigurierbar. Beispielgrenzen: 1 USD, 176000 reservierte Token,
40000 Input, 4000 Output, vier Versuche, ein Retry, 30 s/Aufruf, 120 s/Run.
Die Preise sind durch den Nutzer vor dem Lauf zu ergänzen, nicht zu erfinden.

Live-CLI akzeptiert nur einen Fall des mitgelieferten synthetischen Korpus, keine
beliebige PDF. live-report.json enthält eine Einzelfallauswertung, keine belastbare
Gesamtqualität. Die Python-API verlangt synthetische Dokumentdeklaration; diese
Deklaration ist **keine DLP-/Echtheitsprüfung**. Operatoren dürfen keine echten AVB
oder Kundendaten als synthetisch deklarieren. Auch das lokale Korpusfile ist eine
Vertrauensgrenze; unreviewte Änderungen sind nicht zum Senden freigegeben.

## Speicherung und Replay

Der bestehende append-only SHA-256-Store wird um semantic_contexts, model_outputs,
model_calls und semantic_runs ergänzt. Original-PDFs bleiben in originals; alle
Referenzen sind hashgebunden. model_outputs enthalten Rohtext, Modellkennung,
Status, verfügbare Usage und den SDK-Response-Envelope. model_calls referenzieren
Request- und Outputhash, Run-ID, Promptversion, Inputhashes, Versuch/Reihenfolge und Retry-Klassifikation,
Latenz, redigierten Fehlercode, Preisannahmen im Runbudget und Kostenschätzung.
Modelldaten stehen in synthetischen Artefakten; Konsolenlogs enthalten nur IDs/Status.
HTTP-Fehlertexte und Zugangsdaten werden nicht protokolliert.

```python
from pathlib import Path
from axiory.extraction.pipeline import replay
from axiory.parsers.store import LayoutStore

store = LayoutStore(Path("datasets/evaluation-semantic/cases/family-0-clear_coverage/store"))
# original_run_hash aus report.json, Feld verified; kein neuer API-Aufruf.
# replay_hash, result = replay(store, original_run_hash)
```

Replay lädt und reproduziert Original/Parser/Context, vergleicht Request, Modell,
Schema und Prompt und validiert die Rohantworten erneut. Alle aufgezeichneten Versuche müssen vollständig verbraucht werden. Importierte Claim-/Verifier-
Flags werden nicht übernommen. Abweichungen vom neu berechneten Ergebnis führen zu
IntegrityError. Vom Originalrun replayen, nicht von einem Replayrun. Zeit, Run-IDs
und Aufrufartefakthashes ändern sich; Claims, Verdicts und Fehler sind der semantische
Replayvergleich. Abweichende Budgets/Timeoutbedingungen können Fehlerläufe nicht
reproduzieren; dann wird geschlossen abgelehnt. Hashes sind keine digitalen Signaturen.

## Budgets und bekannte Grenzen

Vor jedem Versuch werden Input-Bytes plus Framingreserve als konservative Token-
Näherung und das Outputmaximum reserviert, ebenso deren Kosten. Nach Timeouts wird
keine Reservation freigegeben, weil der Anbieter den Versuch verrechnen könnte.
Gemeldete Überschreitungen werden als Fehler erfasst und Reservationen nachgezogen.
Input-Bytes sind kein offizieller Tokenizer; Preise sind konfigurierte Schätzungen,
keine Rechnungsdaten. Versteckte Providerabrechnung kann lokale Grenzen überschreiten.
Keine Usage bedeutet unbekannte Kosten/Token, nicht Null. Mock/Replay bezahlen keine API.

Nur Timeout/Verbindungsfehler/429/5xx sind begrenzt wiederholbar; keine Reparaturloops
für fehlerhaftes JSON. Aktuell sofortiger begrenzter Retry ohne Backoff. Transport-
Timeout plus nachträgliche Deadline-Prüfung sind keine harten CPU-/RAM-/Walltime-Limits.
Auch Responsegrössen werden erst nach Empfang geprüft und zur Diagnose gespeichert.
Isolierter Worker, Streaming-/Prozesslimits, fachlicher Review und kontrollierte
Quellenaufnahme bleiben Voraussetzung vor echten AVB und Produktion.
