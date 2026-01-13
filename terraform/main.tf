# ============================================
# Yandex Cloud Terraform Configuration
# News Site Infrastructure
# ============================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.177"
    }
  }
}

# Провайдер Yandex Cloud
provider "yandex" {
  zone                      = var.cloud_config.region_zone
  service_account_key_file  = var.cloud_config.service_account_key_file != "" ? var.cloud_config.service_account_key_file : null
  token                     = var.cloud_config.service_account_key_file != "" ? null : var.cloud_config.token
}

# ============================================
# Network Configuration
# ============================================

# Виртуальная сеть
resource "yandex_vpc_network" "news_site_network1" {
  name      = "${var.project_name}-network1"
  folder_id = var.cloud_config.folder_id
}

# Подсеть для PostgreSQL
resource "yandex_vpc_subnet" "news_site_subnet_a" {
  name           = "${var.project_name}-subnet-a"
  folder_id      = var.cloud_config.folder_id
  zone           = var.cloud_config.region_zone
  v4_cidr_blocks = ["10.0.0.0/24"]
  network_id     = yandex_vpc_network.news_site_network1.id
}

# ============================================
# Database Configuration (Managed PostgreSQL)
# ============================================

# Кластер PostgreSQL
resource "yandex_mdb_postgresql_cluster" "news_site_db" {
  name        = "${var.project_name}-db"
  folder_id   = var.cloud_config.folder_id
  description = "PostgreSQL cluster for news site"
  environment = var.db_config.environment
  network_id  = yandex_vpc_network.news_site_network1.id
  
  config {
    version = var.db_config.postgresql_version
    resources {
      resource_preset_id = var.db_config.resource_preset_id
      disk_type_id       = var.db_config.disk_type_id
      disk_size          = var.db_config.disk_size
    }
  }
  
  # Удалён в пользу отдельного ресурса yandex_mdb_postgresql_user
  # user { ... }
  
  host {
    zone       = var.cloud_config.region_zone
    subnet_id  = yandex_vpc_subnet.news_site_subnet_a.id
    assign_public_ip = var.db_config.assign_public_ip
  }
  
  maintenance_window {
    type = var.db_config.maintenance_window_type
    day  = var.db_config.maintenance_window_day
    hour = var.db_config.maintenance_window_hour
  }
  
  lifecycle {
    prevent_destroy = false
  }
}

# Отдельный ресурс для БД (рекомендуемый подход)
resource "yandex_mdb_postgresql_database" "news_site_database" {
  cluster_id = yandex_mdb_postgresql_cluster.news_site_db.id
  name       = var.db_config.database_name
  owner      = var.db_config.username  # Создадим отдельного пользователя-владельца
  
  depends_on = [yandex_mdb_postgresql_user.news_site_user]
}

# Отдельный ресурс для пользователя (рекомендуемый подход)
resource "yandex_mdb_postgresql_user" "news_site_user" {
  cluster_id = yandex_mdb_postgresql_cluster.news_site_db.id
  name       = var.db_config.username
  password   = var.db_config.password
  login      = true  # Разрешить логин
}

# ============================================
# Service Account (используем существующий admin)
# ============================================

# ============================================
# Service Account Static Access Keys
# ============================================

# Статические ключи доступа для Object Storage (S3)
resource "yandex_iam_service_account_static_access_key" "s3_access_key" {
  service_account_id = var.cloud_config.service_account_id
  description        = "Static access key for Object Storage (S3)"
}
  
resource "yandex_resourcemanager_folder_iam_member" "sa_s3_admin" {
  folder_id = var.cloud_config.folder_id
  role      = "storage.admin"
  member    = "serviceAccount:${var.cloud_config.service_account_id}"
}

# Статические ключи доступа для Message Queue (SQS)
resource "yandex_iam_service_account_static_access_key" "sqs_access_key" {
  service_account_id = var.cloud_config.service_account_id
  description        = "Static access key for Message Queue"
}
  
