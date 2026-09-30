import json

import pytest

from models.critic_review import CriticReview
from models.evidence import Evidence
from models.evidence_store import EvidenceStore
from models.research_state import ResearchState, ResearchStatus
from models.state_store import save_state, load_state
from workers.planner import ResearchPlan, ResearchSubQuestion
from workflow import pipeline


def test_researcher_cannot_assign_store_ids():
    from workflow.stages import run_research_query

    class Runner:
        def invoke(self, query, max_turns):
            return json.dumps({"evidence": [{
                "evidence_id": "invented-invalid-id", "title": "Web evidence",
                "evidence_type": "web", "source": "Web Search", "summary": "A fact",
            }]})

    papers = run_research_query("query", runner=Runner())
    assert papers[0].evidence_id is None
    store = EvidenceStore()
    store.add_many(papers)
    assert store.get_all()[0].evidence_id == "E1"


@pytest.mark.parametrize("resume", [False, True])
def test_citations_survive_reresearch_revision_and_checkpoint(monkeypatch, tmp_path, resume):
    initial = [Evidence(title=title, evidence_type="paper", source="OpenAlex",
                        summary="Supported fact", year=2025, doi=f"10.1/{i}")
               for i, title in enumerate(["Paper A", "Paper B"])]
    plan = ResearchPlan(research_goal="goal", sub_questions=[
        ResearchSubQuestion(id=1, question="initial", search_type="paper_search"),
    ])
    review = CriticReview(overall_assessment="More evidence", issues=[],
                         evidence_gaps=["New work"], needs_research=True,
                         research_queries=["followup"], verdict="PASS_WITH_REVISIONS")
    final_review = review.model_copy(update={"needs_research": False, "research_queries": []})
    monkeypatch.setattr(pipeline, "run_planner", lambda question: plan)
    monkeypatch.setattr(pipeline, "run_critic", lambda prompt: final_review if "最终审核" in prompt else review)

    def research(query, **kwargs):
        if query == "initial":
            return initial
        return [initial[0].model_copy(update={"source": "Semantic Scholar", "evidence_id": None}),
                Evidence(title="Paper C", evidence_type="paper", source="Semantic Scholar",
                         summary="New finding", year=2024)]

    monkeypatch.setattr(pipeline, "run_research_query", research)
    prompts = []

    def writer(prompt):
        prompts.append(prompt)
        # The first '[' is the evidence JSON array, not a citation index.
        context, _ = json.JSONDecoder().raw_decode(prompt[prompt.index("["):])
        expected = ["E1", "E2", "E3"] if len(context) == 3 else ["E1", "E2"]
        assert [item["evidence_id"] for item in context] == expected
        assert [item["citation"] for item in context] == [f"[{i}]" for i in expected]
        assert context[0]["title"] == "Paper A"
        assert context[0]["doi"] == "10.1/0"
        return "Revised claim [E1][E3]." if len(context) == 3 else "Initial claim [E1][E2]."

    monkeypatch.setattr(pipeline, "run_writer", writer)
    path = tmp_path / "checkpoint.json"
    if resume:
        store = EvidenceStore()
        store.add_many(initial)
        state = ResearchState(question="test", plan=plan, evidence=store.get_all(),
                              draft_report="Initial claim [E1][E2].", critic_review=review,
                              status=ResearchStatus.RE_RESEARCHING)
        save_state(state, path)
        state = pipeline.run_research_pipeline(state=load_state(path), state_path=path)
    else:
        state = pipeline.run_research_pipeline("test", state_path=path)
    assert len(prompts) == (1 if resume else 2)

    assert [e.evidence_id for e in state.evidence] == ["E1", "E2", "E3"]
    assert state.evidence[0].source == "OpenAlex | Semantic Scholar"
    refs = state.final_report.split("## References\n", 1)[1]
    assert "[E1] Paper A" in refs and "[E3] Paper C" in refs
    assert "[E2]" not in refs
    saved = load_state(path)
    assert saved.model_dump() == state.model_dump()
    assert pipeline.run_research_pipeline(state=saved).final_report == state.final_report
    assert len(prompts) == (1 if resume else 2)


