# Instructions: HR Analytics Skill

## What this skill does
Answers People Analytics questions using live HR data from BigQuery:
- Headcount by department, team, level, or location
- Attrition rates and departure patterns
- Open roles and hiring pipeline status
- Compensation band distribution (aggregated, never individual)
- Tenure and workforce composition

## Access levels
- **Standard users**: Can query headcount, attrition, open roles
- **HR_ADMIN role**: Can also access compensation data (still aggregated)

## Example questions
1. "What is our total headcount by department?"
2. "Which teams had the highest attrition in Q3?"
3. "How many open roles do we have in Engineering and what levels?"
4. "Show me average tenure by department"
5. "What is the headcount trend over the last 12 months?"

## Privacy rules built into this skill
- Individual salaries are never shown — only band/department aggregates
- Employee names are never combined with compensation data
- All compensation queries include a privacy reminder in the output

## Supported metrics
| Metric | How to ask |
|--------|-----------|
| Headcount | "How many people in [team/dept]?" |
| Attrition rate | "What is attrition rate for [team] last [period]?" |
| Hiring pipeline | "How many open roles in [dept]?" |
| Tenure | "Average tenure in [dept]?" |
| Level distribution | "Show me level breakdown in [team]" |

## Developer notes
- Tool: bigquery_tool → MCP Toolbox → BigQuery (HR dataset)
- Privacy enforcement: skill_loader checks privacy_rules section before executing
- The orchestrator passes user role to the skill; HR_ADMIN bypasses some aggregation limits
- Prompts: PROMPT.md → sql_generation_prompt + summary_prompt (or attrition_analysis_prompt for attrition queries)
