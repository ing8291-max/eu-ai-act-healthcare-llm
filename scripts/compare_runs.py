"""Compare two evaluation runs question by question.

    python scripts/compare_runs.py runs/OLD.jsonl runs/NEW.jsonl
    python scripts/compare_runs.py --latest          # the two newest files in runs/

Prints what changed and exits with code 1 on a regression:
  - any question that became "wrong"         (most important)
  - fewer correct answers or abstentions than before
Token and call changes are reported but never fail the check.
"""
import argparse
import json
import pathlib
import sys

GOOD = {"correct", "abstain_ok"}


def load(path):
    rows, summary = {}, None
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if "summary" in rec:
            summary = rec["summary"]
        else:
            rows[(rec["doc_id"], rec["medication"], rec["kind"])] = rec
    return summary, rows


def compare(old_path, new_path):
    s_old, old = load(old_path)
    s_new, new = load(new_path)
    regressions, changes = [], []

    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        if a is None or b is None:
            changes.append(f"  only in {'new' if a is None else 'old'}: {key}")
            continue
        if a["status"] == b["status"]:
            continue
        line = f"  {key[0]}  {key[1]:<22} {a['status']:>10} -> {b['status']:<10}"
        if b["status"] == "wrong" or (a["status"] in GOOD and b["status"] not in GOOD):
            regressions.append(line + "  <- REGRESSION")
        else:
            changes.append(line)

    print(f"old: {old_path}\nnew: {new_path}\n")
    fields = ["wrong", "correct", "abstain_ok", "missed", "calls_per_q", "tokens_per_q"]
    print(f"  {'':<14}{'old':>8}{'new':>8}")
    for f in fields:
        print(f"  {f:<14}{s_old.get(f, '-'):>8}{s_new.get(f, '-'):>8}")
    print()
    if regressions:
        print("REGRESSIONS")
        print("\n".join(regressions))
    if changes:
        print("other changes")
        print("\n".join(changes))
    if not regressions and not changes:
        print("no question changed status")

    worse_totals = (s_new["wrong"] > s_old["wrong"]
                    or s_new["correct"] < s_old["correct"]
                    or s_new["abstain_ok"] < s_old["abstain_ok"])
    return 1 if (regressions or worse_totals) else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("old", nargs="?")
    p.add_argument("new", nargs="?")
    p.add_argument("--latest", action="store_true", help="compare the two newest files in runs/")
    a = p.parse_args(argv)
    if a.latest:
        files = sorted(pathlib.Path("runs").glob("*.jsonl"))
        if len(files) < 2:
            p.error("need at least two files in runs/")
        old, new = files[-2], files[-1]
    elif a.old and a.new:
        old, new = a.old, a.new
    else:
        p.error("give OLD and NEW, or --latest")
    return compare(old, new)


if __name__ == "__main__":
    sys.exit(main())
