# TinyAct Emulator

**LLM makes the environment realistic; Python makes it reliable.**

一个支持单一 Agent 和多 Agent 兼容的操作模拟环境框架，用于评估和提升小模型 Agent 的真实操作能力。

## 核心理念

> **Python/Rule 负责真值，LLM 负责语义外壳。**

TinyAct Emulator 不是纯模拟器，也不是纯 benchmark，而是用来系统性回答：
**strong harness 能把 small model 的真实操作能力提升到什么程度。**

### 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                    Operation Emulator                    │
├─────────────────────────────────────────────────────────┤
│  Python State Engine      │  Hidden State (Ground Truth)│
│  Rule-based Tool Runtime  │  Deterministic Execution    │
│  Rule-based Verifier      │  Success/Failure/Risk       │
├─────────────────────────────────────────────────────────┤
│  LLM-based Simulator      │  Instructions, Feedback     │
│  Observation Compiler     │  State Abstraction          │
│  Trace Recorder           │  Full Episode Logging       │
├─────────────────────────────────────────────────────────┤
│            Multi-Agent Compatibility Layer               │
│  ┌─────────────┬─────────────┬──────────────┐           │
│  │ SingleAgent │  Manager    │  Worker      │           │
│  │ Orchestrator│  Hierarchical│  Debate      │           │
│  └─────────────┴─────────────┴──────────────┘           │
└─────────────────────────────────────────────────────────┘
                          ↑
                    Harness Layer
                          ↑
              Small/Large Model Agents
```

## 核心特性

### 1. 单一 & 多 Agent 无缝兼容

框架通过统一的 `BaseAgent` 接口和 `MultiAgentOrchestrator` 编排器，实现了对单一 Agent 和多 Agent 场景的无缝支持。

#### 单一 Agent 模式

```python
from tinyact import create_agent, LLMAdapter, MockLLMClient

# 创建单一 Agent
agent = create_agent("single", agent_id="assistant")
llm_agent = LLMAdapter(llm_client=mock_client)

# 直接使用
tool_name, args = agent.act(
    instruction="Save the invoice attachment",
    observation=obs,
    available_tools=tools
)
```

#### 多 Agent 协作模式

```python
from tinyact import create_agent, create_orchestrator

# 创建不同角色的 Agent
manager = create_agent("manager", agent_id="boss")
worker = create_agent("worker", agent_id="dev_A", specialty="coding")
reviewer = create_agent("reviewer", agent_id="critic")

# 创建编排器（支持 4 种模式）
orchestrator = create_orchestrator(
    mode="hierarchical",  # sequential, hierarchical, debate, broadcast
    agents=[manager, worker, reviewer]
)

# 运行协作会话
result = orchestrator.run_collaboration(
    instruction="Implement and review a feature",
    observation=obs,
    available_tools=tools,
    max_rounds=10
)
```

### 2. 四种协作模式

| 模式 | 描述 | 适用场景 | 示例 |
|------|------|----------|------|
| `sequential` | 轮流执行，Round-robin | 简单任务分工 | 数据提取→处理→验证 |
| `hierarchical` | 经理优先，然后工人 | 层级化任务分解 | 项目经理分配任务给开发 |
| `debate` | 全员讨论，经理决策 | 复杂决策场景 | 安全审查、风险评估 |
| `broadcast` | 信息共享，任意执行 | 开放式协作 | 头脑风暴、问题诊断 |

### 3. 预定义 Agent 角色

| 角色 | 职责 | 典型行为 |
|------|------|----------|
| **Manager** | 协调者 | 任务分配、结果聚合、冲突解决 |
| **Worker** | 执行者 | 具体任务实施、工具调用 |
| **Reviewer** | 审核者 | 安全性检查、质量评估 |
| **Specialist** | 专家 | 特定领域任务（如财务、法律） |
| **Critic** | 评论者 | 提供改进建议、发现盲点 |
| **Planner** | 规划者 | 制定执行计划、步骤分解 |
| **Executor** | 执行器 | 默认单一 Agent 角色 |

### 4. Harness 增强层级

框架支持多级 Harness 增强，逐步提升小模型能力：

```python
from tinyact import HarnessAgent, LLMAdapter

