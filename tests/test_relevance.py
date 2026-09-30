import pytest

from models.academic_paper import AcademicPaper
from tools.academic.relevance import normalize_query, tokenize_query, score_paper, rank_papers


def paper(title, abstract=None, **metadata):
    return AcademicPaper(title=title, abstract=abstract, source="OpenAlex", **metadata)


def test_normalization_and_technical_tokens():
    assert normalize_query(" Recent Research on Retrieval-Augmented   Generation! ") == (
        "recent research on retrieval augmented generation"
    )
    assert tokenize_query("Recent Research on Retrieval-Augmented Generation") == (
        "retrieval", "augmented", "generation"
    )
    assert tokenize_query("C++ RAG LLM BERT GPT-4 GNN") == (
        "c++", "rag", "llm", "bert", "gpt", "4", "gnn"
    )
    assert score_paper("C++", paper("C language")) == 0
    assert score_paper("RAG", paper("Storage systems")) == 0


@pytest.mark.parametrize("query,title", [
    ("retrieval augmented generation", "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"),
    ("medical image segmentation", "Medical Image Segmentation with Transformers"),
    ("graph neural network multimodal recommendation", "Graph Neural Network for Multimodal Recommendation"),
])
def test_related_titles_outrank_unrelated_and_abstract_only(query, title):
    related = score_paper(query, paper(title))
    assert related >= 0.7
    assert related > score_paper(query, paper("An unrelated study", abstract=query))
    assert related > score_paper(query, paper("Database Index Management"))


def test_rag_full_phrase_beats_partial_and_unrelated():
    query = "retrieval augmented generation"
    scores = [score_paper(query, paper(title)) for title in [
        "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "Retrieval-Augmented Language Models",
        "Generation Methods",
        "Graph Neural Networks for Collaborative Filtering",
    ]]
    assert scores[0] > scores[1] > scores[2] > scores[3]
    assert score_paper(query, paper("Retrieval Augmented Generation")) > score_paper(
        query, paper("Generation Augmented Retrieval")
    )


def test_ranking_keeps_zero_scores_and_relevance_beats_citations_and_year():
    low = paper("Image Classification", citations=10000, year=2026)
    high = paper("Retrieval Augmented Generation", citations=10, year=2020)
    ranked = rank_papers("retrieval augmented generation", [low, high])
    assert [result.paper for result in ranked] == [high, low]
    assert ranked[0].score > ranked[1].score == 0
    assert low.title == "Image Classification"


def test_ties_are_stable_and_input_is_not_reordered():
    papers = [paper("Other", citations=None), paper("Another", citations=10000)]
    ranked = rank_papers("RAG", papers)
    assert [result.paper for result in ranked] == papers
    assert papers[0].title == "Other"


@pytest.mark.parametrize("query", ["", "  !!! ", "recent research on", "RAG", "RAG RAG"])
def test_missing_metadata_and_score_bounds(query):
    for candidate in [paper(""), paper("RAG", abstract="RAG"), paper("Other")]:
        score = score_paper(query, candidate)
        assert 0 <= score <= 1
    assert score_paper(query, paper("")) == 0
    assert rank_papers(query, []) == []


def test_query_changes_ranking_and_duplicate_tokens_do_not_inflate_score():
    rag = paper("Retrieval Augmented Generation")
    medical = paper("Medical Image Segmentation")
    assert rank_papers("retrieval augmented generation", [medical, rag])[0].paper == rag
    assert rank_papers("medical image segmentation", [rag, medical])[0].paper == medical
    assert score_paper("RAG RAG", paper("RAG")) == score_paper("RAG", paper("RAG"))
