# ── Image refs (updated by CI/CD) ──
locals {
  registry        = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
  backend_image   = "${local.registry}/backend:latest"
  frontend_image  = "${local.registry}/frontend:latest"
  toolbox_image   = var.toolbox_image
}

# ════════════════════════════
# ORCHESTRATOR (backend)
# ════════════════════════════
resource "google_cloud_run_v2_service" "orchestrator" {
  name     = "${local.name}-orchestrator"
  location = var.region
  labels   = local.labels

  template {
    service_account = google_service_account.orchestrator.email
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = local.backend_image
      name  = "orchestrator"

      resources {
        limits = { cpu = "2", memory = "2Gi" }
        startup_cpu_boost = true
      }

      ports { container_port = 8080 }

      env { name = "GCP_PROJECT_ID"  value = var.project_id }
      env { name = "GCP_REGION"      value = var.region }
      env { name = "BQ_DATASET"      value = var.bq_dataset }
      env { name = "SKILLS_DIR"      value = "skills" }
      env { name = "TOOLBOX_URL"     value = "http://localhost:5000" }
      env { name = "TOKEN_TTL_HOURS" value = tostring(var.token_ttl_hours) }
      env { name = "DB_HOST"         value = google_sql_database_instance.main.private_ip_address }
      env { name = "DB_NAME"         value = var.cloud_sql_db_name }
      env { name = "DB_USER"         value = var.cloud_sql_user }
      env { name = "SECRET_NAME"     value = google_secret_manager_secret.users.secret_id }

      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get { path = "/health" port = 8080 }
        initial_delay_seconds = 10
        period_seconds        = 5
        failure_threshold     = 10
      }
      liveness_probe {
        http_get { path = "/health" port = 8080 }
        period_seconds    = 30
        failure_threshold = 3
      }
    }

    # MCP Toolbox sidecar
    containers {
      image = local.toolbox_image
      name  = "toolbox"
      args  = ["--config", "/etc/toolbox/toolbox_config.yaml"]

      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }

      ports { container_port = 5000 }
    }
  }

  depends_on = [
    google_project_iam_member.orchestrator_roles,
    google_sql_database_instance.main,
    google_secret_manager_secret_version.db_password,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "orchestrator_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.orchestrator.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ════════════════════════════
# FRONTEND
# ════════════════════════════
resource "google_cloud_run_v2_service" "frontend" {
  name     = "${local.name}-frontend"
  location = var.region
  labels   = local.labels

  template {
    scaling {
      min_instance_count = 1
      max_instance_count = 5
    }
    containers {
      image = local.frontend_image
      name  = "frontend"
      resources { limits = { cpu = "1", memory = "256Mi" } }
      ports { container_port = 80 }
      env {
        name  = "API_BASE"
        value = google_cloud_run_v2_service.orchestrator.uri
      }
    }
  }
  depends_on = [google_cloud_run_v2_service.orchestrator]
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
