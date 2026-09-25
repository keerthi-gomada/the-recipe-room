"""Vercel entrypoint for the Epicure FastAPI application."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from backend.app import app
