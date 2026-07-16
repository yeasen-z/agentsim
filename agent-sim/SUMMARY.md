# Agent-Sim 框架梳理总结

## 🎯 核心定位

**agent-sim = 标准化环境框架 + Trace 监控器**

```
┌─────────────────────────────────────────────────────────┐
│                  agent-sim framework                     │
│                                                          │
│  ✅ 场景定义 (Scenario)                                   │
│  ✅ 环境引擎 (OperationEmulator)                          │
│  ✅ 工具系统 (ToolExecutor)                               │
│  ✅ 验证器 (Verifier)                                     │
│  ✅ Trace 监控器 (核心！)                                  │
│                                                          │
│  ❌ 不提供具体的 Runtime (用户自己实现)                    │
│  ❌ 不提供具体的 Agent (用户自己实现)                       │
└─────────────────────────────────────────────────────────┘
```

## 📐 三层架构

```
┌──────────────────────────────────────────────────────┐
│  Layer 1: 场景定义层                                   │
│  - ScenarioDefinition                                │
│  - TaskDefinition                                    │
│  - ToolDefinition                                    │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│  Layer 2: 环境引擎层 (核心)                            │
│  - OperationEmulator                                 │
│  - ToolExecutor                                      │
│  - Verifier                                          │
│  - Trace Monitor ← 黑匣子                            │
└──────────────────────────────────────────────────────┘
                        ↓ 标准接口
┌──────────────────────────────────────────────────────┐
│  Layer 3: 运行时层 (可插拔)                            │
│  - SingleAgentRuntime (用户实现)                      │
│  - MultiAgentRuntime (用户实现)                       │
│  - CustomRuntime (用户实现)                           │
│                                                       │
│  + Agent (可插拔)                                     │
│    - LLMAgent                                        │
│    - RuleAgent                                       │
│    - HumanAgent                                      │
└──────────────────────────────────────────────────────┘
```

## 🔌 标准接口

### EnvironmentInterface (环境提供给 Runtime)

```python
class EnvironmentInterface(Protocol):
    def get_info() -> EnvironmentInfo
    def get_tools() -> List[ToolDefinition]
    def reset(task_id, seed, instruction) -> Observation
    def step(action) -> Tuple[Observation, bool, Dict]
    def get_trace() -> Trace          # ← 关键：监控器输出
    def verify() -> Dict[str, Any]
```

### AgentInterface (Agent 需要实现)

```python
class AgentInterface(Protocol):
    def decide(observation, available_tools, context) -> Action
    def reset()
```

### RuntimeInterface (Runtime 需要实现)

```python
class RuntimeInterface(Protocol):
    def run(env, agent, config) -> ExecutionResult
```

## 🎬 使用流程

### 场景 1: 使用现有 Runtime

```python
from agent_sim import OperationEmulator, load_scenario
from my_runtimes import SingleAgentRuntime
from my_agents import MyLLMAgent

# 1. 加载场景 (agent-sim 提供)
scenario = load_scenario("email_management")
emulator = OperationEmulator(scenario)

# 2. 创建 Runtime 和 Agent (用户提供)
runtime = SingleAgentRuntime(agent=MyLLMAgent(), max_steps=10)

# 3. 执行
result = runtime.run(emulator)

# 4. 获取 Trace (核心功能!)
trace = emulator.get_trace()
trace.save_json("trace.json")
```

### 场景 2: 自定义 Runtime

```python
class MyCustomRuntime:
    def run(self, env, agent, config):
        # 完全自定义的执行逻辑
        env.reset(...)
        
        for step in range(config['max_steps']):
            observation = env.observe()
            action = agent.decide(observation, env.get_tools())
            
            if action.action_type == "call_tool":
                env.call_tool(action.tool_name, action.arguments)
            elif action.action_type == "return_result":
                break
        
        return {
            "status": "finished",
            "trace": env.get_trace()  # ← Trace 自动记录
        }

# 使用
runtime = MyCustomRuntime()
result = runtime.run(emulator, my_agent)
```

### 场景 3: 多 Agent 协作

```python
class MultiAgentRuntime:
    def __init__(self, agents, orchestrator):
        self.agents = agents
        self.orchestrator = orchestrator
    
    def run(self, env, config):
        env.reset(...)
        
        for round in range(config['max_rounds']):
            # 选择下一个 agent
            agent = self.orchestrator.select_next()
            
            # agent 决策
            action = agent.decide(env.observe(), env.get_tools())
            
            # 执行
            env.call_tool(...)
            
            # Trace 自动记录所有交互
        
        return {"trace": env.get_trace()}
```

## 🔍 Trace 监控器详解

### Trace 记录什么？

