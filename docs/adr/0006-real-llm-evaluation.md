# ADR 0006: Gepaarte mehrsprachige Evaluation mit gemeinsamem Budgetjournal

Status: angenommen für synthetische Experimente, 9. Oktober 2026.

## Kontext

Sprint 5 implementiert Extraktion und Verifikation, misst aber noch keine Live-Qualität.
Ein zweiter Modellaufruf kann Fehler sowohl erkennen als auch verursachen. Ein fairer
Vergleich braucht dieselbe A-Antwort, festgeschriebenes Gold und kontrollierte Kosten.

## Entscheidungen

1. Zusätzliches Modul experiments statt Erweiterung alter gespeicherter DTOs.
   CandidateV2/semantic-2/travel-2 ergänzen geschlossene Bedingungs-/Ausschlussatome und
   einen separaten Selbstbehalt. RequestV2 trägt Prompt-, Temperatur- und Tierkonfiguration.
   Legacy Request, ClaimRecord, Dokumentversionen und deren Hashsemantik bleiben identisch.
2. Ein versionierter, vor Live eingefrorener 120-Fälle-DE/FR/IT-Korpus. Familien-,
   Produkt- und Templatesplits sind disjunkt. Source ist ein blindes DTO ohne Labels.
   Gold ist single-author und **nicht unabhängig fachlich geprüft**. Es darf nicht
   als objektive Wahrheit oder repräsentative Schweizer AVB-Sammlung gelten.
3. Feste Pipeline A -> B/C, exakt gleiche gespeicherte A-Rohantwort für beide Reviews;
   C sieht B nicht. Keine Agenten, keine Tools, kein Retrieval, keine Reparaturschleife.
   supported öffnet nur bei gültigen Quellen/Checks das Gate. Keine automatische
   Claimkorrektur; neue versionierte CaseRuns können Vorgänger referenzieren.
4. Gemeinsame Kosten-/Token-/Aufruf-/Zeitlimits über alle Fälle und Rollen. Jeder
   Versuch bekommt vor Versand eine unveränderliche Reservation, hashverkettet und
   exklusiv journalisiert. SDK-Retries aus. Unsichere Timeouts behalten ihre Reservation.
   Ein bestehender Sessionpfad darf auch nach Neustart nicht als frisches Budget dienen.
5. Pilot auf 24 vorab festgelegte Fälle, 2 USD, geprüften gpt-4.1-mini-Snapshot und
   dokumentierte Preise begrenzt. Live ist ausdrücklich opt-in; Vollkorpus nur offline.
   Simulationsbudgets sind keine kostenpflichtige Freigabe. Harte Ressourcengrenzen
   und serverseitige Rechnungsobergrenzen sind nicht durch lokale Zulassung bewiesen.
6. Originale/Extraktionen im bestehenden LayoutStore, neue CAS-Collections für Requests,
   Reservationen, Antworten, Fälle, Kontext, Gold, Freeze und Manifest. Manifest und
   Report pro neuem Runverzeichnis; abgebrochene Stores werden nicht überschrieben.
7. Replay reproduziert Quellen, Payloads, Status und Gates aus unveränderten Rohantworten,
   kontrolliert Budgetketten und bewertet erneut. Keine importierten Freigabeflags.
   Lokale Hashes schützen Integrität innerhalb des Vertrauensmodells, keine Authentizität.
   Parser-/Promptänderungen brauchen neue Versionen und passend ausgecheckte Replaycodes.
8. Predeclared Metriken mit Zähler/Nenner, leere Messwerte null, technische Fehler im
   End-to-End-Nenner. Gepaarter Bootstrap auf Familien statt unabhängiger Fallbootstrap;
   explorative Intervalle und Complete-case-Sensitivität, keine Signifikanzbehauptung.
9. OFFLINE_PROTOCOL_TEST und LIVE getrennt; Rohantworten/Usage/Fehler vor Interpretation
   speichern. Familien-/Szenariolabels nie zum Provider senden. API-Latenz und Kosten
   kumulativ je Arm plus Zusatzaufwand, keine Doppelzählung gemeinsam genutzter A-Aufrufe.
10. CI ohne Runtime-Netzwerk; Abhängigkeiten werden im vorgeschalteten Setup geladen.
    Optionaler SDK-Vertragstest nutzt In-Memory-HTTP, niemals Secrets oder bezahlte Calls.

## Folgen und abgelehnte Alternativen

Keine neue Laufzeitabhängigkeit, Datenbank oder Orchestrierungsbibliothek. Dateibasierter
CAS und deterministische Statistikauswertung reichen für den Pilot. Signiertes Eventlog,
Crash-Resume und verteilte Budgetkoordination sind bewusst nicht implementiert. Der
lokale Store unterstützt eine exklusive Session, keine geteilten Kontobudgets.

Ein ungeprüfter Goldstandard kann systematische Fehlbewertungen erzeugen. Derselbe
Snapshot in drei Rollen liefert keine unabhängigen Fehler. C kostet einen zusätzlichen
Aufruf, ohne zugesicherten Nutzen. Ein repräsentativeres, fachlich geprüftes Holdout und
beobachtete Pilotfehler entscheiden über weitere Investition. Es gibt weiterhin keine
Freigabe echter Versicherungsdaten und keine UI.

Details: [Benchmark](../REAL_LLM_BENCHMARK.md),
[Verifikationsstrategie](../VERIFICATION_STRATEGY.md).
