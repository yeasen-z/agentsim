# Agent-Sim

> **The Flight Simulator for Autonomous Agents.**
> **自主智能体的"飞行模拟器"**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

**Agent-Sim** 是一个通用的、高保真的、可编程的**人机交互仿真环境**。

它不是单纯的 Benchmark，也不是 GUI 模拟器。它的核心使命是：**为自主智能体（Autonomous Agents）提供一个安全、可控、可复现的"飞行模拟器"**。

在这里，Agent 可以像飞行员在模拟舱中一样，进行成千上万次的起飞、降落、故障处理训练，而无需承担真实世界的风险与成本。

---

## 🌟 核心理念

> **LLM makes the environment realistic; Python makes it reliable.**
> **LLM 负责真实感，Python 负责可靠性。**

传统的 Agent 评测往往依赖静态数据集或不可控的真实 API，导致：
- ❌ **幻觉无法验证**：环境状态由 LLM 维护，评测变成"自问自答"。
- ❌ **风险不可控**：真实误操作可能导致数据丢失或资金损失。
- ❌ **复现困难**：动态变化的真实环境让 Bug 难以追踪。

Agent-Sim 采用 **Hybrid Architecture (混合架构)** 解决这些问题：

| 模块 | 实现方式 | 职责 |
| :--- | :--- | :--- |
| **Hidden State (真值)** | **Python Objects** | 维护绝对正确的环境状态 (文件、邮件、数据库) |
| **Tool Runtime (执行)** | **Deterministic Rules** | 确定性地执行工具调用，保证状态转移可复现 |
| **Verifier (验证)** | **Rule-based Logic** | 客观判断任务成功/失败/违规，无幻觉 |
| **Semantic Layer (语义)** | **LLM Simulation** | 生成自然的用户指令、邮件正文、模糊需求、环境噪声 |

---

## 🚀 为什么选择 Agent-Sim？

### 1. 通用交互环境 (General-Purpose)
不仅仅服务于小模型。它是**所有 Agent 的基础设施**：
- 🤖 **大模型厂商**：大规模压力测试、安全对齐 (Safety Alignment)、长程任务评估。
- 🏢 **企业自动化**：在部署到真实 ERP/CRM 前，进行零风险的流程验证 (RPA)。
- 🧠 **强化学习 (RL)**：提供确定性的状态空间和奖励信号，训练策略网络。
- 🤝 **多智能体协作**：模拟复杂的团队分工、沟通与冲突解决场景。

### 2. 高保真仿真 (High-Fidelity)
- **语义复杂度**：LLM 生成的用户指令包含模糊性、多轮追问、隐含意图。
- **环境噪声**：模拟真实的网络延迟、API 错误、非结构化数据。
- **动态反馈**：根据 Agent 行为动态生成自然语言解释和后果。

### 3. 安全沙箱 (Safe Sandbox)
- **零风险试错**：随意删除"生产数据"、发送"错误邮件"，一切均可瞬间重置。
- **边界测试**：构造极端边缘案例 (Edge Cases)，测试 Agent 的鲁棒性。
- **审计追踪**：全量记录每一步的状态变化、工具调用和决策逻辑。

### 4. 灵活扩展 (Extensible)
- **Scenario Registry**：轻松定义新场景 (Email, File, CRM, Calendar, SQL, Linux Shell...)。
- **Plugin System**：自定义工具、验证规则和 LLM 模拟器。
- **Multi-Agent Ready**：原生支持单 Agent 和多 Agent 协作模式。

---

## 🏗️ 架构设计

### 总体架构图

```text
┌─────────────────────────────────────────────────────────────┐
│                    Operation Emulator                        │
├─────────────────────────────────────────────────────────────┤
│  Python State Engine      │  Hidden State (Ground Truth)    │
│  Rule-based Tool Runtime  │  Deterministic Execution        │
│  Rule-based Verifier      │  Success/Failure/Risk Check     │
├─────────────────────────────────────────────────────────────┤
│  LLM-based Simulator      │  Instructions, Content, Noise   │
│  Observation Compiler     │  State Abstraction for Agent    │
│  Trace Recorder           │  Full Episode Logging           │
├─────────────────────────────────────────────────────────────┤
│              Multi-Agent Compatibility Layer                 │
│  ┌──────────────┬──────────────┬────────────────┐           │
│  │ SingleAgent  │  Manager     │  Worker        │           │
│  │ Orchestrator │  Hierarchical│  Debate/Broadcast          │
│  └──────────────┴──────────────┴────────────────┘           │
└─────────────────────────────────────────────────────────────┘
                          ↑
                    Harness Layer
                          ↑
              Small/Large Model Agents
```

### 核心组件

