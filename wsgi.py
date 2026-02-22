from main import app
from waitress import serve
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # 'threads' parameter helps with concurrent requests (Scalability)
    # Cloud Run expects listening on 0.0.0.0
    print(f"Starting Production Server via Waitress on port {port}...")
    serve(app, host="0.0.0.0", port=port, threads=8)
