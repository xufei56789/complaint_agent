"""
main.py
程序入口：构建 LangGraph Agent 并执行完整工作流

运行：
    cd complaint_agent
    python main.py

切换 LLM 模式：
    export ARK_API_KEY=<你的豆包 API Key>
    # 修改 graph/nodes.py 中 USE_LLM = True
    python main.py
"""
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（非包模式运行时需要）
sys.path.insert(0, str(Path(__file__).parent))

from graph.builder import build_agent
from graph.state import AgentState


def main() -> None:
    print("=" * 60)
    print("工单智能分析 Agent")
    print("=" * 60)

    agent = build_agent()

    initial_state: AgentState = {
        "raw_data":        [],
        "four_elements":   [],
        "classifications": [],
        "group_complaints":[],
        "output_path":     "",
        "error":           None,
    }

    final_state = agent.invoke(initial_state)

    print("\n" + "=" * 60)
    print("✅ 处理完成！")
    print(f"   四要素:   {len(final_state['four_elements'])} 条")
    print(f"   四级分类: {len(final_state['classifications'])} 条")
    print(f"   群诉工单: {len(final_state['group_complaints'])} 条")
    print(f"   输出文件: {final_state['output_path']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
