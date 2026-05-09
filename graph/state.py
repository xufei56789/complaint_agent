"""
graph/state.py
AgentState —— 贯穿整个 LangGraph 工作流的共享状态容器

每个节点接收一个 AgentState，返回一个（部分更新的）AgentState。
LangGraph 会自动将返回值合并到全局状态中。
"""
from typing import TypedDict, List, Dict, Optional


class AgentState(TypedDict):
    """LangGraph 状态定义"""

    # ── 原始数据 ──────────────────────────────────────────────
    raw_data: List[Dict]
    """从 Excel 加载的原始工单列表，每项含 工单编号 / 主要内容"""

    # ── 节点2 输出 ────────────────────────────────────────────
    four_elements: List[Dict]
    """
    四要素提取结果，每项结构：
    {
        "工单编号": str,
        "时间": str,
        "地点": str,
        "人物": str,
        "事件": str,
    }
    """

    # ── 节点3 输出 ────────────────────────────────────────────
    classifications: List[Dict]
    """
    四级分类结果，每项结构：
    {
        "工单编号": str,
        "一级分类": str,
        "二级分类": str,
        "三级分类": str,
        "四级分类": str,
    }
    """

    # ── 节点4 输出 ────────────────────────────────────────────
    group_complaints: List[Dict]
    """
    群诉工单（同点位+同问题的多工单聚合），每项结构：
    {
        "群诉编号": str,       # GROUP-001
        "工单编号": str,
        "涉及点位": str,
        "共性问题": str,
        "涉及工单数": int,
        "事件摘要": str,
    }
    """

    # ── 节点5 输出 ────────────────────────────────────────────
    output_path: str
    """生成的 Excel 文件路径"""

    # ── 全局错误信息 ──────────────────────────────────────────
    error: Optional[str]
