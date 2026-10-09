# ruff: noqa: E501
"""Authoring tool: explicitly regenerate/review/freeze a NEW synthetic corpus version before live use.

No tested extractor, parser or verifier is imported. Annotations are authored scenario semantics,
not independent professional annotations. Never run this to fit observed model errors.
"""

import json
from hashlib import sha256
from pathlib import Path

LABELS = {
    "de": [
        "Annullierung",
        "Reiseabbruch",
        "Reisegepäck",
        "Medizinische Assistance",
        "Mietwagen-Selbstbehalt",
    ],
    "fr": [
        "Annulation",
        "Interruption du voyage",
        "Bagages",
        "Assistance médicale",
        "Franchise du véhicule de location",
    ],
    "it": [
        "Annullamento",
        "Interruzione del viaggio",
        "Bagaglio",
        "Assistenza medica",
        "Franchigia del veicolo a noleggio",
    ],
}
CODES = ["cancellation", "interruption", "baggage", "medical_assistance", "rental_car_deductible"]
KINDS = [
    "clear",
    "exclusion",
    "negation",
    "exception",
    "conditional",
    "sublimit",
    "deductible",
    "basis",
    "ambiguity",
    "contradiction",
    "table",
    "cross_page",
]
# Different syntactic forms and document organisation across splits; no template is reused.
TEXT = {
    "de": {
        "dev": {
            "clear": ["{label} ist versichert. Die Limite beträgt CHF {amount} pro Ereignis."],
            "exclusion": ["{label} ist ausdrücklich nicht versichert."],
            "negation": [
                "Ein Ausschluss der Leistung {label} besteht nicht; die Leistung ist gedeckt."
            ],
            "exception": [
                "{label} ist ausgeschlossen, ausser bei einem Notfall.",
                "Im Notfall besteht Deckung nur mit ärztlichem Zeugnis.",
            ],
            "conditional": [
                "{label} ist versichert, sofern eine vorgängige Genehmigung vorliegt.",
                "Es gilt eine Limite von CHF {amount} pro Person und Reise.",
            ],
            "sublimit": [
                "Reisegepäck ist bis CHF {amount} pro Ereignis versichert.",
                "Für Elektronik gilt innerhalb dieser Limite eine Sublimite von CHF 200 pro Gegenstand.",
            ],
            "deductible": [
                "{label} ist bis CHF {amount} pro Ereignis gedeckt.",
                "Der Selbstbehalt beträgt CHF 100 pro Ereignis; er ist keine zusätzliche Limite.",
            ],
            "basis": [
                "{label} ist gedeckt. Über alle Ereignisse zusammen gilt CHF {amount} pro Jahr."
            ],
            "ambiguity": [
                "{label} kann je nach nicht näher beschriebenem Sachverhalt gedeckt sein.",
                "Weder Zusage noch Ausschluss lassen sich daraus eindeutig ableiten.",
            ],
            "contradiction": [
                "Abschnitt A: {label} ist versichert.",
                "Abschnitt B: {label} ist nicht versichert. Eine Vorrangregel fehlt.",
            ],
            "table": [
                "Die Tabelle benennt die versicherten Leistungen.",
                "Leistung | CHF-Limite | Bezugsgrösse",
                "{label} | {amount} | pro Ereignis",
                "Zusatzleistung | 9000 | pro Jahr",
            ],
            "cross_page": [
                "{label} ist bis CHF {amount} pro Ereignis versichert.",
                "Die Voraussetzung auf der folgenden Seite gehört zu dieser Deckung.",
                "PAGE",
                "Diese Deckung setzt eine vorgängige Genehmigung voraus.",
            ],
        },
        "holdout": {
            "clear": [
                "Leistungszusage für {label}:",
                "Je Schadenereignis übernehmen wir Kosten höchstens bis CHF {amount}.",
            ],
            "exclusion": [
                "Vom Leistungsumfang ausgenommen bleibt der Bereich {label}.",
                "Hierfür wird keinerlei Versicherungsschutz gewährt.",
            ],
            "negation": [
                "Für {label} wäre die Aussage 'kein Versicherungsschutz' falsch.",
                "Vereinbart ist ausdrücklich eine Deckung ohne hier genannte Höchstsumme.",
            ],
            "exception": [
                "Notfälle mit ärztlicher Bescheinigung begründen Versicherungsschutz für {label}.",
                "Ausserhalb dieser Ausnahme sind sämtliche übrigen Ereignisse ausgeschlossen.",
            ],
            "conditional": [
                "Eine Genehmigung muss vor dem Ereignis eingeholt werden.",
                "Nur dann werden für {label} bis CHF {amount} je versicherter Person und Reise erstattet.",
            ],
            "sublimit": [
                "Im Baustein Reisegepäck zahlen wir je Schadenereignis maximal CHF {amount}.",
                "Elektronik: je Gegenstand höchstens CHF 200, als Teilbetrag der genannten Gesamtsumme.",
            ],
            "deductible": [
                "Bei {label} verbleiben je Schadenereignis CHF 100 beim Versicherten.",
                "Die zugesagte Deckung hat davon getrennt eine Obergrenze von CHF {amount} je Ereignis.",
            ],
            "basis": [
                "Für den Baustein {label} wird Versicherungsschutz zugesagt.",
                "Sämtliche Zahlungen eines Versicherungsjahres sind zusammen auf CHF {amount} begrenzt.",
            ],
            "ambiguity": [
                "Ob für {label} eine Leistung vereinbart ist, richtet sich nach einer fehlenden Anlage.",
                "Der vorliegende Text legt den Deckungsstatus nicht fest.",
            ],
            "contradiction": [
                "Zusageblatt: Für {label} gilt Versicherungsschutz.",
                "Nachtragsblatt: Für denselben Bereich entfällt jeder Versicherungsschutz.",
                "Beide Blätter sind gleichrangig; es gibt keine Auflösung dieses Widerspruchs.",
            ],
            "table": [
                "Erstattungsplan; nur nachfolgend aufgeführte Positionen sind eingeschlossen.",
                "Position | Bezugszeitraum | Maximalbetrag CHF",
                "Zusatzleistung | Versicherungsjahr | 9000",
                "{label} | einzelnes Ereignis | {amount}",
            ],
            "cross_page": [
                "Eine Genehmigung ist vorab zwingend einzuholen; siehe Zusage auf dem nächsten Blatt.",
                "PAGE",
                "Unter dieser Voraussetzung ist {label} gedeckt.",
                "Die Erstattung endet je Schadenereignis bei CHF {amount}.",
            ],
        },
    },
    "fr": {
        "dev": {
            "clear": ["{label} est couvert. La limite est de CHF {amount} par événement."],
            "exclusion": ["{label} est expressément exclu de la couverture."],
            "negation": [
                "{label} ne fait pas l'objet d'une exclusion; cette prestation est couverte."
            ],
            "exception": [
                "{label} est exclu, sauf en cas d'urgence.",
                "En cas d'urgence, la couverture exige un certificat médical.",
            ],
            "conditional": [
                "{label} est couvert sous réserve d'une autorisation préalable.",
                "La limite est de CHF {amount} par personne et par voyage.",
            ],
            "sublimit": [
                "Les bagages sont couverts jusqu'à CHF {amount} par événement.",
                "Pour l'électronique, une sous-limite de CHF 200 par objet s'applique dans cette limite.",
            ],
            "deductible": [
                "{label} est couvert jusqu'à CHF {amount} par événement.",
                "La franchise est de CHF 100 par événement, distincte de la limite de couverture.",
            ],
            "basis": [
                "{label} est couvert. Le total de tous les événements est limité à CHF {amount} par année."
            ],
            "ambiguity": [
                "{label} pourrait être couvert selon des circonstances non précisées.",
                "Aucune conclusion certaine sur l'inclusion ou l'exclusion n'est possible.",
            ],
            "contradiction": [
                "Article A: {label} est couvert.",
                "Article B: {label} est exclu. Aucune règle de priorité n'est définie.",
            ],
            "table": [
                "Les prestations assurées figurent dans le tableau.",
                "Prestation | Limite CHF | Base",
                "{label} | {amount} | par événement",
                "Prestation annexe | 9000 | par année",
            ],
            "cross_page": [
                "{label} est couvert jusqu'à CHF {amount} par événement.",
                "La condition de la page suivante fait partie de cette couverture.",
                "PAGE",
                "Cette couverture exige une autorisation préalable.",
            ],
        },
        "holdout": {
            "clear": [
                "Engagement relatif à la prestation {label}:",
                "Pour chaque sinistre, les frais sont pris en charge à concurrence de CHF {amount}.",
            ],
            "exclusion": [
                "Le poste {label} demeure hors du champ des garanties.",
                "Aucune prestation assurée ne peut être demandée pour ce poste.",
            ],
            "negation": [
                "Qualifier {label} de prestation non assurée serait inexact.",
                "Le contrat accorde explicitement cette garantie sans montant maximal indiqué ici.",
            ],
            "exception": [
                "Une urgence attestée par un médecin ouvre droit à la garantie {label}.",
                "Tous les événements ne relevant pas de cette exception restent exclus.",
            ],
            "conditional": [
                "L'accord doit être obtenu avant la survenance de l'événement.",
                "A cette seule condition, {label} est remboursé jusqu'à CHF {amount} pour chaque assuré et voyage.",
            ],
            "sublimit": [
                "La garantie bagages prévoit un plafond global de CHF {amount} pour chaque sinistre.",
                "La part électronique ne peut dépasser CHF 200 pour chaque objet; elle est incluse dans le plafond.",
            ],
            "deductible": [
                "Au titre de {label}, CHF 100 restent à la charge de l'assuré pour chaque sinistre.",
                "La garantie accordée est séparément plafonnée à CHF {amount} pour chaque événement.",
            ],
            "basis": [
                "Le poste {label} bénéficie d'une garantie.",
                "Les remboursements cumulés sur une année d'assurance ne peuvent dépasser CHF {amount}.",
            ],
            "ambiguity": [
                "Le statut de la garantie {label} dépend d'une annexe indisponible.",
                "Ce document ne tranche pas la question de la couverture.",
            ],
            "contradiction": [
                "Fiche de garantie: {label} est inclus.",
                "Avenant: toute garantie pour ce même poste est supprimée.",
                "Les deux textes ont le même rang et aucune clause ne résout leur incompatibilité.",
            ],
            "table": [
                "Barème des remboursements; les positions suivantes bénéficient de la garantie.",
                "Position | Période de référence | Maximum CHF",
                "Prestation annexe | année d'assurance | 9000",
                "{label} | sinistre individuel | {amount}",
            ],
            "cross_page": [
                "L'accord doit impérativement être obtenu au préalable; la garantie suit au prochain feuillet.",
                "PAGE",
                "Sous cette condition, la prestation {label} est assurée.",
                "Pour chaque sinistre, le remboursement ne dépasse pas CHF {amount}.",
            ],
        },
    },
    "it": {
        "dev": {
            "clear": ["{label} è coperto. Il limite è CHF {amount} per evento."],
            "exclusion": ["{label} è espressamente escluso dalla copertura."],
            "negation": ["{label} non è oggetto di esclusione; questa prestazione è coperta."],
            "exception": [
                "{label} è escluso, salvo in caso di emergenza.",
                "In caso di emergenza la copertura richiede un certificato medico.",
            ],
            "conditional": [
                "{label} è coperto a condizione che vi sia un'autorizzazione preventiva.",
                "Il limite è CHF {amount} per persona e per viaggio.",
            ],
            "sublimit": [
                "Il bagaglio è coperto fino a CHF {amount} per evento.",
                "Per l'elettronica vale un sottolimite di CHF 200 per oggetto compreso nel limite totale.",
            ],
            "deductible": [
                "{label} è coperto fino a CHF {amount} per evento.",
                "La franchigia è CHF 100 per evento, distinta dal limite della copertura.",
            ],
            "basis": [
                "{label} è coperto. La somma di tutti gli eventi è limitata a CHF {amount} per anno."
            ],
            "ambiguity": [
                "{label} potrebbe essere coperto in circostanze non specificate.",
                "Non si può concludere con certezza né l'inclusione né l'esclusione.",
            ],
            "contradiction": [
                "Articolo A: {label} è coperto.",
                "Articolo B: {label} è escluso. Non è indicata alcuna regola di prevalenza.",
            ],
            "table": [
                "La tabella indica le prestazioni assicurate.",
                "Prestazione | Limite CHF | Base",
                "{label} | {amount} | per evento",
                "Prestazione accessoria | 9000 | per anno",
            ],
            "cross_page": [
                "{label} è coperto fino a CHF {amount} per evento.",
                "La condizione nella pagina successiva fa parte della copertura.",
                "PAGE",
                "Questa copertura richiede un'autorizzazione preventiva.",
            ],
        },
        "holdout": {
            "clear": [
                "Impegno relativo alla garanzia {label}:",
                "Per ciascun sinistro vengono rimborsate spese fino a un massimo di CHF {amount}.",
            ],
            "exclusion": [
                "La voce {label} rimane estranea alle garanzie contrattuali.",
                "Per questa voce non viene concessa alcuna prestazione assicurativa.",
            ],
            "negation": [
                "Definire {label} una prestazione non assicurata sarebbe inesatto.",
                "Il contratto accorda espressamente tale garanzia senza indicare qui un massimale.",
            ],
            "exception": [
                "Un'emergenza certificata da un medico dà diritto alla garanzia {label}.",
                "Tutti gli eventi estranei a tale eccezione restano esclusi.",
            ],
            "conditional": [
                "Il consenso deve essere ottenuto prima che si verifichi l'evento.",
                "Solo in tal caso {label} viene rimborsato fino a CHF {amount} per ciascun assicurato e viaggio.",
            ],
            "sublimit": [
                "La garanzia bagaglio prevede un massimale complessivo di CHF {amount} per ciascun sinistro.",
                "La quota elettronica non supera CHF 200 per ciascun oggetto ed è inclusa nel massimale.",
            ],
            "deductible": [
                "Per {label}, CHF 100 rimangono a carico dell'assicurato per ciascun sinistro.",
                "La garanzia concessa ha separatamente un tetto di CHF {amount} per ciascun evento.",
            ],
            "basis": [
                "Alla voce {label} è accordata una garanzia.",
                "I rimborsi cumulati in un anno assicurativo non possono superare CHF {amount}.",
            ],
            "ambiguity": [
                "Lo stato della garanzia {label} dipende da un allegato non disponibile.",
                "Questo documento non determina l'esistenza della copertura.",
            ],
            "contradiction": [
                "Scheda di garanzia: {label} è incluso.",
                "Appendice: ogni garanzia per la medesima voce viene revocata.",
                "I due testi hanno pari rango e nessuna disposizione risolve il contrasto.",
            ],
            "table": [
                "Prospetto dei rimborsi: le seguenti voci sono comprese nella garanzia.",
                "Voce | Periodo di riferimento | Massimo CHF",
                "Prestazione accessoria | anno assicurativo | 9000",
                "{label} | singolo sinistro | {amount}",
            ],
            "cross_page": [
                "Il consenso deve essere ottenuto preventivamente; la garanzia segue sul prossimo foglio.",
                "PAGE",
                "A tale condizione la prestazione {label} è assicurata.",
                "Per ciascun sinistro il rimborso non supera CHF {amount}.",
            ],
        },
    },
}


