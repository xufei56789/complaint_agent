"""
graph/nodes.py
LangGraph 节点函数（共 5 个）

每个节点签名：(state: AgentState) -> AgentState
节点之间通过 AgentState 传递数据，无直接调用关系。
"""
import json
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import (
    INPUT_FILE, BATCH_SIZE, GROUP_MIN_COUNT,
    LLM_MODEL, ARK_API_KEY, LLM_BASE_URL,
)
from config.classification import CLASSIFICATION_SYSTEM_PROMPT
from graph.state import AgentState
from tools.extractor import extract_event
from tools.group_detector import extract_location_key, extract_issue_key, detect_community_groups
from output.excel_writer import write_excel

_llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=0.0,
    api_key=ARK_API_KEY,
    base_url=LLM_BASE_URL,
)


# ============================================================
# 节点 1：加载数据
# ============================================================
def node_load_data(state: AgentState) -> AgentState:
    print("📂 [节点1] 加载工单数据...")
    df = pd.read_excel(str(INPUT_FILE))
    raw_data = df.to_dict("records")
    print(f"   → 加载成功，共 {len(raw_data)} 条工单")
    return {**state, "raw_data": raw_data}


# ============================================================
# 节点 2：提取四要素
# ============================================================
def node_extract_elements(state: AgentState) -> AgentState:
    print("🔍 [节点2] 提取四要素（时间/地点/人物/事件）...")
    raw_data = state["raw_data"]
    total = len(raw_data)

    batches = [
        (i, raw_data[i : i + BATCH_SIZE])
        for i in range(0, total, BATCH_SIZE)
    ]

    def call_batch(idx: int, batch: list) -> tuple[int, list]:
        batch_input = [
            {"工单编号": r["工单编号"], "主要内容": str(r["主要内容"])[:800]}
            for r in batch
        ]
        prompt = (
            "你是工单分析专家，请从每条工单提取四要素，"
            "以JSON数组返回，每项：{\"工单编号\":..,\"时间\":..,\"地点\":..,\"人物\":..,\"事件\":..}\n"
            f"工单列表：{json.dumps(batch_input, ensure_ascii=False)}"
        )
        response = _llm.invoke([HumanMessage(content=prompt)])
        return idx, json.loads(response.content)

    results_map: dict[int, list] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(call_batch, idx, batch): idx for idx, batch in batches}
        for future in as_completed(futures):
            idx, parsed = future.result()
            results_map[idx] = parsed
            done = sum(len(v) for v in results_map.values())
            print(f"   → 已处理 {done}/{total} 条")

    results = [item for idx in sorted(results_map) for item in results_map[idx]]
    print(f"   → 四要素提取完成，共 {len(results)} 条")
    return {**state, "four_elements": results}


# ============================================================
# 节点 3：四级分类
# ============================================================
def node_classify_content(state: AgentState) -> AgentState:
    print("📊 [节点3] 执行四级内容分类...")
    raw_data = state["raw_data"]
    total = len(raw_data)

    batches = [
        (i, raw_data[i : i + BATCH_SIZE])
        for i in range(0, total, BATCH_SIZE)
    ]

    def call_batch(idx: int, batch: list) -> tuple[int, list]:
        batch_input = [
            {"工单编号": r["工单编号"], "主要内容": str(r["主要内容"])[:600]}
            for r in batch
        ]
        prompt_text = (
            "请对以下工单逐条分类，以JSON数组返回，"
            "每项：{\"工单编号\":..，\"一级分类\":..，\"二级分类\":..，\"三级分类\":..，\"四级分类\":..}\n"
            f"工单列表：{json.dumps(batch_input, ensure_ascii=False)}"
        )
        response = _llm.invoke([
            SystemMessage(content=CLASSIFICATION_SYSTEM_PROMPT),
            HumanMessage(content=prompt_text),
        ])
        return idx, json.loads(response.content)

    results_map: dict[int, list] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(call_batch, idx, batch): idx for idx, batch in batches}
        for future in as_completed(futures):
            idx, parsed = future.result()
            results_map[idx] = parsed
            done = sum(len(v) for v in results_map.values())
            print(f"   → 已分类 {done}/{total} 条")

    results = [item for idx in sorted(results_map) for item in results_map[idx]]
    print(f"   → 分类完成，共 {len(results)} 条")
    l1_counts = Counter(r["一级分类"] for r in results)
    for cat, cnt in l1_counts.most_common():
        print(f"      {cat}: {cnt}条")

    return {**state, "classifications": results}


# ============================================================
# 节点 4：群诉检测
# ============================================================
def node_detect_groups(state: AgentState) -> AgentState:
    print("🔗 [节点4] 检测群诉工单...")
    raw_data = state["raw_data"]

    def track1() -> list:
        groups: dict = defaultdict(list)
        for rec in raw_data:
            t     = str(rec.get("主要内容", ""))
            loc   = extract_location_key(t)
            issue = extract_issue_key(t)
            key   = f"{loc}|{issue}" if loc else ""
            if key:
                groups[key].append(rec)

        complaints, t1_gid = [], 1
        for key, tickets in groups.items():
            if len(tickets) >= GROUP_MIN_COUNT:
                loc, issue = key.split("|", 1)
                for tk in tickets:
                    t = str(tk.get("主要内容", ""))
                    complaints.append({
                        "群诉编号":   f"T1-{t1_gid:03d}",
                        "工单编号":   tk.get("工单编号", ""),
                        "涉及点位":   loc,
                        "共性问题":   issue,
                        "涉及工单数": len(tickets),
                        "事件摘要":   extract_event(t)[:80],
                    })
                t1_gid += 1
        return complaints

    def track2() -> dict:
        return detect_community_groups(raw_data, min_count=3)

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(track1)
        f2 = executor.submit(track2)
        group_complaints: list = f1.result()
        community_groups: dict = f2.result()

    existing = {g["工单编号"] for g in group_complaints}
    gid = len({g["群诉编号"] for g in group_complaints}) + 1

    for comm, ticket_ids in community_groups.items():
        if not any(t for t in ticket_ids if t not in existing):
            continue
        for tid in ticket_ids:
            record = next((r for r in raw_data if r.get("工单编号") == tid), {})
            text   = str(record.get("主要内容", ""))
            if not any(g["工单编号"] == tid and g["涉及点位"] == comm for g in group_complaints):
                group_complaints.append({
                    "群诉编号":   f"T2-{gid:03d}",
                    "工单编号":   tid,
                    "涉及点位":   comm,
                    "共性问题":   extract_issue_key(text),
                    "涉及工单数": len(ticket_ids),
                    "事件摘要":   extract_event(text)[:80],
                })
        gid += 1

    seen, unique = set(), []
    for g in group_complaints:
        k = (g["工单编号"], g["涉及点位"])
        if k not in seen:
            seen.add(k)
            unique.append(g)

    print(f"   → 检测到群诉工单 {len(unique)} 条")
    return {**state, "group_complaints": unique}


# ============================================================
# 节点 5：生成 Excel
# ============================================================
def node_generate_output(state: AgentState) -> AgentState:
    print("[节点5] 生成结果文件...")
    path = write_excel(
        four_elements    = state["four_elements"],
        classifications  = state["classifications"],
        group_complaints = state["group_complaints"],
    )
    print(f"   → 文件已保存至: {path}")
    return {**state, "output_path": path}
