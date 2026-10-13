"""Edges: how the nodes are wired together."""
from langgraph.graph import END, START, StateGraph

from .nodes import (MAX_ATTEMPTS, abstain, emit_result, fallback_section, load_document,
                    make_extract, make_retrieve, route_intent, verify_evidence)
from .state import AgentState


def _has_next_section(state: AgentState) -> bool:
    return state["section_idx"] + 1 < len(state["section_plan"])


# ---- conditional edge 1: after retrieve
def after_retrieve(state: AgentState) -> str:
    if state["chunks"]:
        return "extract"
    if _has_next_section(state):
        return "fallback_section"        # nothing close enough here -> next section
    return "abstain"


# ---- conditional edge 2: after verify_evidence
def after_verify(state: AgentState) -> str:
    v = state["verdict"]
    if v == "ok":
        return "emit_result"
    if v in ("span_mismatch", "wrong_section", "name_mismatch") and state["attempts"] < MAX_ATTEMPTS:
        return "extract"                 # wrong citation or wrong section -> try again
    if v == "not_found" and _has_next_section(state):
        return "fallback_section"        # drug not in this section -> next section
    return "abstain"                     # no_dose / multiple_doses / retries or sections used up


def build_graph(vectorstore, threshold=None, mode="A", extractor=None):
    """threshold=None: distance filter off (10/06 system eval: 46/46 vs 41/46 at 0.68).
    mode: "A" retrieved chunks / "D" whole document as context.
    extractor: override the extract node (e.g. nodes.extract_regex or a fake for tests).
    """
    g = StateGraph(AgentState)

    g.add_node("load_document", load_document)
    g.add_node("route_intent", route_intent)
    g.add_node("retrieve", make_retrieve(vectorstore, threshold=threshold))
    g.add_node("fallback_section", fallback_section)
    g.add_node("extract", extractor or make_extract(mode))
    g.add_node("verify_evidence", verify_evidence)
    g.add_node("emit_result", emit_result)
    g.add_node("abstain", abstain)

    g.add_edge(START, "load_document")
    g.add_edge("load_document", "route_intent")
    g.add_edge("route_intent", "retrieve")
    g.add_conditional_edges("retrieve", after_retrieve,
                            ["extract", "fallback_section", "abstain"])
    g.add_edge("fallback_section", "retrieve")
    g.add_edge("extract", "verify_evidence")
    g.add_conditional_edges("verify_evidence", after_verify,
                            ["emit_result", "extract", "fallback_section", "abstain"])
    g.add_edge("emit_result", END)
    g.add_edge("abstain", END)

    return g.compile()
