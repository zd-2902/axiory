"""Fully synthetic deterministic fixtures; no extraction or network access."""

import json
from hashlib import sha256

from axiory.models import Claim, Coverage, Document, Evidence, InsuranceProduct, Insurer
from axiory.provenance import verify_source


def build_demo() -> dict:
    insurers, products, documents, claims, sources = [], [], [], [], {}
    for suffix, amount in (("a", "5000"), ("b", "8000")):
        insurer = Insurer(id=f"synthetic-{suffix}", name=f"Fiktiv {suffix.upper()}")
        product = InsuranceProduct(
            id=f"travel-{suffix}", insurer_id=insurer.id, name=f"Demo Reise {suffix.upper()}"
        )
        text = (
            f"SYNTHETISCH. Annullierung: CHF {amount} pro Person und Reise bei Krankheit.\n"
            "Gepaeck ist ausgeschlossen.\n"
        )
        source = text.encode("utf-8")
        document = Document(
            id=f"doc-{suffix}",
            product_id=product.id,
            title="Synthetische Bedingungen",
            source_uri=f"synthetic://axiory/{suffix}/conditions-v1.txt",
            sha256=sha256(source).hexdigest(),
            kind="policy_conditions",
            version="1",
        )
        for code, status, quote in (
            ("travel.cancellation", "covered", text.splitlines()[0]),
            ("travel.baggage", "excluded", text.splitlines()[1]),
        ):
            start = text.index(quote)
            coverage = Coverage(
                code=code,
                status=status,
                **(
                    {
                        "limit_amount": amount,
                        "currency": "CHF",
                        "limit_basis": "per_person_per_trip",
                        "conditions": ("bei Krankheit",),
                    }
                    if status == "covered"
                    else {}
                ),
            )
            claim = Claim(
                id=f"{product.id}.{code}",
                product_id=product.id,
                coverage=coverage,
                evidence=(
                    Evidence(
                        id=f"evidence-{suffix}-{code}",
                        document_id=document.id,
                        quote=quote,
                        start_char=start,
                        end_char=start + len(quote),
                        locator=f"line:{1 if start == 0 else 2}",
                    ),
                ),
                method="synthetic_fixture",
                method_version="1",
            )
            verify_source(claim, document, source)
            claims.append(
                Claim.model_validate({**claim.model_dump(), "verification": "source_matched"})
            )
        claims.append(
            Claim(
                id=f"{product.id}.travel.medical",
                product_id=product.id,
                coverage=Coverage(code="travel.medical", status="unknown"),
                method="synthetic_fixture",
                method_version="1",
                unknown_reason="In der synthetischen Quelle nicht beschrieben.",
            )
        )
        insurers.append(insurer)
        products.append(product)
        documents.append(document)
        sources[document.id] = text
    return {
        "synthetic": True,
        "schema_version": "0.1.0",
        "insurers": [x.model_dump(mode="json") for x in insurers],
        "products": [x.model_dump(mode="json") for x in products],
        "documents": [x.model_dump(mode="json") for x in documents],
        "claims": [x.model_dump(mode="json") for x in claims],
        "sources": sources,
        "comparison": [
            {"product_id": claim.product_id, **claim.coverage.model_dump(mode="json")}
            for claim in claims
        ],
    }


def main() -> None:
    print(json.dumps(build_demo(), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
