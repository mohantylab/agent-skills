# Instructions: Code Assistant Skill

## What this skill does
Helps engineers with three types of tasks:
- **Review**: Finds bugs, security issues, and style problems in existing code
- **Generate**: Creates boilerplate, functions, classes, and scripts from a description
- **Explain**: Translates complex code into plain English

## How to use

### Code review
Paste your code and ask for a review:
- "Review this Python function for bugs"
- "Check this SQL query for security issues"
- "What's wrong with this code: [paste code]"

### Code generation
Describe what you need:
- "Write a Python function that reads a CSV and uploads it to BigQuery"
- "Generate a FastAPI endpoint for user login with JWT"
- "Create a Cloud Run Dockerfile for a Python app"

### Code explanation
Paste code and ask what it does:
- "Explain what this SQL query does"
- "Walk me through this Python class"
- "What does this regex match?"

## Supported languages
Python, SQL (BigQuery, Postgres), JavaScript, TypeScript, YAML, Bash, Terraform HCL

## Developer notes
- Tool: gcs_tool (saves generated code to GCS on request)
- Prompts: PROMPT.md → review_prompt | generate_prompt | explain_prompt
- Action is auto-detected from the question keywords
- To add a language: update trigger_keywords in SKILL.md
