from workers.planner import ResearchPlan, ResearchSubQuestion
from workflow.report_plan import include_research_questions


def plan():
    return ResearchPlan(research_goal="目标", sub_questions=[
        ResearchSubQuestion(id=7, question="有哪些代表性方法？", search_type="paper_search"),
        ResearchSubQuestion(id=3, question="这些方法有哪些局限？", search_type="hybrid"),
    ])


def test_insert_actual_plan_questions_after_research_question():
    report = "# Research Report\n\n## 研究问题\n\n原始问题\n\n## 核心结论\n\n结论 [E1]"
    result = include_research_questions(report, plan())
    assert "## 研究子问题\n\n1. 有哪些代表性方法？\n2. 这些方法有哪些局限？" in result
    assert result.index("原始问题") < result.index("## 研究子问题") < result.index("## 核心结论")
    assert result.endswith("结论 [E1]")
    assert include_research_questions(result, plan()) == result


def test_replace_model_questions_with_actual_plan_and_support_missing_question_section():
    report = "# Report\n\n## 研究子问题\n\n1. 模型编造的问题\n\n## 结论\n\n正文"
    result = include_research_questions(report, plan())
    assert "模型编造" not in result
    assert result.count("## 研究子问题") == 1
    assert result.index("## 研究子问题") < result.index("## 结论")


def test_missing_or_empty_plan_leaves_report_unchanged():
    report = "正文"
    assert include_research_questions(report, None) == report
    assert include_research_questions(report, ResearchPlan(research_goal="目标", sub_questions=[])) == report
