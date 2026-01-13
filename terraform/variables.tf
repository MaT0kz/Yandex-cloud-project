# ============================================
# Terraform Variables
# ============================================

# Cloud Configuration
variable "cloud_config" {
  description = "Yandex Cloud configuration"
  type = object({
    folder_id              = string
    service_account_id     = string
    region                 = string
    region_zone            = string
    token                  = string
    service_account_key_file = string
  })
  default = {
    folder_id              = "b1gxxxxxxxxxxxxx"
    service_account_id     = "ajepq0p2v2c4s2h8v5g0"  # ID сервисного аккаунта admin
    region                 = "ru-central1"
    region_zone            = "ru-central1-a"
    token                  = ""
    service_account_key_file = ""
  }
}

# Project Configuration
variable "project_name" {
  description = "Project name (used as prefix for resources)"
  type        = string
  default     = "news-site"
}

# Database Configuration
variable "db_config" {
  description = "PostgreSQL database configuration"
  type = object({
    postgresql_version     = number
    environment            = string
    resource_preset_id     = string
    disk_type_id           = string
    disk_size              = number
    port                   = number
    database_name          = string
    username               = string
    password               = string
    assign_public_ip       = bool
    maintenance_window_type = string
    maintenance_window_day = string
    maintenance_window_hour = number
  })
  default = {
    postgresql_version     = 15
    environment            = "PRODUCTION"
    resource_preset_id     = "s2.micro"
    disk_type_id           = "network-hdd"
    disk_size              = 10
    port                   = 6432
    database_name          = "news_db"
    username               = "news_user"
    password               = ""  # Будет сгенерирован или укажи те свой
    assign_public_ip       = false
    maintenance_window_type = "WEEKLY"
    maintenance_window_day = "MON"
    maintenance_window_hour = 12
  }
}

# Storage Configuration
variable "storage_config" {
  description = "Object Storage bucket configuration"
  type = object({
    bucket_name          = string
    pages_bucket_name    = string
    max_size             = number
    cors_allowed_origins = list(string)
    versioning_enabled   = bool
    lifecycle_enabled    = bool
    expiration_days      = number
  })
  default = {
    bucket_name          = "news-site-images-bucket"
    pages_bucket_name    = "news-site-pages"
    max_size             = 1073741824  # 1 GB
    cors_allowed_origins = ["*"]  # Для разработки; в продакшене укажите конкретный домен
    versioning_enabled   = false
    lifecycle_enabled    = true
    expiration_days      = 30
  }
}

# Message Queue Configuration (minimal - only name is required)
variable "mq_config" {
  description = "Message Queue configuration"
  type = object({
    queue_name = string
  })
  default = {
    queue_name = "news-image-delete-queue"
  }
}

# Cloud Function Configuration
variable "function_config" {
  description = "Cloud Function configuration"
  type = object({
    runtime          = string
    entrypoint       = string
    memory           = number
    execution_timeout = string
  })
  default = {
    runtime          = "python311"
    entrypoint       = "index.handler"
    memory           = 128
    execution_timeout = "10s"
  }
}

# Container Configuration
variable "container_config" {
  description = "Serverless Container configuration"
  type = object({
    image_url         = string
    registry_id       = string
    cores             = number
    memory            = number
    core_fraction     = number
    execution_timeout = string
  })
  default = {
    image_url         = ""
    registry_id       = ""
    cores             = 1
    memory            = 256  # MB
    core_fraction     = 100
    execution_timeout = "15s"
  }
}

# Application Configuration
variable "app_config" {
  description = "Application configuration"
  type = object({
    secret_key = string
  })
  default = {
    secret_key = ""  # Будет сгенерирован или укажите свой
  }
}

# Tags for resources
variable "tags" {
  description = "Tags to add to all resources"
  type = map(string)
  default = {
    project     = "news-site"
    managed-by  = "terraform"
    environment = "production"
  }
}