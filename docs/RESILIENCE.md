# Resiliente Extraktion: Plan → Aussage → Reflexion → Gate

Stand: 15. Oktober 2026. Ausschliesslich synthetische Dokumente.

Die zwei bekannten Durchrutscher werden jetzt durch technische Regeln blockiert.
Die zusätzliche Prompt-Reflexion ist implementiert, ihre Live-Wirkung ist **ungemessen**.
Kein Selbsturteil ersetzt einen Quellenbeleg oder unabhängigen Fachreview.

## Ablauf und gespeicherte Nachweise

1. Verifizierten Original-/Extraktionskontext laden. Daraus entsteht `evidence-plan-1`
   mit Kontexthash, erforderlichen Seiten-/Zeichenspannen, Tabellenverdacht,
   begrenzt erkennbaren Tabellenzeilen und expliziten Strukturproblemen.
2. Request speichert diesen Plan mit SHA-256. Goldlabels und andere Reviewerurteile
   gehören nicht zum Prompt. Alle Texte aus Dokument und Kandidat bleiben untrusted.
3. Promptversion 3 fordert Planung vor der Aussage und einen kurzen Selbstcheck des
   finalen Ergebnisses. Die Antwort enthält die unveränderten atomaren v2-Geldfelder
   plus `reflection`: Planhash und genau sechs unterschiedliche Auditbefunde.
4. Jeder Befund nennt `check`, `outcome`, `evidence_indices` und eine kurze `summary`.
   Indizes referenzieren die Zitate dieser Antwort; bei Reviews folgen Gegenbelege
   auf die normalen Belege. Pass benötigt einen Beleg. `not_applicable` ist nur bei
   fehlendem Tabellenverdacht erlaubt. Keine privaten Gedankengänge oder Scores.
5. Die Anwendung prüft Quellen, vollständige Belegabdeckung, Tabellenbindung,
   Planidentität, Checkvollständigkeit und Widersprüche zwischen Befunden und Verdict.
   Jeder Fehler verhindert Freigabe. Der Deckungsstatus bleibt erhalten; Zurückhalten
   bedeutet weder excluded noch automatisch unknown. Ein begründetes unknown bleibt
   über `supported_unknown` freigabefähig.
6. B/C prüfen weiterhin denselben gespeicherten Kandidaten. Es bleiben maximal drei
   reguläre Aufrufe pro Fall; keine zusätzliche Planungs-API, kein Agentenframework,
   keine unbeschränkte Reparatur. Rohantworten bleiben vor Validierung im CAS.
7. Replay rekonstruiert Plan, Request, Reflexion und Gates aus Original und Rohantwort.
   Importierte Freigabeflags werden nicht geglaubt. Alte v1/v2-Runs bleiben unverändert.

## Was die deterministischen Regeln leisten

**Belegvollständigkeit:** Alle Nicht-Whitespace-Zeichen des bereitgestellten Kontexts
müssen durch aufgelöste Evidence-Spannen auf derselben Seite abgedeckt sein. Nur der
exakte synthetische Banner ist ausgenommen. Einzelne Zitate dürfen gemeinsam abdecken;
fehlende Satzteile, Antezedenten oder Seiten werden nicht durch zusammengesetzte
Textsuche kaschiert. Vollständige Kontextabschnitte dürfen zitiert werden.

Diese konservative Regel verhindert die beobachtete isolierte Aussage «cette garantie»
ohne den Annulation-Satz. Sie ist absichtlich breiter als eine semantische Auswahl
relevanter Klauseln: bei langen Dokumenten steigen Kosten und Fehlablehnungen.
Vollständigkeit gilt **nur für den verifizierten bereitgestellten Text**, nicht für
visuell verlorene PDF-Inhalte. Bereits als abgeschnitten/unvollständig markierter
Kontext bleibt gesperrt. Vollkontextzitierung beweist keine richtige Interpretation.

**Tabellenbindung:** Eine explizite DE/FR/IT-Grammatik erkennt drei separate Header
für Leistung, CHF-Limite und Bezugsgrösse; Spaltenreihenfolge ist frei. Danach müssen
vollständige Zeilengruppen aus drei Zellen folgen. Zeilen sind an genaue Header- und
Quellspannen gebunden. Eine eindeutige Zielzeile muss zu Code, Betrag, CHF und Basis
passen. Fremde Zeilen werden weder Hauptlimit noch Sublimit. Doppelte/unbekannte
Zielbezeichnungen, unklare Header oder Hierarchien halten den Claim zurück.

Dies ist ein Adapter für kontrollierte synthetische Row-major-Texte, **keine aus PDF-
Geometrie bewiesene Tabellenrekonstruktion**. Tabellenverdacht beruht auf Headern,
Markern, isolierten Zahlen und Separatoren; beliebige unbekannte Layouts werden nicht
zuverlässig erkannt. Erkannte, aber nicht unterstützte Tabellen scheitern geschlossen.
Komplexe Zeilenumbrüche, zusammengeführte Zellen, Fussnoten, mehrere Tabellen pro
Abschnitt, Sublimit-/Selbstbehalt-Hierarchien und neue Vokabeln benötigen Review bzw.
einen neuen versionierten Adapter. Keine Behauptung allgemeiner AVB-Layoutintelligenz.

## Fehlerbehandlung und kontrollierte Verbesserung

