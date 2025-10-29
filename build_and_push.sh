#!/bin/bash
# DayDo Backend - Build and Push Docker Image to ECR
# Run this script after Docker Desktop is started

set -e

ECR_REGISTRY="646654473689.dkr.ecr.eu-west-3.amazonaws.com"
IMAGE_NAME="daydo-backend"
REGION="eu-west-3"

echo "🚀 DayDo Backend - Docker Build and Push Script"
echo "================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Step 1: Authenticate Docker to ECR
echo "Step 1: Authenticating Docker to ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

if [ $? -eq 0 ]; then
    echo "✅ Successfully authenticated to ECR"
else
    echo "❌ Failed to authenticate to ECR"
    exit 1
fi

echo ""

# Step 2: Build Docker image
echo "Step 2: Building Docker image..."
cd /Users/family.schindlericloud.com/Documents/GitHub/DayDo2Backend
docker build -t ${IMAGE_NAME}:latest .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Failed to build Docker image"
    exit 1
fi

echo ""

# Step 3: Tag Docker image for ECR
echo "Step 3: Tagging Docker image for ECR..."
docker tag ${IMAGE_NAME}:latest ${ECR_REGISTRY}/${IMAGE_NAME}:latest

if [ $? -eq 0 ]; then
    echo "✅ Docker image tagged successfully"
else
    echo "❌ Failed to tag Docker image"
    exit 1
fi

echo ""

# Step 4: Push Docker image to ECR
echo "Step 4: Pushing Docker image to ECR..."
docker push ${ECR_REGISTRY}/${IMAGE_NAME}:latest

if [ $? -eq 0 ]; then
    echo "✅ Docker image pushed successfully"
    echo ""
    echo "🎉 Success! Your Docker image is now in ECR:"
    echo "   ${ECR_REGISTRY}/${IMAGE_NAME}:latest"
else
    echo "❌ Failed to push Docker image"
    exit 1
fi

echo ""
echo "✅ Step 2 Complete! Ready for Step 3 (App Runner setup)"
