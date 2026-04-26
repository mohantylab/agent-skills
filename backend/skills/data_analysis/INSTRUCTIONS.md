# Instructions: Data Analysis Skill

## What this skill does
Answers questions about your business data stored in BigQuery.
Ask in plain English — no SQL knowledge needed.

## Best question formats
- "Show me [metric] by [dimension] for [time period]"
- "What is the [top/bottom] N [things] by [metric]?"
- "How does [thing A] compare to [thing B] over [period]?"
- "What is the trend of [metric] over the last [N] months?"

## Available data
This skill can query:
- **Sales data**: revenue, units sold, by region, product, date
- **Customer data**: signups, plan type (free/pro/enterprise), region
- **Order data**: order amounts, status, timestamps

## Example questions
1. "Show me total revenue by region for the last 90 days"
2. "Which product had the most units sold in January?"
3. "How many enterprise customers signed up this year vs last year?"
4. "What is the month-over-month revenue trend for APAC?"
5. "Top 10 customers by lifetime order value"

## Tips for best results
- Be specific about time periods: "last quarter", "year to date", "last 30 days"
- Mention the dimension you want to group by: "by region", "by product", "by plan"
- If you want a specific number of rows: "top 5", "bottom 10"

## Limitations
- Cannot modify data (SELECT only)
- Cannot join external data sources not in BigQuery
- Results are capped at 100 rows by default (ask for more if needed)

## Developer notes
- Tool: bigquery_tool → MCP Toolbox → BigQuery
- Prompts: PROMPT.md → sql_generation_prompt + summary_prompt
- Schema: defined in SKILL.md → schema_hint section
- To add tables: edit schema_hint in SKILL.md, call POST /skills/data_analysis/reload
