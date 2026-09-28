# DeepResearch-Agent Development Guide

DeepResearch-Agent is a LangChain-based multi-agent research assistant.

## Architecture

The application uses a custom sequential Workflow Pipeline:

User -> Planner Chain -> Researcher Tool Calling -> EvidenceStore -> Writer Chain
-> Critic Chain -> additional research when needed -> Revision -> Final Review.

- `llm.py`: lazy `ChatOpenAI` factory; DeepSeek is the default provider.
- `workers/planner.py`: `ChatPromptTemplate` and structured `ResearchPlan` output.
- `workers/researcher.py`: bounded tool-calling loop with actual tool execution and `ToolMessage` feedback.
- `workers/writer.py`: LCEL prompt/model/string-parser chain for drafts and revisions.
- `workers/critic.py`: structured `CriticReview` chain with one retry for invalid output.
- `workflow/stages.py`: public `run_planner`, `run_research_query`, `run_writer`, and `run_critic` adapters.
- `workflow/pipeline.py`: domain-level orchestration, evidence aggregation, checkpoints, and memory.
- `workflow/tool_router.py`: permissions based on `SearchType`.
- `workflow/resume.py`: maps persisted status to a workflow stage.

The Pipeline does not import LangChain. Do not introduce graph orchestration.

## Search and Evidence

`tools/paper_search.py` and `tools/web_search.py` expose LangChain tools.
`paper_search` uses OpenAlex and Semantic Scholar. `web_search` uses DDGS with
backend fallback. Preserve search budgets, source formatting, deduplication,
year filtering, and the academic recommendation/multimodal/GNN relevance rules.

`PAPER_SEARCH` permits only academic search; `WEB_SEARCH` permits only web
search; `HYBRID` permits both. The Researcher executes only permitted tools,
returns tool failures to the model, and stops after eight model turns.

`Evidence` is a Pydantic model. The stage adapter validates evidence and sets
query and retrieval timestamps locally. `EvidenceStore` deduplicates and
merges metadata. Web evidence is not marked as independently verified.

## Persistence and Interfaces

- `models/research_state.py`: serializable workflow state.
- `models/state_store.py`: JSON checkpoint loading and saving.
- `memory.py`: persistent research records and text-matched Planner context.
- `main.py`: CLI with checkpoint, memory, logs, report, and review output.
- `api/server.py`: FastAPI endpoints sharing the custom Pipeline.
- `frontend/app.py`: Streamlit report and evidence presentation.

The CLI writes to `outputs/`. Completed checkpoints display the saved report
without model calls. Resume works at workflow-stage granularity; subsequent
research and revision follow the persisted review. API requests do not enable
checkpoint or memory paths by default. `/research/stream` emits accumulated
events after processing; it is not a live event stream.

## Configuration

Use Python 3.11 and install `requirements.txt` in the `deepresearch` environment.

Configure `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, and `DEEPSEEK_BASE_URL`.
The model factory sets temperature to zero and disables DeepSeek thinking mode
so named schema tools and required search calls are supported. Optional
`LLM_PROVIDER=openai` selects the corresponding `OPENAI_*` variables.

Never print credentials or commit `.env`. Keep generated outputs out of Git.

## Validation

```bash
python -m pytest -q
python -m pip check
python main.py
python main.py --resume outputs/state_YYYYMMDD_HHMMSS.json
python -m uvicorn api.server:app --reload
python -m streamlit run frontend/app.py
```

Tests use offline model completions, real LangChain chains and tools, local
ASGI transports, and Streamlit AppTest. Live provider checks are separate.
Keep all tests; validate public signatures and domain output types when
changing model components. Do not change search business rules to make a
smoke test return more results.

## Operational Limits

Academic providers can rate-limit requests. Fixed topic filtering can yield
no academic evidence. Tool counters are process-local and the demo assumes
a local single-user session. Completed workflow status is distinct from a
passing review. Model-generated reports still require source checking.
