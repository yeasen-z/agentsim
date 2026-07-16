# Agent Sim

> **LLM makes the environment realistic; Python makes it reliable.**  
> **LLM 负责真实感，Python 负责可靠性。**

Agent Sim is a **general-purpose agent interaction simulation platform** for developing, testing, and evaluating AI agents across diverse scenarios. It provides controlled task environments with hidden programmatic state, deterministic tool transitions, LLM-generated semantic complexity, and rule-based verification—supporting agents of all sizes from small models to large foundation models.

Agent Sim 是一个 **通用的智能体交互模拟平台**，用于开发、测试和评估各类 AI 智能体。它通过程序化 hidden state、确定性工具状态转移、LLM 生成的语义复杂度和 rule-based 验证，构造可控、可诊断、可复现的真实工作任务场景，适用于从小模型到大型基础模型的各种智能体。

---

## 🎯 Core Philosophy

> **Python/Rule maintains ground truth; LLM generates semantic complexity.**  
> **Python/rule 负责真值，LLM 负责语义外壳。**

The platform is built on a fundamental principle: **anything that affects evaluation ground truth must not rely solely on LLM**. This ensures reliable, reproducible, and diagnosable agent evaluation and development.

### What Agent Sim Is NOT

- ❌ Not a GUI emulator
- ❌ Not a pure benchmark suite
- ❌ Not an LLM-maintained simulation environment
- ❌ Not limited to small model evaluation

### What Agent Sim IS

- ✅ A Python-maintained state engine with deterministic transitions
- ✅ A rule-based tool runtime with verifiable outcomes
- ✅ An LLM-powered semantic layer for realistic interactions
- ✅ A flexible framework for developing and testing agents of all capabilities
- ✅ A systematic platform for answering: **How do different agents perform in controlled, realistic scenarios?**

---

## 🏗️ Architecture

```
Agent Sim Platform
├── Python State Engine        # Ground truth environment state
├── Rule-based Tool Runtime    # Deterministic tool execution & state transitions
├── Rule-based Verifier        # Success/failure/risk judgment (ground truth)
├── LLM-based Simulator        # User language, task variants, environmental text, perturbations
├── Observation Compiler       # State compilation for agent consumption
├── Trace Recorder             # Full episode recording
└── Scenario Registry          # EmailOps / FileOps / CRM / Calendar / DataOps / Custom ...
```

### Execution Flow

```
Scenario Definition
       ↓
Python initializes hidden state
       ↓
LLM generates user instruction & environmental text
       ↓
Agent observes current visible state
       ↓
Agent selects and calls tools
       ↓
Rule engine updates state deterministically
       ↓
Verifier checks success/failure/violation
       ↓
Trace recorded for analysis and iteration
```

---

## 🔑 Three Separated Components

### 1. Python State Engine (Ground Truth)

Maintains the real environment state. Never delegated to LLM.

**Example - EmailOps:**
```json
{
  "emails": [
    {
      "id": "e_001",
      "from": "billing@acme.com",
      "subject": "June Invoice",
      "attachments": ["invoice_june.pdf"],
      "labels": ["inbox"]
    }
  ],
  "drafts": [],
  "files": {}
}
```

**Example - CRMOps:**
```json
{
  "customers": [
    {
      "id": "c_001",
      "name": "Alice Zhang",
      "company": "Acme Corp",
      "status": "New"
    }
  ]
}
```

### 2. Rule-based Tool Runtime (Deterministic Execution)

All tool calls execute deterministically via Python rules.

```python
def update_customer_status(state, customer_id, status):
    customer = state.customers[customer_id]
    customer.status = status
    return {
        "ok": True,
        "message": f"Updated customer {customer_id} status to {status}."
    }

def save_attachment(state, email_id, attachment_id, path):
    attachment = state.get_attachment(email_id, attachment_id)
    state.files[path] = attachment.content
    return {
        "ok": True,
        "path": path
    }
```

### 3. LLM-based Simulator (Semantic Complexity)

LLM generates natural language variations without affecting ground truth:

