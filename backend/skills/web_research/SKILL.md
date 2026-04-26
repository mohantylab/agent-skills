# Skill: Web Research

## metadata
- id: web_research
- name: Web Research
- folder: web_research
- version: 1.1.0
- enabled: true
- icon: 🔍
- color: #2dd4bf
- category: research
- description: Searches for current information using Vertex AI Search and returns a structured research brief with key findings and cited sources.
- landing_example: What are the latest enterprise AI trends?
- landing_example_2: Competitor overview for Salesforce CRM
- landing_example_3: Current GCP vs AWS cloud pricing comparison

## trigger_keywords
- search, find, look up, latest, current, news, what is, who is, recent, today, market, competitor, industry, trend, research, overview of, background on, tell me about

## tools
- vertex_search_tool

## output_format
- answer: string           direct 2-3 sentence answer
- key_findings: array      3-5 factual findings
- sources: array           source descriptions
- confidence: string       high | medium | low
- caveat: string           limitations to verify