```python
@dataclass
class Trace:
    scenario_id: str
    start_time: str
    end_time: str
    initial_state: Dict
    steps: List[StepRecord]      # ← 完整交互历史
    metadata: Dict
    
@dataclass
class StepRecord:
    step_number: int
    timestamp: str
    observation: Any             # 环境→Agent
    thought: Optional[str]       # Agent 思考 (如果有)
    action: Optional[str]        # Agent 行动
    tool_calls: List[ToolCallRecord]
    state_snapshot_after: Dict   # 状态快照
```

### Trace 的用途

1. **调试分析**: 查看 agent 每一步的决策过程
2. **性能评估**: 统计成功率、步骤数、工具使用情况
3. **行为审计**: 追踪高风险操作
4. **训练数据**: 用于微调或强化学习
5. **可视化**: 生成执行流程图

```python
# 示例：分析 trace
trace = emulator.get_trace()

# 1. 保存
trace.save_json("episode_001.json")

# 2. 分析工具使用
tool_history = trace.get_tool_call_history()
print(f"Total tool calls: {len(tool_history)}")

# 3. 检查状态变化
if trace.has_state_changed("files"):
    print("Files were modified!")

# 4. 可视化
plot_trace(trace)
```

## 📁 目录结构

```
agent-sim/
├── core/                      # 核心框架
│   ├── interfaces.py          # 标准接口定义 ⭐
│   ├── trace.py               # Trace 监控系统 ⭐
│   ├── scenario.py            # 场景定义
│   ├── tool.py                # 工具定义
│   ├── verifier.py            # 验证器
│   └── state.py               # 状态管理
│
├── emulator/                  # 环境引擎
│   └── operation_emulator.py  # 主引擎 ⭐
│
├── adapters/                  # 适配器 (可选)
│   └── ...                    # 帮助现有组件接入
│
├── scenarios/                 # 场景库
│   ├── email_scenario.py
│   └── file_ops_scenario.py
│
├── examples/                  # 使用示例
│   ├── custom_runtime_example.py
│   └── ...
│
├── ARCHITECTURE_REDESIGN.md   # 架构设计文档
└── README.md                  # 使用指南
```

## 🔄 与你的 SingleAgentRuntime 的关系

你的 `SingleAgentRuntime` 是一个**Runtime 实现**，它应该：

1. **依赖接口而非具体实现**
   ```python
   class SingleAgentRuntime:
       def run(self, env: EnvironmentInterface, agent: AgentInterface):
           # 使用接口，不依赖具体类
   ```

2. **通过适配器连接 agent-sim**
   ```python
   # 适配器将 OperationEmulator 转换为 EnvironmentInterface
   adapter = AgentSimEnvironmentAdapter(emulator)
   
   # 现在可以用你的 Runtime
   result = runtime.run(adapter, agent)
   ```

3. **利用 Trace 进行追溯**
   ```python
   # Trace 由环境自动记录，不需要 Runtime 处理
   trace = env.get_trace()
   ```

## ✅ 关键设计原则

### 1. 环境为核心 (Environment-Centric)
- agent-sim **只**提供环境和监控器
- Runtime 和 Agent 是用户的责任
- 通过标准接口解耦

### 2. Trace 作为第一公民 (Trace as First-Class Citizen)
- Trace 不是事后添加的功能
- Trace 是环境的**核心输出**
- 所有交互自动记录

### 3. 可插拔设计 (Pluggable Design)
- 可以替换 Runtime 而不改环境
- 可以替换 Agent 而不改 Runtime
- 适配器模式连接外部组件

### 4. 单一真实来源 (Single Source of Truth)
- 环境维护 Ground Truth 状态
- Agent 只能通过观察和操作与环境交互
- 验证器基于真实状态判断成功

## 🚀 下一步行动

### 已完成
- ✅ 定义了标准接口 (`core/interfaces.py`)
- ✅ 创建了架构设计文档 (`ARCHITECTURE_REDESIGN.md`)
- ✅ 提供了自定义 Runtime 示例 (`examples/custom_runtime_example.py`)

### 待完成
- [ ] 更新 `OperationEmulator` 实现 `EnvironmentInterface`
- [ ] 创建适配器将现有组件连接到新接口
- [ ] 更新文档说明框架定位
- [ ] 添加更多示例 (Multi-Agent, RL Training 等)

## 💡 总结

**一句话理解 agent-sim**:

> agent-sim 是一个**标准化的仿真环境框架**，它提供场景定义、环境引擎和完整的 Trace 监控系统，让开发者可以专注于实现自己的 Runtime 和 Agent，同时获得可追溯、可分析的执行记录。

**三个关键点**:
1. **环境是核心** - 提供 Ground Truth 和 Trace
2. **Runtime 可插拔** - 用户可以自定义执行逻辑
3. **接口标准化** - 通过 Protocol 定义清晰的边界

这样的设计使 agent-sim 成为一个**真正的框架**，而不是一个固定的解决方案。
