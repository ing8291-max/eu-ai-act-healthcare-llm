"""Grid-search chunk_size / chunk_overlap against the answer keys.

No embeddings, no LLM - every metric is a deterministic string check,
so this runs in seconds and the result does not depend on the model.

Metrics (per setting, over all expected answers in tests/fixtures):
  intact    answer literal sits whole inside at least one chunk
  labeled   that chunk also contains its section header
            (e.g. "Discharge Medications:") - the retriever and the LLM
            need the header to know WHICH list the dose belongs to
  clean     that chunk does NOT also contain "Medications on Admission:"
            - mixing both lists in one chunk invites the old-dose error
  offset_ok every chunk satisfies doc[start:start+len] == chunk text
"""
import json
import pathlib

from langchain_text_splitters import RecursiveCharacterTextSplitter

SIZES = [150, 200, 250, 300, 400, 500, 700, 1000]
OVERLAPS = [0, 50, 100]
ADMISSION = "Medications on Admission:"


def load():
    items = []
    for f in sorted(pathlib.Path("tests/fixtures").glob("doc_*.json")):
        fx = json.loads(f.read_text(encoding="utf-8"))
        doc = pathlib.Path(fx["source"]).read_text(encoding="utf-8")
        items.append((fx, doc))
    return items


def evaluate(items, size, overlap):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size, chunk_overlap=overlap, add_start_index=True
    )
    total = intact = labeled = clean = 0
    offset_bad = 0
    n_chunks = 0
    lengths = []
    for fx, doc in items:
        chunks = splitter.create_documents([doc])
        n_chunks += len(chunks)
        spans = []
        for c in chunks:
            s = c.metadata["start_index"]
            e = s + len(c.page_content)
            lengths.append(len(c.page_content))
            if doc[s:e] != c.page_content:
                offset_bad += 1
            spans.append((s, e, c.page_content))
        for med in fx["expected"]:
            total += 1
            lit = med["literal_in_doc"]
            a0 = doc.index(lit)
            a1 = a0 + len(lit)
            hosts = [t for s, e, t in spans if s <= a0 and a1 <= e]
            if not hosts:
                continue
            intact += 1
            header = med["section"] + ":"
            best = min(hosts, key=len)
            if header in best:
                labeled += 1
            if ADMISSION not in best:
                clean += 1
    return {
        "size": size, "overlap": overlap, "chunks": n_chunks,
        "avg_len": sum(lengths) / len(lengths),
        "intact": intact / total, "labeled": labeled / total,
        "clean": clean / total, "offset_bad": offset_bad, "n": total,
    }


def main():
    items = load()
    rows = [evaluate(items, s, o) for s in SIZES for o in OVERLAPS if o < s]
    print(f"{len(items)} documents, {rows[0]['n']} expected answers\n")
    print(f"{'size':>5} {'ovl':>4} {'chunks':>6} {'avg':>5}  "
          f"{'intact':>7} {'labeled':>8} {'clean':>6} {'offset':>7}")
    for r in rows:
        print(f"{r['size']:>5} {r['overlap']:>4} {r['chunks']:>6} "
              f"{r['avg_len']:>5.0f}  {r['intact']:>7.0%} {r['labeled']:>8.0%} "
              f"{r['clean']:>6.0%} {('ok' if r['offset_bad'] == 0 else r['offset_bad']):>7}")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------
# Section-first splitting: cut at section headers, then size-split only
# sections that are too long. Offsets are re-based onto the full document.
# ---------------------------------------------------------------------
import re
from langchain_core.documents import Document

HEADER_RE = re.compile(r"^([A-Z][A-Za-z /]+):\s*$", re.M)


def split_by_section(doc_text, doc_id, size=500, overlap=50):
    marks = [(m.start(), m.group(1)) for m in HEADER_RE.finditer(doc_text)]
    marks = [(0, "Header")] + marks
    inner = RecursiveCharacterTextSplitter(
        chunk_size=size, chunk_overlap=overlap, add_start_index=True
    )
    out = []
    for i, (start, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(doc_text)
        body = doc_text[start:end].rstrip()
        if not body.strip():
            continue
        for piece in inner.create_documents([body]):
            s = start + piece.metadata["start_index"]   # offset in the FULL document
            e = s + len(piece.page_content)
            text = piece.page_content
            # A long section split in two: repeat the header on the second piece
            # so it still says which list it belongs to. char_start/char_end keep
            # pointing at the original text only.
            if name != "Header" and not text.startswith(name + ":"):
                text = f"{name}:\n{text}"
            out.append(Document(page_content=text, metadata={
                "doc_id": doc_id, "section": name,
                "char_start": s, "char_end": e,
            }))
    return out


def evaluate_sections(items, size, overlap):
    total = intact = labeled = clean = bad = n = 0
    for fx, doc in items:
        chunks = split_by_section(doc, fx["doc_id"], size, overlap)
        n += len(chunks)
        for c in chunks:
            s, e = c.metadata["char_start"], c.metadata["char_end"]
            if doc[s:e] not in c.page_content:
                bad += 1
        for med in fx["expected"]:
            total += 1
            lit = med["literal_in_doc"]
            a0 = doc.index(lit); a1 = a0 + len(lit)
            hosts = [c for c in chunks
                     if c.metadata["char_start"] <= a0 and a1 <= c.metadata["char_end"]]
            if not hosts:
                continue
            intact += 1
            best = min(hosts, key=lambda c: len(c.page_content))
            labeled += (med["section"] + ":") in best.page_content
            clean += ADMISSION not in best.page_content
    return total, intact, labeled, clean, bad, n


if __name__ == "__main__":
    print("\nsection-first splitting")
    print(f"{'size':>5} {'ovl':>4} {'chunks':>6}  {'intact':>7} {'labeled':>8} {'clean':>6} {'offset':>7}")
    for size in [300, 500, 800]:
        t, i, l, c, b, n = evaluate_sections(load(), size, 50)
        print(f"{size:>5} {50:>4} {n:>6}  {i/t:>7.0%} {l/t:>8.0%} {c/t:>6.0%} {('ok' if b == 0 else b):>7}")
