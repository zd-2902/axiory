# Evaluation

Aktuelle Tests prüfen deterministische Softwareverträge; sie messen **keine** Qualität
realer AVB-Extraktion. Es gibt noch keinen Benchmark und keine Qualitätsbehauptung.

| Dimension | Geplante Messung |
| --- | --- |
| Struktur | Anteil ohne Schemafehler; invalides JSON separat zählen |
| Extraktion | Precision/Recall je Leistung, Ausschluss, Limite und Bedingung |
| Normalisierung | Exakte Ontologiecode-, Betrag-, Währungs- und Basisübereinstimmung |
| Provenienz | Anteil gültiger Hashes/Spannen sowie fachlich stützender Zitate |
| Wissenslücken | Unknown-Recall; insbesondere false excluded bei unbekannten Fällen |
| Vollständigkeit | Fehlende Ausnahmen, Sublimiten und Bedingungen |
| Betrieb | Laufzeit, Kosten und reproduzierbare Modell-/Prompt-/Parserversion |

Goldstandard nach Gate: dokumentversionierte Beispiele, zwei fachliche Annotationen
und geklärte Konflikte. Entwicklungs- und Testsplit auf Produktebene, um ähnliche
Dokumentversionen nicht über beide Splits zu verteilen. DE/FR/IT und schwierige Tabellen,
Negationen, fehlende Informationen und widersprüchliche Dokumente getrennt auswerten.

Prozentwerte mit Nennern und Fallzahlen berichten; unsupported Claims separat zeigen.
Grenzwerte für fachliche Freigabe sind mit Domänenverantwortlichen festzulegen.
Unbelegte Behauptungen und unknown→excluded sind vor Freigabe einzeln zu untersuchen.

Aktuelle Regressionen: Evidenzpflicht, Unknown-Semantik, Limitenkonsistenz, strikte
Offsets, zusätzliche Felder, ungültige Ontologiecodes, manipulierte Quellen und
Referenzen, deterministisches JSON sowie installierter CLI-Einstieg.

## Sprint 2: Ingestion-Regressionen

Synthetische PDFs werden im Test erzeugt, nicht heruntergeladen. Regressionen prüfen
Mehrseitenextraktion, unveränderte Bytes, Unicode/Whitespace, deterministische Hashes,
Seitenreferenzen, Deduplikation, Metadatenrevisionen und unterschiedliche Versionen.
Alle Manifesttypen und Originale werden auf Manipulation geprüft; auch neu gehashte
falsche Extraktionen müssen an der Reproduktion scheitern. Fehlerfälle umfassen
verschlüsselte/kaputte PDFs, null Seiten, leere Seiten, Bilder ohne Text, Vektorgrafik
und einzelne defekte Content-Streams. Teilfehler dürfen andere Seiten nicht verlieren.
I/O-Fehler, falsche Parser-Versionen, ungültige Spannen und importierte Verifikationsflags
sind ebenfalls abgedeckt. Die ursprünglichen Demo-/CLI-Tests bleiben bestehen.

Das ist eine Integritäts- und Vertragsprüfung, kein PDF-Qualitätsbenchmark. Noch offen:
Layoutvergleich, echte Font-/Encoding-Vielfalt, Tabellen, Ressourcenlimits, Quellenechtheit
und fachliche Annotation. Kein success-Status darf als fachliche Vollständigkeit gelten.
