#!/bin/sh
set -e

# Wait for DB if needed
python - <<'PY'
import os, time
import socket
host = os.getenv('POSTGRES_HOST','db')
port = int(os.getenv('POSTGRES_PORT','5432'))
s = socket.socket()
for i in range(60):
    try:
        s.connect((host, port))
        s.close()
        break
    except OSError:
        time.sleep(1)
else:
    print('DB not reachable on %s:%s' % (host, port))
PY

# Run Alembic migrations
alembic -c /app/alembic.ini upgrade head || true

# Start API
exec uvicorn main:app --host 0.0.0.0 --port 8000
