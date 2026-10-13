"""compare_runs must flag a new wrong answer and a lost correct answer as regressions."""
import json

from scripts.compare_runs import compare


def _run(path, statuses):
    s = {"wrong": 0, "correct": 0, "abstain_ok": 0, "missed": 0, "calls_per_q": 1.0, "tokens_per_q": 400}
    rows = []
    for (doc, med, kind), st in statuses.items():
        s[st] += 1
        rows.append({"doc_id": doc, "medication": med, "kind": kind, "status": st})
    path.write_text("\n".join(json.dumps(x) for x in [{"summary": s}] + rows), encoding="utf-8")
    return path


BASE = {("doc_02", "omeprazole", "answerable"): "correct",
        ("doc_05", "gabapentin", "missing_dose"): "abstain_ok"}


def test_same_results_pass(tmp_path):
    assert compare(_run(tmp_path / "a.jsonl", BASE), _run(tmp_path / "b.jsonl", BASE)) == 0


def test_new_wrong_answer_fails(tmp_path):
    worse = {**BASE, ("doc_05", "gabapentin", "missing_dose"): "wrong"}
    assert compare(_run(tmp_path / "a.jsonl", BASE), _run(tmp_path / "b.jsonl", worse)) == 1


def test_correct_to_missed_fails(tmp_path):
    worse = {**BASE, ("doc_02", "omeprazole", "answerable"): "missed"}
    assert compare(_run(tmp_path / "a.jsonl", BASE), _run(tmp_path / "b.jsonl", worse)) == 1


def test_missed_to_correct_passes(tmp_path):
    before = {**BASE, ("doc_02", "omeprazole", "answerable"): "missed"}
    assert compare(_run(tmp_path / "a.jsonl", before), _run(tmp_path / "b.jsonl", BASE)) == 0
