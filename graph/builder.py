"""
graph/builder.py
build_agent() —— 组装并编译 LangGraph 工作流

工作流拓扑（有向无环图）：
    load_data → extract_elements → classify_content → detect_groups → generate_output → END
"""
from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    node_load_data,
    node_extract_elements,
    node_classify_content,
    node_detect_groups,
    node_generate_output,
)


def build_agent():
    """
    构建并编译 LangGraph Agent。

    Returns:
        CompiledGraph: 可调用的 agent（支持 .invoke / .stream / .ainvoke）
    """
    graph = StateGraph(AgentState)

    # ── 注册节点 ──────────────────────────────────────────────
    graph.add_node("load_data",        node_load_data)
    graph.add_node("extract_elements", node_extract_elements)
    graph.add_node("classify_content", node_classify_content)
    graph.add_node("detect_groups",    node_detect_groups)
    graph.add_node("generate_output",  node_generate_output)

    # ── 入口 ──────────────────────────────────────────────────
    graph.set_entry_point("load_data")

    # ── 顺序边 ────────────────────────────────────────────────
    graph.add_edge("load_data",        "extract_elements")
    graph.add_edge("extract_elements", "classify_content")
    graph.add_edge("classify_content", "detect_groups")
    graph.add_edge("detect_groups",    "generate_output")
    graph.add_edge("generate_output",  END)

    return graph.compile()
