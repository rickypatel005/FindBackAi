"""
Vercel Python Serverless entry-point for the FindBack AI FastAPI backend.

Vercel's @vercel/python runtime looks for an ASGI app exported from a file
inside the `api/` directory. Importing `app` here is enough — Vercel
handles the ASGI ↔ HTTP gateway automatically.

Important: on Vercel, ENABLE_IMAGE_AI and ENABLE_TEXT_AI are set to False
via environment variables (model weights are ~855 MB, far above Vercel's
250 MB function size limit). The matching engine falls back to the
text/field heuristic path, which still works end-to-end.
"""
from app.main import app  # noqa: F401  — re-exported as the ASGI entrypoint
