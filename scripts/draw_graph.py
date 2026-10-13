"""Draw the agent graph FROM THE CODE, so the picture can never drift from it.

    python -m scripts.draw_graph            # prints a mermaid block
    python -m scripts.draw_graph --write    # also updates docs/graph.mmd

LLM nodes are colored amber, code-only nodes teal.
"""
import pathlib
import sys

from agents.graph import build_graph
from tests.fakes import SectionStore   # structure only; nothing is retrieved

LLM_NODES = {"extract"}
STYLE = """
	classDef llm fill:#FDE68A,stroke:#B45309,color:#1F2937
	classDef code fill:#CCFBF1,stroke:#0E7C86,color:#1F2937
	class {llm} llm
	class {code} code"""


def mermaid() -> str:
    g = build_graph(SectionStore()).get_graph()
    nodes = [n for n in g.nodes if not n.startswith("__")]
    src = g.draw_mermaid().rstrip()
    return src + STYLE.format(llm=",".join(sorted(LLM_NODES)),
                              code=",".join(sorted(set(nodes) - LLM_NODES)))


if __name__ == "__main__":
    text = mermaid()
    print(text)
    if "--write" in sys.argv:
        pathlib.Path("docs/graph.mmd").write_text(text + "\n", encoding="utf-8")
