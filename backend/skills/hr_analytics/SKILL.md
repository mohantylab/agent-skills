# Skill: HR Analytics

## metadata
- id: hr_analytics
- name: HR Analytics
- folder: hr_analytics
- version: 1.0.0
- enabled: true
- icon: 👥
- color: #e879a0
- category: people_analytics
- description: Answers workforce questions by querying HR data in BigQuery — headcount, attrition, hiring pipeline, compensation bands, and team composition.
- landing_example: What is our current headcount by department?
- landing_example_2: Show me attrition rate by team for last 6 months
- landing_example_3: How many open roles are in engineering?

## trigger_keywords
- headcount, employees, staff, attrition, turnover, hiring, pipeline, roles, departments, teams, compensation, salary, band, people, workforce, hires, joiners, leavers, tenure, diversity, org chart

## tools
- bigquery_tool

## schema_hint
Table: employees
  - employee_id STRING, name STRING, department STRING, team STRING
  - level STRING (L1-L8), start_date DATE, status STRING (active/inactive)
  - manager_id STRING, location STRING, cost_center STRING

Table: attrition_events
  - employee_id STRING, departure_date DATE, reason STRING
  - voluntary BOOLEAN, department STRING, tenure_months INT64

Table: open_roles
  - role_id STRING, title STRING, department STRING, level STRING
  - opened_date DATE, status STRING (open/filled/cancelled), recruiter STRING

Table: compensation
  - employee_id STRING, base_salary FLOAT64, band STRING
  - effective_date DATE, currency STRING

## output_format
- summary: string       plain English workforce insight
- sql: string           generated SQL
- rows: array           result data rows
- row_count: integer
- privacy_note: string  reminder if PII handling needed

## privacy_rules
- Never return individual employee names with salary data in the same row
- Aggregate results to team/department level unless the user is authenticated as HR_ADMIN
- Add privacy_note when query touches compensation table
