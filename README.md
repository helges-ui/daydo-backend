# DayDo Backend

A Django REST API backend for the DayDo family task management application.

## Features

- **Role-based Authentication**: PARENT and CHILD_USER roles with JWT tokens
- **Family Management**: Create and manage family units with multiple members
- **Child Profiles**: Support for both CHILD_VIEW (view-only) and CHILD_USER (with login)
- **Permission System**: Fine-grained permissions for child users
- **RESTful API**: Complete API endpoints for all user stories

## Architecture

- **Framework**: Django 4.2 with Django REST Framework
- **Authentication**: JWT tokens with SimpleJWT
- **Database**: PostgreSQL (configurable)
- **Deployment**: AWS App Runner ready

## Models

### Family
- Central unit linking all family members
- Customizable family name
- Created during first parent registration

### User
- Custom user model extending AbstractUser
- Two roles: PARENT and CHILD_USER
- Family association and role-based permissions

### ChildProfile
- Separate entity for child profiles
- Supports both CHILD_VIEW and CHILD_USER types
- Links to User model when login account is created

### ChildUserPermissions
- Fine-grained permissions for CHILD_USER role
- Deny-by-exception policy
- Controls access to various features

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new parent and create family
- `POST /api/auth/login/` - Login user and get JWT tokens
- `POST /api/auth/invite_parent/` - Invite another parent

### Family Management
- `GET /api/family/` - Get family details
- `PUT /api/family/{id}/` - Update family details
- `GET /api/family/{id}/members/` - Get all family members
- `GET /api/family/{id}/children/` - Get all child profiles
- `GET /api/family/{id}/dashboard/` - Get family dashboard

### Child Profiles
- `GET /api/children/` - List child profiles
- `POST /api/children/` - Create child profile
- `GET /api/children/{id}/` - Get child profile details
- `PUT /api/children/{id}/` - Update child profile
- `DELETE /api/children/{id}/` - Delete child profile
- `POST /api/children/{id}/create_login_account/` - Convert to CHILD_USER
- `DELETE /api/children/{id}/remove_login_account/` - Convert back to CHILD_VIEW

### User Management
- `GET /api/users/me/` - Get current user profile
- `PUT /api/users/update_profile/` - Update current user profile
- `GET /api/users/{id}/permissions/` - Get user permissions

### Dashboard
- `GET /api/dashboard/` - Get dashboard with children's progress

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

3. **Database Setup**
   - Install PostgreSQL
   - Create database: `createdb daydo`
   - Update database settings in `.env`

4. **Run Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

## User Stories Implementation

### Epic 1: Family & Account Management
- ✅ **US-1**: Family Account Creation
- ✅ **US-2**: Add Parent/Partner
- ✅ **US-3**: Add Child Profiles

### Epic 2: Parent Task Management
- 🔄 **US-4**: Parent's Personal To-Do List (Next Phase)
- 🔄 **US-5**: Assign Tasks to Children (Next Phase)
- 🔄 **US-6**: Create Recurring Tasks (Next Phase)
- ✅ **US-7**: Monitor Child's Progress (Dashboard)

### Epic 3: Child's App Experience
- 🔄 **US-8**: View Daily To-Do List (Next Phase)
- 🔄 **US-9**: Mark Task as Complete (Next Phase)
- 🔄 **US-10**: Visual Task Icons (Next Phase)

## Role-Based Access Control

### Parent Permissions
- Full access to family management
- Can create, edit, delete child profiles
- Can assign tasks to children (kids)
- Can monitor child progress
- Can invite other parents

### Child User Permissions
- Configurable permissions via ChildUserPermissions model
- Default: All permissions denied (deny-by-exception)
- Can be granted specific permissions by parents

## Deployment

The application is designed for deployment on AWS App Runner:

1. **Container Configuration**: Use the provided Dockerfile
2. **Environment Variables**: Set production values in App Runner
3. **Database**: Use RDS PostgreSQL
4. **Static Files**: Configure for production serving

## Development

### Running Tests
```bash
python manage.py test
```

### Code Style
- Follow PEP 8
- Use Django best practices
- Document all API endpoints

### Contributing
1. Create feature branch
2. Implement changes
3. Add tests
4. Submit pull request
