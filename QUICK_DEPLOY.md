# Quick Deploy Migration to Server

## Server Details
- **Static IP:** 13.36.190.238
- **IPv6:** 2a05:d012:8db:8700:b329:ad93:121:3138
- **User:** ubuntu

## Quick Deploy (One Command)

### Option 1: Use the automated script
```bash
cd /Users/family.schindlericloud.com/Documents/GitHub/DayDo2Backend
./apply_migration_remote.sh
```

### Option 2: Manual SSH command
```bash
ssh ubuntu@13.36.190.238 "cd /home/ubuntu/daydo-backend && source venv/bin/activate && git pull && python manage.py migrate daydo"
```

### Option 3: Step-by-step manual deployment

1. **SSH to server:**
   ```bash
   ssh ubuntu@13.36.190.238
   ```

2. **Navigate to backend:**
   ```bash
   cd /home/ubuntu/daydo-backend
   ```

3. **Pull latest code:**
   ```bash
   git pull origin main
   ```

4. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

5. **Apply migration:**
   ```bash
   python manage.py migrate daydo
   ```

6. **Verify migration:**
   ```bash
   python manage.py showmigrations daydo | tail -5
   ```

## Verify Migration

After applying, check the database tables were created:

```bash
python manage.py dbshell
```

In PostgreSQL:
```sql
\dt daydo_*
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'daydo_%';
\q
```

Expected tables:
- `daydo_task`
- `daydo_event`
- `daydo_eventassignment`
- `daydo_role` (if not already exists)
- `daydo_userrole` (if not already exists)

## Troubleshooting

### If SSH connection fails:
- Check your SSH key is added to the server
- Verify security group allows SSH (port 22)
- Try: `ssh -i ~/.ssh/your-key.pem ubuntu@13.36.190.238`

### If migration fails:
- Check database connection: `python manage.py check`
- Verify environment variables are set
- Check logs: `tail -f /var/log/daydo/django.log`

### If migration file is missing:
- Ensure you've pulled latest code: `git pull`
- Check file exists: `ls -la daydo/migrations/0003_*`

