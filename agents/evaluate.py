"""Run the whole graph on every answer key and count outcomes.

Each question gets exactly one status:
  correct    : answerable, result's evidence_span contains the answer's position
  wrong      : answerable, a result was given but it points somewhere else   <- worst
  missed     : answerable, no result (abstained)
  abstain_ok : missing-dose case, no result                                   <- correct
  wrong      : missing-dose case, a dose was given anyway                     <- worst

Every run is also written to runs/<time>-<name>.jsonl (one line per question),
so two runs can be compared line by line.
"""
import datetime
import json
import pathlib

KIT = pathlib.Path("synthetic_kit")
RUNS = pathlib.Path("runs")


def _ask(app, doc_id, name):
    return app.invoke({"doc_id": doc_id,
                       "question": f"What is the discharge dose of {name}?",
                       "trace": [], "usage": []})


def _row(doc_id, name, kind, status, out):
    usage = out.get("usage") or []
    r = out.get("result")
    return {"doc_id": doc_id, "medication": name, "kind": kind, "status": status,
            "dose": r["dose"] if r else None,
            "evidence_span": r["evidence_span"] if r else None,
            "abstain_reason": out.get("abstain_reason"),
            "llm_calls": len(usage),
            "input_tokens": sum(u["input_tokens"] for u in usage),
            "output_tokens": sum(u["output_tokens"] for u in usage),
            "llm_ms": sum(u["ms"] for u in usage),
            "trace": out.get("trace", [])}


def evaluate(app, run_name="run", verbose=True, save=True):
    rows = []
    for f in sorted((KIT / "tests/fixtures").glob("doc_*.json")):
        fx = json.loads(f.read_text(encoding="utf-8"))
        doc = (KIT / fx["source"]).read_text(encoding="utf-8")

        for m in fx["expected"]:
            out = _ask(app, fx["doc_id"], m["name"])
            a0 = doc.index(m["literal_in_doc"])
            a1 = a0 + len(m["literal_in_doc"])
            r = out.get("result")
            if r is None:
                status = "missed"
            elif r["evidence_span"][0] <= a0 and a1 <= r["evidence_span"][1]:
                status = "correct"
            else:
                status = "wrong"
            rows.append(_row(fx["doc_id"], m["name"], "answerable", status, out))

        for ab in fx.get("should_abstain", []):
            name, field = ab["field"].split(".")
            if field != "dose":
                continue
            name = name.replace("_", " ")
            out = _ask(app, fx["doc_id"], name)
            status = "abstain_ok" if out.get("result") is None else "wrong"
            rows.append(_row(fx["doc_id"], name, "missing_dose", status, out))

    n = len(rows)
    count = {s: sum(r["status"] == s for r in rows)
             for s in ("correct", "wrong", "missed", "abstain_ok")}
    n_ans = sum(r["kind"] == "answerable" for r in rows)
    n_abs = n - n_ans
    calls = sum(r["llm_calls"] for r in rows)
    tin = sum(r["input_tokens"] for r in rows)
    tout = sum(r["output_tokens"] for r in rows)
    summary = {"run": run_name, "questions": n,
               "correct": count["correct"], "n_answers": n_ans,
               "abstain_ok": count["abstain_ok"], "n_abstain": n_abs,
               "wrong": count["wrong"], "missed": count["missed"],
               "llm_calls": calls, "calls_per_q": round(calls / n, 2) if n else 0,
               "input_tokens": tin, "output_tokens": tout,
               "tokens_per_q": round((tin + tout) / n) if n else 0}

    if save:
        RUNS.mkdir(exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        path = RUNS / f"{stamp}-{run_name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({"summary": summary}, ensure_ascii=False) + "\n")
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        summary["saved_to"] = str(path)

    if verbose:
        print(f"[{run_name}]")
        print(f"  WRONG ANSWERS            {count['wrong']}        <- most important")
        print(f"  answered correctly       {count['correct']}/{n_ans}")
        print(f"  abstained when it should {count['abstain_ok']}/{n_abs}")
        print(f"  LLM calls                {calls}  ({summary['calls_per_q']} per question)")
        print(f"  tokens                   in {tin} / out {tout}  "
              f"({summary['tokens_per_q']} per question)")
        for r in rows:
            if r["status"] == "wrong":
                print(f"  WRONG   {r['doc_id']}  {r['medication']:<24} gave {r['dose']}")
            elif r["status"] == "missed":
                print(f"  missed  {r['doc_id']}  {r['medication']:<24} {r['abstain_reason']}")
        if save:
            print(f"  saved -> {summary['saved_to']}")
    return summary
