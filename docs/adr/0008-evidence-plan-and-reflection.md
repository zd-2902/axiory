# ADR 0008 – Evidenzplanung und begrenzte Reflexion

- Status: angenommen
- Datum: 2026-10-15
- Ergänzt ADR 0006/0007; historische Protokolle bleiben gültig.

## Kontext

Im diagnostischen v2-Pilot passieren eine falsche Tabellenzuordnung und ein
unvollständiger Beleg beide Modellreviews. Bereits stärkere Tabellenanweisungen
in v2 haben den Fehler nicht verhindert. Selbstvertrauen, Schemaeinhaltung und
Literalbelege sind kein Ersatz für überprüfbare Zuordnung und Vollständigkeit.

## Entscheidung

Neue Konfiguration `experiment-config-3` bindet `evidence-plan-3` und Promptversion 3.
`pilot-config-v3.json` wird CLI-Standard. v1/v2 bleiben explizit wählbar; ihre Prompt-
und Schemahashes sind eingefroren. Keine Änderung an Ontologie travel-2, CandidateV2,
PDF-Originalen, Goldfreeze oder historischen Report-/CaseRun-Bytes.

Ein deterministischer EvidencePlan entsteht vor dem Provideraufruf aus Context,
niemals aus Goldlabels. Er bindet erforderliche Quellspannen, begrenzt erkennbare
Tabellenzeilen und Strukturprobleme an den Kontexthash. Der Request enthält Plan,
Planhash und versionierten Systemprompt; sein CAS-Hash bindet diese gemeinsam.
Ein separater veränderlicher Planstore ist nicht erforderlich.

Extraktions- und Reviewantworten ergänzen eine verpflichtende Reflection mit Planhash
und sechs verschiedenen kurzen Auditbefunden. Jeder Pass referenziert vorhandene
Zitate. Unsichere/fehlerhafte Checks verhindern Freigabe; Reviewverdict und strukturierte
Befunde müssen übereinstimmen. Freitextbegründungen können weiterhin falsch sein.
Die Reflexion bleibt im unveränderten Raw Reply nachvollziehbar. Der normalisierte
CheckedClaim/CheckedReview enthält berechnete Issuecodes; Replay decodiert die rohe
Reflexion erneut und vergleicht das Ergebnis. Keine nachträglich erfundenen Befunde.

Zusätzlich erzwingen voneinander unabhängige Regeln vollständige Nicht-Whitespace-
Kontextabdeckung durch aufgelöste Evidence-Spannen sowie passende Zielzeile/Betrag/
Währung/Basis in der engen synthetischen Dreispaltengrammatik. Positive Modellurteile
können diese Regeln nicht aufheben. Nicht unterstützte erkannte Tabellen und monetäre
Hierarchien werden zurückgehalten. Unbekannt bleibt unbekannt; Fehler machen keine
Deckung zu einem Ausschluss. Kein stillschweigender Werte-/Hashersatz.

Der Prozess bleibt synchron mit drei begrenzten Aufrufen pro Fall. Planung ist lokal,
Reflexion erfolgt in derselben strukturierten Antwort, ohne zusätzliche kostenpflichtige
Reflexionsschleife. Neue Versionen werden durch Engineering/Regressionen eingeführt,
nicht durch selbstmodifizierende Systemprompts. Bestehende Retry-/Budget-/CAS-Regeln
bleiben erhalten. Standardkonfiguration berücksichtigt das verbleibende Gesamtbudget;
Offline-Simulationen erweitern nur simulierte Budgets und können niemals Live zulassen.

## Alternativen und Folgen

- Nur den Prompt verschärfen: nach beobachtetem v2-Fehler unzureichend.
- Unbegrenzte Selbstkorrektur oder neue Agenten: zusätzliche Kosten und korrelierte
  Fehler ohne garantierten Beleggewinn; verworfen.
- Sofort universeller semantischer Feldbeweis/Tabellenparser: ohne neue Annotation und
  Geometrieprüfung nicht seriös lieferbar; explizit nächste Iteration.
- Vollkontextpflicht statt semantischer Klauselauswahl: konservativ, nachvollziehbar,
  aber potentiell teuer und mit Fehlablehnungen. Beweist nur Kontextabdeckung, keine
  Interpretation und keine Vollständigkeit gegenüber visuellen PDF-Inhalten.
- Tabellenparser: begrenzte Row-major-Heuristik mit explizitem Vokabular; keine
  generelle Strukturgarantie. Unbekannte Tabellen können unerkannt bleiben.
- Keine allgemeine semantische Fehlerfreiheit, kein menschlicher Freigabestatus.

Die [offizielle Structured-Outputs-Dokumentation](https://developers.openai.com/api/docs/guides/structured-outputs)
trennt Schema-Konformität von möglichen inhaltlichen Fehlern. Deshalb werden Befunde
lokal validiert und technische Regeln separat erzwungen. SDK-Vertragstests laufen
nur über In-Memory-Transport; Standardtests und CI bleiben offline.

## Nachweis und Vertrauensgrenzen

Regressionen umfassen beide konkreten Fehler mit falschem einstimmigem Modellurteil,
korrekte Varianten, Zeilen-/Spaltenpermutationen in DE/FR/IT, unbekannte Header,
doppelte Zielzeilen, seitenübergreifende Belege, Auditmanipulation und Replayangriffe.
Legacy v1/v2 behalten ihre Regeln. Gespeicherte v2-Kandidaten werden separat offline
strukturell nachgeprüft; keine Änderung alter Antworten, Gates oder Qualitätswerte.

Neue Tests und bekannte Pilotfälle sind Entwicklungsmaterial. Neue unabhängige
Fachannotation und eingefrorene Familien bleiben Voraussetzung für Qualitätsaussagen.
Kein neuer Live-Lauf oder Vollkorpusauftrag; keine Änderung an Freigabegrenzen echter
AVB oder fehlender Worker-Isolation. [Details und Fehlerkatalog](../RESILIENCE.md).
