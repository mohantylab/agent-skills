# Skill: Code Assistant

## metadata
- id: code_assistant
- name: Code Assistant
- folder: code_assistant
- version: 1.0.0
- enabled: true
- icon: 💻
- color: #f5a623
- category: engineering
- description: Reviews code for bugs and quality issues, generates boilerplate, explains complex code snippets, and converts pseudocode to working Python or SQL.
- landing_example: Review this Python function for bugs
- landing_example_2: Convert this pseudocode to Python
- landing_example_3: Explain what this SQL query does

## trigger_keywords
- code, review, bug, function, python, sql, script, refactor, explain this, convert, implement, write a function, generate, boilerplate, class, api, error, exception, test, unit test, what does this code do

## tools
- gcs_tool

## output_format
- action: string         review | generate | explain | convert
- language: string       python | sql | javascript | other
- result: string         the code output or explanation
- issues: array          list of bugs/issues found (for review)
- suggestions: array     improvement suggestions
- explanation: string    plain English explanation