def build():
    cases = []
    pilot = []
    for li, language in enumerate(LABELS):
        for split_index, split in enumerate(("dev", "holdout")):
            for n in range(20):
                scenario = KINDS[n % 12]
                k = (n + li) % 5
                if scenario == "sublimit":
                    k = 2
                amount = str(1200 + li * 300 + n * 25 + split_index * 75)
                lines = [
                    x.format(label=LABELS[language][k], amount=amount)
                    for x in TEXT[language][split][scenario]
                ]
                pages = [[]]
                for line in lines:
                    if line == "PAGE":
                        pages.append([])
                    else:
                        pages[-1].append(line)
                status = (
                    "excluded"
                    if scenario == "exclusion"
                    else "unknown"
                    if scenario in ("ambiguity", "contradiction")
                    else "covered"
                )
                monetary = scenario in (
                    "clear",
                    "conditional",
                    "sublimit",
                    "deductible",
                    "basis",
                    "table",
                    "cross_page",
                )
                basis = (
                    "per_person_per_trip"
                    if scenario == "conditional"
                    else "per_year"
                    if scenario == "basis"
                    else "per_event"
                )
                condition = (
                    ["prior_approval"]
                    if scenario in ("conditional", "cross_page")
                    else ["emergency", "medical_certificate"]
                    if scenario == "exception"
                    else []
                )
                family = f"family-{language}-{split_index}-{n // 4}"
                case_id = f"document-{language}-{split_index}-{n:02}"
                cases.append(
                    {
                        "source": {
                            "id": case_id,
                            "product_id": family,
                            "language": language,
                            "coverage_code": CODES[k],
                            "pages": pages,
                            "synthetic": True,
                        },
                        "family": family,
                        "template": f"template-{language}-{split}-{scenario}",
                        "split": split,
                        "scenario": scenario,
                        "difficulty": "simple"
                        if scenario in ("clear", "exclusion")
                        else "hard"
                        if scenario in ("exception", "contradiction", "table", "cross_page")
                        else "moderate",
                        "expected": {
                            "status": status,
                            "amount": amount if monetary else None,
                            "currency": "CHF" if monetary else None,
                            "basis": basis if monetary else None,
                            "conditions": condition,
                            "exclusions": ["non_emergency"] if scenario == "exception" else [],
                            "sublimits": [
                                {
                                    "subject": "electronics",
                                    "amount": "200",
                                    "currency": "CHF",
                                    "basis": "per_item",
                                }
                            ]
                            if scenario == "sublimit"
                            else [],
                            "deductible": {"amount": "100", "currency": "CHF", "basis": "per_event"}
                            if scenario == "deductible"
                            else None,
                            "anchors": [
                                line for line in lines if line != "PAGE" and "|" not in line
                            ]
                            if scenario != "table"
                            else [LABELS[language][k], amount],
                            "rationale": f"Authored {scenario} semantics; no precedence or coverage inferred. "
                            "Single synthetic author, no independent professional review.",
                        },
                    }
                )
                if n // 4 < 4 and n % 4 == (li + n // 4 + split_index * 2) % 4:
                    pilot.append(case_id)
    return {
        "schema_version": "multilingual-gold-1",
        "annotation_status": "single_author_synthetic_not_independently_reviewed",
        "cases": cases,
    }, pilot


if __name__ == "__main__":
    root = Path("datasets/multilingual")
    root.mkdir(parents=True, exist_ok=True)
    corpus, pilot = build()
    raw = (json.dumps(corpus, ensure_ascii=False, indent=2) + "\n").encode()
    canonical = json.dumps(
        corpus, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    (root / "gold-v1.json").write_bytes(raw)
    freeze = {
        "schema_version": "gold-freeze-1",
        "corpus_sha256": sha256(canonical).hexdigest(),
        "file_sha256": sha256(raw).hexdigest(),
        "case_count": len(corpus["cases"]),
        "pilot_ids": pilot,
        "frozen_before_live": True,
        "independent_review_count": 0,
    }
    (root / "freeze-v1.json").write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
    print(
        f"Authored {len(corpus['cases'])} synthetic cases; pilot {len(pilot)}. Review before live."
    )