resource "yandex_resourcemanager_folder_iam_member" "sa_mq_admin" {
  folder_id = var.cloud_config.folder_id
  role      = "ymq.admin"
  member    = "serviceAccount:${var.cloud_config.service_account_id}"
}
  
resource "yandex_resourcemanager_folder_iam_member" "sa_function_invoker" {
  folder_id = var.cloud_config.folder_id
  role      = "functions.functionInvoker"
  member    = "serviceAccount:${var.cloud_config.service_account_id}"
}

resource "yandex_resourcemanager_folder_iam_member" "sa_container_invoker" {
  folder_id = var.cloud_config.folder_id
  role      = "serverless.containers.invoker"
  member    = "serviceAccount:${var.cloud_config.service_account_id}"
}

# Право на чтение образов из Container Registry
resource "yandex_resourcemanager_folder_iam_member" "sa_container_registry_viewer" {
  folder_id = var.cloud_config.folder_id
  role      = "container-registry.images.puller"
  member    = "serviceAccount:${var.cloud_config.service_account_id}"
}

# ============================================
# Object Storage
# ============================================

# Бакет для изображений
resource "yandex_storage_bucket" "news_site_images" {
  bucket    = var.storage_config.bucket_name
  folder_id = var.cloud_config.folder_id
  max_size  = var.storage_config.max_size
  
  # Публичный доступ для чтения
  anonymous_access_flags {
    read = true
    list = false
  }
  
  # CORS для доступа к изображениям
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "DELETE"]
    allowed_origins = var.storage_config.cors_allowed_origins
    max_age_seconds = 3600
  }
  
  versioning {
    enabled = var.storage_config.versioning_enabled
  }
  
  lifecycle_rule {
    enabled = var.storage_config.lifecycle_enabled
    expiration {
      days = var.storage_config.expiration_days
    }
  }
}

# Бакет для статических страниц (HTML-шаблоны)
resource "yandex_storage_bucket" "news_site_pages" {
  bucket    = var.storage_config.pages_bucket_name
  folder_id = var.cloud_config.folder_id
  max_size  = var.storage_config.max_size

  # Публичный доступ для чтения
  anonymous_access_flags {
    read = true
    list = true
  }

  # CORS для доступа к страницам
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = var.storage_config.cors_allowed_origins
    max_age_seconds = 86400
  }

  # Веб-сайт хостинг
  website {
    index_file = "index.html"
    error_file = "404.html"
  }
}

# ============================================
# Message Queue (Yandex Message Queue)
# ============================================

# Примечание: Yandex Message Queue не требует folder_id в ресурсе Terraform
# Очередь создаётся в папке, указанной в cloud_config.folder_id
resource "yandex_message_queue" "image_delete_queue" {
  name       = var.mq_config.queue_name
  access_key = yandex_iam_service_account_static_access_key.sqs_access_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sqs_access_key.secret_key
}

# ============================================
# Cloud Function (Image Deletion)
# ============================================

# Функция для удаления изображений
resource "yandex_function" "delete_image_function" {
  name        = "${var.project_name}-delete-image"
  folder_id   = var.cloud_config.folder_id
  description = "Cloud Function for deleting images from Object Storage"
  
  user_hash          = filemd5("${path.module}/../cloud_function/function.zip")
  runtime            = var.function_config.runtime
  entrypoint         = var.function_config.entrypoint
  memory             = var.function_config.memory
  execution_timeout  = 10  # секунды (число, не строка!)
  service_account_id = var.cloud_config.service_account_id
  
  # Подключение zip-архива с кодом функции
  content {
    zip_filename = "${path.module}/../cloud_function/function.zip"
  }
  
  environment = {
    YANDEX_BUCKET_NAME  = yandex_storage_bucket.news_site_images.bucket
    YANDEX_ENDPOINT_URL = "https://storage.yandexcloud.net"
    YANDEX_REGION       = var.cloud_config.region
    AWS_ACCESS_KEY_ID     = yandex_iam_service_account_static_access_key.s3_access_key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.s3_access_key.secret_key
  }
}

