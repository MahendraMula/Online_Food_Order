#!/bin/bash
# ==============================================================================
#  OFO-DBMS — Azure App Service Linux Custom Startup Script
# ==============================================================================
set -e

echo "=== [OFO-DBMS] Initializing Azure App Service Environment ==="

# 1. Apply database migrations to both SQLite databases
echo "--> Applying migrations to primary domain database (food_ordering.db)..."
python manage.py migrate --run-syncdb

echo "--> Applying migrations to framework database (django_database.db)..."
python manage.py migrate --database=django_database --run-syncdb

# 2. Collect and compress static assets with WhiteNoise
echo "--> Collecting and hashing static assets with WhiteNoise..."
python manage.py collectstatic --noinput

# 3. Auto-seed initial demo catalog if database is unpopulated
echo "--> Verifying database seed state..."
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dbms_project.settings')
django.setup()
from restaurants.models import Restaurant
if Restaurant.objects.count() == 0:
    from django.core.management import call_command
    print('--> Seeding initial catalog records (categories, restaurants, menu)...')
    call_command('seed_db')
else:
    print(f'--> Existing database detected with {Restaurant.objects.count()} restaurants. Skipping seed.')
"

# 4. Launch production Gunicorn WSGI server
echo "=== [OFO-DBMS] Launching Gunicorn WSGI Server on port 8000 ==="
exec gunicorn --config gunicorn.conf.py dbms_project.wsgi:application
