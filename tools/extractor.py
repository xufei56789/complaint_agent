"""
tools/extractor.py
LangChain Tool 工具函数：四要素提取 + 规则分类

所有函数均为纯函数（无副作用），可单独测试。
生产建议：extract_* 系列函数由 LLM 替换（见 nodes.py 中 USE_LLM 开关）。
"""
import re
from typing import Dict

from config.classification import CLASSIFICATION_SYSTEM

# ============================================================
# 时间提取
# ============================================================
_TIME_PATTERNS = [
    r"\d{4}年\d{1,2}月\d{1,2}日",
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
    r"\d{4}年\d{1,2}月",
    r"[去今明前]年|[上本下]个?月|[昨今明]天|[上本下]周",
    r"最近|目前|当前|现在",
    r"\d{4}年",
]


def extract_time(text: str) -> str:
    """提取时间要素，优先精确日期，其次年份，再次时态词"""
    for pattern in _TIME_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            return "、".join(list(dict.fromkeys(matches))[:3])
    return "未明确"


# ============================================================
# 地点提取
# ============================================================
_ADDR_PATTERNS = [
    r"[^\s，。,]{2,10}(?:小区|苑|城|园|里|街|路|大道|广场)",
    r"[^\s，。,]{2,10}(?:医院|学校|公司|中心|市场)",
    r"[^\s，。,]{2,8}(?:镇|村|社区)",
]


def extract_location(text: str) -> str:
    """提取地点要素：优先具名地址，其次返回脱敏标记"""
    locations = []
    for p in _ADDR_PATTERNS:
        found = re.findall(p, text[:400])
        locations.extend(found[:2])

    if locations:
        return "、".join(list(dict.fromkeys(locations))[:3])

    if re.search(r"\[(?:门牌号|区名)\]", text):
        return "含地址信息（已脱敏）"
    return "未明确"


# ============================================================
# 人物提取
# ============================================================
def extract_person(text: str) -> str:
    """提取人物要素：投诉主体 + 被投诉方"""
    persons = []

    # 被投诉方（公司/机构）
    subjects = re.findall(r"[^\s，。]{2,12}(?:公司|开发商|物业|平台|银行|医院|学校)", text[:500])
    persons.extend(subjects[:2])

    # 投诉方
    citizen = re.findall(r"(?:市民|业主|居民|用户|投诉人)", text[:100])
    if citizen:
        persons.insert(0, citizen[0])

    if persons:
        return "、".join(list(dict.fromkeys(persons))[:3])
    return "市民"


# ============================================================
# 事件提取
# ============================================================
_CLEAN_PATTERNS = [
    (r"工单来源：.*?={5,}", ""),
    (r"留言标题：|留言原文：", ""),
    (r"\[(?:区名|门牌号|手机号)\]", ""),
]

_DEMAND_PATTERNS = [
    r"要求(.{5,30})[，。,]",
    r"诉求[：:]\s*(.{5,50})",
    r"(?:来电|来访)反映(.{5,40})[问题。，]",
    r"投诉(.{5,40})[问题。，,]",
    r"(?:申请|请求)(.{5,30})[，。,]",
]


def extract_event(text: str) -> str:
    """提取事件要素：核心诉求描述（≤80字）"""
    clean = text
    for pat, rep in _CLEAN_PATTERNS:
        clean = re.sub(pat, rep, clean)
    clean = clean.strip()[:200]

    for p in _DEMAND_PATTERNS:
        m = re.search(p, clean)
        if m:
            return m.group(1).strip()[:80]

    return clean[:80].replace("\n", " ")


# ============================================================
# 四级分类（规则模式）
# ============================================================
def classify_ticket(text: str) -> Dict[str, str]:
    """
    基于关键词匹配对工单进行四级分类。
    返回：{一级分类, 二级分类, 三级分类, 四级分类}
    生产环境建议替换为 LLM 调用（见 nodes.py）。
    """
    best_match = None
    best_score = 0

    for l1, l2_dict in CLASSIFICATION_SYSTEM.items():
        for l2, l3_dict in l2_dict.items():
            for l3, kws in l3_dict.items():
                score = sum(1 for kw in kws if kw in text)
                if score > best_score:
                    best_score = score
                    best_match = (l1, l2, l3, kws)

    if best_match and best_score > 0:
        l1, l2, l3, kws = best_match
        matched = [kw for kw in kws if kw in text]
        l4 = matched[0] + "类诉求" if matched else l3 + "投诉"
        return {"一级分类": l1, "二级分类": l2, "三级分类": l3, "四级分类": l4}

    return {"一级分类": "其他诉求", "二级分类": "一般投诉", "三级分类": "待分类", "四级分类": "其他"}
