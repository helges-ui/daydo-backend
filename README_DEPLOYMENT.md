# Deployment Scripts

## Main Script: `deploy.sh`

Unified deployment script for all backend operations.

### Usage

```bash
./deploy.sh [command]
```

### Commands

- **`migrate`** (default) - Apply database migrations
- **`token`** - Update Mapbox token in .env
- **`restart`** - Restart Django service
- **`status`** - Show migration and service status
- **`merge`** - Create and apply merge migration
- **`resolve`** - Resolve migration conflict (marks 0005 as fake)

### Examples

```bash
# Apply migrations (default)
./deploy.sh migrate
# or simply
./deploy.sh

# Update Mapbox token
./deploy.sh token

# Check status
./deploy.sh status

# Restart service
./deploy.sh restart
```

## Other Scripts

- **`test_mapbox_token.sh`** - Test Mapbox token endpoint
- **`apply_migration_remote.sh`** - Deprecated, use `deploy.sh migrate`
- **`create_merge_migration.sh`** - Deprecated, use `deploy.sh merge`

## Server Configuration

- **Server:** 13.36.190.238
- **User:** ubuntu
- **Backend Path:** /opt/daydo/app
- **Service:** daydo-gunicorn
- **SSH Key:** LightsailDefaultKey-eu-west-3.pem