| 组件 | 描述 |
| :--- | :--- |
| **State Engine** | Python 对象维护的 Hidden State，环境的"唯一真值" |
| **Tool Runtime** | 确定性规则执行工具调用，保证状态转移可复现 |
| **Verifier** | Rule-based 逻辑判断任务成功/失败/违规 |
| **LLM Simulator** | 生成自然语言指令、内容、反馈和环境噪声 |
| **Observation Compiler** | 将复杂状态编译为 Agent 可理解的观察 |
| **Trace Recorder** | 记录完整的行为轨迹，支持回放和分析 |
| **Multi-Agent Orchestrator** | 支持多种协作模式的编排器 |

---

## 🎯 支持的场景 (Scenarios)

Agent-Sim 采用插件化设计，可以轻松扩展各种交互场景：

### MVP v0.1 (首批场景)

| 场景 | 数据类型 | 典型任务 |
| :--- | :--- | :--- |
| **FileOps** | 文件、文件夹、元数据 | 归档发票、批量重命名、提取 TODO、修改配置 |
| **EmailOps** | 邮件、附件、联系人 | 保存附件、写草稿、打标签、提取 Action Items |
| **CRMOps** | 客户、交易、备注 | 更新状态、创建跟进任务、修改 Deal Stage |

### 未来扩展

- **CalendarOps**: 会议安排、冲突检测、日程优化
- **DataOps**: SQL 查询、数据清洗、报表生成
- **FinanceOps**: 账单处理、报销审核、预算跟踪
- **LinuxOps**: Shell 命令、进程管理、日志分析
- **WebOps**: 浏览器操作、表单填写、信息抓取

---

## 🛠️ 快速开始

### 安装

```bash
git clone https://github.com/your-org/agent_sim-emulator.git
cd agent_sim-emulator
pip install -e .
```

### 基础使用示例

#### 1. 单一 Agent 模式

```python
from agent_sim import OperationEmulator, create_agent, LLMAdapter

# 初始化仿真器
emulator = OperationEmulator()
emulator.reset(scenario_id="file_ops", task_id="archive_invoice_001", seed=42)

# 创建 Agent
agent = create_agent("single", agent_id="assistant")
llm_agent = LLMAdapter(llm_client=your_llm_client)

# 运行循环
for step in range(10):
    obs = emulator.observe()
    tools = emulator.available_tools()
    
    # Agent 决策
    action = llm_agent.act(
        instruction=emulator.instruction,
        observation=obs,
        available_tools=tools
    )
    
    # 执行动作
    result = emulator.call_tool(action.tool_name, action.args)
    
    # 检查是否完成
    verification = emulator.verify()
    if verification["success"] or verification["failed"]:
        break

# 获取轨迹
trace = emulator.get_trace()
print(f"Task Success: {verification['success']}")
```

#### 2. 多 Agent 协作模式

```python
from agent_sim import create_agent, create_orchestrator

# 创建不同角色的 Agent
manager = create_agent("manager", agent_id="boss")
worker = create_agent("worker", agent_id="dev_A", specialty="file_ops")
reviewer = create_agent("reviewer", agent_id="critic")

# 创建编排器（支持 4 种模式）
orchestrator = create_orchestrator(
    mode="hierarchical",  # sequential, hierarchical, debate, broadcast
    agents=[manager, worker, reviewer]
)

# 运行协作会话
result = orchestrator.run_collaboration(
    instruction="Archive all invoices from June 2026",
    emulator=emulator
)

print(f"Collaboration Result: {result}")
```

#### 3. 使用 Harness 增强

```python
from agent_sim.harness import HarnessAgent, StateCompiler, CandidateActionGenerator

# 创建 Harness 层
compiler = StateCompiler(max_emails=5, max_files=10)
action_gen = CandidateActionGenerator(top_k=3)

harness_agent = HarnessAgent(
    base_agent=llm_agent,
    state_compiler=compiler,
    action_generator=action_gen,
    safety_gate=True
)

# Harness 会自动压缩状态、生成候选动作、过滤风险操作
action = harness_agent.act(instruction, observation, tools)
```

---

## 📊 实验矩阵

Agent-Sim 支持系统化的实验设计，回答关键研究问题：

### 模型维度

| 模型类型 | 示例 | 用途 |
| :--- | :--- | :--- |
| **Small (1-3B)** | Qwen2.5-1.5B, Phi-3-mini | 端侧部署、低延迟场景 |
| **Medium (4-8B)** | Qwen2.5-7B, Llama-3-8B | 平衡性能与成本 |
| **Large (API)** | GPT-4, Claude-3.5 | 天花板参考、复杂任务 |

### Harness 层级

