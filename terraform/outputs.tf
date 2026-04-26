output "orchestrator_url" {
  description = "Backend API URL"
  value       = google_cloud_run_v2_service.orchestrator.uri
}

output "frontend_url" {
  description = "Frontend Web UI URL"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "cloud_sql_instance" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "cloud_sql_private_ip" {
  description = "Cloud SQL private IP"
  value       = google_sql_database_instance.main.private_ip_address
  sensitive   = true
}

output "artifact_registry" {
  description = "Docker registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "cicd_service_account" {
  description = "Service account email for GitHub Actions"
  value       = google_service_account.cicd.email
}

output "workload_identity_provider" {
  description = "Workload Identity provider resource name for GitHub Actions"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "users_secret_id" {
  description = "Secret Manager secret ID for user credentials"
  value       = google_secret_manager_secret.users.secret_id
}