# Триггер для очереди сообщений
resource "yandex_function_trigger" "mq_trigger" {
  name        = "${var.project_name}-mq-trigger"
  folder_id   = var.cloud_config.folder_id
  description = "Trigger for processing image deletion queue"
  
  message_queue {
    queue_id           = yandex_message_queue.image_delete_queue.arn
    service_account_id = var.cloud_config.service_account_id
    batch_cutoff       = 10
    batch_size         = 10
  }
  
  function {
    id                 = yandex_function.delete_image_function.id
    service_account_id = var.cloud_config.service_account_id
  }
}

# ============================================
# Serverless Container
# ============================================

resource "yandex_serverless_container" "news_site_container" {
  name        = "${var.project_name}-container"
  folder_id   = var.cloud_config.folder_id
  description = "Serverless Container for news site Flask application"
  
  image {
    url = var.container_config.image_url
    environment = {
      DB_HOST                 = yandex_mdb_postgresql_cluster.news_site_db.host.0.fqdn
      DB_PORT                 = var.db_config.port
      DB_NAME                 = var.db_config.database_name
      DB_USER                 = var.db_config.username
      DB_PASSWORD             = var.db_config.password
      YANDEX_BUCKET_NAME      = yandex_storage_bucket.news_site_images.bucket
      YANDEX_ENDPOINT_URL     = "https://storage.yandexcloud.net"
      YANDEX_REGION           = var.cloud_config.region
      AWS_ACCESS_KEY_ID       = yandex_iam_service_account_static_access_key.s3_access_key.access_key
      AWS_SECRET_ACCESS_KEY   = yandex_iam_service_account_static_access_key.s3_access_key.secret_key
      YANDEX_SQS_ENDPOINT_URL = "https://message-queue.api.cloud.yandex.net"
      YANDEX_SQS_QUEUE_URL    = "https://message-queue.api.cloud.yandex.net/${var.cloud_config.folder_id}/${yandex_message_queue.image_delete_queue.name}"
      YANDEX_SQS_ACCESS_KEY_ID = yandex_iam_service_account_static_access_key.sqs_access_key.access_key
      YANDEX_SQS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.sqs_access_key.secret_key
      # Static pages bucket configuration
      STATIC_PAGES_BUCKET_NAME = yandex_storage_bucket.news_site_pages.bucket
      STATIC_PAGES_ENABLED     = "true"
    }
  }
  
  memory          = var.container_config.memory
  cores           = var.container_config.cores
  core_fraction   = var.container_config.core_fraction
  execution_timeout = var.container_config.execution_timeout
  service_account_id = var.cloud_config.service_account_id
  
  # Подключаем контейнер к VPC сети для доступа к PostgreSQL
  connectivity {
    network_id = yandex_vpc_network.news_site_network1.id
  }
}
  
# ============================================
# API Gateway
# ============================================

resource "yandex_api_gateway" "news_site_api" {
  name        = "${var.project_name}-api"
  folder_id   = var.cloud_config.folder_id
  description = "API Gateway for news site"
  
  # Спецификация OpenAPI
  spec = jsonencode({
    openapi = "3.0.0"
    info = {
      title   = "News Site API"
      version = "1.0.0"
    }
    paths = {
      "/" = {
        get = {
          x-yc-apigateway-integration = {
            type            = "serverless_containers"
            container_id    = yandex_serverless_container.news_site_container.id
            service_account = var.cloud_config.service_account_id
          }
          operationId = "index"
        }
      }
      "/{proxy+}" = {
        parameters = [
          {
            name = "proxy"
            in   = "path"
            required = true
            schema = {
              type = "string"
            }
          }
        ]
        get = {
          x-yc-apigateway-integration = {
            type            = "serverless_containers"
            container_id    = yandex_serverless_container.news_site_container.id
            service_account = var.cloud_config.service_account_id
          }
          operationId = "proxyGet"
        }
        post = {
          x-yc-apigateway-integration = {
            type            = "serverless_containers"
            container_id    = yandex_serverless_container.news_site_container.id
            service_account = var.cloud_config.service_account_id
          }
          operationId = "proxyPost"
        }
        put = {
          x-yc-apigateway-integration = {
            type            = "serverless_containers"
            container_id    = yandex_serverless_container.news_site_container.id
            service_account = var.cloud_config.service_account_id
          }
          operationId = "proxyPut"
        }
        delete = {
          x-yc-apigateway-integration = {
            type            = "serverless_containers"
            container_id    = yandex_serverless_container.news_site_container.id
            service_account = var.cloud_config.service_account_id
          }
          operationId = "proxyDelete"
        }
      }
    }
  })
}

