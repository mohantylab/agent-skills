# Skill: Document Processing

## metadata
- id: document_processing
- name: Document Processing
- folder: document_processing
- version: 1.3.0
- enabled: true
- icon: 📄
- color: #7c6af5
- category: productivity
- description: Extracts headline, key points, action items, decisions, and sentiment from meeting notes, reports, emails, and any pasted document text.
- landing_example: Summarise this meeting note or quarterly report
- landing_example_2: Extract action items from this email thread
- landing_example_3: What decisions were made in this document?

## trigger_keywords
- summarise, summarize, summary, tldr, brief, overview, key points, action items, extract, document, report, meeting, notes, email, decisions, what does this say, read this, analyse this, review this

## tools
- gcs_tool

## output_format
- headline: string           one sentence, max 20 words
- key_points: array          3-5 bullet strings
- action_items: array        concrete next steps with owner if mentioned
- decisions: array           decisions made in the document
- sentiment: string          positive | neutral | negative | mixed
- word_count: integer        approximate word count
- document_type: string      inferred type (meeting_notes | report | email | other)