# H0: Raw (无增强) - 直接暴露原始工具和状态
base_agent = LLMAdapter(llm_client)

# H1: Structured Observation - 状态压缩和摘要
harness_agent = HarnessAgent(
    base_agent=base_agent,
    harness_level=1,
    state_compiler=my_compiler  # 将 100 封邮件压缩为 Top-5 相关
)

# H2: Candidate Actions - 生成候选动作
harness_agent = HarnessAgent(
    base_agent=base_agent,
    harness_level=2,
    candidate_generator=my_generator  # 生成 A1/A2/A3 选项
)

# H3: Verifier Feedback - 实时验证反馈
harness_agent = HarnessAgent(
    base_agent=base_agent,
    harness_level=3,
    verifier_feedback=True  # "参数错误，应该是..."
)

# H4: Safety Gate - 风险操作拦截
harness_agent = HarnessAgent(
    base_agent=base_agent,
    harness_level=4,
    safety_gate=True  # 删除/发送操作需二次确认
)

# H5: Skill Reuse - 历史成功模式复用
harness_agent = HarnessAgent(
    base_agent=base_agent,
    harness_level=5,
    skill_library=my_skills  # "上次类似任务这样成功了"
)
```

## 快速开始

### 安装

```bash
cd tinyact-emulator
pip install -e .
```

### 完整示例：单一 Agent 工作流

```python
from tinyact import (
    OperationEmulator, HiddenState, ToolExecutor,
    ToolDefinition, ToolRiskLevel, Verifier,
    TaskDefinition, ScenarioDefinition,
    LLMAdapter, MockLLMClient
)

# 1. 定义场景
scenario = ScenarioDefinition(
    scenario_id="file_ops",
    name="File Operations",
    state_schema=["files", "folders"],
    tools={"read": ["list_dir", "read_file"], "write": ["write_file"]}
)

# 2. 初始化状态
def init_state(config, seed):
    state = HiddenState()
    state.metadata = {"seed": seed}
    state.entities = {"files": []}
    state.files = {}
    return state

# 3. 注册工具
executor = ToolExecutor()

@executor.register("list_dir")
def list_dir_func(state, path: str):
    return {"files": list(state.files.keys())}

@executor.register("write_file")
def write_file_func(state, path: str, content: str):
    state.files[path] = content
    return {"ok": True, "path": path}

# 4. 创建仿真器
emulator = OperationEmulator(
    scenario=scenario,
    state_initializer=init_state,
    tool_executor=executor,
    verifier=Verifier()
)

# 5. 创建任务
task = TaskDefinition(
    task_id="create_readme_001",
    scenario="file_ops",
    hidden_goal={"action": "write_file", "path": "README.md"},
    instruction="Create a README file",
    max_steps=5
)

# 6. 创建 Agent（使用 Mock LLM）
mock_client = MockLLMClient([
    '{"tool": "write_file", "args": {"path": "README.md", "content": "# Hello"}}',
    '{"tool": "finish", "args": {}}'
])
agent = LLMAdapter(llm_client=mock_client)

# 7. 运行完整 episode
observation = emulator.reset(task=task, seed=42, instruction=task.instruction)

for step in range(task.max_steps):
    # Agent 决策
    tool_name, args = agent.act(
        instruction=emulator.instruction,
        observation=observation,
        available_tools=emulator.available_tools()
    )
    
    # 检查是否结束
    if not tool_name or tool_name == "finish":
        break
    
    # 执行工具
    result = emulator.call_tool(tool_name, args)
    
    # 检查验证结果
    verification = emulator.verify()
    if verification.success or verification.failed:
        break
    
    # 获取新观察
    observation = emulator.observe()

# 8. 获取结果
print(f"Success: {emulator.get_final_result().success}")
print(f"Trace: {len(emulator.get_trace().steps)} steps")

