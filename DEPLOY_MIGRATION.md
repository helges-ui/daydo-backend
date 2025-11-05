# Deploy Phase 2 & 3 Migrations to Server

## Quick Deploy

### Option 1: Using the Deployment Script

1. **Copy the script to the server:**
   ```bash
   scp apply_migration.sh ubuntu@<your-lightsail-ip>:/home/ubuntu/
   ```

2. **SSH to the server:**
   ```bash
   ssh ubuntu@<your-lightsail-ip>
   ```

3. **Run the script:**
   ```bash
   cd /home/ubuntu
   chmod +x apply_migration.sh
   ./apply_migration.sh
   ```

### Option 2: Manual Steps

1. **SSH to the Lightsail server:**
   ```bash
   ssh ubuntu@<your-lightsail-ip>
   ```

2. **Navigate to backend directory:**
   ```bash
   cd /home/ubuntu/daydo-backend
   # Or wherever your backend is located
   ```

3. **Pull latest changes (if using git):**
   ```bash
   git pull origin main  # or master, depending on your branch
   ```

4. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   # Or: source .venv/bin/activate
   ```

5. **Apply migrations:**
   ```bash
   python manage.py migrate daydo
   ```

6. **Verify migration:**
   ```bash
   python manage.py showmigrations daydo
   ```

## Migration Details

**Migration File:** `daydo/migrations/0003_event_eventassignment_role_task_userrole_and_more.py`

**Creates:**
- ✅ Task model
- ✅ Event model
- ✅ EventAssignment model
- ✅ Role model (if not already migrated)
- ✅ UserRole model (if not already migrated)

**Database Indexes:**
- Task: `(family, date)`, `(assigned_to, date)`, `(completed)`
- Event: `(family, start_datetime)`, `(start_datetime)`

## Verification

After applying the migration, verify the tables were created:

```bash
python manage.py dbshell
```

Then in PostgreSQL:
```sql
\dt daydo_*
SELECT * FROM daydo_task LIMIT 1;
SELECT * FROM daydo_event LIMIT 1;
SELECT * FROM daydo_eventassignment LIMIT 1;
\q
```

## Troubleshooting

### If migration fails with "table already exists":
- This is normal if Role/UserRole were already migrated
- Django will skip creating existing tables
- The migration should complete successfully

### If you get connection errors:
- Check database credentials in `.env` or environment variables
- Verify RDS instance is accessible
- Check security groups allow connections from Lightsail

### If migration file is missing:
- Ensure you've pulled the latest code from git
- Check the file exists: `ls -la daydo/migrations/0003_*`

## Rollback (if needed)

If you need to rollback the migration:

```bash
python manage.py migrate daydo 0002_add_color_fields
```

This will revert to the previous migration state.

