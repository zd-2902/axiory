# Roadmap

1. **Fundament (dieser Stand):** Paket, Schemata, synthetische Demo, Unit-Tests,
   Lockfile, CI und dokumentierte Grenzen.
2. **Ingestion-/Provenienz-Gate:** zunächst synthetische PDFs und Fehlerfälle nutzen.
   Originalbytes unverändert speichern, SHA-256 prüfen, Quell-URL/Abrufzeit und
   Dokumentversion erfassen; Parserversion, extrahierten Text und Seitenbezug persistieren.
   Referenzen, doppelte IDs, Manipulation, leere/OCR-Quellen und Encoding testen.
   Freigabekriterium: reproduzierbarer Weg von jeder Fundstelle zu Originalbytes,
   dokumentierte Nutzungs-/Speicherregeln und bestandene Integrationstests. Erst dann
   echte öffentliche Dokumente kontrolliert aufnehmen; keine Kundendaten.
3. **Goldstandard und Ontologie:** repräsentative Fälle manuell doppelt annotieren,
   Differenzen klären, Sprach-/Produktversionen trennen, Bedingungen/Sublimiten ergänzen.
4. **Extraktion:** zunächst einfache Baseline, dann optional LLM mit Schema-Validierung,
   Modell-/Promptversion und Kostenmessung. Unsicherheit und Konflikte sichtbar halten.
5. **Vergleich:** nur kompatible Bezugsgrössen und Gültigkeitsstände zusammenstellen;
   Quellenansicht und dokumentierter fachlicher Review vor Produktivfreigabe.

Offen: Lizenz, fachliche Ontologieverantwortung, Reviewprozess und Freigabeschwellen,
zulässige Speicherung öffentlicher Quellen, Mehrsprachigkeit, Versions-/Gültigkeitsmodell.
LLM-Anbieter, Persistenz und UI werden erst anhand dieser Anforderungen entschieden.
