# PowerShell script to build and push Docker image to Yandex Container Registry
# Usage: .\push_to_cr.ps1

$ErrorActionPreference = "Stop"

# ============================================
# Configuration
# ============================================
$FOLDER_ID = "b1gpijfvkfbdaifm95oi"  # Your Yandex Cloud folder ID
$CR_URL = "cr.yandex/$FOLDER_ID"    # Container Registry URL
$IMAGE_NAME = "news-site"
$IMAGE_TAG = "latest"

# ============================================
# Step 1: Authenticate to Yandex Container Registry
# ============================================
Write-Host "Authenticating to Yandex Container Registry..." -ForegroundColor Cyan

# Get IAM token and login
$token = yc iam create-token
if ([string]::IsNullOrEmpty($token)) {
    Write-Error "Failed to get IAM token. Make sure Yandex CLI is authenticated."
}

# Login to CR using IAM token
$token | docker login $CR_URL -u oauth --password-stdin
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to login to Yandex Container Registry"
}

Write-Host "Successfully authenticated to $CR_URL" -ForegroundColor Green

# ============================================
# Step 2: Build Docker image
# ============================================
Write-Host "Building Docker image: $IMAGE_NAME:latest" -ForegroundColor Cyan

docker build -t $IMAGE_NAME:latest .
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed"
}

Write-Host "Docker image built successfully" -ForegroundColor Green

# ============================================
# Step 3: Tag image for Yandex CR
# ============================================
Write-Host "Tagging image for Yandex Container Registry..." -ForegroundColor Cyan

$fullImageName = "$CR_URL/$IMAGE_NAME:$IMAGE_TAG"
docker tag $IMAGE_NAME:latest $fullImageName

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker tag failed"
}

Write-Host "Image tagged as $fullImageName" -ForegroundColor Green

# ============================================
# Step 4: Push image to Yandex CR
# ============================================
Write-Host "Pushing image to Yandex Container Registry..." -ForegroundColor Cyan

docker push $fullImageName
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker push failed"
}

Write-Host "Image pushed successfully to $fullImageName" -ForegroundColor Green

# ============================================
# Output image URL for Terraform
# ============================================
Write-Host "`n========================================" -ForegroundColor Yellow
Write-Host "Image URL for terraform.tfvars:" -ForegroundColor Yellow
Write-Host $fullImageName -ForegroundColor White
Write-Host "========================================" -ForegroundColor Yellow
