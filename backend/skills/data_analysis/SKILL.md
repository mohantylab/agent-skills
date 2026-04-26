# Skill: Data Analysis

## metadata
- id: data_analysis
- name: Data Analysis
- folder: data_analysis
- version: 2.0.0
- enabled: true
- icon: 📊
- color: #4f8ef7
- category: analytics
- description: Converts natural language questions into BigQuery SQL queries, executes them via MCP Toolbox, and returns insights with a summary and data table.
- landing_example: Show me revenue by region for last quarter
- landing_example_2: Which product had the highest growth in January?
- landing_example_3: Compare enterprise vs pro customer signups YTD

## trigger_keywords
- revenue, sales, orders, units, customers, region, product, top, total, count, average, trend, growth, how many, how much, which, compare, breakdown, query, data, analytics, report, metrics, kpi, performance

## tools
- bigquery_tool

## schema_hint
Table: sales
  - date DATE, region STRING, product STRING, revenue FLOAT64, units_sold INT64
Table: customers
  - customer_id STRING, signup_date DATE, region STRING, plan STRING (free/pro/enterprise)
Table: orders
  - order_id STRING, customer_id STRING, amount FLOAT64, created_at TIMESTAMP, status STRING

## output_format
- summary: string       plain English insight (2-3 sentences)
- sql: string           generated BigQuery SQL
- rows: array           result data rows
- row_count: integer    total rows returned
- chart_hint: string    suggested chart type (bar/line/pie)
