"""
ReAct Agent - 多轮思考行动
"""
from app.ollama import ollama
from app.models.tools import TOOLS


class ReActAgent:
    """ReAct 模式 Agent"""

    def __init__(self, max_iterations: int = 5):
        self.tools = TOOLS
        self.max_iterations = max_iterations  # 最多循环几次

    def _get_tool_descriptions(self) -> str:
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"- {name}: {tool['description']}")
        return "\n".join(descriptions)

    def _execute_tool(self, tool_name: str, tool_args: str) -> str:
        if tool_name not in self.tools:
            return f"未知工具: {tool_name}"

        tool_func = self.tools[tool_name]["function"]

        if tool_name == "get_current_time":
            return tool_func()
        elif tool_name == "calculate":
            return tool_func(tool_args)
        elif tool_name == "get_weather":
            return tool_func(tool_args)
        elif tool_name == "web_search":
            return tool_func(tool_args)

        return "工具执行失败"

    def run(self, question: str) -> str:
        """运行 ReAct Agent"""

        tool_desc = self._get_tool_descriptions()

        # 记录整个思考过程
        thought_history = []

        for i in range(self.max_iterations):
            print(f"\n{'=' * 50}")
            print(f"🔄 第 {i + 1} 轮思考")

            # 构建 prompt，包含历史记录
            history_text = "\n".join(thought_history)

            prompt = f"""你是一个助手，使用 ReAct 模式解决问题。

可用工具：
{tool_desc}

请按以下格式回复：
Thought: 思考当前需要做什么
Action: 工具名("参数") 或者 无
Observation: （等待工具结果）

如果已经有足够信息回答问题，回复：
Thought: 我已经有足够信息了
Final Answer: 最终答案

用户问题：{question}

{history_text}

继续："""

            response = ollama.chat(prompt)
            print(f"🤖 AI 回复:\n{response}")

            # 检查是否有最终答案
            if "Final Answer:" in response:
                # 提取最终答案
                answer_start = response.index("Final Answer:") + 13
                final_answer = response[answer_start:].strip()
                print(f"\n✅ 最终答案: {final_answer}")
                return final_answer

            # 解析 Action
            if "Action:" in response:
                action_start = response.index("Action:") + 7
                action_end = response.find("\n", action_start)
                if action_end == -1:
                    action_end = len(response)
                action = response[action_start:action_end].strip()

                if action != "无" and "(" in action:
                    # 解析工具名和参数
                    tool_name = action[:action.index("(")].strip()
                    args_start = action.index("(") + 1
                    args_end = action.rindex(")")
                    tool_args = action[args_start:args_end].strip().strip('"\'')

                    # 执行工具
                    print(f"🔧 执行工具: {tool_name}({tool_args})")
                    observation = self._execute_tool(tool_name, tool_args)
                    print(f"📋 观察结果: {observation}")

                    # 记录这一轮
                    thought_history.append(response)
                    thought_history.append(f"Observation: {observation}")
                else:
                    thought_history.append(response)
            else:
                thought_history.append(response)

        return "达到最大迭代次数，无法完成任务"


agent = ReActAgent()


'''
### 测试效果
```
用户问题："北京现在几点了，天气怎么样？"

'''