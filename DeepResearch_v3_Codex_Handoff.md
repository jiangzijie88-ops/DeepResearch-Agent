# DeepResearch-Agent v3 → Codex 交接文档

> 用途：把当前 DeepResearch-Agent v3 的真实状态、架构、已完成功能、已知问题和收尾任务交给 Codex，避免重新猜项目结构。
>
> 项目目标：用于求职展示的大模型智能体项目。v3 的目标不是继续无限加功能，而是完成一个**可运行、可测试、可网页展示、可放 GitHub README 的 Web Demo 版本**。更高级的 RAG/向量记忆、真正实时流、并行 Agent、Human-in-the-loop 等放到 v4。

---

## 1. 当前仓库与环境

- 项目名：`DeepResearch-Agent`
- 本地路径：`D:\AIProgects\GitProjects\DeepResearch-Agent`
- Conda 环境：`deepresearch`
- Python：3.11.15
- Git 分支：`main`
- GitHub：`jiangzijie88-ops/DeepResearch-Agent`
- 当前最近提交：
  - `3c36c35 fix: move critic persistence into workflow`
  - `4ea4b3d feat: implement DeepResearch v2 multi-agent workflow`
  - `c3d73ef docs: add project README`
  - `c50ba60 feat: complete DeepResearch v1`
- v3 目前大量改动尚未统一 commit；用户此前要求 **v3 完成后再统一 commit/push**。
- `.env` 在项目里但已被 `.gitignore` 忽略，**不要读取后写入日志、不要提交、不要展示密钥内容**。

### 启动命令

后端 FastAPI：

```bash
conda activate deepresearch
cd D:\AIProgects\GitProjects\DeepResearch-Agent
uvicorn api.server:app --reload
```

前端 Streamlit：

```bash
conda activate deepresearch
cd D:\AIProgects\GitProjects\DeepResearch-Agent
streamlit run frontend/app.py
```

地址：

- Web UI：`http://localhost:8501`
- FastAPI：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`

---

## 2. v1 / v2 / v3 演进

### v1：基础 Research Agent

单 Agent + 工具调用：

```text
User → Research Agent → paper_search / web_search → Answer
```

重点：LLM 抽象、OpenAlex、DDGS、多轮搜索、基本工具调用。

### v2：Multi-Agent Workflow

```text
User
 ↓
Planner
 ↓
Researcher
 ↓
Evidence
 ↓
Writer
 ↓
Critic
 ↓
Re-Research（可选）
 ↓
Revision
 ↓
Final Critic
 ↓
Final Report
```

重点：Planner / Researcher / Writer / Critic 分工、EvidenceStore、CLI 工作流。

### v3：工程化 + Web 产品化

核心新增：

- `ResearchState`：统一任务状态
- `StateStore`：JSON checkpoint 持久化
- `Resume`：断点恢复
- Evidence Schema 增强 + 去重/元数据合并
- OpenAlex + Semantic Scholar 多源学术检索
- Provider fallback（单源失败不让系统整体失败）
- `SearchType` + `ToolRouter`
- Planner-driven Tool Routing
- Dynamic Researcher Agent / Tool Permission
- Researcher 严格 Evidence JSON 输出
- LLM JSON 容错解析
- 轻量长期 Memory 模块
- FastAPI
- Streamlit Web UI
- 大量 pytest 单元测试

---

## 3. 当前真实目录结构（重点）

```text
DeepResearch-Agent/
├── api/
│   └── server.py
├── frontend/
│   └── app.py
├── memory/
│   ├── memory_context.py
│   ├── memory_item.py
│   ├── memory_storage.py
│   └── memory_store.py
├── models/
│   ├── academic_paper.py
│   ├── critic_review.py
│   ├── evidence.py
│   ├── evidence_store.py
│   ├── research_state.py
│   ├── search_type.py
│   └── state_store.py
├── scripts/
│   └── manual_workflow.py
├── skills/
│   └── academic_search/SKILL.md
├── tests/
│   └── 多个 pytest 文件
├── tools/
│   ├── academic/
│   │   ├── aggregator.py
│   │   ├── openalex.py
│   │   └── semantic_scholar.py
│   ├── paper_search.py
│   └── web_search.py
├── workers/
│   ├── critic.py
│   ├── planner.py
│   ├── researcher.py
│   ├── researcher_factory.py
│   └── writer.py
├── workflow/
│   ├── cli.py
│   ├── pipeline.py
│   ├── researcher_factory.py   # 旧重复文件，当前无引用，候选删除
│   ├── research_stage.py       # 仅测试/历史抽象层使用，主流程未真正使用
│   ├── resume.py
│   ├── stages.py
│   └── tool_router.py
├── llm.py
├── main.py
├── README.md
├── requirements.txt
└── .gitignore
```

---

## 4. 当前两条 Workflow：必须理解

当前不是完全统一的一条 Workflow，而是两条：

### A. CLI 完整流程：`main.py`

这是功能最完整的一条：

```text
CLI input
 ↓
