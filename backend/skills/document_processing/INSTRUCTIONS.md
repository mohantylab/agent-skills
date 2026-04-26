# Instructions: Document Processing Skill

## What this skill does
Analyses any text — meeting notes, reports, emails, proposals — and extracts:
- A one-sentence headline summarising the whole document
- 3–5 key points the reader needs to know
- Explicit action items with owners and due dates where mentioned
- Decisions that were made
- Overall sentiment

## How to use
Paste your document text directly into the chat. The agent detects the content automatically.

You can also ask follow-up questions after the summary:
- "Who owns the pricing action item?"
- "What was decided about the product roadmap?"
- "Translate the key points to French"

## Example inputs
1. Paste a full meeting note → get structured summary + action items
2. "Summarise this: [paste email chain]" → get headline + decisions
3. "Extract action items from: [paste Slack thread]" → get just the tasks
4. Paste a 10-page quarterly report → get executive summary

## Tips
- Longer documents produce better summaries — paste the full text
- If an action item has an owner, the skill will extract them: "John to update pricing by Friday"
- Works in any language (output is translated to English)

## Developer notes
- Tool: gcs_tool (for saving results to GCS if needed)
- Prompts: PROMPT.md → analysis_prompt
- Output: JSON parsed into structured result object
- To extend: add fields to output_format in SKILL.md and update analysis_prompt in PROMPT.md
