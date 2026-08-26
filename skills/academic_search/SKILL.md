# Academic Search Skill

## Purpose

Use this skill when the user asks for academic papers,
literature reviews, publication information, citation counts,
authors, venues, DOI information, or research trends.

## Search Strategy

1. Identify the core research topic from the user's question.

2. Extract explicit time constraints.
   For example:
   - "2024 to 2026" → start_year=2024, end_year=2026
   - "recent three years" → infer the corresponding year range.

3. Build focused academic queries.
   Avoid overly broad queries.

   Bad query:
   - graph neural network

   Better query:
   - multimodal recommendation graph neural network

4. For academic literature, use paper_search before web_search.

5. Do not repeat semantically equivalent search queries.

6. Search at most three times unless explicitly required otherwise.

When calling paper_search, always provide:

- query
- start_year
- end_year

Example:

paper_search(
    query="multimodal recommendation graph neural network",
    start_year=2024,
    end_year=2026
)

## Relevance Rules

A returned paper should match the user's topic,
not merely contain one isolated keyword.

For a query about GNN-based multimodal recommendation,
prefer papers that are related to all of the following:

- recommender systems or recommendation
- multimodal or multimedia information
- graph neural networks, graph learning, graph convolution,
  graph attention, or related graph-based methods

Reject obviously unrelated domains such as:

- medical image segmentation
- brain tumor analysis
- time-series anomaly detection
- generic GNN surveys unrelated to recommendation

## Time Filtering

Extract the user's requested publication time range.

Examples:

- "2024 to 2026"
  → start_year=2024, end_year=2026

- "from 2024 to now"
  → start_year=2024, end_year=current year

- "since 2024"
  → start_year=2024, end_year=current year

- "recent three years"
  → infer the three-year range ending in the current year

Do not hard-code the current year in the skill.
Resolve it dynamically at runtime.

## Citation Reliability

Never estimate or invent citation counts.

Citation counts may only be reported when returned
by an academic database tool.

If citation data is unavailable, write:

"citation count unavailable"

## Source Priority

Prefer:

1. Academic database metadata
2. Official conference or journal pages
3. arXiv
4. Author or official GitHub repositories
5. General web search only as a fallback

## Output

When the user asks for a paper list, prefer reporting:

- Title
- Authors
- Year
- Venue if verified
- Citation count if verified
- DOI
- URL

Clearly separate verified metadata from background knowledge.