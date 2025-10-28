# 🚀 DayDo Backend - AWS App Runner Deployment Checklist

## ✅ Pre-Deployment Checklist

### 🔐 Security Configuration
- [x] **SECRET_KEY**: Generated secure production key (`pnvAjsUvxICsLq8smBt1syhKOLA0owd56Kdcw3Ce6MVqWYDL3R`)
- [x] **DEBUG**: Set to `False` for production
- [x] **ALLOWED_HOSTS**: Configured for App Runner URL
- [x] **Security Headers**: HTTPS, HSTS, XSS protection enabled
- [x] **Database Password**: Generated secure password (`yIdYwIqSuNHua8gt^^k@`)

### 🗄️ Database Setup
- [ ] **AWS RDS PostgreSQL**: Create production database instance
- [ ] **Database Name**: `daydo_production`
- [ ] **Database User**: `daydo_user`
- [ ] **Database Password**: `yIdYwIqSuNHua8gt^^k@`
- [ ] **Security Groups**: Configure RDS security groups
- [ ] **Backup Strategy**: Enable automated backups

### 🌐 CORS Configuration
- [ ] **Frontend Domain**: Add your Amplify domain to CORS_ALLOWED_ORIGINS
- [ ] **Custom Domain**: Add custom domain if applicable
- [ ] **HTTPS Only**: Ensure all CORS origins use HTTPS

### 📧 Email Configuration (Optional)
- [ ] **SMTP Settings**: Configure email backend for notifications
- [ ] **Email Templates**: Set up email templates for invitations
- [ ] **Email Testing**: Test email functionality

## 🚀 AWS App Runner Deployment Steps

### 1. Create AWS RDS PostgreSQL Database
```bash
# Using AWS CLI
aws rds create-db-instance \
    --db-instance-identifier daydo-production \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username daydo_user \
    --master-user-password yIdYwIqSuNHua8gt^^k@ \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-your-security-group \
    --db-subnet-group-name your-subnet-group
```

### 2. Configure App Runner Service
1. **Go to AWS App Runner Console**
2. **Create Service** → **Container image**
3. **Configure Service**:
   - **Service name**: `daydo-backend`
   - **Container image URI**: Your ECR repository URI
   - **Port**: `8000`

### 3. Set Environment Variables in App Runner
```
SECRET_KEY=pnvAjsUvxICsLq8smBt1syhKOLA0owd56Kdcw3Ce6MVqWYDL3R
DEBUG=False
ALLOWED_HOSTS=your-app-runner-url.awsapprunner.com
DB_NAME=daydo_production
DB_USER=daydo_user
DB_PASSWORD=yIdYwIqSuNHua8gt^^k@
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_PORT=5432
CORS_ALLOWED_ORIGINS=https://your-amplify-domain.amplifyapp.com
JWT_ACCESS_TOKEN_LIFETIME=3600
JWT_REFRESH_TOKEN_LIFETIME=604800
SECURE_SSL_REDIRECT=True
LOG_LEVEL=INFO
```

### 4. Deploy Container Image
```bash
# Build and push to ECR
aws ecr create-repository --repository-name daydo-backend
docker build -t daydo-backend .
docker tag daydo-backend:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/daydo-backend:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/daydo-backend:latest
```

### 5. Run Database Migrations
```bash
# Connect to App Runner service and run migrations
aws apprunner start-deployment --service-arn your-service-arn
```

## 🧪 Post-Deployment Testing

### 1. Health Check
- [ ] **Service Status**: Verify App Runner service is running
- [ ] **Health Endpoint**: Test `/api/dashboard/` endpoint
- [ ] **Database Connection**: Verify database connectivity

### 2. API Testing
- [ ] **Authentication**: Test user registration and login
- [ ] **Family Management**: Test family creation and management
- [ ] **Child Profiles**: Test child profile creation
- [ ] **Permissions**: Test role-based permissions

### 3. Security Testing
- [ ] **HTTPS**: Verify SSL certificate is working
- [ ] **CORS**: Test CORS configuration with frontend
- [ ] **Authentication**: Test JWT token generation and validation

## 📊 Monitoring Setup

### 1. CloudWatch Logs
- [ ] **Log Groups**: Verify logs are being sent to CloudWatch
- [ ] **Log Retention**: Set appropriate log retention period
- [ ] **Log Monitoring**: Set up log-based alerts

### 2. Performance Monitoring
- [ ] **Metrics**: Monitor CPU, memory, and request metrics
- [ ] **Alerts**: Set up alerts for high error rates
- [ ] **Dashboards**: Create CloudWatch dashboards

### 3. Error Tracking (Optional)
- [ ] **Sentry**: Set up Sentry for error tracking
- [ ] **Error Alerts**: Configure error notifications

## 🔄 CI/CD Pipeline (Future)

### 1. GitHub Actions
- [ ] **Build Pipeline**: Automated Docker image builds
- [ ] **Test Pipeline**: Run tests before deployment
- [ ] **Deploy Pipeline**: Automated deployment to App Runner

### 2. Code Quality
- [ ] **Linting**: Automated code quality checks
- [ ] **Security Scanning**: Automated security vulnerability scanning
- [ ] **Dependency Updates**: Automated dependency updates

## 📋 Production Environment Variables Summary

```bash
# Core Django Settings
SECRET_KEY=pnvAjsUvxICsLq8smBt1syhKOLA0owd56Kdcw3Ce6MVqWYDL3R
DEBUG=False
ALLOWED_HOSTS=your-app-runner-url.awsapprunner.com,your-custom-domain.com

# Database Configuration
DB_NAME=daydo_production
DB_USER=daydo_user
DB_PASSWORD=yIdYwIqSuNHua8gt^^k@
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_PORT=5432

# CORS Configuration
CORS_ALLOWED_ORIGINS=https://your-amplify-domain.amplifyapp.com,https://your-custom-domain.com

# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME=3600
JWT_REFRESH_TOKEN_LIFETIME=604800

# Security Settings
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
X_FRAME_OPTIONS=DENY

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/daydo/django.log
```

## 🆘 Troubleshooting

### Common Issues:
1. **Database Connection**: Check RDS security groups and endpoint
2. **CORS Errors**: Verify CORS_ALLOWED_ORIGINS includes frontend domain
3. **Authentication**: Check JWT settings and secret key
4. **Static Files**: Ensure CloudFront or S3 is configured

### Debug Commands:
```bash
# Check environment variables
python manage.py shell -c "import os; print(os.environ.get('DEBUG'))"

# Test database connection
python manage.py dbshell

# Check Django settings
python manage.py diffsettings
```

## ✅ Ready for Production!

Your DayDo backend is now configured with:
- ✅ **Secure production settings**
- ✅ **Database configuration**
- ✅ **Security headers**
- ✅ **CORS configuration**
- ✅ **JWT authentication**
- ✅ **Logging configuration**
- ✅ **Environment variable management**

**Next Step**: Deploy to AWS App Runner using the Dockerfile!
