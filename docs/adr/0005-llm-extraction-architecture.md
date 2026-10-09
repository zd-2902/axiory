# ADR 0005: Versionierte semantische Extraktion mit untrusted Modellantworten

Status: angenommen für ausschliesslich synthetische Experimente.

## Kontext

Sprint 1–4 liefern reproduzierbare Quellen, Text und Layout, aber keine fachlich
belegten Versicherungsclaims. Eine LLM-Antwort kann strukturell gültig und trotzdem
falsch sein; ein Quellenzitat beweist nicht die behauptete Interpretation.

## Entscheidungen

1. Additive semantic-1-/travel-1-Modelle; keine Migration oder Umdeutung von Legacy-
   Coverage 0.1.0, pdf-1 oder Parserartefakten 1/2. Money als positive dezimale Strings
   mit CHF und Basis; semantischer Zahlenvergleich über Decimal. Separate Sublimiten.
2. Drei Deckungsstatus: covered, excluded, unknown. Bedingungen und Ausnahmen gehören
   zur Deckungsaussage. conditional würde eine zweite, überlappende Statusdimension
   schaffen und wird nicht eingeführt. Unklare/Widerspruchsfälle sind unknown.
3. Deterministischer, absatzerhaltender Präfixkontext. Originalspannen, Parserkonfig,
   Hashes und ausgelassener Textumfang bleiben explizit. Kein Retrievaldienst.
4. Ein einzelner Extraktionsaufruf, ein optionaler separat instruierter Verifier.
   Kein Agentenframework. OpenAI ist der einzige echte Adapter, optionaler SDK-Extra;
   Standardausführung ist offline. Modellwahl explizit, keine behauptete Deterministik.
5. Rohantwort zuerst im CAS, danach DTO-/Quellenprüfung. Das Modell darf keine
   trusted Verifikationsflags liefern. Unauffindbare/mehrdeutige Zitate produzieren
   review_required, niemals erfundene Spannen. Wortlautprüfung ist keine Fachprüfung.
6. Verifier erfordert Originalkontext, Begründung und erneut kontrollierte Zitate.
   Er liefert ein experimentelles Urteil, überschreibt nichts. Korrekturen sind
   neue Runs mit predecessor_sha256 und demselben Kontext. Explizites Gate hält
   unsichere Claims zurück; fehlende Ausgabe bedeutet niemals excluded.
7. Bestehender append-only Store, neue Collections statt Datenbank. Replay berechnet
   Claim-/Verifierstatus aus Originalkontext und gespeicherten Rohantworten neu;
   importierter Ergebnisstatus besitzt keine Autorität. Keine signierte Authentizität.
8. Konfigurierbare Token-/Kostenreservation pro Versuch, begrenzte Retries und
   Transporttimeouts. Keine versteckten SDK-Retries. Fehlende Usage bleibt unbekannt.
   Harte Ressourcen-/Zeitgrenzen erfordern weiterhin einen isolierten Worker.
9. Neuer unabhängiger Semantik-Goldstandard: 120 annotierte Fälle, zwölf Szenarien,
   72 Entwicklung/48 Holdout nach Produktfamilie. Sprint-3-Goldstandard unverändert.
   Familien teilen derzeit Templates: kein Nachweis sprachlicher Generalisierung.
10. Rules, Mock-Extractor und Mock-Verifier-Gate werden explizit als Offline-Simulation
    verglichen. Keine Live-Qualität oder Verifier-Wirtschaftlichkeit aus Mocks ableiten.

## Folgen und Alternativen

Die kleine synchrone Pipeline ist testbar und auf weitere Ontologien übertragbar.
Keine Vektordatenbank, kein Multi-Agent-Schwarm, keine UI und keine automatische
Produktfreigabe. Exakte Textsuche bevorzugt falsche Reviewfälle gegenüber erfundenen
Quellen; paraphrasierte Zitate werden abgelehnt. Die Baseline ist absichtlich eng.
Ein Verifier mit demselben Modell kann dieselben Fehler wiederholen. Freitextbedingungen,
DE/FR/IT, verschachtelte Ausnahmen, Dokumentprioritäten und Tabellenzuordnung brauchen
fachlich doppelt annotierte Daten und separate Experimente. Aktuell englische,
vereinfachte synthetische AVB mit CHF, kein repräsentativer Schweizer Marktvergleich.

Details: [Extraktion](../LLM_EXTRACTION.md), [Evaluation](../LLM_EVALUATION.md).