# ============================================
# Outputs
# ============================================

output "database_host" {
  description = "Database host FQDN"
  value       = yandex_mdb_postgresql_cluster.news_site_db.host.0.fqdn
}

output "database_connection_string" {
  description = "PostgreSQL connection string"
  value       = "postgresql://${var.db_config.username}:${var.db_config.password}@${yandex_mdb_postgresql_cluster.news_site_db.host.0.fqdn}:${var.db_config.port}/${var.db_config.database_name}"
  sensitive   = true
}

output "storage_bucket_name" {
  description = "Object Storage bucket name"
  value       = yandex_storage_bucket.news_site_images.bucket
}

output "storage_bucket_url" {
  description = "Object Storage bucket URL"
  value       = "https://storage.yandexcloud.net/${yandex_storage_bucket.news_site_images.bucket}"
}

output "message_queue_url" {
  description = "Message Queue URL"
  value       = yandex_message_queue.image_delete_queue.arn
}

output "message_queue_name" {
  description = "Message Queue name"
  value       = yandex_message_queue.image_delete_queue.name
}

output "cloud_function_id" {
  description = "Cloud Function ID"
  value       = yandex_function.delete_image_function.id
}

output "cloud_function_url" {
  description = "Cloud Function invoke URL"
  value       = "https://functions.yandexcloud.net/${yandex_function.delete_image_function.id}"
}

output "serverless_container_id" {
  description = "Serverless Container ID"
  value       = yandex_serverless_container.news_site_container.id
}

output "serverless_container_url" {
  description = "Serverless Container URL"
  value       = yandex_serverless_container.news_site_container.url
}

output "api_gateway_url" {
  description = "API Gateway URL (main application endpoint)"
  value       = "https://${yandex_api_gateway.news_site_api.domain}"
}

output "api_gateway_domain" {
  description = "API Gateway domain"
  value       = yandex_api_gateway.news_site_api.domain
}

# ============================================
# Service Account Static Access Keys (for S3 and SQS)
# ============================================

output "service_account_id" {
  description = "Service Account ID"
  value       = var.cloud_config.service_account_id
}

output "s3_access_key" {
  description = "Service Account Access Key for Object Storage (S3)"
  value       = yandex_iam_service_account_static_access_key.s3_access_key.access_key
  sensitive   = true
}

output "s3_secret_key" {
  description = "Service Account Secret Key for Object Storage (S3)"
  value       = yandex_iam_service_account_static_access_key.s3_access_key.secret_key
  sensitive   = true
}

output "sqs_access_key" {
  description = "Service Account Access Key for Message Queue"
  value       = yandex_iam_service_account_static_access_key.sqs_access_key.access_key
  sensitive   = true
}

output "sqs_secret_key" {
  description = "Service Account Secret Key for Message Queue"
  value       = yandex_iam_service_account_static_access_key.sqs_access_key.secret_key
  sensitive   = true
}

# ============================================
# Static Pages Bucket Outputs
# ============================================

output "static_pages_bucket_name" {
  description = "Static Pages bucket name"
  value       = yandex_storage_bucket.news_site_pages.bucket
}

output "static_pages_bucket_url" {
  description = "Static Pages bucket URL"
  value       = "https://storage.yandexcloud.net/${yandex_storage_bucket.news_site_pages.bucket}"
}

output "static_pages_website_url" {
  description = "Static Pages website endpoint URL"
  value       = yandex_storage_bucket.news_site_pages.website_endpoint
}