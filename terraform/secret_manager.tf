# ── Secret: user credentials (populated externally via create_users_secret.py) ──
resource "google_secret_manager_secret" "users" {
  secret_id = "${var.app_name}-users"
  labels    = local.labels
  replication {
    auto {}
  }
}

# ── Secret: Cloud SQL password (auto-generated) ──
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}:?"
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.app_name}-db-password"
  labels    = local.labels
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# ── Secret: Cloud SQL connection string ──
resource "google_secret_manager_secret" "db_connection" {
  secret_id = "${var.app_name}-db-connection"
  labels    = local.labels
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_connection" {
  secret      = google_secret_manager_secret.db_connection.id
  secret_data = "${var.project_id}:${var.region}:${google_sql_database_instance.main.name}"
}
