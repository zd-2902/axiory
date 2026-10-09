# Synthetischer Semantik-Goldstandard v1

120 explizit annotierte Fälle in gold-v1.json: zwölf Szenarien pro Produktfamilie,
family-0 bis family-5 Entwicklung (72), family-6 bis family-9 Holdout (48).
Quelltexte, erwartete Status-/Limit-/Bedingungs-/Ausschlusswerte, Sublimiten,
Beleganker und Begründungen wurden gemeinsam als synthetische Szenarien verfasst;
sie werden nicht aus Parser- oder Modellausgaben abgeleitet. Keine echten AVB.

Englische vereinfachte Vertragsklauseln und CHF, kein fachlich doppelt annotiertes
Schweizer Sprach-/Marktkorpus. Alle Familien teilen Szenariotemplates; Beträge und
Coverage-Kategorien variieren. Der Holdout trennt Produkte, nicht Templatefamilien.
Nicht für Generalisierungs- oder Produktionsfreigabe verwenden. Goldänderungen
versionieren und unabhängig von Modellfehlern reviewen. Sprint-3-Gold bleibt separat.

PDFs erzeugt axiory.evaluation.semantic.pdf deterministisch zur Laufzeit. Keine
PDF-Binärdateien oder Schlüssel in Git. Reports/Rohantworten/Stores sind unter
datasets/evaluation-semantic ignoriert und in CI als temporäre Artefakte verfügbar.
