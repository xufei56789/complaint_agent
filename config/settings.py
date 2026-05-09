"""
config/settings.py
全局配置：API Key、模型名、路径等
"""
import os
from pathlib import Path

# ── 项目路径 ────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
RESULT_DIR = BASE_DIR / "results"

INPUT_FILE  = DATA_DIR / "测试数据.xlsx"
OUTPUT_FILE = RESULT_DIR / "结果.xlsx"

# ── LLM 配置（豆包 / ByteDance Ark）────────────────────────
ARK_API_KEY     = os.getenv("ARK_API_KEY", "")
LLM_BASE_URL    = "https://ark.cn-beijing.volces.com/api/v3"
LLM_MODEL       = "doubao-seed-2-0-lite-260428"   # 模型
LLM_TEMPERATURE = 0.0               # 分类任务设 0，保证确定性

# ── 批处理配置 ───────────────────────────────────────────────
BATCH_SIZE       = 10            # 每批调用 LLM 的工单数
GROUP_MIN_COUNT  = 2             # 群诉最小工单数阈值
