terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    random = { source = "hashicorp/random" }
  }

  backend "gcs" {
    bucket = "YOUR_TERRAFORM_STATE_BUCKET"
    prefix = "skill-agent/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

locals {
  name   = "${var.app_name}-${var.env}"
  labels = { app = var.app_name, env = var.env, managed_by = "terraform" }
}

# ── Enable required GCP APIs ──
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "bigquery.googleapis.com",
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "vpcaccess.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# ── Artifact Registry (Docker images) ──
resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = "${var.app_name}-docker"
  format        = "DOCKER"
  labels        = local.labels
  description   = "Skill Agent Docker images"
  depends_on    = [google_project_service.apis]
}

# ── BigQuery Dataset ──
resource "google_bigquery_dataset" "analytics" {
  dataset_id            = var.bq_dataset
  location              = var.region
  labels                = local.labels
  delete_contents_on_destroy = false
}

# ── Random suffix for globally unique names ──
resource "random_id" "suffix" {
  byte_length = 4
}
