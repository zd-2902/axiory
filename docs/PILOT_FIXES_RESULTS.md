# Pilot-Korrekturen v2 – Ergebnis vom 15. Oktober 2026

## Änderung und Nachweise

Zahlenprüfung mit Satzzeichen und Schweizer Gruppierung korrigiert. Atomare Geldobjekte
verhindern unvollständige Provider-Felder; strikte Fachvalidierung bleibt bestehen.
Ein korrekt unbekannter Status braucht nun supported_unknown von beiden Reviews.
insufficient_evidence ist weiterhin keine Freigabe. Prompts v2 präzisieren Tabellenzeilen,
Bedingungen und Widersprüche. Keine neuen Abhängigkeiten. Details: [ADR 0007](adr/0007-versioned-pilot-fixes.md).

65 neue Regressionstests und zwei zusätzliche SDK-Konfigurationstests. Lokal:
**387 bestanden, 33 optionale PyMuPDF-Skips**; Ruff Lint/Format und Demo erfolgreich.
[CI #27](https://github.com/zd-2902/axiory/actions/runs/38780347848) am Implementierungscommit
`3a5e62c03e18f87fb3051e1a3b6cf9422a0e77ec` vollständig grün. v1-Live-Replay behält
`92f559870c3846c25265c46e7d88b587dbc9e6044354dd6a40268be7721a9b0f`;
v1- und v2-Offline-Vollkorpus behalten den Protokollfingerprint
`e97f58730476048653c21c67e743ac6de81fb6bb31e513ed815e62a0d3526309`.

Die separate [Offline-Nachprüfung gespeicherter Kandidaten](benchmarks/sprint6-source-reassessment-v2.json)
ändert genau den fälschlich blockierten CHF-1875-Fall. Sie verwendet keine Modelle,
ändert keine historischen Rohantworten und keine Reviewurteile.

## Diagnostischer Live-Vergleich

Dieselben 24 bekannten Entwicklungsfälle, dasselbe Modell gpt-4.1-mini-2025-04-14,
aber neue Schemas/Prompts/Gates. Run `run-cbf3a88b1c8143119d2834a764698fac` am obigen
sauberen Commit (git_dirty=false). Alle 24 Fälle mit **72 erfolgreichen Antworten**,
keine HTTP-/Schemafehler, keine Retries. 24/24 Extraktionen haben den richtigen
Deckungsstatus; das bedeutet nicht, dass alle Felder und Belege korrekt sind.

| Messwert | v1 A / B / C | v2 A / B / C |
| --- | --- | --- |
| Korrekte freigegebene Deckungsbehauptungen / freigegebene Behauptungen | 13/17 · 13/16 · 13/15 | 18/21 · 17/20 · 17/19 |
| Recall: korrekte Behauptungen / 21 bekannte Goldstatus | 13/21 · 13/21 · 13/21 | 18/21 · 17/21 · 17/21 |
| Korrekte freigegebene unknown / drei Gold-unknown | 2/3 · 0/3 · 0/3 | 3/3 · 3/3 · 3/3 |
| Fehlerhafte freigegebene Behauptungen / alle 24 Fälle | 4/24 · 3/24 · 2/24 | 3/24 · 3/24 · 2/24 |
| Ungültige Extraktionsantworten | 4/24 | 0/24 |

A = Extraktion plus Quellenprüfung; B ergänzt Verifier; C ergänzt Kritiker und beide
Reviewgates. Precision schliesst unknown aus. Die Anzahl verbleibender Fehler in C
bleibt bei **zwei**; die höhere Ausbeute ist kein pauschaler Sicherheitsnachweis.
Die 24 Fälle wurden nach Einsicht in ihre Fehler erneut verwendet. Kein unabhängiger
Holdoutnachweis, keine kausale Zuordnung zu einzelnen Änderungen, kein Signifikanzclaim.
Gold und ursprüngliche Ergebnisse bleiben unverändert; frischen Holdout erst für
spätere Qualitätsbewertung verwenden.

## Gelöst und weiterhin offen

- **Beobachtet behoben:** vier bisher ungültige Geldantworten sind jetzt valide;
  drei korrekt unbekannte Status bestehen beide Gates; der Satzpunkt-Betrag wird
  akzeptiert. Der italienische Ausnahmefall enthält nun emergency und medical_certificate.
- **Tabellenfehler bleibt:** `document-it-1-10` verwechselt weiterhin CHF 9000/Jahr
  einer Zusatzleistung mit dem Gepäckbetrag CHF 2125/Ereignis. B und C bestätigen dies.
  Promptpräzisierung allein hat das Problem nicht gelöst.
- **Beleg unvollständig:** `document-fr-1-14` extrahiert den Status korrekt, zitiert aber
  nur den Satz über „diese Garantie“, nicht den Satz, der Annulation nennt. Ein
  Gold-Beleganker fehlt. Die Bewertung zählt dies als unbelegte Freigabe, obwohl die
  Felder stimmen. Nicht mit erfundenen Zitaten oder falschem Deckungsstatus gleichsetzen.
- **Korrekte Extraktion zurückgehalten:** `document-de-0-10` wird korrekt extrahiert;
  beide Reviews liefern jedoch falsche Quellenhashes. Die Quellenprüfung blockiert sie.
- **Unzuverlässige Reviewbegründung:** `document-fr-0-01` erfindet intentional_events.
  B übersieht das. C sagt contradicted, erklärt aber gleichzeitig, dass der Claim
  unterstützt sei, und identifiziert den erfundenen Atom nicht. Der Claim wird
  zurückgehalten; dies ist kein Nachweis kohärenter fachlicher Fehlererkennung.

Nächste Iteration: strukturierte Tabellenzeilen und feldbezogene Belegabdeckung in
Schemas/Verifikation aufnehmen; Review-Quellenreferenzen deterministisch an zulässige
Kontextreferenzen binden, ohne ungültige Antworten stillschweigend zu reparieren.
Widersprüche zwischen Verdict und Begründung benötigen gezielte Evaluation und
Fachreview. Keine weiteren Promptschleifen auf dem bereits bekannten Holdout.

## Kosten und Reproduzierbarkeit

129'211 Input- und 18'510 Output-Token; konservative Schätzung ohne Cacheabschlag:
**0.081333 USD** für diesen Lauf. API-Zeit 217.559 Sekunden. Preise am 15. Oktober
auf der [offiziellen Modellseite](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
mit 0.40 USD/M Input und 1.60 USD/M Output erneut geprüft; Konfigurationsdatum bleibt
zur Schema-Kompatibilität unverändert. Der Modell-Snapshot ist dort inzwischen als
deprecated markiert; für Vergleichbarkeit wurde er nicht ausgetauscht.

Gesamtbudget weiterhin 2 USD: kumulativ **1.6128 USD vorsorglich reserviert**, Rest
**0.3872 USD**. Bekannte geschätzte Kosten aller Läufe **0.145033 USD**; tatsächliche
Gesamtkosten wegen fehlender Usage vier früherer Fehlversuche unbekannt. Keine
weiteren kostenpflichtigen Versuche und kein Live-Vollkorpuslauf gestartet.

[Snapshot mit Manifest, vollständigen Strata, Fallprüfungen und Budget](benchmarks/sprint6-live-pilot-v2-summary.json).
Lokaler Store: `datasets/evaluation-real/live-pilot-v2-20261015/`. Replay erfolgreich,
Fingerprint `aaa80b6493d1b90bdd5cd38f48180bfef501012aac886f71e23e0a79739a258c`.
Der Snapshot allein ersetzt Originale und Rohantworten im lokalen CAS nicht.

```sh
uv run axiory-real-eval --replay datasets/evaluation-real/live-pilot-v2-20261015
uv run axiory-real-eval --all-offline --output datasets/evaluation-real/new-v2-offline
```
