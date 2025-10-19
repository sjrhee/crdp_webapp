from __future__ import annotations

import os
import json
from flask import Flask, jsonify, request, send_from_directory, Response
import requests


app = Flask(__name__, static_folder=".")


def _parse_json_body() -> dict:
    """Deterministic JSON parse with raw-body first.
    Order: raw body -> request.get_json(silent=True) -> {}
    """
    # 1) Raw body first
    try:
        raw = request.get_data(cache=True)
        if raw:
            ch = getattr(request, "charset", None)
            if not ch:
                # Fallback to Content-Type charset param or utf-8
                ch = request.mimetype_params.get("charset", "utf-8") if hasattr(request, "mimetype_params") else "utf-8"
            txt = raw.decode(ch, errors="replace").strip()
            if txt.startswith("{") or txt.startswith("["):
                try:
                    parsed = json.loads(txt)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    # fall through to loose parser
                    pass
                # 1b) Loose parser for curl-style unquoted bodies: {k:v,k:v}
                if txt.startswith("{") and ":" in txt:
                    try:
                        inner = txt.strip().strip("{}")
                        pairs = [p for p in inner.split(",") if ":" in p]
                        d = {}
                        for p in pairs:
                            k, v = p.split(":", 1)
                            k = k.strip().strip('"')
                            v = v.strip().strip('"')
                            d[k] = v
                        if d:
                            return d
                    except Exception:
                        pass
    except Exception:
        pass
    # 2) Flask helper as fallback
    try:
        body = request.get_json(silent=True)
        if isinstance(body, dict):
            return body
    except Exception:
        pass
    # 3) Default empty
    return {}


def _get_request_body() -> dict:
    """Return a merged body from JSON, form, and query string."""
    body = _parse_json_body()
    if not isinstance(body, dict):
        body = {}
    # Merge form fields (for application/x-www-form-urlencoded)
    try:
        if request.form:
            body = {**request.form.to_dict(flat=True), **body}
    except Exception:
        pass
    # Merge query params (as last resort overrides existing keys)
    try:
        if request.args:
            # Do not overwrite body keys unless missing
            q = request.args.to_dict(flat=True)
            for k, v in q.items():
                body.setdefault(k, v)
    except Exception:
        pass
    return body


# -------------------- Static files --------------------
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/style.css")
def style():
    return send_from_directory(app.static_folder, "style.css")


@app.get("/app.js")
def app_js():
    # Ensure correct content type for ES modules
    return send_from_directory(app.static_folder, "app.js", mimetype="text/javascript")


# -------------------- API proxy endpoints --------------------


@app.route("/proxy/_debug", methods=["GET", "POST"])
def proxy_debug():
    raw = request.get_data(cache=True) or b""
    ch = (request.mimetype_params.get("charset") if hasattr(request, "mimetype_params") else None) or "utf-8"
    txt = raw.decode(ch, errors="replace")
    parsed = _get_request_body()
    return jsonify({
        "method": request.method,
        "content_type": request.headers.get("Content-Type"),
        "raw_len": len(raw),
        "raw_preview": txt[:256],
        "parsed_body": parsed,
    })


# -------------------- Local mock endpoints for testing --------------------

@app.post("/mock/v1/protect")
def mock_protect():
    body = _get_request_body()
    policy = body.get("protection_policy_name")
    data = body.get("data")
    if not policy or data is None:
        return jsonify({"error": "bad_request", "message": "protection_policy_name and data are required"}), 400
    # Trivial mock: prefix to simulate protected data; include external_version
    return jsonify({
        "protected_data": f"pd:{data}",
        "external_version": "1001002",
    })


@app.post("/mock/v1/reveal")
def mock_reveal():
    body = _get_request_body()
    policy = body.get("protection_policy_name")
    protected_data = body.get("protected_data")
    if not policy or protected_data is None:
        return jsonify({"error": "bad_request", "message": "protection_policy_name and protected_data are required"}), 400
    # Trivial mock: strip the prefix
    prefix = "pd:"
    data = protected_data[len(prefix):] if isinstance(protected_data, str) and protected_data.startswith(prefix) else protected_data
    return jsonify({
        "data": str(data)
    })


@app.post("/proxy/v1/protect")
def proxy_protect():
    try:
        body = _get_request_body()
        host = body.pop("host", None)
        port = body.pop("port", None)
        scheme = (body.pop("scheme", "http") or "http").lower()
        base_path = body.pop("base_path", "/v1") or "/v1"
        if not host or not port:
            return jsonify({"error": "invalid_input", "message": "host and port required"}), 400
        if scheme not in ("http", "https"):
            return jsonify({"error": "invalid_input", "message": "scheme must be http or https"}), 400
        if not base_path.startswith("/"):
            base_path = "/" + base_path
        url = f"{scheme}://{host}:{port}{base_path}/protect"
        try:
            up = requests.post(url, json=body, timeout=10)
        except requests.exceptions.RequestException as e:
            return jsonify({"error": "upstream_request_failed", "message": str(e)}), 502
        return Response(up.content, status=up.status_code, content_type=up.headers.get("Content-Type", "application/json"))
    except Exception as e:
        return jsonify({"error": "exception", "message": str(e)}), 500


@app.post("/proxy/v1/reveal")
def proxy_reveal():
    try:
        body = _get_request_body()
        host = body.pop("host", None)
        port = body.pop("port", None)
        scheme = (body.pop("scheme", "http") or "http").lower()
        base_path = body.pop("base_path", "/v1") or "/v1"
        if not host or not port:
            return jsonify({"error": "invalid_input", "message": "host and port required"}), 400
        if scheme not in ("http", "https"):
            return jsonify({"error": "invalid_input", "message": "scheme must be http or https"}), 400
        if not base_path.startswith("/"):
            base_path = "/" + base_path
        url = f"{scheme}://{host}:{port}{base_path}/reveal"
        try:
            up = requests.post(url, json=body, timeout=10)
        except requests.exceptions.RequestException as e:
            return jsonify({"error": "upstream_request_failed", "message": str(e)}), 502
        return Response(up.content, status=up.status_code, content_type=up.headers.get("Content-Type", "application/json"))
    except Exception as e:
        return jsonify({"error": "exception", "message": str(e)}), 500


def main():
    # Default port 5000 for local dev; host 0.0.0.0 for container/VM.
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