| Fehlercode | Reaktion / nächster Schritt |
| --- | --- |
| `incomplete_evidence_context` | Zurückhalten; vollständige Quellstellen inklusive Bezugssätzen und Einschränkungen in einem neuen verknüpften Lauf belegen. |
| `table_limit_binding_mismatch` | Zurückhalten; eindeutige Zielzeile, Betrag und Bezugsgrösse prüfen. Kein automatischer Austausch des Betrags. |
| `ambiguous_target_table_row` | Zurückhalten; doppelte oder nicht zuordenbare Zielzeilen klären. |
| `unsupported_table_layout` | Zurückhalten; Strukturadapter/Geometrie oder Fachreview erforderlich. Kein Rückfall auf Zahlenvorkommen. |
| `unsupported_table_monetary_hierarchy` | Zurückhalten; Sublimit/Selbstbehalt kann aus der flachen Tabelle nicht bewiesen werden. |
| `incomplete_context` / `empty_evidence_plan` | Kontextaufnahme/Extraktion korrigieren, keine Belege erfinden. |
| `missing_reflection` / `reflection_incomplete_checks` | Antwort unvollständig; Original unverändert aufbewahren. |
| `reflection_wrong_plan` / `reflection_invalid_reference` / `reflection_missing_reference` | Veraltete/falsche Referenzen zurückweisen; nie Hashes oder Indizes stillschweigend reparieren. |
| `reflection_*_unresolved` / `reflection_decision_conflict` | Ergebnis zurückhalten; offene Prüfung oder widersprüchliches Urteil dokumentieren. |
| `extract:invalid_response` / `verify:invalid_response` / `critic:invalid_response` | Striktes Schema verletzt; Rohantwort bleibt gespeichert, keine automatische JSON-Reparatur. |
| Provider-/Budgetfehler | Bestehende begrenzte Retry-/Abbruchregeln und gemeinsame Reservierungen bleiben massgeblich. |

Neue Fehler werden als kleine synthetische Regression mit erwarteter Zurückhaltung
oder korrektem Ergebnis festgehalten. Erst dann Regeln/Prompt als neue Version ändern,
Legacy-Replays prüfen und die Änderung an **neuen** Familien evaluieren. Kein laufendes
Modell darf seinen Systemprompt, die Regeln oder Goldannotation selbst überschreiben.
Diese kontrollierte Rückkopplung macht Fehler wiederholbar bearbeitbar.

## Messstand und nächste Freigabe

Die Offline-Nachprüfung der 24 gespeicherten v2-Kandidaten findet neue Strukturfehler
bei genau den zwei damals durch C freigegebenen Fällen:

- `document-it-1-10`: falsche CHF-9000/Jahr-Zeile und erfundene monetäre Hierarchie.
- `document-fr-1-14`: unvollständige Kontextbelege ohne Deckungsbezug.

[Snapshot](benchmarks/sprint6-structural-reassessment-v3.json) enthält Originalmanifest-,
Kandidaten- und Planhashes. `scripts/reassess_pilot_structure.py` verifiziert zuerst den
historischen Replay. Es erzeugt keine v3-Reflexion für alte Antworten, verändert keine
Gates und meldet keine neue Modellprecision. Neue synthetische Mutationstests prüfen
auch gültige Gegenbeispiele, damit «alles zurückhalten» kein Scheinerfolg ist.

Es wurden keine weiteren API-Aufrufe ausgelöst. Vom genehmigten kumulativen Budget
sind konservativ 0.3872 USD übrig; ein voller neuer 24-Fälle-Lauf reserviert maximal
0.8064 USD und wird mit der neuen Standardkonfiguration vorab abgelehnt. Der Offline-
Betrieb skaliert nur Simulationsbudgets, nie Live-Budgets. Preisannahmen bleiben für
einen künftigen Live-Aufruf erneut zu prüfen. Keine automatische Modellmigration.

Offen: allgemeine semantische Vollständigkeit aller Bedingungs-/Ausschlussatome,
Interpretation von Negation und Widersprüchen, zuverlässige beliebige Tabellen sowie
unabhängige Qualitätsmessung. Nächste Iteration: neue Klausel-/Produktfamilien getrennt
und blind doppelt annotieren, Differenzen klären, vor Promptänderungen einfrieren und
Precision/Recall/Unknown/Fehlablehnungen gemeinsam bewerten. Aktuell: null unabhängige
Fachannotation; bekannte Pilotfälle und neue Tests sind Entwicklungsmaterial.


## Ausgeführte Qualitätsprüfungen

- `uv run pytest`: 450 bestanden, 33 Skips für lokal nicht installiertes optionales PyMuPDF.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run axiory-demo`: erfolgreich.
- `uv run --extra llm-openai pytest tests/test_openai_adapter.py`: 11 bestanden, nur In-Memory-HTTP.
- 61 neue Resilienzregressionen plus zwei zusätzliche v3-SDK-Vertragstests.
- v3-Offline-Vollkorpus: 120 Fälle, 360 simulierte Calls, vollständig abgearbeitet,
  keine API-Aufrufe. Mock meldet bewusst unsichere Reflexion und hält Claims zurück.
  [Protokoll-Snapshot](benchmarks/sprint6-resilience-offline-summary.json).

Die CI prüft weiterhin v1/v2 und zusätzlich v3 mit Replay bei isoliertem Laufzeitnetz.
