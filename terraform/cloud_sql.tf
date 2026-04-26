# ── Cloud SQL: Postgres instance ──
resource "google_sql_database_instance" "main" {
  name             = "${local.name}-postgres-${random_id.suffix.hex}"
  database_version = "POSTGRES_15"
  region           = var.region
  depends_on       = [google_service_networking_connection.private_vpc]

  deletion_protection = true

  settings {
    tier              = var.cloud_sql_tier
    availability_type = var.env == "prod" ? "REGIONAL" : "ZONAL"
    disk_autoresize   = true
    disk_size         = 20
    disk_type         = "PD_SSD"

    labels = local.labels

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      backup_retention_settings {
        retained_backups = 14
      }
    }

    maintenance_window {
      day          = 7
      hour         = 4
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = false
    }

    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"
    }
  }
}

# ── Database ──
resource "google_sql_database" "app" {
  name     = var.cloud_sql_db_name
  instance = google_sql_database_instance.main.name
}

# ── Application user ──
resource "google_sql_user" "app" {
  name     = var.cloud_sql_user
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}
