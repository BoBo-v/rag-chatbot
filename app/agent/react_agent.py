"""
ReAct Agent
"""
import re
from typing import List, Tuple, Optional

from app.llm.ollama_client import llm_client
from app.tools.registry import tool_registry
from app.agent.prompts import REACT_SYSTEM_PROMPT, REACT_CONTINUE_PROMPT


class ReActAgent:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.tools = tool_registry

    def _parse_response(self, response: str) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        thought = ""
        action = None
        action_input = None
        final_answer = None

        # 提取 Thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|Final Answer:|$)', response, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()

        # 提取 Final Answer
        final_match = re.search(r'Final Answer:\s*(.+?)$', response, re.DOTALL)
        if final_match:
            final_answer = final_match.group(1).strip()
            return thought, None, None, final_answer

        # 提取 Action
        action_patterns = [
            r'Action:\s*(\w+)\s*\(\s*["\']?([^"\']*)["\']?\s*\)',
            r'Action:\s*(\w+)\s*\(([^)]*)\)',
            r'Action:\s*(\w+)',
        ]

        for pattern in action_patterns:
            action_match = re.search(pattern, response)
            if action_match:
                action = action_match.group(1).strip()
                action_input = action_match.group(2).strip() if action_match.lastindex >= 2 else ""
                action_input = action_input.strip('"\'')
                break

        return thought, action, action_input, final_answer

    def run(self, question: str) -> dict:
        """运行 Agent，返回字典格式结果"""
        steps = []  # 使用字典列表，而不是 dataclass
        history_lines = []

        initial_prompt = REACT_SYSTEM_PROMPT.format(
            tool_descriptions=self.tools.get_tools_description(),
            question=question
        )

        for i in range(self.max_iterations):
            print(f"\n{'='*50}")
            print(f"🔄 第 {i+1} 轮思考")

            if i == 0:
                current_prompt = initial_prompt
            else:
                history_text = "\n".join(history_lines)
                current_prompt = initial_prompt + REACT_CONTINUE_PROMPT.format(history=history_text)

            response = llm_client.chat(current_prompt)
            print(f"🤖 AI: {response[:300]}...")

            thought, action, action_input, final_answer = self._parse_response(response)

            # 使用字典而不是 dataclass
            step = {
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": None
            }

            if final_answer:
                print(f"\n✅ 最终答案: {final_answer}")
                return {
                    "answer": final_answer,
                    "steps": steps,
                    "iterations": i + 1
                }

            if action:
                print(f"🔧 执行: {action}({action_input})")
                tool = self.tools.get(action)

                if tool:
                    try:
                        result = tool(action_input) if action_input else tool()
                        observation = result.data if result.success else f"错误: {result.error}"
                    except Exception as e:
                        observation = f"工具执行异常: {e}"
                else:
                    observation = f"未知工具: {action}，可用: {', '.join(self.tools.list_tools())}"

                print(f"📋 结果: {observation}")
                step["observation"] = observation

                history_lines.append(f"Thought: {thought}")
                history_lines.append(f"Action: {action}(\"{action_input}\")")
                history_lines.append(f"Observation: {observation}")
            else:
                history_lines.append(f"Thought: {thought}")
                history_lines.append("Observation: 请给出 Action 或 Final Answer")

            steps.append(step)

        return {
            "answer": "达到最大思考轮数，无法完成任务。",
            "steps": steps,
            "iterations": self.max_iterations
        }


react_agent = ReActAgent()