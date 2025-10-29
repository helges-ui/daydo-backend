# 🐳 Step 2: Build and Push Docker Image to ECR

## Prerequisites
- ✅ Docker Desktop installed and running
- ✅ AWS CLI configured with credentials
- ✅ ECR repository created: `646654473689.dkr.ecr.eu-west-3.amazonaws.com/daydo-backend`

## Quick Setup Instructions

### 1. Configure AWS CLI (if not done yet)
```bash
aws configure
# Enter your:
# - AWS Access Key ID
# - AWS Secret Access Key  
# - Default region: eu-west-3
# - Default output format: json
```

### 2. Start Docker Desktop
- Open Docker Desktop from Applications
- Wait until Docker is running (whale icon in menu bar)

### 3. Run the Build Script
```bash
cd /Users/family.schindlericloud.com/Documents/GitHub/DayDo2Backend
./build_and_push.sh
```

## Manual Steps (if script doesn't work)

### Step 1: Authenticate Docker to ECR
```bash
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 646654473689.dkr.ecr.eu-west-3.amazonaws.com
```

### Step 2: Build Docker Image
```bash
cd /Users/family.schindlericloud.com/Documents/GitHub/DayDo2Backend
docker build -t daydo-backend:latest .
```

### Step 3: Tag Docker Image
```bash
docker tag daydo-backend:latest 646654473689.dkr.ecr.eu-west-3.amazonaws.com/daydo-backend:latest
```

### Step 4: Push to ECR
```bash
docker push 646654473689.dkr.ecr.eu-west-3.amazonaws.com/daydo-backend:latest
```

## Verification

After pushing, verify the image in ECR:
```bash
aws ecr describe-images --repository-name daydo-backend --region eu-west-3
```

## Troubleshooting

### Docker not running
```bash
# Check Docker status
docker info

# If error, start Docker Desktop from Applications
```

### AWS authentication failed
```bash
# Reconfigure AWS CLI
aws configure

# Test AWS connection
aws sts get-caller-identity
```

### Build failed
- Check Dockerfile syntax
- Ensure all dependencies are in requirements.txt
- Check Docker logs for errors

### Push failed
- Verify ECR repository exists
- Check AWS permissions
- Ensure you're authenticated to ECR
