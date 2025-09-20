"""Entry point for running the ChronoFront web server locally."""

from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run("rts_web.server:app", host="0.0.0.0", port=8000, reload=False)
