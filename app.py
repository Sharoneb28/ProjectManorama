from flask import Flask, jsonify, request

import ticker_service as ts

app = Flask(__name__, static_folder="static", static_url_path="")
MAX_ITEMS, MAX_CHARS = 50, 8000


@app.get("/")
def index():
    return app.send_static_file("index.html")


def _entries(raw):
    """Split a batch into valid (id, text) pairs and rejected entries with reasons."""
    good, rejected = [], []
    for i, a in enumerate(raw):
        text = a.get("text") if isinstance(a, dict) else None
        if not isinstance(text, str):
            rejected.append({"index": i + 1, "reason": "entry has no 'text' string"})
        elif not text.strip():
            rejected.append({"index": i + 1, "reason": "announcement is empty"})
        elif len(text) > MAX_CHARS:
            rejected.append({"index": i + 1, "reason": f"too long ({len(text)} characters; max {MAX_CHARS})"})
        else:
            good.append((str(a.get("id") or f"a{i + 1}"), text.strip()))
    return good, rejected


def _run(item_id, text, avoid=()):
    try:
        return {"id": item_id, "source": text, **ts.generate(text, avoid)}
    except Exception as exc:  # one bad item must not sink the batch
        return {"id": item_id, "source": text, "ticker": "", "alternatives": [],
                "flags": [ts.flag("error", "failed", f"Generation failed: {str(exc)[:120]}")]}


@app.post("/api/generate")
def generate():
    raw = (request.get_json(silent=True) or {}).get("announcements")
    if not isinstance(raw, list) or not raw:
        return jsonify(error="Send a non-empty 'announcements' list."), 400
    if len(raw) > MAX_ITEMS:
        return jsonify(error=f"Too many announcements ({len(raw)}). The limit is {MAX_ITEMS} per batch."), 400
    good, rejected = _entries(raw)
    if not good:
        return jsonify(error="No valid announcements.", rejected=rejected), 400
    return jsonify(items=[_run(i, t) for i, t in good], rejected=rejected)


@app.post("/api/regenerate")
def regenerate():
    b = request.get_json(silent=True) or {}
    text = str(b.get("text", "")).strip()
    if not text or len(text) > MAX_CHARS:
        return jsonify(error="Invalid announcement text."), 400
    return jsonify(_run(str(b.get("id", "")), text, [str(a) for a in b.get("avoid", [])][:20]))


def _verdict(source, ticker):
    flags = ts.check(ticker, source)
    n = ts.word_count(ticker)
    return {"word_count": n, "flags": flags,
            "ok": 0 < n <= ts.MAX_WORDS and not any(f["level"] == "error" for f in flags)}


@app.post("/api/check")
def check():
    b = request.get_json(silent=True) or {}
    return jsonify(_verdict(str(b.get("source", "")), str(b.get("ticker", ""))))


@app.post("/api/validate")
def validate():
    """Authoritative re-check of many tickers; used before export."""
    raw = (request.get_json(silent=True) or {}).get("items")
    if not isinstance(raw, list) or len(raw) > MAX_ITEMS:
        return jsonify(error="Send an 'items' list (max 50)."), 400
    return jsonify(results=[{"id": str(i.get("id", "")), **_verdict(str(i.get("source", "")), str(i.get("ticker", "")))}
                            for i in raw if isinstance(i, dict)])


if __name__ == "__main__":
    app.run(port=5000)
