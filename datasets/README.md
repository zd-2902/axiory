# Datenregeln

Ausschliesslich synthetische Daten. Die Text-Fixtures stehen in src/axiory/demo.py,
PDF-Testdokumente werden durch tests/pdf_fixtures.py zur Laufzeit erzeugt.
Keine echten Versicherungsunterlagen, personenbezogenen Daten oder Zugangsdaten ablegen.

Lokale PDF-Ingestion unter datasets/ingestion/ speichern. Dieser Ordner, raw/ und
processed/ sind von Git ausgeschlossen; auch *.pdf wird ignoriert. Der Store enthält
Originalbytes und versionierte JSON-Artefakte. Fehlerhafte/leere Originale werden
ebenfalls aufbewahrt; keine automatische Löschung. Details: docs/INGESTION.md.

Echte Daten erfordern weiterhin das noch offene Gate in docs/ROADMAP.md.
