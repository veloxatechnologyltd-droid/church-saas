"""Serverless entrypoint (Vercel's Python runtime looks for an ASGI ``app`` here)."""
from app.main import app  # noqa: F401
