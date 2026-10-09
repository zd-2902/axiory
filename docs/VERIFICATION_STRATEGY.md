# Verification Strategy

Drei getrennte Ebenen: (1) exakte Fundstelle im verifizierten Original,
(2) experimentelle semantische Unterstützung durch ein Modell,
(3) fachliche menschliche Freigabe. Keine Ebene ersetzt die nächste.

## Deterministische Quellenprüfung

Original-PDF, Version, Parserkonfiguration, Extraktion und Kontext werden beim Reload
geprüft. Zitate müssen genau einmal auf ihrer angegebenen Seite und vollständig in
der gesendeten Textspanne vorkommen. Hash, Seite und Zeichenoffset bleiben überprüfbar.
Produkt/Zielcode müssen passen, der Kontext muss vollständig sein. Geldbeträge und CHF
müssen im zitierten Text vorkommen. Betrag-Anwesenheit beweist weder dessen Zuordnung
zu einer Tabellenzeile noch die Interpretation einer Ausnahme: das bleibt semantisch.
Mehrsprachige Negationen werden nicht über ein englisches Stichwort automatisiert
fachlich freigegeben. Ungültige Zitate erzeugen review_required; niemals erfundene Spannen.

## Urteil und Gate

| Reviewentscheidung | B/C-Freigabe |
| --- | --- |
| supported | nur mit vollständigen Checks und gültigen Reviewfundstellen |
| unsupported | zurückhalten |
| contradicted | zurückhalten; Gegenbeleg/Interpretation protokollieren |
| insufficient_evidence | zurückhalten, keine Umwandlung in excluded |
| requires_human_review | zurückhalten |

A verlangt source_matched. B verlangt zusätzlich ein gültiges supported von B.
C verlangt beides und ein gültiges supported von C. C beurteilt dieselbe gespeicherte
A-Antwort unabhängig von Bs sichtbarer Meinung. Alle sechs Prüfdimensionen sind Pflicht:
Support, Auslassungen, Limiten, Negation, Widersprüche und Unbekanntheit. Begründungen,
Fundstellen, optionale Gegenbelege und alternative Interpretation bleiben erhalten.
Ein schön formuliertes supported ohne gültige Quellen öffnet das Gate nicht.

Kein Urteil darf den Candidate ändern. Eine Korrektur wird neu erzeugt und über
predecessor_sha256 an den vorherigen CaseRun desselben Kontexts gebunden. Der alte
Hash bleibt lesbar. human_status bleibt stets not_reviewed. Ein späterer Fachprozess
braucht benannte Reviewer, Zeit, Begründung, Zuständigkeit und Version, bevor dieser
Status erweitert werden darf.

## Angreifer- und Vertrauensmodell

Dokumenttext, Modellantwort und importierte Statusfelder sind untrusted. Die Modelle
haben keine Tools und sehen keine Goldlabels. Systemprompt und JSON-Dokumentpayload
sind getrennt; Prompt-Injection-Tests prüfen Rollen-/Datenfluss, Schema und Gateverhalten.
Das ist **kein empirischer Nachweis**, dass ein echtes Modell jeder Injection widersteht.
Modelle können plausible, exakt zitierte Aussagen trotzdem falsch interpretieren.

Replay prüft Originalbytes durch den vorhandenen LayoutStore, bindet sie an die
gefrorene synthetische Quelle, reproduziert Kontext/Request und dekodiert Rohantworten
neu. Kandidaten, Reviewchecks und Releaseflags werden erneut berechnet und mit den
Artefakten verglichen. Auch Journal, Request-/Antwortbezüge, gemeinsame Reservierungen,
Kosten und Bericht werden geprüft. Importierte source_matched/supported-Flags allein
haben keine Autorität. Die vorhandenen SHA-256-Hashes sind keine Signatur: wer den
vollständigen Store samt Vertrauensankern austauscht, kann keine digitale Echtheit
allein durch lokale Hashes beweisen. Aufgezeichnete Providerlaufzeiten und Transportfehler
sind Beobachtungen, keine aus Antworttext rekonstruierbaren Tatsachen.

Timeouts sind begrenzt, aber harte Prozessressourcenlimits erfordern den späteren
isolierten Worker. Standard-CI sperrt nach dem Dependency-Setup das Runtime-Netzwerk
über Linux-Netzwerknamespace; pytest blockiert zusätzlich Socketverbindungen.
Keine echten AVB, keine Kundendaten, keine Schlüssel im Repository.

## Zu prüfende Hypothesen

Ein Verifier könnte ausgelassene Bedingungen, falsche Tabellenzeilen, Verwechslung von
Limit/Sublimit/Selbstbehalt oder Negationen erkennen. Er könnte dieselben Fehler wie
A wiederholen oder korrekte Claims übervorsichtig zurückhalten. Der aktuelle Stand
behauptet keines dieser Verhalten als gemessen. Ein Modell für alle drei Rollen hat
korrelierte Fehler; ein Modellwechsel benötigt einen neuen kontrollierten Vergleich.

Zuerst fachlich blindes Review des 24-Fälle-Pilots, einschliesslich falsch abgelehnter
korrekter Claims und durchgelassener Fehler. Danach Reviewzeit messen und über C anhand
von zusätzlichem Nutzen, Kosten und Latenz entscheiden. Kein zusätzlicher Agent ohne
beobachteten Qualitätsgewinn oder Risikoreduktion.