Memory retrieval
 ↓
Planner
 ↓
EvidenceStore + Researcher
 ↓
Writer
 ↓
Critic
 ↓
Critic-guided Re-Research（可选）
 ↓
Writer Revision
 ↓
Final Critic
 ↓
保存 report / critic / memory / state
 ↓
COMPLETED
```

CLI 已包含：

- StateStore / checkpoint
- Resume
- EvidenceStore 去重
- tool budget reset
- Critic 补搜
- Revision
- Final Critic
- Memory read/write
- 最终报告落盘

### B. Web 简化流程：`workflow/pipeline.py`

网页实际走：

```text
Streamlit
 ↓
FastAPI
 ↓
run_research_pipeline()
 ↓
Planner
 ↓
Dynamic Researcher
 ↓
Writer
 ↓
Critic
 ↓
ResearchState return
```

当前 Web Pipeline **没有完整使用**：

- StateStore checkpoint
- Resume
- CLI 的完整 EvidenceStore 流程
- Memory
- Critic-guided re-research
- Revision
- Final Critic
- final report file persistence

### v3 收尾原则

**不要为了“架构完美”在 v3 重新大规模重构 main.py。**

v3 建议明确定位：

- CLI = Advanced Workflow（完整功能）
- Web = Demo Workflow（展示型）
- v4 再考虑真正统一为单一 Pipeline

---

## 5. 关键模块原理

### ResearchState

`models/research_state.py`

统一保存：

- question
- plan
- tool_routes
- evidence
- draft_report
- critic_review
- research_round
- status
- final_report
- final_review

它是“当前任务存档内容”。

### StateStore

`models/state_store.py`

- `save_state(state, path)`
- `load_state(path)`

把 `ResearchState` JSON 化并保存/恢复。CLI 的 checkpoint 真实使用该模块。

### Evidence

Evidence 不是“论文”的同义词，而是 Agent 找到的一条**结构化、可追溯的证据记录**。

统一字段包括：title、evidence_type、year、citations、source、doi、url、summary、verified、authors、venue、published_at、retrieved_at、query、confidence 等。

Researcher → Evidence → EvidenceStore → Writer/ Critic。

### EvidenceStore

负责 DOI / URL / normalized title+year 去重，以及元数据合并。

### ToolRouter

Planner 输出 `SearchType`：

- `paper_search`
- `web_search`
- `hybrid`

`ToolRouter` 决定允许的工具；`workers/researcher_factory.py` 再动态创建 Researcher Agent。

### Dynamic Researcher

`workers/researcher_factory.py`

按照 Planner 的 `search_type` 动态赋予工具权限，而不是所有 Researcher 都拿到所有工具。

### Researcher JSON Contract

`workers/researcher.py` 中 `RESEARCHER_INSTRUCTIONS` 是当前唯一应使用的 Researcher 行为规范。

它严格要求：

- 只输出合法 JSON
- 不要 Markdown / 解释文字
- year/citations 类型正确
- 没结果时返回 `{"evidence": []}`

`workers/researcher_factory.py` 已复用该统一 prompt。

### safe_json_loads

`workflow/stages.py`

用于清理 LLM 可能输出的 markdown code block / 包裹文本，并解析 JSON。

`run_research_query()` 对非法 JSON 有 fallback：按 0 条 evidence 处理，避免 Web 500。

### Mock / Fake

测试里使用 FakeRunner / monkeypatch 替代真实 LLM、网络和 pipeline，让 pytest 快速稳定，不每次真实消耗 API/token。

---

## 6. 已经验证成功的能力

真实 Web E2E 已经跑通：

```text
Browser
 ↓
Streamlit
 ↓
FastAPI
 ↓
Pipeline
 ↓
Planner
 ↓
ToolRouter
 ↓
Dynamic Researcher
 ↓
OpenAlex / Semantic Scholar / Web Search
 ↓
Evidence
 ↓
Writer
 ↓
Critic
 ↓
FastAPI JSON
 ↓
