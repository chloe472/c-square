echo "Starting Princess Diaries API..."
gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 30 app:app