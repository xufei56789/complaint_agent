"""
tools/group_detector.py
群诉识别工具函数

群诉定义：不同工单描述同一点位、相同问题。
本模块实现两条识别轨道：
  轨道1（节点内）：位置键 + 问题键联合索引
  轨道2（本模块）：小区/苑/城名聚合
"""
import re
from collections import defaultdict
from typing import Dict, List


# ── 问题关键词 → 问题类型映射 ───────────────────────────────
_ISSUE_MAP = {
    "精装修": "精装修纠纷",
    "供暖":   "供暖问题",
    "暖气":   "供暖问题",
    "房产证": "房产证问题",
    "房本":   "房产证问题",
    "物业":   "物业纠纷",
    "退款":   "退款纠纷",
    "退费":   "退款纠纷",
    "噪音":   "噪音扰民",
    "违建":   "违章建筑",
    "道路":   "道路交通",
    "停车":   "停车问题",
    "电梯":   "电梯问题",
    "渗漏":   "房屋渗漏",
    "漏水":   "房屋渗漏",
    "开发商": "开发商纠纷",
    "装修":   "装修问题",
    "交房":   "开发商纠纷",
}

# 小区名识别正则
_COMMUNITY_PATTERN = r"[^\s，。,]{2,12}(?:小区|苑|城|园|项目|楼盘)"

# 位置键识别正则（优先级从高到低）
_LOCATION_PATTERNS = [
    r"[^\s，。,]{2,15}(?:小区|苑|城|园|里)",
    r"[^\s，。,]{2,12}(?:项目|楼盘)",
    r"[^\s，。,]{2,10}(?:路|街|大道)",
]


def extract_location_key(text: str) -> str:
    """提取用于群诉比对的位置键（取文本前600字中第一个命中）"""
    for pattern in _LOCATION_PATTERNS:
        m = re.search(pattern, text[:600])
        if m:
            return m.group(0).strip()
    return ""


def extract_issue_key(text: str) -> str:
    """提取问题类型键（优先级按 _ISSUE_MAP 顺序）"""
    for kw, issue_type in _ISSUE_MAP.items():
        if kw in text:
            return issue_type
    return "其他"


def detect_community_groups(
    raw_data: List[Dict],
    min_count: int = 3,
) -> Dict[str, List]:
    """
    按小区/苑/城名聚合工单，返回命中 ≥ min_count 的字典。

    Returns:
        {小区名: [工单编号, ...]}
    """
    community_groups: Dict[str, list] = defaultdict(list)

    for record in raw_data:
        text = str(record.get("主要内容", ""))
        communities = re.findall(_COMMUNITY_PATTERN, text[:500])
        for comm in communities[:1]:              # 每条工单只取第一个命中
            community_groups[comm].append(record.get("工单编号"))

    return {
        comm: list(dict.fromkeys(ids))            # 去重但保序
        for comm, ids in community_groups.items()
        if len(set(ids)) >= min_count
    }
