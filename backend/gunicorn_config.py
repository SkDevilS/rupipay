import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
# For c7i.flex large (2 vCPU): 2 * 2 + 1 = 5 workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"  # Use gevent for async I/O
worker_connections = 1000
max_requests = 1000  # Restart workers after 1000 requests (prevent memory leaks)
max_requests_jitter = 50
timeout = 60  # 60 seconds for external API calls
keepalive = 5

# Logging
log_dir = "/var/log/moneyone"
os.makedirs(log_dir, exist_ok=True)
accesslog = "-"  # Log to stdout (terminal)
errorlog = "-"   # Log to stderr (terminal)
loglevel = "debug"  # Changed from "info" to "debug" for more detailed logs
# Detailed access log format with IP, method, path, status, response time
access_log_format = '%(t)s | IP: %(h)s | %(m)s %(U)s%(q)s | Status: %(s)s | Size: %(B)s | Time: %(M)sms | Referrer: "%(f)s" | User-Agent: "%(a)s"'

# Server mechanics
daemon = False
pidfile = "/var/run/moneyone-api.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# Performance
preload_app = True  # Load app before forking workers (saves memory)

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print(f"Starting Gunicorn with {workers} workers")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("Reloading Gunicorn workers")

def when_ready(server):
    """Called just after the server is started."""
    print(f"Gunicorn is ready. Listening on {bind}")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    print(f"Worker {worker.pid} received INT or QUIT signal")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    print(f"Worker {worker.pid} received SIGABRT signal")
