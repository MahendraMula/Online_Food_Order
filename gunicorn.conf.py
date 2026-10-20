# ==============================================================================
#  OFO-DBMS — Production Gunicorn Configuration for Azure App Service
# ==============================================================================
import multiprocessing
import os

# Server socket
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# Worker processes
# For SQLite, keeping worker count lean (2) avoids excessive database file lock contention
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = "gthread"
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "600"))
keepalive = 5

# Process naming
proc_name = "ofo_dbms_gunicorn"

# Logging: output stdout/stderr directly to Azure Log Stream
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
capture_output = True
enable_stdio_inheritance = True
