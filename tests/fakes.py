"""Test doubles shared by several test files. No network, no embeddings."""
from langchain_core.documents import Document

from agents.nodes import DATA_DIR, HEADER_RE


class SectionStore:
    """Stands in for Chroma: returns the whole requested section as one chunk.

    Must look like the REAL chunks from split_by_section: the chunk text starts
    with the section header line ("Discharge Medications:") and char_start points
    at that header. (10/13: a header-less version made the real LLM answer
    found=false, because the prompt names a section it could not see.)
    Same filter format as the real store: {"$and": [{"doc_id": ...}, {"section": ...}]}
    """
    def similarity_search_with_score(self, query, k=3, filter=None):
        cond = {list(c)[0]: list(c.values())[0] for c in filter["$and"]}
        doc = (DATA_DIR / f"{cond['doc_id']}.txt").read_text(encoding="utf-8")
        heads = list(HEADER_RE.finditer(doc))
        for i, m in enumerate(heads):
            if m.group(1) == cond["section"]:
                start = m.start()
                end = heads[i + 1].start() if i + 1 < len(heads) else len(doc)
                text = doc[start:end].rstrip()
                meta = {"doc_id": cond["doc_id"], "section": cond["section"],
                        "char_start": start, "char_end": start + len(text)}
                return [(Document(page_content=text, metadata=meta), 0.5)]
        return []
