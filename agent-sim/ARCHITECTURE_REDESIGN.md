# Agent-Sim 架构重构方案

## 核心理念

**agent-sim 是核心环境框架**，它提供：
1. **标准化的环境接口** - 场景、工具、状态、验证的完整定义
2. **监控器（Trace）系统** - 全链路记录，作为"黑匣子"
3. **可插拔的运行时支持** - Runtime 和 Agent 可以被灵活替换

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent-Sim Framework                       │
│  (核心贡献 - 标准化环境 + 监控器)                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │   Scenario       │         │      Trace       │          │
│  │   Definition     │────────▶│    Monitor       │          │
│  │   (场景定义)      │         │    (监控器)       │          │
│  └──────────────────┘         └──────────────────┘          │
│           │                              ▲                   │
│           ▼                              │                   │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │   Operation      │         │     Verifier     │          │
│  │   Emulator       │────────▶│    (验证器)       │          │
│  │   (环境引擎)      │         │                  │          │
│  └──────────────────┘         └──────────────────┘          │
│           │                                                  │
│           │ 标准接口                                          │
│           ▼                                                  │
│  ═══════════════════════════════════════════════════════    │
│                     框架边界                                  │
│  ═══════════════════════════════════════════════════════    │
│           │                                                  │
│           │ 可插拔组件                                        │
│           ▼                                                  │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │     Runtime      │         │      Agent       │          │
│  │   (执行控制器)    │◀───────▶│    (决策引擎)     │          │
│  └──────────────────┘         └──────────────────┘          │
│           │                          │                       │
│           │ 可以替换为：                │ 可以替换为：         │
│           │ - SingleAgentRuntime      │ - LLMAgent          │
│           │ - MultiAgentRuntime       │ - RuleAgent         │
│           │ - Custom Runtime          │ - Human Agent       │
│           │                           │ - Custom Agent      │
└─────────────────────────────────────────────────────────────┘
```

## 三层架构

### Layer 1: 场景定义层 (Scenario Definition Layer)
**职责**: 定义任务、工具、初始状态、验证规则

```python
@dataclass
class ScenarioDefinition:
    scenario_id: str
    name: str
    description: str
    state_schema: List[str]          # 状态结构定义
    tools: Dict[str, List[str]]      # 工具分类
    tasks: List[TaskDefinition]      # 任务列表
```

### Layer 2: 环境引擎层 (Environment Engine Layer)
**职责**: 维护状态、执行工具、记录 Trace、验证结果

```python
class OperationEmulator:
    def reset(task, seed, instruction) -> Observation
    def observe() -> Observation
    def call_tool(tool_name, args) -> ToolResult
    def verify() -> VerificationResult
    def get_trace() -> Trace          # 关键：监控器输出
```

### Layer 3: 运行时层 (Runtime Layer) - **可插拔**
**职责**: 控制执行流程、调用 Agent 决策、调用工具

```python
# 示例：SingleAgentRuntime (用户自定义)
class SingleAgentRuntime:
    agent: BaseAgent                  # 可替换
    max_steps: int
    
    def run(instruction) -> Result:
        for step in range(max_steps):
            action = agent.decide(observation, tools)
            result = emulator.call_tool(action)
            trace.record(step, action, result)
```

## 关键设计原则

### 1. 环境为核心 (Environment-Centric)
- agent-sim **不依赖**任何特定的 Runtime 或 Agent 实现
- Runtime 和 Agent 通过**标准接口**与环境交互
- 环境提供**唯一真实来源**(Ground Truth)

### 2. Trace 作为监控器 (Trace as Monitor)
```python
@dataclass
class Trace:
    scenario_id: str
    steps: List[StepRecord]          # 完整交互历史
    metadata: Dict[str, Any]
    
    def to_dict() -> Dict           # 可序列化
    def save_json(filepath)         # 可存储
    def analyze() -> Analysis       # 可分析
```

**Trace 记录的内容**:
- 每一步的 Observation (环境→Agent)
- 每一步的 Action (Agent→环境)
- 工具调用的参数和结果
- 状态变化快照
- 时间戳和元数据

### 3. 适配器模式连接外部组件
```python
# 适配器将外部组件转换为环境兼容的接口
class RuntimeAdapter:
    def __init__(self, external_runtime):
        self.runtime = external_runtime
    
    def execute(self, emulator, agent) -> Result:
        # 转换接口调用
        pass

