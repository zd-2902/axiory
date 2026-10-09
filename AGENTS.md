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

- Sprint 5: Modellantworten vor fachlicher Verarbeitung unverändert im CAS speichern.
  source_matched beweist nur Fundstellen, keine semantische Wahrheit. Verifier-Urteile
  sind experimentell; nie automatisch als human_reviewed markieren.
- Standardtests/CI und axiory-semantic-eval bleiben offline. Live-Aufrufe benötigen
  explizites --live/allow_live, synthetische Eingaben, bewusste Modellwahl und Preis-/
  Token-/Zeitbudgets. Keine Schlüssel in Konfiguration, Prompts oder Fehlerlogs.
- Layoutgold (Sprint 3) und Semantikgold getrennt halten. Holdout nach Produktfamilien;
  Mock-/Replaymetriken niemals als Live-LLM-Qualität berichten. Messlücken nicht nullen.
- Semantische Korrekturen als neue Runs mit predecessor speichern. Importierte Flags
  durch Replay aus Rohantwort und verifiziertem Originalkontext neu berechnen.
- Bei Provider-/Promptänderungen SDK-Vertragstests mit In-Memory-Transport ausführen;
  niemals für CI live testen. Optional: uv run --extra llm-openai pytest tests/test_openai_adapter.py.