# 9. 结束 episode
emulator.end_episode()
```

### 完整示例：多 Agent 协作工作流

```python
from tinyact import (
    create_agent, create_orchestrator,
    OperationEmulator, TaskDefinition,
    LLMAdapter, MockLLMClient
)

# 1. 创建仿真器和任务（同上）
emulator = OperationEmulator(...)
task = TaskDefinition(...)

# 2. 创建不同角色的 Agent
manager_llm = MockLLMClient([
    '{"tool": "delegate", "args": {"to": "worker", "task": "write_file"}}',
    '{"tool": "finish", "args": {"result": "done"}}'
])
worker_llm = MockLLMClient([
    '{"tool": "write_file", "args": {"path": "README.md", "content": "# Doc"}}',
    '{"tool": "report", "args": {"to": "manager", "status": "completed"}}'
])
reviewer_llm = MockLLMClient([
    '{"tool": "approve", "args": {"quality": "good"}}',
    '{"tool": "finish", "args": {}}'
])

manager = LLMAdapter(llm_client=manager_llm, agent_id="manager")
worker = LLMAdapter(llm_client=worker_llm, agent_id="worker")
reviewer = LLMAdapter(llm_client=reviewer_llm, agent_id="reviewer")

# 3. 创建层级式编排器
orchestrator = create_orchestrator(
    mode="hierarchical",
    agents=[manager, worker, reviewer]
)

# 4. 运行协作会话
observation = emulator.reset(task=task, seed=42, instruction=task.instruction)

collaboration_result = orchestrator.run_collaboration(
    instruction=task.instruction,
    observation=observation,
    available_tools=emulator.available_tools(),
    max_rounds=10,
    emulator=emulator  # 传入 emulator 以执行工具调用
)

# 5. 查看结果
print(f"Contributing agents: {collaboration_result.contributing_agents}")
print(f"Final decision: {collaboration_result.tool_name}")
print(f"Total rounds: {collaboration_result.total_rounds}")

# 6. 获取完整 trace
trace = emulator.get_trace()
print(f"Total steps: {len(trace.steps)}")
print(f"Agent contributions: {trace.metadata.get('agent_contributions', {})}")

emulator.end_episode()
```

### Harness 增强示例

```python
from tinyact import HarnessAgent, LLMAdapter, StateCompiler

# 创建基础 Agent
base_agent = LLMAdapter(llm_client)

# 创建状态编译器（将复杂状态压缩为简洁表示）
class MyCompiler(StateCompiler):
    def compile(self, state, context):
        # 例如：从 100 封邮件中提取 Top-5 相关
        return {
            "summary": "Found 3 relevant emails",
            "top_items": [...]
        }

# H2 级别：结构化观察 + 候选动作
harness_agent = HarnessAgent(
    base_agent=base_agent,
    harness_level=2,
    state_compiler=MyCompiler(),
    candidate_generator=lambda state: [
        {"id": "A1", "tool": "read_email", "args": {"id": "e_001"}},
        {"id": "A2", "tool": "read_email", "args": {"id": "e_002"}},
        {"id": "A3", "tool": "finish", "args": {}}
    ]
)