- User task expressions
- Email/ticket/note body content
- Customer remarks
- Ambiguous requirements
- User follow-up questions
- Natural language tool response explanations
- Error message variations

**Example:** For the same hidden goal:
```json
{
  "intent": "save_attachment",
  "sender": "Acme Corp",
  "attachment_type": "invoice",
  "month": "2026-06",
  "target_folder": "invoices/2026-06"
}
```

LLM can generate different user instructions:
- "帮我把 Acme 上个月发来的发票附件存到 6 月发票文件夹里。"
- "Acme 那边 6 月账单应该发过来了，帮我找出来归档一下。"

Task completion is still verified by Python rules.

---

## 📐 Core API

```python
class OperationEmulator:
    def reset(self, scenario_id: str, task_id: str, seed: int):
        """Initialize episode with specific task and random seed"""
        
    def observe(self):
        """Get current observable state (compiled for agent)"""
        
    def available_tools(self):
        """Return list of available tools with signatures"""
        
    def call_tool(self, tool_name: str, args: dict):
        """Execute tool call via rule engine"""
        
    def verify(self):
        """Check success/failure/violation status"""
        
    def get_trace(self):
        """Return full episode trace for analysis"""
```

**Agent Access Restrictions:**
- ✅ Can call `observe()`
- ✅ Can call `call_tool(...)`
- ❌ Cannot directly access hidden state
- ⚠️ `verify()` optionally exposed depending on evaluation setting

---

## 📦 Scenario Structure

Scenarios are the basic unit of Agent Sim. Each scenario defines a controllable interaction environment:

```yaml
scenario_id: email_ops
name: Email Operations

state_schema:
  - emails
  - threads
  - contacts
  - attachments
  - drafts
  - files

tools:
  read:
    - search_emails
    - read_email
    - list_attachments
  write:
    - save_attachment
    - create_draft
    - apply_label
  risky:
    - send_email
    - delete_email

tasks:
  - email_save_invoice_attachment
  - email_draft_reply
  - email_label_github_notifications
```

### Task Definition

```yaml
task_id: email_save_invoice_attachment_001
scenario: email_ops

hidden_goal:
  action: save_attachment
  sender: Acme Corp
  attachment_type: invoice
  month: 2026-06
  target_path: invoices/2026-06/acme_invoice.pdf

instruction_generator:
  type: llm
  style: natural_user_request

initial_state:
  seed: email_seed_001

success:
  checks:
    - type: file_exists
      path: invoices/2026-06/acme_invoice.pdf
    - type: attachment_origin_matches
      sender: Acme Corp
      attachment_type: invoice

forbidden:
  - send_email
  - delete_email

max_steps: 8
```

---

## 🎭 Rule vs LLM Boundary

| Module                      | Python / Rule | LLM     |
| --------------------------- | ------------- | ------- |
| Hidden state                | **Required**  | Unused  |
| Tool execution              | **Required**  | Unused  |
| Success verification        | **Required**  | Unused  |
| Risk judgment (ground truth)| **Required**  | Optional assist |
| User task expression        | Template OK   | **Preferred** |
| Email/ticket/note content   | Template OK   | **Preferred** |
| Ambiguous requirements      | Rule OK       | **Preferred** |
| Observation summary         | Rule OK       | Optional |
| Failure explanation         | Rule OK       | Optional |

**Golden Rule:** > **Anything affecting evaluation ground truth must not rely solely on LLM.**

---

## 🧪 Harness Integration

Agent Sim separates the simulation platform from the agent harness, enabling flexible integration with various agent architectures:

```
Agent Sim Platform
       ↑
    Harness (Optional)
       ↑
Any Agent (Small / Large / Custom)
```

### Harness Capabilities

Harnesses provide optional enhancements for agent development:

- State compression and summarization
- Candidate action generation
- Argument normalization
- Tool risk filtering
- Verification feedback
- Failure recovery strategies
- Trace/replay support

### Example: Observation Compilation

Raw state contains 100 emails → Harness compiles for efficient agent processing:

