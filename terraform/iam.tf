# ── Service Account: Orchestrator (Cloud Run backend) ──
resource "google_service_account" "orchestrator" {
  account_id   = "${var.app_name}-orchestrator"
  display_name = "Skill Agent Orchestrator SA"
}

# ── Service Account: CI/CD (GitHub Actions) ──
resource "google_service_account" "cicd" {
  account_id   = "${var.app_name}-cicd"
  display_name = "Skill Agent CI/CD SA (GitHub Actions)"
}

# ── IAM bindings for orchestrator ──
locals {
  orchestrator_roles = [
    "roles/secretmanager.secretAccessor",
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
    "roles/aiplatform.user",
    "roles/storage.objectAdmin",
    "roles/run.invoker",
    "roles/cloudsql.client",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ]
}

resource "google_project_iam_member" "orchestrator_roles" {
  for_each = toset(local.orchestrator_roles)
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.orchestrator.email}"
}

# ── IAM bindings for CI/CD ──
locals {
  cicd_roles = [
    "roles/run.admin",
    "roles/artifactregistry.writer",
    "roles/iam.serviceAccountUser",
    "roles/storage.admin",
    "roles/secretmanager.viewer",
  ]
}

resource "google_project_iam_member" "cicd_roles" {
  for_each = toset(local.cicd_roles)
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.cicd.email}"
}

# ── Workload Identity Federation (GitHub Actions → GCP, no long-lived keys) ──
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "${var.app_name}-github-pool"
  display_name              = "GitHub Actions Pool"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Actions OIDC"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "cicd_wif" {
  service_account_id = google_service_account.cicd.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/YOUR_GITHUB_ORG/YOUR_REPO"
}

# ── Secret: orchestrator SA can access ──
resource "google_secret_manager_secret_iam_member" "users_secret" {
  secret_id = google_secret_manager_secret.users.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.orchestrator.email}"
}

resource "google_secret_manager_secret_iam_member" "db_pass_secret" {
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.orchestrator.email}"
}