# 使用时，Agent 只需要选择候选动作
tool_name, args = harness_agent.act(
    instruction="Find the invoice email",
    observation=compiled_obs,
    available_tools=candidates  # 这里是候选动作列表
)
# 返回可能是："A1", {}  表示选择第一个候选动作
```

## 项目结构

```
tinyact-emulator/
├── tinyact/
│   ├── __init__.py              # 主包入口，导出所有公共 API
│   ├── emulator.py              # 核心仿真器类 OperationEmulator
│   │
│   ├── core/                    # 核心组件
│   │   ├── state.py             # HiddenState, EntityState
│   │   ├── tool.py              # ToolDefinition, ToolExecutor, ToolResult
│   │   ├── task.py              # TaskDefinition, ScenarioDefinition
│   │   ├── verifier.py          # Verifier, VerificationResult
│   │   └── trace.py             # StepRecord, EpisodeTrace
│   │
│   ├── multi_agent/             # 多 Agent 框架
│   │   ├── agents.py            # BaseAgent, ManagerAgent, WorkerAgent 等
│   │   ├── orchestrator.py      # MultiAgentOrchestrator
│   │   └── __init__.py          # create_agent, create_orchestrator
│   │
│   ├── agents/                  # Agent 适配器
│   │   ├── adapters.py          # LLMAdapter, HarnessAgent
│   │   └── __init__.py
│   │
│   ├── llm_sim/                 # LLM 模拟器
│   │   ├── simulator.py         # InstructionGenerator, ContentGenerator
│   │   └── __init__.py
│   │
│   ├── harness/                 # Harness 组件（待实现）
│   │   ├── compiler.py          # StateCompiler
│   │   ├── candidates.py        # CandidateGenerator
│   │   └── safety.py            # SafetyGate
│   │
│   └── scenarios/               # 场景定义（待实现）
│       ├── file_ops/
│       ├── email_ops/
│       └── crm_ops/
│
├── test_compatibility.py        # 单/多 Agent 兼容性测试
├── setup.py                     # 包安装配置
└── README.md
```

## 实验矩阵

框架设计用于支持以下维度的系统性评估：

| 维度 | 选项 |
|------|------|
| **模型规模** | 1.5B, 3B, 4B, 7B/8B, Large API |
| **Harness 层级** | H0 Raw, H1 Obs, H2 Actions, H3 Feedback, H4 Safety, H5 Skills |
| **场景类型** | FileOps, EmailOps, CRMOps, CalendarOps, DataOps |
| **Agent 模式** | Single, Sequential, Hierarchical, Debate, Broadcast |
| **协作角色** | Manager, Worker, Reviewer, Specialist, Critic, Planner |

### 核心评估指标

- **Task Success Rate**: 任务完成率
- **Invalid Tool Call Rate**: 无效工具调用率
- **Wrong Argument Rate**: 参数错误率
- **Premature Finish Rate**: 过早结束率
- **Unsafe Action Rate**: 不安全操作率
- **Average Steps**: 平均步数
- **Recovery Success**: 失败恢复成功率
- **Small-vs-Large Gap**: 小模型与大模型的差距
- **Harness Gain**: Harness 带来的提升

## 核心 API 参考

### OperationEmulator

```python
class OperationEmulator:
    """核心仿真器类，管理环境状态和工具执行"""
    
    def reset(self, task: TaskDefinition, seed: int, instruction: str) -> Dict:
        """重置环境并开始新 episode"""
        
    def observe(self) -> Dict:
        """获取当前观察（编译后的状态）"""
        
    def available_tools(self) -> List[Dict]:
        """获取可用工具列表"""
        
    def call_tool(self, tool_name: str, args: Dict, agent_id: str = "default") -> ToolResult:
        """执行工具调用"""
        
    def verify(self) -> VerificationResult:
        """验证当前状态是否满足任务目标"""
        
    def is_done(self) -> bool:
        """检查 episode 是否结束"""
        
    def get_trace(self) -> EpisodeTrace:
        """获取完整执行轨迹"""
        
    def get_final_result(self) -> FinalResult:
        """获取最终结果"""
        
    def end_episode(self):
        """结束当前 episode"""
```

### MultiAgentOrchestrator

```python
class MultiAgentOrchestrator:
    """多 Agent 编排器，支持多种协作模式"""
    
    def __init__(self, mode: str, agents: List[BaseAgent]):
        """
        初始化编排器
        mode: sequential, hierarchical, debate, broadcast
        """
        
    def add_agent(self, agent: BaseAgent):
        """添加 Agent"""
        
    def select_next_agent(self, context: Dict) -> BaseAgent:
        """根据上下文选择下一个执行的 Agent"""
        
    def broadcast_message(self, message: AgentMessage):
        """广播消息给所有 Agent"""
        
    def run_collaboration(
        self,
        instruction: str,
        observation: Dict,
        available_tools: List[Dict],
        max_rounds: int = 10,
        emulator: OperationEmulator = None
    ) -> CollaborationResult:
        """运行协作会话"""
        
    def reset(self):
        """重置编排器状态"""