```
Task: Save the June invoice from Acme Corp.

Relevant emails:
[1] From billing@acme.com, Subject: June Invoice, Date: 2026-06-30, Attachments: invoice_june.pdf
[2] From news@acme.com, Subject: Product Updates, Date: 2026-06-20, Attachments: none
[3] From billing@beta.com, Subject: June Invoice, Date: 2026-06-28, Attachments: beta_invoice.pdf

Candidate actions:
A1. read_email(e_001)
A2. read_email(e_002)
A3. read_email(e_003)
A4. finish
```

Small model only needs to select `A1`.

---

## 🎯 Experimental Matrix

Agent Sim enables systematic evaluation and development across diverse dimensions:

### Models (Any Size)
- Small models (1.5B - 4B)
- Medium models (7B - 14B)
- Large foundation models
- Proprietary API models
- Custom fine-tuned agents

### Harness Levels (Optional Enhancements)
- **H0**: Raw tools and observations
- **H1**: Structured observation compilation
- **H2**: Candidate action generation
- **H3**: Verifier feedback integration
- **H4**: Safety gate enforcement
- **H5**: Skill library and reuse

### Scenarios (Extensible)
- EmailOps (email management)
- FileOps (file system operations)
- CalendarOps (scheduling)
- CRMOps (customer relationship)
- DataOps (data processing)
- FinanceOps (financial tasks)
- Custom scenarios (user-defined)

### Key Research & Development Questions

- How do different model sizes perform across scenarios?
- What improvements do harnesses provide for various agents?
- Which tool calls are most error-prone?
- Which scenarios require advanced reasoning capabilities?
- Where do agents primarily fail: search, parameter filling, state tracking, or safety judgment?
- How can we iteratively improve agent reliability?

---

## 🚀 MVP v0.1 Scope

### Scenarios (3 total)

#### 1. FileOps
- **Data**: files, folders, metadata, file content
- **Tools**: list_dir, read_file, search_files, mkdir, move_file, copy_file, rename_file, write_file, delete_file
- **Tasks**: Archive invoices, Extract TODOs, Batch rename, Generate summary, Modify JSON config

#### 2. EmailOps
- **Data**: emails, threads, contacts, attachments, drafts
- **Tools**: search_emails, read_email, save_attachment, create_draft, apply_label, archive_email, send_email, delete_email
- **Tasks**: Find emails, Save attachments, Write drafts, Apply labels, Extract action items

#### 3. CRMOps
- **Data**: customers, companies, deals, notes, tasks
- **Tools**: search_customer, read_customer, update_customer, create_note, create_task, search_deals, update_deal
- **Tasks**: Update customer status, Create follow-up tasks, Modify deal stage, Add notes, Filter high-value customers

### Per Scenario Requirements
- 1 seed state
- 10 tasks
- 8–12 tools
- Rule-based verifier
- LLM-generated instruction variants
- Trace recorder

### Harness Levels (v0.1)
- H0: Raw tools and observations
- H1: Structured observation compilation
- H2: Candidate action generation
- H3: Verifier feedback integration

### Evaluation Models (Examples)
- Qwen2.5-1.5B
- Qwen2.5-3B
- Qwen3-4B
- 7B/8B models
- Large API models

### Output Metrics
- Task success rate
- Invalid tool call rate
- Wrong argument rate
- Premature finish rate
- Unsafe action rate
- Average steps
- Recovery success rate
- Model comparison analysis
- Harness improvement gains

---

## 📁 Project Structure

