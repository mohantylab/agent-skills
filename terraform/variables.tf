variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Primary GCP region"
  type        = string
  default     = "us-central1"
}

variable "env" {
  description = "Environment: dev | staging | prod"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "Application name prefix for all resources"
  type        = string
  default     = "skill-agent"
}

variable "bq_dataset" {
  description = "BigQuery dataset name"
  type        = string
  default     = "analytics"
}

variable "cloud_sql_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-g1-small"
}

variable "cloud_sql_db_name" {
  description = "Postgres database name"
  type        = string
  default     = "skill_agent"
}

variable "cloud_sql_user" {
  description = "Postgres application user"
  type        = string
  default     = "skill_agent_app"
}

variable "cloud_run_min_instances" {
  description = "Cloud Run minimum instances (set >0 to avoid cold starts)"
  type        = number
  default     = 1
}

variable "cloud_run_max_instances" {
  description = "Cloud Run maximum instances"
  type        = number
  default     = 10
}

variable "toolbox_image" {
  description = "MCP Toolbox Docker image"
  type        = string
  default     = "us-docker.pkg.dev/cloud-sql-connectors/cloud-sql-proxy/cloud-sql-proxy:latest"
}

variable "token_ttl_hours" {
  description = "Session token TTL in hours"
  type        = number
  default     = 8
}

variable "alert_email" {
  description = "Email address for Cloud Monitoring alerts"
  type        = string
  default     = ""
}
