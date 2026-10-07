# Engineering-Regeln für Axiory

- Python 3.12+, src-Layout, uv; Abhängigkeiten in pyproject.toml und uv.lock pflegen.
- Vor Abschluss `uv run pytest`, `uv run ruff check .` und
  `uv run ruff format --check .` ausführen. Fehler und nicht ausgeführte Prüfungen benennen.
- Keine echten Versicherungsdaten vor dem dokumentierten Ingestion-/Provenienz-Gate.
  Tests und Beispiele müssen ausdrücklich synthetisch sein.
- Unbekannte Informationen niemals als Ausschluss oder Nullbetrag darstellen.
- Positive und negative Behauptungen brauchen nachvollziehbare Originalfundstellen.
- Externe/LLM-JSON-Ausgaben an der Grenze mit `model_validate_json` validieren;
  unbekannte Felder ablehnen. Validierung ersetzt keine Quellen-/Fachprüfung.
- Status `source_matched` nur nach Quellenprüfung vergeben; `human_reviewed` braucht
  später einen dokumentierten Reviewprozess. Kein unvalidiertes `model_construct` oder
  `model_copy(update=...)` für externe Daten.
- Keine Schlüssel, Zugangsdaten, Kundendaten oder lokale Umgebungen committen.
- Keine Datenbank, Microservices, Agentenorchestrierung oder Multi-Agent-Schwärme
  ohne begründete neue Anforderungen. Bevorzuge deterministische Funktionen.
- Relevante Architekturentscheidungen als ADR unter docs/adr dokumentieren.
- Bei Schemaänderungen Tests, Dokumentation und Schema-/Ontologieversion prüfen.