```

### BaseAgent

```python
class BaseAgent(ABC):
    """Agent 抽象基类"""
    
    def __init__(self, agent_id: str, specialty: str = None):
        self.agent_id = agent_id
        self.specialty = specialty
    
    @abstractmethod
    def act(
        self,
        instruction: str,
        observation: Dict,
        available_tools: List[Dict],
        context: Dict = None
    ) -> Tuple[str, Dict]:
        """执行决策，返回工具名和参数"""
        
    def process_message(self, message: AgentMessage):
        """处理来自其他 Agent 的消息"""
        
    def reset(self):
        """重置 Agent 状态"""
```

### 工厂函数

```python
def create_agent(role: str, agent_id: str, **kwargs) -> BaseAgent:
    """
    创建指定角色的 Agent
    
    role: single, manager, worker, reviewer, specialist, critic, planner, executor
    """

def create_orchestrator(mode: str, agents: List[BaseAgent]) -> MultiAgentOrchestrator:
    """
    创建编排器
    
    mode: sequential, hierarchical, debate, broadcast
    """
```

## 设计原则

1. **Hidden State 不可见**: Agent 只能通过 `observe()` 获取编译后的状态，无法直接访问真实状态
2. **工具执行确定性**: 相同输入产生相同输出，不依赖 LLM，确保评测可复现
3. **验证基于规则**: 成功/失败判断完全由 Python rule 决定，LLM 不参与真值判断
4. **LLM 仅生成语义**: 指令变体、内容文本、自然语言反馈等由 LLM 生成，增加真实感
5. **统一接口**: 单一 Agent 和多 Agent 使用相同的 `act()` 接口，无缝切换
6. **可扩展性**: 新增场景、工具、Agent 角色只需继承基类，无需修改核心框架

## 下一步开发计划

### v0.1 MVP（当前优先级）

- [ ] **FileOps 场景** (10 tasks)
  - 归档发票、提取 TODO、批量重命名、生成 summary、修改 JSON 配置
  
- [ ] **EmailOps 场景** (10 tasks)
  - 找邮件、保存附件、写草稿、打标签、提取 action items
  
- [ ] **CRMOps 场景** (10 tasks)
  - 更新客户状态、创建跟进任务、修改 deal stage、添加备注、筛选高价值客户
  
- [ ] **Harness H0-H3 实现**
  - H1: StateCompiler
  - H2: CandidateGenerator
  - H3: VerifierFeedback
  
- [ ] **基础评估指标**
  - 成功率、错误率、步数统计、Harness 增益分析

### v0.2 扩展

- [ ] CalendarOps, DataOps, FinanceOps 场景
- [ ] Harness H4-H5 (Safety Gate, Skill Reuse)
- [ ] 更多 Agent 角色和协作模式
- [ ] 可视化调试工具
- [ ] Batch 运行和并行评估

## 常见问题

**Q: 为什么不用 LLM 维护状态？**  
A: LLM 会产生幻觉，导致评测不可靠。Python 维护 hidden state 确保真值确定性。

**Q: 单一 Agent 和多 Agent 能混合使用吗？**  
A: 可以。可以在同一个 episode 中先用单一 Agent 执行简单步骤，遇到复杂决策时切换到多 Agent 模式。

**Q: Harness 层级越高越好吗？**  
A: 不一定。H5 虽然功能最强，但可能掩盖小模型的真实能力缺陷。建议从 H0 开始逐步增加，观察每层增益。

**Q: 如何自定义 Agent 角色？**  
A: 继承 `BaseAgent` 类，实现 `act()` 方法，可选重写 `process_message()` 处理多 Agent 通信。

**Q: 支持真实 LLM API 吗？**  
A: 支持。`LLMAdapter` 可以包装任何 LLM 客户端，只需实现 `generate()` 方法返回 JSON 格式的工具调用。

## License

MIT License

---

> **TinyAct Emulator** - A Python + rule + LLM-based operation emulator for evaluating and improving small-model agents.
> 
> **LLM makes the environment realistic; Python makes it reliable.**