class AgentAdapter:
    def __init__(self, external_agent):
        self.agent = external_agent
    
    def act(self, observation, tools) -> Action:
        # 转换决策接口
        pass
```

## 接口定义

### 环境提供给 Runtime 的接口
```python
class EnvironmentInterface(Protocol):
    def get_info() -> EnvironmentInfo
    def get_tools() -> List[ToolDefinition]
    def reset(task) -> Observation
    def step(action) -> Tuple[Observation, Reward, Done]
    def get_trace() -> Trace
    def verify() -> VerificationResult
```

### Runtime 需要实现的接口
```python
class RuntimeInterface(Protocol):
    def run(
        env: EnvironmentInterface,
        agent: AgentInterface,
        config: RuntimeConfig
    ) -> ExecutionResult
```

### Agent 需要实现的接口
```python
class AgentInterface(Protocol):
    def decide(
        observation: Observation,
        available_tools: List[ToolDefinition],
        context: Dict
    ) -> Action
```

## 使用示例

### 场景 1: 使用 SingleAgentRuntime
```python
# 1. 加载场景
scenario = load_scenario("email_management")
emulator = OperationEmulator(scenario)

# 2. 创建 Runtime (用户自带)
runtime = SingleAgentRuntime(
    agent=MyLLMAgent(),
    max_steps=10
)

# 3. 执行并获取 Trace
result = runtime.run(emulator)
trace = emulator.get_trace()
trace.save_json("trace.json")
```

### 场景 2: 使用 MultiAgentRuntime
```python
# 1. 加载场景
scenario = load_scenario("collaborative_writing")
emulator = OperationEmulator(scenario)

# 2. 创建多 Agent 运行时
runtime = MultiAgentRuntime(
    agents=[
        PlannerAgent(),
        WriterAgent(),
        ReviewerAgent()
    ],
    orchestrator="hierarchical"
)

# 3. 执行并获取 Trace
result = runtime.run(emulator)
trace = emulator.get_trace()
analyze_collaboration(trace)
```

### 场景 3: 自定义 Runtime
```python
# 用户可以实现自己的 Runtime 逻辑
class MyCustomRuntime:
    def run(self, env, agent):
        # 完全自定义的执行逻辑
        # 例如：强化学习训练循环、人类反馈循环等
        pass

runtime = MyCustomRuntime()
result = runtime.run(emulator, my_agent)
```

## 目录结构建议

```
agent-sim/
├── core/                      # 核心框架 (不可变)
│   ├── interface.py           # 环境接口定义
│   ├── trace.py               # Trace 监控系统
│   ├── scenario.py            # 场景定义
│   ├── tool.py                # 工具定义
│   ├── verifier.py            # 验证器
│   └── state.py               # 状态管理
│
├── emulator/                  # 环境引擎 (不可变)
│   └── operation_emulator.py  # 主引擎实现
│
├── adapters/                  # 适配器层 (可选)
│   ├── runtime_adapters.py    # Runtime 适配器
│   └── agent_adapters.py      # Agent 适配器
│
├── scenarios/                 # 场景库 (可扩展)
│   ├── email_scenario.py
│   ├── file_ops_scenario.py
│   └── ...
│
└── examples/                  # 使用示例
    ├── single_agent_demo.py
    ├── multi_agent_demo.py
    └── custom_runtime_demo.py
```

## 迁移路径

### 当前状态
- ✅ agent-sim 有完整的场景定义、环境引擎、Trace 系统
- ✅ SingleAgentRuntime 作为外部组件存在
- ⚠️ 接口边界不够清晰，耦合较多

### 目标状态
1. **明确框架边界**: agent-sim 只提供环境和监控器
2. **定义标准接口**: Protocol 定义 Runtime 和 Agent 接口
3. **提供适配器**: 帮助现有组件接入
4. **文档化**: 清晰的使用指南和示例

### 实施步骤
1. 提取 `EnvironmentInterface` Protocol
2. 提取 `RuntimeInterface` Protocol  
3. 提取 `AgentInterface` Protocol
4. 创建适配器示例
5. 更新文档说明框架定位

## 总结

**agent-sim 的核心价值**:
1. 标准化的仿真环境定义
2. 完整的 Trace 监控系统
3. 灵活的运行时支持

**Runtime 和 Agent 是用户的责任**:
- 用户可以提供自己的实现
- 框架通过标准接口与之交互
- 适配器帮助现有组件接入

这种设计使得 agent-sim 成为一个**真正的框架**，而不是一个固定的解决方案。
