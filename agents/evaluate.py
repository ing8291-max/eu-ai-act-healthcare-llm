"""Run the whole graph on every answer key and count outcomes.

answered : expected answers where the agent emitted a result whose
           evidence_span contains the answer's position in the document
abstained: missing-dose cases (should_abstain *.dose) where the agent
           returned no result
"""
import json
import pathlib

KIT = pathlib.Path("synthetic_kit")


def _ask(app, doc_id, name):
    return app.invoke({"doc_id": doc_id,
                       "question": f"What is the discharge dose of {name}?",
                       "trace": []})


def evaluate(app, verbose=True):
    answered, missed, abstained, wrong = 0, [], 0, []
    for f in sorted((KIT / "tests/fixtures").glob("doc_*.json")):
        fx = json.loads(f.read_text(encoding="utf-8"))
        doc = (KIT / fx["source"]).read_text(encoding="utf-8")

        for m in fx["expected"]:
            out = _ask(app, fx["doc_id"], m["name"])
            a0 = doc.index(m["literal_in_doc"])
            a1 = a0 + len(m["literal_in_doc"])
            r = out.get("result")
            if r and r["evidence_span"][0] <= a0 and a1 <= r["evidence_span"][1]:
                answered += 1
            else:
                missed.append((fx["doc_id"], m["name"], out.get("abstain_reason")))

        for ab in fx.get("should_abstain", []):
            name, field = ab["field"].split(".")
            if field != "dose":
                continue
            name = name.replace("_", " ")
            out = _ask(app, fx["doc_id"], name)
            if out.get("result") is None:
                abstained += 1
            else:
                wrong.append((fx["doc_id"], name, out["result"]["dose"]))

    n_a, n_c = answered + len(missed), abstained + len(wrong)
    if verbose:
        print(f"answered correctly       {answered}/{n_a}")
        print(f"abstained when it should {abstained}/{n_c}")
        for doc_id, name, why in missed:
            print(f"  missed        {doc_id}  {name:<24} {why}")
        for doc_id, name, dose in wrong:
            print(f"  WRONG ANSWER  {doc_id}  {name:<24} gave {dose}")
    return {"answered": answered, "n_answers": n_a, "abstained": abstained,
            "n_abstain": n_c, "missed": missed, "wrong": wrong}