| 层级 | 功能 | 预期提升 |
| :--- | :--- | :--- |
| **H0 Raw** | 原始工具接口 | Baseline |
| **H1 Structured Obs** | 状态压缩与摘要 | +5~15% |
| **H2 Candidate Actions** | 生成候选动作集 | +10~25% |
| **H3 Verifier Feedback** | 实时验证反馈 | +5~10% |
| **H4 Safety Gate** | 风险操作拦截 | 降低 Unsafe Rate |
| **H5 Skill Reuse** | 历史成功轨迹复用 | +10~20% |

### 评估指标

- ✅ **Task Success Rate**: 任务完成率
- ⚠️ **Invalid Tool Call Rate**: 无效工具调用率
- 🎯 **Wrong Argument Rate**: 参数错误率
- 🛑 **Premature Finish Rate**: 过早结束率
- 🔒 **Unsafe Action Rate**: 不安全操作率
- 📏 **Average Steps**: 平均步数
- 🔄 **Recovery Success**: 错误恢复成功率
- 📈 **Harness Gain**: Harness 带来的提升幅度

---

## 📁 项目结构

```text
agent_sim-emulator/
├── README.md                  # 项目文档
├── setup.py                   # 安装配置
├── requirements.txt           # 依赖列表
│
├── agent_sim/                   # 核心包
│   ├── __init__.py
│   ├── emulator.py            # OperationEmulator 主类
│   │
│   ├── core/                  # 核心组件
│   │   ├── __init__.py
│   │   ├── state.py           # Hidden State 管理
│   │   ├── tool.py            # Tool 定义与执行
│   │   ├── task.py            # Task 定义
│   │   ├── verifier.py        # Rule-based 验证器
│   │   └── trace.py           # 轨迹记录
│   │
│   ├── multi_agent/           # 多 Agent 框架
│   │   ├── __init__.py
│   │   └── agents.py          # BaseAgent + 角色 + Orchestrator
│   │
│   ├── agents/                # Agent 适配器
│   │   ├── __init__.py
│   │   └── adapters.py        # LLMAdapter, HarnessAgent
│   │
│   ├── llm_sim/               # LLM 模拟器
│   │   ├── __init__.py
│   │   └── simulator.py       # 指令/内容/反馈生成器
│   │
│   ├── harness/               # Harness 层
│   │   ├── __init__.py
│   │   ├── state_compiler.py
│   │   ├── candidate_actions.py
│   │   ├── safety_gate.py
│   │   └── verifier_feedback.py
│   │
│   └── scenarios/             # 场景定义
│       ├── file_ops/
│       │   ├── state.py
│       │   ├── tools.py
│       │   ├── tasks.yaml
│       │   ├── verifier.py
│       │   └── seeds/
│       ├── email_ops/
│       └── crm_ops/
│
├── tests/                     # 测试用例
│   ├── test_emulator.py
│   ├── test_multi_agent.py
│   └── test_scenarios.py
│
└── examples/                  # 使用示例
    ├── single_agent_demo.py
    ├── multi_agent_demo.py
    └── harness_demo.py
```

---

## 🔬 研究问题

Agent-Sim 旨在帮助回答以下关键问题：

1. **能力边界**: 小模型在哪些场景下可以独立完成任务？哪些必须依赖大模型？
2. **Harness 效果**: 结构化辅助能将小模型能力提升到什么程度？性价比如何？
3. **错误模式**: 小模型主要失败在搜索、参数填充、状态跟踪还是安全判断？
4. **协作增益**: 多 Agent 协作能否弥补单个小模型的能力不足？最佳协作模式是什么？
5. **泛化能力**: 在一个场景训练的 Harness 能否迁移到新场景？
6. **安全对齐**: 如何在保证效率的同时，有效拦截不安全操作？

---

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 开发环境设置

```bash
git clone https://github.com/your-org/agent_sim-emulator.git
cd agent_sim-emulator
pip install -e ".[dev]"
```

### 添加新场景

1. 在 `agent_sim/scenarios/` 下创建新目录
2. 定义 `state.py`, `tools.py`, `verifier.py`
3. 编写 `tasks.yaml` 定义任务
4. 添加测试用例

### 提交 PR

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 📬 联系方式

- 📧 Email: your-email@example.com
- 💬 Issues: [GitHub Issues](https://github.com/your-org/agent_sim-emulator/issues)
- 📖 文档: [Wiki](https://github.com/your-org/agent_sim-emulator/wiki)

---

## 🙏 致谢

感谢所有为 Agent-Sim 做出贡献的开发者和研究者！

---

<div align="center">

**Built with ❤️ for the Agent Community**

[⬆ Back to Top](#agent_sim-emulator)

</div>