@pytest.mark.parametrize("resume", [False, True])
def test_support_gap_triggers_existing_research_and_final_validation(monkeypatch, tmp_path, resume):
    from models.critic_review import ClaimSupportCheck
    initial = Evidence(title="GraphRAG", summary="Proposes graph retrieval.",
                       evidence_type="paper", source="OpenAlex")
    new = Evidence(title="Evaluation", summary="Evaluation describes limitations.",
                   evidence_type="paper", source="Semantic Scholar")
    plan = ResearchPlan(research_goal="GraphRAG", sub_questions=[
        ResearchSubQuestion(id=1, question="initial", search_type="paper_search"),
    ])
    monkeypatch.setattr(pipeline, "run_planner", lambda question: plan)
    searches = []

    def research(query, **kwargs):
        searches.append(query)
        return [initial] if query == "initial" else [new]

    monkeypatch.setattr(pipeline, "run_research_query", research)
    draft = "Accuracy improves 35% [E1]."
    revised = "Evaluation has limitations [E2]. Missing [E999]."
    bodies = iter([revised] if resume else [draft, revised])
    monkeypatch.setattr(pipeline, "run_writer", lambda prompt: next(bodies))
    batches = []

    def critic(prompt):
        assert "## References" not in prompt
        start = prompt.index('{')
        batch, _ = json.JSONDecoder().raw_decode(prompt[start:])
        batches.append(batch)
        final = "最终审核" in prompt
        checks = [ClaimSupportCheck(
            claim_id=c["claim_id"], claim=c["claim"], evidence_ids=c["evidence_ids"],
            status="supported" if final else "partially_supported",
            reason="Summary supports limitations." if final else "No percentage in supplied evidence.",
        ) for c in batch["claims"] if c["semantic_validation"]]
        return CriticReview(overall_assessment="Review", issues=[], evidence_gaps=[],
                            needs_research=not final,
                            research_queries=[] if final else ["GraphRAG accuracy evaluation"],
                            verdict="PASS", claim_support_checks=checks)

    monkeypatch.setattr(pipeline, "run_critic", critic)
    path = tmp_path / "support_state.json"
    if resume:
        from workflow.citation_validation import validate_citations, merge_citation_review
        store = EvidenceStore()
        store.add_many([initial])
        validation = validate_citations(draft, store.get_all())
        check = ClaimSupportCheck(**validation.claims[0].model_dump(),
                                  status="partially_supported", reason="No percentage in supplied evidence.")
        old_review = CriticReview(overall_assessment="Gap", issues=[], evidence_gaps=[],
                                 needs_research=True, research_queries=["GraphRAG accuracy evaluation"],
                                 verdict="PASS_WITH_REVISIONS", claim_support_checks=[check])
        state = ResearchState(question="GraphRAG", plan=plan, evidence=store.get_all(),
                              draft_report=draft, status=ResearchStatus.RE_RESEARCHING,
                              critic_review=merge_citation_review(old_review, validation))
        save_state(state, path)
        state = pipeline.run_research_pipeline(state=load_state(path), state_path=path)
    else:
        state = pipeline.run_research_pipeline("GraphRAG", state_path=path)
    assert searches == (["GraphRAG accuracy evaluation"] if resume else ["initial", "GraphRAG accuracy evaluation"])
    assert len(batches) == (1 if resume else 2)
    assert state.critic_review.evidence_gaps
    assert state.critic_review.verdict == "PASS_WITH_REVISIONS"
    assert batches[-1]["citation_validation"]["invalid_citation_ids"] == ["E999"]
    assert batches[-1]["claims"][0]["evidence"][0]["evidence_id"] == "E2"
    assert state.final_review.citation_validation.invalid_citation_ids == ["E999"]
    assert state.final_review.verdict == "PASS_WITH_REVISIONS"
    refs = state.final_report.split("## References", 1)[1]
    assert "[E2]" in refs and "[E999]" not in refs
    restored = load_state(path)
    assert restored.model_dump() == state.model_dump()
    assert pipeline.run_research_pipeline(state=restored).final_review == state.final_review