Streamlit Research Report
```

曾成功输出真实 Research Report，并显示非零 Evidence Count。

Tool Budget bug 已修：每个 sub-question 开始前会 `reset_search_count()` 和 `reset_paper_search_count()`。

Semantic Scholar 经常 429/网络错误，但 aggregator 有 fallback，OpenAlex 可继续工作。

---

## 7. 当前已知问题 / 技术债（Codex 优先处理）

### P0：必须收尾

1. **`models/research_state.py` mutable default**

当前：

```python
tool_routes: dict[str, list[str]] = {}
```

改为：

```python
tool_routes: dict[str, list[str]] = Field(default_factory=dict)
```

2. **`api/server.py` mutable default**

当前：

```python
evidence: list = []
```

改为 Pydantic `Field(default_factory=list)`。

3. **`main.py` 重复/无用 import**

- `load_memory` 重复 import
- `run_research_stage` import 当前未实际使用

4. **`workflow/pipeline.py` Web evidence 目前直接 list.extend，无 EvidenceStore 去重**

Web 应至少引入 `EvidenceStore`，使 Web 和 CLI 的 evidence 管理行为一致。

5. **Web pipeline status 语义不一致**

现在 Critic 完成后仍是 `REVIEWING`，却 emit `Research completed`。

若 v3 Web 到 Critic 即结束，返回前应设置：

```python
state.status = ResearchStatus.COMPLETED
```

6. **Writer 输入格式**

当前 `pipeline.py` 仍直接把 `{evidence}`（Pydantic 对象列表字符串）放进 prompt。

建议改为：

```python
evidence_json = json.dumps(
    [item.model_dump() for item in evidence],
    ensure_ascii=False,
    indent=2,
)
```

再注入 Writer Prompt。

### P1：Web 展示收尾

7. **Streamlit 展示 Evidence 表格**

API 已返回 `evidence`，但 `frontend/app.py` 只展示 report + evidence_count。

建议增加一个可折叠/表格区域，至少列：

- Title
- Year
- Citations
- Venue
- Source
- Verified

8. **错误提示更具体**

前端目前只有 `Research failed`，建议显示 status code / response text（注意不要泄漏 secret）。

9. **`/research/stream` 不是真正实时流**

当前是 pipeline 全部跑完后，再统一 yield `events`。

v3 不建议重构成真正 SSE/async queue；可：

- 保留接口但 README 明确为 event callback prototype；或
- 暂时不在 README 宣称 “real-time streaming”。

真正实时流放 v4。

### P1：仓库清理

10. **`workflow/researcher_factory.py` 是旧重复文件，当前没有任何 import 引用**

真正使用的是：

```text
workers/researcher_factory.py
```

建议确认测试后删除 `workflow/researcher_factory.py`。

11. **`workflow/research_stage.py` 当前主流程未使用**

仅有 `tests/test_research_stage.py` 和 `main.py` 的无用 import 关联。

可以二选一：

- v3 保留作为实验抽象层，并在注释说明；或
- 删除文件 + 对应测试，减少复盘负担。

倾向：如果目标是项目瘦身，可删除，但删除前先 grep 全仓引用、跑全量测试。

12. 删除/忽略本地缓存：

- `__pycache__/`
- `.pytest_cache/`
- `outputs/`

它们已经大多在 `.gitignore`，不要 commit。

### P1：依赖文件

13. **`requirements.txt` 当前缺 Web v3 依赖**

现在只有：

```text
openai-agents
openai
python-dotenv
pydantic
requests
ddgs
```

至少还应加入：

```text
fastapi
uvicorn
streamlit
pytest
```

如测试客户端有显式依赖，也需确认环境后补齐。

### P2：README

14. 当前 README 基本只有两条启动命令，不够用于求职展示。

v3 README 至少应包含：

- 项目简介
- v1 → v2 → v3 演进
- 架构图（ASCII/mermaid）
- 核心能力
- 技术栈
- 目录结构
- 快速开始
- CLI 与 Web 区别
- Web 截图
- 示例研究问题
- 测试命令
- 已知限制
- v4 Roadmap

---

## 8. 不要在 v3 做的事情

为避免 scope creep，Codex 在 v3 收尾阶段不要主动加入：

- FAISS / Vector DB / Embedding RAG
- 真正实时 SSE/WebSocket streaming
- 并行 Research Agent
- Human-in-the-loop
- Docker 部署（可选项，不是必须）
- 大规模重构 `main.py` 成类
- 替换整个 Agent 框架

这些放 v4。

---

## 9. 建议的 Codex 收尾顺序

严格按小步执行，每步都跑测试：

### Step A：小清理

- 修 mutable defaults
- 清 main.py 重复 import
- 确认并删除 stale `workflow/researcher_factory.py`
- 决定是否删除 `workflow/research_stage.py`

运行：

```bash
python -m py_compile main.py workflow/pipeline.py api/server.py models/research_state.py
python -m pytest -v
```

### Step B：Web Pipeline 质量对齐

- 引入 `EvidenceStore`
- Writer 输入改成 JSON
- Critic 结束后 status → `COMPLETED`
- 保持 tool budget reset
- 不新增真实网络测试

### Step C：Web UI 展示

- report 用 Markdown 渲染
- Evidence 表格
- 更清晰的错误信息
- 不强行做真 streaming

### Step D：依赖 + README

- 补 requirements
- README 完整重写
- 补运行截图位置说明

### Step E：最终验证

```bash
python -m pytest -v
python -m py_compile main.py workflow/pipeline.py api/server.py frontend/app.py
```

手动：

1. CLI 跑一个小问题
2. FastAPI `/docs` 正常
3. Streamlit 输入小问题得到 report + evidence

### Step F：Git

用户明确希望 v3 最终完成后再提交。

先检查：

```bash
git status
git diff --stat
```

确认 `.env`、outputs、缓存没有进入 staged 内容。

建议最终 commit：

```bash
git add .
git commit -m "feat: complete DeepResearch v3 web agent platform"
git push
```

**不要在未经用户确认前自动 commit/push。**

---

## 10. 当前测试哲学

- 单元测试优先 FakeRunner / monkeypatch
- 不在普通 pytest 中真实请求 LLM / OpenAlex / Web
- 真实 E2E 只做少量手动验证
- 已经有 100+ 测试，不要为了“文件少”删除测试目录

测试是项目工程化卖点，不是垃圾文件。

---

## 11. Codex 工作方式要求（很重要）

用户希望：

1. **先读实际文件，不要猜代码结构**。
2. 修改前说明：
   - 改哪个文件
   - 为什么改
   - 具体替换什么
3. 一次只做一个小阶段，避免大爆改。
4. 遇到失败先定位 root cause，再改代码。
5. 尽量 TDD / 小步验证。
6. 不要频繁跑真实 API；真实检索慢、会限流。
7. 不要碰 `.env` 内容，不要打印 secret。
8. v3 收尾优先稳定和可展示，不追求过度工程化。
9. 不要自动 commit/push，先让用户确认。

---

## 12. 给 Codex 的直接任务提示词

可以把下面这一段直接粘给 Codex：

> 我正在维护 `D:\AIProgects\GitProjects\DeepResearch-Agent`。这是一个用于求职展示的多智能体 DeepResearch 项目，目前处于 v3 Web 版收尾阶段。请先完整阅读仓库，再严格按照 `DeepResearch_v3_Codex_Handoff.md` 的现状和优先级工作，不要凭空假设文件结构。
>
> 当前目标不是开发 v4，而是把 v3 稳定收尾：修复小型工程问题、让 Web Pipeline 使用 EvidenceStore、修正 status、用 JSON 传 Evidence 给 Writer、完善 Streamlit Evidence 展示、补 requirements、重写 README、跑全量测试并做最终手动验证。
>
> 请避免大规模重构 `main.py`；CLI 完整 Workflow 和 Web Demo Workflow 在 v3 可以暂时并存。RAG、FAISS、真正实时 streaming、并行 Agent、Human-in-the-loop 放 v4。
>
> 每一步先说明你准备改哪些文件和原因，再执行；遇到失败先做 root-cause 分析。普通 pytest 必须使用 mock/fake，避免真实 LLM/网络调用。不要读取或提交 `.env`，不要自动 commit/push，最终提交前先让我确认。
>
> 先从“v3 收尾 Step A：小清理与结构检查”开始，并先运行 `git status`、检查当前测试，再给出最小修改计划。

---

## 13. 一句话项目介绍（README/面试可用）

> DeepResearch-Agent is a multi-agent research assistant that decomposes complex research questions, dynamically routes tasks to academic/web tools, aggregates and validates evidence, generates structured reports, critiques outputs, supports persistent CLI state and resume, and exposes a FastAPI + Streamlit Web demo.

中文：

> DeepResearch-Agent 是一个面向科研检索场景的多智能体研究助手，通过 Planner 拆解任务、Tool Router 动态分配搜索能力、Researcher 收集结构化证据、Writer 生成报告、Critic 审核结果，并在 CLI 端支持状态持久化与断点恢复，同时提供 FastAPI + Streamlit Web Demo。

---

## 14. v4 Roadmap（只记录，不在 v3 实现）

- Semantic / Vector Memory：Embedding + FAISS
- 真正实时 Streaming：SSE / async queue
- 并行子问题 Research Agent
- Human-in-the-loop Planner approval
- Agent Evaluation / benchmark
- 更完善的 citation grounding
- Docker / cloud deployment

