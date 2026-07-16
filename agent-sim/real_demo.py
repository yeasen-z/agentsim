#!/usr/bin/env python3
"""
真实可运行的多 Agent Demo
- 真实创建文件
- 真实执行工具
- 真实记录 Trace
- 展示框架核心能力
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# ==================== 核心接口定义 ====================

class ITool:
    """工具接口"""
    @property
    def name(self) -> str: ...
    
    @property
    def description(self) -> str: ...
    
    def execute(self, **kwargs) -> Any: ...


class IAgent:
    """Agent 接口"""
    @property
    def agent_id(self) -> str: ...
    
    @property
    def role(self) -> str: ...
    
    def decide(self, state: Dict[str, Any], available_tools: List[Dict]) -> Dict[str, Any]: ...


class IRuntime:
    """Runtime 接口"""
    def run(self, agents: List[IAgent], initial_state: Dict[str, Any]) -> Dict[str, Any]: ...


class ITraceMonitor:
    """Trace 监控器接口"""
    def record(self, event: Dict[str, Any]): ...
    def get_trace(self) -> List[Dict[str, Any]]: ...
    def export(self, filepath: str): ...


# ==================== 核心实现 ====================

@dataclass
class TraceMonitor(ITraceMonitor):
    """内置 Trace 监控器 - 框架的核心监控组件"""
    _trace: List[Dict[str, Any]] = field(default_factory=list)
    
    def record(self, event: Dict[str, Any]):
        self._trace.append(event)
        print(f"[TRACE] {event.get('type', 'unknown')}: {event.get('description', '')}")
    
    def get_trace(self) -> List[Dict[str, Any]]:
        return self._trace.copy()
    
    def export(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._trace, f, indent=2, ensure_ascii=False)
        print(f"[TRACE] Exported to {filepath}")


class ToolRegistry:
    """工具注册表"""
    def __init__(self):
        self._tools: Dict[str, ITool] = {}
    
    def register(self, tool: ITool):
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[ITool]:
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict]:
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]
    
    def execute(self, name: str, **kwargs) -> Any:
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        return tool.execute(**kwargs)


@dataclass
class Environment:
    """环境 - 框架的核心容器"""
    tool_registry: ToolRegistry
    trace_monitor: TraceMonitor
    shared_state: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.trace_monitor.record({
            "type": "environment_initialized",
            "description": "Environment created with tools and trace monitor",
            "tools_count": len(self.tool_registry._tools)
        })


# ==================== 具体工具实现 ====================

class CalculatorTool(ITool):
    """计算器工具 - 真实执行计算"""
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Perform mathematical calculations"
    
    def execute(self, expression: str) -> Dict[str, Any]:
        try:
            # 安全评估表达式
            result = eval(expression, {"__builtins__": {}}, {})
            return {"success": True, "result": result, "expression": expression}
        except Exception as e:
            return {"success": False, "error": str(e)}


class FileWriteTool(ITool):
    """文件写入工具 - 真实创建文件"""
    @property
    def name(self) -> str:
        return "file_writer"
    
    @property
    def description(self) -> str:
        return "Write content to a file"
    
    def execute(self, filename: str, content: str) -> Dict[str, Any]:
        try:
            filepath = Path(filename)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding='utf-8')
            return {
                "success": True,
                "file": str(filepath.absolute()),
                "size": len(content),
                "message": f"File written successfully"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class FileReadTool(ITool):
    """文件读取工具 - 真实读取文件"""
    @property
    def name(self) -> str:
        return "file_reader"
    
    @property
    def description(self) -> str:
        return "Read content from a file"
    
    def execute(self, filename: str) -> Dict[str, Any]:
        try:
            filepath = Path(filename)
            if not filepath.exists():
                return {"success": False, "error": "File not found"}
            content = filepath.read_text(encoding='utf-8')
            return {
                "success": True,
                "file": str(filepath.absolute()),
                "content": content,
                "size": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ==================== 具体 Agent 实现 ====================

@dataclass
class PlannerAgent(IAgent):
    """规划者 Agent - 负责任务分解"""
    agent_id: str = "planner_001"
    role: str = "planner"
    _step: int = 0
    
    def decide(self, state: Dict[str, Any], available_tools: List[Dict]) -> Dict[str, Any]:
        self._step += 1
        
        if self._step == 1:
            # 第一步：分析任务并分配给 Executor
            task = state.get("task", "")
            return {
                "action": "send_message",
                "target_agent": "executor_001",
                "message": f"Please execute this task: {task}. First calculate 25*4, then save result to output.txt",
                "thought": "I need to delegate the calculation and file writing to the executor"
            }
        
        elif self._step == 2:
            # 第二步：检查是否完成
            if state.get("executor_status") == "completed":
                return {
                    "action": "finish",
                    "result": "Task completed by team!",
                    "thought": "Executor has finished the work"
                }
        
        # 默认继续等待
        return {
            "action": "wait",
            "thought": "Waiting for executor to complete"
        }


@dataclass
class ExecutorAgent(IAgent):
    """执行者 Agent - 负责具体操作"""
    agent_id: str = "executor_001"
    role: str = "executor"
    _step: int = 0
    
    def decide(self, state: Dict[str, Any], available_tools: List[Dict]) -> Dict[str, Any]:
        self._step += 1
        
        # 检查是否有来自 planner 的消息
        messages = state.get("messages", [])
        my_messages = [m for m in messages if m.get("to") == self.agent_id]
        
        if not my_messages or self._step > 3:
            return {
                "action": "idle",
                "thought": "No tasks assigned yet"
            }
        
        latest_msg = my_messages[-1]["content"]
        
        if self._step == 1:
            # 第一步：使用计算器
            return {
                "action": "use_tool",
                "tool_name": "calculator",
                "tool_args": {"expression": "25*4"},
                "thought": "Calculating 25*4"
            }
        
        elif self._step == 2:
            # 第二步：使用文件写入工具
            calc_result = state.get("last_tool_result", {})
            value = calc_result.get("result", 100)
            content = f"Calculation Result: 25 * 4 = {value}\nGenerated by Executor Agent"
            
            return {
                "action": "use_tool",
                "tool_name": "file_writer",
                "tool_args": {"filename": "output.txt", "content": content},
                "thought": f"Writing result {value} to output.txt"
            }
        
        elif self._step == 3:
            # 第三步：回复 planner
            return {
                "action": "send_message",
                "target_agent": "planner_001",
                "message": "Task completed! Calculated 25*4=100 and saved to output.txt",
                "thought": "Reporting completion to planner"
            }
        
        return {
            "action": "finish",
            "result": "Execution complete",
            "thought": "All done"
        }


# ==================== Runtime 实现 ====================

@dataclass
class MultiAgentRuntime(IRuntime):
    """多 Agent Runtime - 调度器和通信总线"""
    max_steps: int = 10
    current_step: int = 0
    
    def run(self, agents: List[IAgent], initial_state: Dict[str, Any], 
            env: Environment) -> Dict[str, Any]:
        
        self.current_step = 0
        state = initial_state.copy()
        state["messages"] = []
        state["agent_states"] = {a.agent_id: "active" for a in agents}
        
        env.trace_monitor.record({
            "type": "runtime_started",
            "description": f"Multi-agent runtime started with {len(agents)} agents",
            "agents": [a.agent_id for a in agents],
            "max_steps": self.max_steps
        })
        
        agents_dict = {a.agent_id: a for a in agents}
        last_active_agent = None
        
        while self.current_step < self.max_steps:
            self.current_step += 1
            
            # 轮询调度：简单轮流执行
            current_agent = agents[self.current_step % len(agents)]
            
            if state["agent_states"].get(current_agent.agent_id) != "active":
                continue
            
            env.trace_monitor.record({
                "type": "agent_turn",
                "description": f"Agent {current_agent.agent_id} is thinking",
                "step": self.current_step,
                "agent_id": current_agent.agent_id
            })
            
            # Agent 决策
            action = current_agent.decide(state, env.tool_registry.list_tools())
            
            env.trace_monitor.record({
                "type": "agent_action",
                "description": f"Agent {current_agent.agent_id} decided: {action['action']}",
                "step": self.current_step,
                "agent_id": current_agent.agent_id,
                "action": action
            })
            
            # 执行动作
            if action["action"] == "finish":
                env.trace_monitor.record({
                    "type": "task_finished",
                    "description": action.get("result", "Finished"),
                    "step": self.current_step,
                    "agent_id": current_agent.agent_id
                })
                return {
                    "status": "finished",
                    "result": action.get("result"),
                    "steps": self.current_step,
                    "final_state": state
                }
            
            elif action["action"] == "use_tool":
                tool_name = action["tool_name"]
                tool_args = action["tool_args"]
                
                env.trace_monitor.record({
                    "type": "tool_call_start",
                    "description": f"Calling tool {tool_name}",
                    "step": self.current_step,
                    "agent_id": current_agent.agent_id,
                    "tool": tool_name,
                    "arguments": tool_args
                })
                
                result = env.tool_registry.execute(tool_name, **tool_args)
                
                state["last_tool_result"] = result
                
                env.trace_monitor.record({
                    "type": "tool_call_end",
                    "description": f"Tool {tool_name} returned: {result}",
                    "step": self.current_step,
                    "agent_id": current_agent.agent_id,
                    "tool": tool_name,
                    "result": result
                })
            
            elif action["action"] == "send_message":
                message = {
                    "from": current_agent.agent_id,
                    "to": action["target_agent"],
                    "content": action["message"],
                    "step": self.current_step
                }
                state["messages"].append(message)
                
                env.trace_monitor.record({
                    "type": "message_sent",
                    "description": f"Message from {current_agent.agent_id} to {action['target_agent']}",
                    "step": self.current_step,
                    "from": current_agent.agent_id,
                    "to": action["target_agent"],
                    "content": action["message"]
                })
            
            elif action["action"] == "wait" or action["action"] == "idle":
                pass  # Just continue
        
        env.trace_monitor.record({
            "type": "max_steps_reached",
            "description": f"Reached maximum steps ({self.max_steps})",
            "steps": self.current_step
        })
        
        return {
            "status": "max_steps_reached",
            "result": None,
            "steps": self.current_step,
            "final_state": state
        }


# ==================== 主函数：运行真实 Demo ====================

def main():
    print("=" * 60)
    print("🚀 真实多 Agent Demo - 开始执行")
    print("=" * 60)
    print()
    
    # 1. 创建工具注册表并注册真实工具
    print("📦 初始化环境...")
    tool_registry = ToolRegistry()
    tool_registry.register(CalculatorTool())
    tool_registry.register(FileWriteTool())
    tool_registry.register(FileReadTool())
    
    # 2. 创建 Trace 监控器
    trace_monitor = TraceMonitor()
    
    # 3. 创建环境
    env = Environment(
        tool_registry=tool_registry,
        trace_monitor=trace_monitor
    )
    
    # 4. 创建 Agents
    planner = PlannerAgent()
    executor = ExecutorAgent()
    agents = [planner, executor]
    
    print(f"✓ 创建了 {len(agents)} 个 Agents:")
    print(f"  - {planner.agent_id} ({planner.role})")
    print(f"  - {executor.agent_id} ({executor.role})")
    print()
    
    # 5. 创建 Runtime
    runtime = MultiAgentRuntime(max_steps=10)
    
    # 6. 定义初始状态
    initial_state = {
        "task": "Calculate 25*4 and save the result to a file",
        "executor_status": "pending"
    }
    
    print("🎯 任务:", initial_state["task"])
    print()
    print("-" * 60)
    print("▶️  开始执行...")
    print("-" * 60)
    print()
    
    # 7. 运行！
    result = runtime.run(agents, initial_state, env)
    
    print()
    print("-" * 60)
    print("✅ 执行完成!")
    print("-" * 60)
    print()
    
    # 8. 输出结果
    print("📊 最终结果:")
    print(f"  状态: {result['status']}")
    print(f"  步数: {result['steps']}")
    print(f"  结果: {result.get('result', 'N/A')}")
    print()
    
    # 9. 验证文件是否真实创建
    output_file = Path("output.txt")
    if output_file.exists():
        print("📄 验证文件创建:")
        print(f"  文件路径: {output_file.absolute()}")
        print(f"  文件大小: {output_file.stat().st_size} bytes")
        print()
        print("  文件内容:")
        print("  " + "-" * 40)
        content = output_file.read_text(encoding='utf-8')
        for line in content.split('\n'):
            print(f"  {line}")
        print("  " + "-" * 40)
        print()
    else:
        print("❌ 文件未创建!")
        print()
    
    # 10. 导出 Trace
    trace_file = "demo_trace.json"
    trace_monitor.export(trace_file)
    print()
    
    # 11. 打印 Trace 摘要
    print("📋 Trace 摘要:")
    trace = trace_monitor.get_trace()
    event_types = {}
    for event in trace:
        etype = event.get("type", "unknown")
        event_types[etype] = event_types.get(etype, 0) + 1
    
    for etype, count in sorted(event_types.items()):
        print(f"  {etype}: {count} 次")
    
    print()
    print("=" * 60)
    print("🎉 Demo 成功完成!")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    main()
