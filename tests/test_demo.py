import json
import subprocess
import sys

import pytest

from axiory.demo import build_demo
from axiory.models import Claim, Document, InsuranceProduct, Insurer
from axiory.provenance import verify_source


def test_demo_deterministic_and_all_assertions_traceable():
    demo = build_demo()
    assert demo == build_demo()
    insurers = {Insurer.model_validate(x).id for x in demo["insurers"]}
    products = {InsuranceProduct.model_validate(x).id for x in demo["products"]}
    assert all(x["insurer_id"] in insurers for x in demo["products"])
    documents = {x["id"]: Document.model_validate(x) for x in demo["documents"]}
    assert len(demo["claims"]) == 6
    assert len({x["id"] for x in demo["claims"]}) == 6
    for payload in demo["claims"]:
        claim = Claim.model_validate(payload)
        assert claim.product_id in products
        if claim.coverage.status == "unknown":
            assert claim.unknown_reason
            assert claim.verification == "unverified"
            continue
        doc = documents[claim.evidence[0].document_id]
        assert doc.synthetic
        verify_source(claim, doc, demo["sources"][doc.id].encode("utf-8"))
        assert claim.verification == "source_matched"
    limits = [x["limit_amount"] for x in demo["comparison"] if x["status"] == "covered"]
    assert limits == ["5000", "8000"]


@pytest.mark.parametrize("corruption", ["bytes", "product", "document", "quote", "empty"])
def test_source_corruption_rejected(corruption):
    demo = build_demo()
    payload = demo["claims"][0]
    doc_payload = demo["documents"][0]
    source = demo["sources"][doc_payload["id"]].encode("utf-8")
    if corruption == "bytes":
        source += b"tampered"
    elif corruption == "product":
        doc_payload["product_id"] = "other-product"
    elif corruption == "document":
        payload["evidence"][0]["document_id"] = "other-document"
    elif corruption == "quote":
        quote = payload["evidence"][0]["quote"]
        payload["evidence"][0]["quote"] = "X" * len(quote)
    else:
        payload = demo["claims"][2]
    with pytest.raises(ValueError):
        verify_source(Claim.model_validate(payload), Document.model_validate(doc_payload), source)


@pytest.mark.parametrize("command", [[sys.executable, "-m", "axiory.demo"], ["axiory-demo"]])
def test_cli(command):
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == build_demo()
    assert result.stderr == ""
