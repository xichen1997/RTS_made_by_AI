"""Flask application that exposes the RTS prototype as a web app."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from web_map_generator import WebMapGenerator


app = Flask(__name__)

# A single shared generator keeps memory usage low and allows players to
# request new maps on demand via the ``/api/map`` endpoint.
MAP_GENERATOR = WebMapGenerator()


@app.get("/")
def index():
    """Serve the single page application."""

    return render_template("index.html")


@app.get("/api/map")
def get_map():
    """Return the current map state.

    The endpoint accepts an optional ``seed`` query argument, allowing the
    front-end to trigger deterministic world generation when desired.
    """

    seed_arg = request.args.get("seed")
    if seed_arg is not None:
        try:
            MAP_GENERATOR.regenerate(seed=int(seed_arg))
        except ValueError as exc:  # pragma: no cover - validation is minimal
            return jsonify({"error": str(exc)}), 400
    return jsonify(MAP_GENERATOR.serialise())


@app.post("/api/map/regenerate")
def regenerate_map():
    """Trigger a brand new procedurally generated map."""

    payload = request.get_json(silent=True) or {}
    seed = payload.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
        except (TypeError, ValueError):
            return jsonify({"error": "seed must be an integer"}), 400

    MAP_GENERATOR.regenerate(seed=seed)
    return jsonify(MAP_GENERATOR.serialise())


if __name__ == "__main__":
    app.run(debug=True)
