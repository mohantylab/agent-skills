# Instructions: Web Research Skill

## What this skill does
Provides structured research briefs on any topic:
- Market trends and industry news
- Competitor overviews and comparisons
- Technology landscape assessments
- Company or product background research

## How to use
Ask any research question in plain English:
- "What are the latest trends in enterprise SaaS pricing?"
- "Give me a competitive overview of the top 3 CRM vendors"
- "What is the current adoption rate of generative AI in healthcare?"

## Output explained
- **Answer**: Direct 2-3 sentence response to your question
- **Key findings**: 3-5 bullet facts you can use in presentations
- **Sources**: Where to verify each finding
- **Confidence**: How reliable the answer is (high/medium/low)
- **Caveat**: What to double-check before using in a presentation

## Best for
- Pre-meeting briefings
- Market sizing estimates
- Competitor intelligence
- Technology assessments
- Industry trend summaries

## Developer notes
- Tool: vertex_search_tool → Vertex AI Search with grounding
- Prompts: PROMPT.md → research_prompt or competitive_research_prompt
- The skill auto-selects competitive_research_prompt when keywords like "competitor", "vs", "compare" are present