```
agent-sim/
├── agent_sim/
│   ├── core/
│   │   ├── emulator.py          # Main emulator class
│   │   ├── state.py             # State management
│   │   ├── tool.py              # Tool definitions & execution
│   │   ├── task.py              # Task definitions
│   │   ├── verifier.py          # Rule-based verification
│   │   └── trace.py             # Trace recording
│   │
│   ├── scenarios/
│   │   ├── file_ops/
│   │   │   ├── state.py
│   │   │   ├── tools.py
│   │   │   ├── tasks.yaml
│   │   │   ├── verifier.py
│   │   │   └── seeds/
│   │   │       └── seed_001.json
│   │   │
│   │   ├── email_ops/
│   │   │   ├── state.py
│   │   │   ├── tools.py
│   │   │   ├── tasks.yaml
│   │   │   ├── verifier.py
│   │   │   └── seeds/
│   │   │       └── seed_001.json
│   │   │
│   │   └── crm_ops/
│   │       ├── state.py
│   │       ├── tools.py
│   │       ├── tasks.yaml
│   │       ├── verifier.py
│   │       └── seeds/
│   │           └── seed_001.json
│   │
│   ├── llm_sim/
│   │   ├── instruction_generator.py
│   │   ├── content_generator.py
│   │   └── user_simulator.py
│   │
│   ├── harness/
│   │   ├── state_compiler.py
│   │   ├── candidate_actions.py
│   │   ├── safety_gate.py
│   │   └── verifier_feedback.py
│   │
│   ├── agents/
│   │   ├── raw_agent.py
│   │   ├── harnessed_agent.py
│   │   └── model_adapters.py
│   │
│   └── eval/
│       ├── runner.py
│       ├── metrics.py
│       └── error_analysis.py
│
├── tests/
├── examples/
├── docs/
└── README.md
```

---

## 💡 Core Value Proposition

> **Agent Sim is a Python + rule + LLM-based interaction simulation platform for developing, testing, and evaluating AI agents across diverse scenarios. It provides controlled task environments with hidden programmatic state, deterministic tool transitions, LLM-generated semantic complexity, and rule-based verification.**

In one sentence:

> **Agent Sim systematically answers: How do different agents perform in realistic, controllable scenarios, and how can we iteratively improve their reliability?**

---

## 🛠️ Getting Started

### Installation

```bash
git clone https://github.com/your-org/agent-sim.git
cd agent-sim
pip install -e .
```

### Quick Start: Hello World Tutorial

Here's a complete example showing how to use Agent Sim with a ReAct-style agent:

```python
from agent_sim.core.emulator import OperationEmulator
from agent_sim.core.trace import Trace

# 1. Initialize the emulator
emulator = OperationEmulator()

# 2. Reset with a specific scenario and task
emulator.reset(
    scenario_id="email_ops",
    task_id="email_save_invoice_attachment_001",
    seed=42
)

# 3. Get initial observation and available tools
obs = emulator.observe()
tools = emulator.available_tools()

print(f"Task instruction: {obs['instruction']}")
print(f"Available tools: {[t['name'] for t in tools]}")

# 4. Agent interaction loop (ReAct pattern)
max_steps = 10
for step in range(max_steps):
    # Reasoning: Agent thinks about what to do next
    thought = agent_reason(obs, tools)  # Your reasoning logic
    
    # Acting: Agent selects a tool and arguments
    tool_name, args = agent_act(thought, tools)  # Your action selection logic
    
    # Execute: Call the tool through the emulator
    result = emulator.call_tool(tool_name, args)
    
    # Observe: Get new state after tool execution
    obs = emulator.observe()
    
    # Check: Verify if task is complete
    verification = emulator.verify()
    if verification["done"]:
        print(f"✅ Task completed in {step + 1} steps!")
        break

# 5. Get the complete trace for analysis
trace: Trace = emulator.get_trace()
print(f"Total steps: {len(trace.steps)}")
print(f"State changed: {trace.has_state_changed()}")

# Save trace for later analysis
trace.save_json("episode_trace.json")
```

### Building Your First Agent

Agent Sim doesn't enforce a specific agent architecture. Here's a simple ReAct agent example:

