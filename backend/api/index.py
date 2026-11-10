"""Vercel serverless entrypoint: the Python runtime serves the ASGI ``app`` from api/*.py."""
import os
import sys

# Make the backend root importable (the function runs with api/ as its directory).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402,F401
