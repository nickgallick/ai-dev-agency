#!/usr/bin/env python3
"""
Lightweight GitHub webhook listener for auto-deploy.
Listens on port 9000 for push events and triggers deploy.sh.

Setup:
  1. Copy to server: scp scripts/webhook-listener.py ubuntu@<server>:~/
  2. Install as systemd service (see scripts/webhook-deploy.service)
  3. Add webhook in GitHub repo settings:
     - URL: http://<server-ip>:9000/webhook
     - Content type: application/json
     - Secret: (set WEBHOOK_SECRET env var on server)
     - Events: Just the push event
"""

import hashlib
import hmac
import json
import os
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
DEPLOY_SCRIPT = os.environ.get("DEPLOY_SCRIPT", "/home/ubuntu/ai-dev-agency/scripts/deploy.sh")
DEPLOY_BRANCH = os.environ.get("DEPLOY_BRANCH", "master")
PORT = int(os.environ.get("WEBHOOK_PORT", "9000"))


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook HMAC signature."""
    if not WEBHOOK_SECRET:
        return True  # Skip verification if no secret set
    if not signature:
        return False
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length)

        # Verify signature
        signature = self.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(payload, signature):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Invalid signature")
            return

        # Parse event
        event = self.headers.get("X-GitHub-Event", "")
        if event != "push":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"Ignored event: {event}".encode())
            return

        # Check branch
        try:
            data = json.loads(payload)
            ref = data.get("ref", "")
            branch = ref.split("/")[-1] if "/" in ref else ref
        except (json.JSONDecodeError, KeyError):
            branch = ""

        if branch != DEPLOY_BRANCH:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"Ignored branch: {branch}".encode())
            return

        # Trigger deploy
        print(f"[webhook] Push to {branch} detected, deploying...")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Deploy triggered")

        # Run deploy in background
        subprocess.Popen(
            ["bash", DEPLOY_SCRIPT, branch],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[webhook] {args[0]}")


if __name__ == "__main__":
    print(f"[webhook] Listening on port {PORT}")
    print(f"[webhook] Deploy branch: {DEPLOY_BRANCH}")
    print(f"[webhook] Secret configured: {'yes' if WEBHOOK_SECRET else 'no (WARNING: unsigned)'}")
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[webhook] Shutting down")
        server.shutdown()