```python
class ReActAgent:
    def __init__(self, model):
        self.model = model
        self.history = []
    
    def act(self, observation, tools, step_history):
        # Build prompt with observation, tools, and history
        prompt = self._build_prompt(observation, tools, step_history)
        
        # Get model response
        response = self.model.generate(prompt)
        
        # Parse response to extract thought and action
        thought, tool_name, args = self._parse_response(response)
        
        # Record in history
        self.history.append({
            "observation": observation,
            "thought": thought,
            "action": {"tool": tool_name, "args": args},
            "result": None  # Will be filled after execution
        })
        
        return tool_name, args
    
    def _build_prompt(self, obs, tools, history):
        # Construct ReAct prompt
        prompt = f"Task: {obs['instruction']}\n\n"
        prompt += "Current state:\n" + obs['state_summary'] + "\n\n"
        prompt += "Available tools:\n"
        for tool in tools:
            prompt += f"- {tool['name']}: {tool['description']}\n"
        prompt += "\nPrevious steps:\n"
        for i, h in enumerate(history):
            prompt += f"Step {i+1}: Thought: {h['thought']}\n"
            prompt += f"         Action: {h['action']['tool']}({h['action']['args']})\n"
            prompt += f"         Result: {h['result']}\n"
        prompt += "\nNow think step by step and decide the next action:"
        return prompt
    
    def _parse_response(self, response):
        # Parse model output to extract thought and action
        # Implementation depends on your response format
        pass
```

### Using Harnesses for Enhanced Performance

Harnesses provide optional enhancements to help agents perform better:

```python
from agent_sim.harness.state_compiler import StateCompiler
from agent_sim.harness.candidate_actions import CandidateActions

# Initialize harness components
compiler = StateCompiler()
candidate_gen = CandidateActions()

# In your agent loop
obs = emulator.observe()
tools = emulator.available_tools()

# H1: Compile raw state into focused summary
compiled_obs = compiler.compile(obs, task_instruction=obs['instruction'])

# H2: Generate candidate actions for easier selection
candidates = candidate_gen.generate(compiled_obs, tools)

# Agent only needs to select from candidates (easier for small models)
selected_action = agent.select_from_candidates(candidates)

# Execute as normal
result = emulator.call_tool(selected_action.tool, selected_action.args)
```

### Defining Custom Scenarios via YAML

Create a `my_scenario.yaml` file:

```yaml
scenario_id: library_ops
name: Library Management
description: Manage book loans, returns, and reservations

state_schema:
  - books
  - patrons
  - loans
  - reservations

tools:
  - name: search_books
    description: Search for books by title, author, or ISBN
    parameters:
      query: string
      field: [title, author, isbn]
    risk_level: safe
    
  - name: checkout_book
    description: Check out a book to a patron
    parameters:
      book_id: string
      patron_id: string
      due_date: date
    risk_level: medium
    
  - name: return_book
    description: Return a checked-out book
    parameters:
      loan_id: string
    risk_level: safe

tasks:
  - task_id: find_and_checkout
    instruction_generator:
      type: llm
      style: casual_request
    hidden_goal:
      action: checkout_book
      book_title: "The Pragmatic Programmer"
      patron: "Alice"
    success:
      checks:
        - type: loan_exists
          book_title: "The Pragmatic Programmer"
          patron: "Alice"
    max_steps: 5
```

Load and use your custom scenario:

```python
from agent_sim.core.registry import ScenarioRegistry

registry = ScenarioRegistry.get_instance()
registry.load_yaml("my_scenario.yaml")

emulator = OperationEmulator()
emulator.reset("library_ops", "find_and_checkout", seed=42)
```

### Analyzing Traces

After running episodes, analyze the traces to understand agent behavior:

```python
from agent_sim.eval.metrics import compute_metrics
from agent_sim.eval.error_analysis import analyze_errors

# Load trace
trace = Trace.load_json("episode_trace.json")

# Compute metrics
metrics = compute_metrics(trace)
print(f"Success: {metrics['success']}")
print(f"Invalid tool calls: {metrics['invalid_tool_rate']}")
print(f"Average steps: {metrics['avg_steps']}")

# Error analysis
errors = analyze_errors(trace)
for error in errors:
    print(f"Error at step {error['step']}: {error['type']}")
    print(f"  Expected: {error['expected']}")
    print(f"  Got: {error['actual']}")
```

---

## 📊 License

MIT License

---

## 🤝 Contributing

Contributions welcome! Please see our contribution guidelines for details.

---

**Built with the philosophy: Python maintains truth, LLM adds realism.**