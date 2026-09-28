"""Adapt LangChain role calls to the custom workflow domain objects."""

import json
from datetime import datetime, timezone

from workers.planner import create_planner_chain, ResearchPlan
from workers.researcher import create_researcher_agent
from workers.writer import create_writer_chain
from workers.critic import create_critic_chain
from models.evidence import Evidence
from models.critic_review import CriticReview
from models.search_type import SearchType

def safe_json_loads(text: str):
    text = text.strip()
    if not text:
        return {'evidence': []}
    if '```json' in text:
        text = text.split('```json', 1)[1].split('```', 1)[0].strip()
    elif '```' in text:
        text = text.split('```', 1)[1].split('```', 1)[0].strip()
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print('\n[JSON PARSE FAILED]')
        print(text)
        raise

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def run_planner(question: str, memory_context: str = '', runner=None) -> ResearchPlan:
    """Run the Planner chain; runner optionally injects a LangChain Runnable."""
    chain = create_planner_chain() if runner is None else runner
    result = chain.invoke({'question': question, 'memory_context': memory_context})
    return ResearchPlan.model_validate(result)

def run_writer(prompt: str, runner=None) -> str:
    """Run the Writer chain; runner optionally injects a LangChain Runnable."""
    chain = create_writer_chain() if runner is None else runner
    return chain.invoke({'prompt': prompt})

def run_critic(prompt: str, runner=None) -> CriticReview:
    """Run the Critic chain; runner optionally injects a LangChain Runnable."""
    chain = create_critic_chain() if runner is None else runner
    result = chain.invoke({'prompt': prompt})
    return CriticReview.model_validate(result)

def run_research_query(
    query: str,
    search_type=None,
    runner=None,
    clock=utc_now,
) -> list[Evidence]:
    """Execute permitted tools and attach locally generated evidence metadata."""
    if search_type is None:
        search_type = SearchType.PAPER_SEARCH
    agent = create_researcher_agent(search_type)
    executor = agent if runner is None else runner
    raw_output = executor.invoke(query, max_turns=8)
    try:
        data = safe_json_loads(raw_output)
    except json.JSONDecodeError:
        data = {'evidence': []}
    evidence_list = []
    for item in data.get('evidence', []):
        item.setdefault('evidence_type', 'paper')
        item.setdefault('source', 'OpenAlex')
        item.setdefault('summary', item.get('abstract', ''))
        evidence_list.append(Evidence.model_validate(item))
    retrieved_at = clock().isoformat(timespec='seconds')
    for evidence in evidence_list:
        evidence.query = query
        evidence.retrieved_at = retrieved_at
    return evidence_list

def run_research_stage(plan: ResearchPlan, runner=None) -> list[Evidence]:
    """
    执行 ResearchPlan 中的全部子问题，
    汇总所有 Evidence。
    """
    all_evidence: list[Evidence] = []
    for sub_question in plan.sub_questions:
        evidence_list = run_research_query(
            query=sub_question.question,
            search_type=sub_question.search_type,
            runner=runner,
        )
        all_evidence.extend(evidence_list)
    return all_evidence
