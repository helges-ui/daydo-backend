# DayDo Backend - Environment Configuration Guide

## 🚀 Production Environment Setup for AWS App Runner

This guide explains how to configure your DayDo backend for production deployment on AWS App Runner.

### 📋 Required Environment Variables

#### **1. Django Core Settings**
```bash
# SECRET_KEY - Generate a secure key for production
SECRET_KEY=your-super-secret-production-key-change-this-in-production

# DEBUG - Always False in production
DEBUG=False

# ALLOWED_HOSTS - Your App Runner URL and custom domain
ALLOWED_HOSTS=your-app-runner-url.awsapprunner.com,your-custom-domain.com
```

#### **2. Database Configuration (AWS RDS)**
```bash
# Database connection to AWS RDS PostgreSQL
DB_NAME=daydo_production
DB_USER=daydo_user
DB_PASSWORD=your-secure-database-password
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_PORT=5432
```

#### **3. CORS Configuration**
```bash
# Frontend domains that can access the API
CORS_ALLOWED_ORIGINS=https://your-amplify-domain.amplifyapp.com,https://your-custom-domain.com
```

#### **4. JWT Token Settings**
```bash
# Token lifetimes (in seconds)
JWT_ACCESS_TOKEN_LIFETIME=3600    # 1 hour
JWT_REFRESH_TOKEN_LIFETIME=604800 # 7 days
```

#### **5. AWS Configuration**
```bash
# AWS credentials (if needed for additional services)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
```

#### **6. Email Configuration**
```bash
# SMTP settings for sending emails
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

#### **7. Security Settings**
```bash
# HTTPS enforcement
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
X_FRAME_OPTIONS=DENY
```

### 🔧 AWS App Runner Configuration

#### **Environment Variables in App Runner Console:**
1. Go to AWS App Runner Console
2. Select your service
3. Go to "Configuration" → "Environment"
4. Add all the environment variables listed above

#### **Example App Runner Environment Variables:**
```
SECRET_KEY=your-super-secret-production-key
DEBUG=False
ALLOWED_HOSTS=your-app-runner-url.awsapprunner.com
DB_NAME=daydo_production
DB_USER=daydo_user
DB_PASSWORD=your-secure-database-password
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_PORT=5432
CORS_ALLOWED_ORIGINS=https://your-amplify-domain.amplifyapp.com
JWT_ACCESS_TOKEN_LIFETIME=3600
JWT_REFRESH_TOKEN_LIFETIME=604800
```

### 🗄️ Database Setup (AWS RDS)

#### **1. Create RDS PostgreSQL Instance:**
```bash
# Using AWS CLI
aws rds create-db-instance \
    --db-instance-identifier daydo-production \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username daydo_user \
    --master-user-password your-secure-database-password \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-your-security-group \
    --db-subnet-group-name your-subnet-group
```

#### **2. Database Connection String:**
```
postgresql://daydo_user:your-secure-database-password@your-rds-endpoint.region.rds.amazonaws.com:5432/daydo_production
```

### 🔐 Security Best Practices

#### **1. Generate Secure Secret Key:**
```python
# Generate a new secret key
import secrets
print(secrets.token_urlsafe(50))
```

#### **2. Database Password:**
- Use a strong password (at least 16 characters)
- Include uppercase, lowercase, numbers, and special characters
- Store securely in AWS Secrets Manager (recommended)

#### **3. CORS Configuration:**
- Only include your actual frontend domains
- Use HTTPS URLs only
- Remove localhost from production

### 📊 Monitoring & Logging

#### **1. CloudWatch Logs:**
```bash
# App Runner automatically sends logs to CloudWatch
LOG_LEVEL=INFO
```

#### **2. Error Tracking (Optional):**
```bash
# Sentry for error tracking
SENTRY_DSN=your-sentry-dsn-for-error-tracking
```

### 🚀 Deployment Checklist

- [ ] Generate secure SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS with your App Runner URL
- [ ] Set up AWS RDS PostgreSQL database
- [ ] Configure CORS with your frontend domains
- [ ] Set up email configuration (if needed)
- [ ] Configure security settings
- [ ] Test database connection
- [ ] Run migrations on production database
- [ ] Create production superuser
- [ ] Test API endpoints

### 🔄 Environment Switching

#### **Development (.env):**
```bash
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_HOST=localhost
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

#### **Production (.env.production):**
```bash
DEBUG=False
ALLOWED_HOSTS=your-app-runner-url.awsapprunner.com
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
CORS_ALLOWED_ORIGINS=https://your-amplify-domain.amplifyapp.com
```

### 📝 Next Steps

1. **Set up AWS RDS PostgreSQL database**
2. **Configure App Runner environment variables**
3. **Deploy using Dockerfile**
4. **Test production endpoints**
5. **Set up monitoring and logging**

### 🆘 Troubleshooting

#### **Common Issues:**
- **Database connection errors**: Check RDS security groups and endpoint
- **CORS errors**: Verify CORS_ALLOWED_ORIGINS includes your frontend domain
- **Authentication errors**: Check JWT settings and secret key
- **Static files**: Ensure CloudFront or S3 is configured for static files

#### **Debug Commands:**
```bash
# Check environment variables
python manage.py shell -c "import os; print(os.environ.get('DEBUG'))"

# Test database connection
python manage.py dbshell

# Check Django settings
python manage.py diffsettings
```
