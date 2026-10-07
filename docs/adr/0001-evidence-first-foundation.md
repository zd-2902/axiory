# ADR 0001: Schlankes, evidenzorientiertes Python-Fundament

Status: angenommen. Datum: 2026-10-07.

## Kontext

Der MVP benötigt nachvollziehbare Versicherungsbehauptungen, bevor automatisierte
Extraktion oder Agenten Mehrwert liefern. Fachliche Wahrheit ist nicht durch ein
plausibles LLM-Ergebnis oder reine Schema-Konformität garantiert.

## Entscheidung

Ein Python-3.12+-Paket im src-Layout, uv samt Lockfile, Pydantic 2, pytest und Ruff.
CLI und reine Funktionen statt Services/Datenbank/Agenten. Synthetische Daten bleiben
die einzige Datenbasis bis zur getesteten Ingestion. Drei Deckungszustände vermeiden
die Gleichsetzung von unbekannt und ausgeschlossen. Evidenzpflicht für positive und
negative Aussagen, Dokumenthashes und genaue Textspannen ermöglichen Rückverfolgung.
Decimal statt Float für Geld; Währung und Bezugsgrösse sind explizit.

## Alternativen und Konsequenzen

Unvalidierte Dictionaries wären kürzer, aber fehleranfällig an LLM-/Importgrenzen.
Boolesche Deckung würde Wissenslücken vernichten. Datenbank und Multi-Agent-System
würden vor validiertem Datenfluss zusätzliche Zustände und Fehlerquellen einführen.
Das Paket bleibt leicht testbar; persistente IDs, PDF-Textzuordnung und Review-Audit
müssen später ergänzt werden. Quellenabgleich ist ausdrücklich keine semantische
Verifikation. Die Ontologie 0.1.0 ist provisorisch und nicht fachlich freigegeben.
