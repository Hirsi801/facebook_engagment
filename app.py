"""Facebook Page Engagement Dashboard — Flask app."""

import re

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, render_template, request

from facebook_client import FacebookClient, FacebookClientError
from settings_store import read_settings, save_settings

app = Flask(__name__)
client = FacebookClient()


def _rebuild_client():
    global client
    client = FacebookClient()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/settings")
def settings_page():
    return render_template("settings.html")


def _masked(token):
    if not token:
        return ""
    if len(token) <= 8:
        return "*" * len(token)
    return token[:4] + "*" * 12 + token[-4:]


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    s = read_settings()
    return jsonify({
        "page_id": s["FB_PAGE_ID"],
        "token_masked": _masked(s["FB_PAGE_ACCESS_TOKEN"]),
        "has_token": bool(s["FB_PAGE_ACCESS_TOKEN"]),
        "api_version": s["FB_API_VERSION"],
        "demo_mode": s["DEMO_MODE"].lower() == "true",
        "effective_demo": client.demo,
    })


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.get_json(silent=True) or {}
    updates = {}
    if "page_id" in data:
        updates["FB_PAGE_ID"] = str(data["page_id"]).strip()
    # Empty token field means "keep the existing token"
    token = str(data.get("access_token", "")).strip()
    if token:
        updates["FB_PAGE_ACCESS_TOKEN"] = token
    if data.get("clear_token"):
        updates["FB_PAGE_ACCESS_TOKEN"] = ""
    if "api_version" in data:
        v = str(data["api_version"]).strip()
        if v and not re.match(r"^v\d+\.\d+$", v):
            return jsonify({"error": "API version must look like v21.0"}), 400
        updates["FB_API_VERSION"] = v or "v21.0"
    if "demo_mode" in data:
        updates["DEMO_MODE"] = "true" if data["demo_mode"] else "false"
    save_settings(updates)
    _rebuild_client()
    return jsonify({"ok": True, "effective_demo": client.demo})


@app.route("/api/settings/test", methods=["POST"])
def api_test_settings():
    """Verify credentials against the Graph API without saving them."""
    data = request.get_json(silent=True) or {}
    s = read_settings()
    page_id = str(data.get("page_id", "")).strip() or s["FB_PAGE_ID"]
    token = str(data.get("access_token", "")).strip() or s["FB_PAGE_ACCESS_TOKEN"]
    api_version = str(data.get("api_version", "")).strip() or s["FB_API_VERSION"]
    if not page_id or not token:
        return jsonify({"ok": False, "error": "Page ID and access token are required."}), 400

    import requests as _rq

    def graph(path, **params):
        params["access_token"] = token
        r = _rq.get(f"https://graph.facebook.com/{api_version}/{path}", params=params, timeout=15)
        d = r.json()
        if "error" in d:
            raise FacebookClientError(d["error"].get("message", "Graph API error"))
        return d

    checks = {}
    page_name = None
    try:
        # Whose token is this? A Page token identifies as the page itself;
        # a User token identifies as a person and can't read insights/posts.
        me = graph("me", fields="id,name")
        if me.get("id") != page_id:
            checks["token_type"] = (
                f'This is a token for "{me.get("name")}" (id {me.get("id")}), not a Page '
                f"token for page {page_id}. In the Graph API Explorer, query me/accounts "
                "and use the access_token listed for your page."
            )
        d = graph(page_id, fields="id,name,fan_count")
        page_name = d.get("name")
        checks["profile"] = "ok"
    except FacebookClientError as e:
        return jsonify({"ok": False, "error": str(e), "checks": checks})
    except Exception as e:
        # Don't echo exception details — request URLs inside them contain the token.
        return jsonify({"ok": False, "error": f"Could not reach the Graph API ({type(e).__name__}). Check your network connection."})

    for name, path, params in (
        ("posts", f"{page_id}/posts", {"fields": "id", "limit": 1}),
        ("insights", f"{page_id}/insights", {"metric": "page_impressions", "period": "day"}),
    ):
        try:
            graph(path, **params)
            checks[name] = "ok"
        except FacebookClientError as e:
            checks[name] = str(e)
        except Exception:
            checks[name] = "unreachable"

    ok = all(v == "ok" for v in checks.values())
    return jsonify({"ok": ok, "page_name": page_name, "checks": checks})


@app.route("/api/overview")
def api_overview():
    try:
        return jsonify(client.page_overview())
    except FacebookClientError as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/insights")
def api_insights():
    days = min(max(request.args.get("days", 28, type=int), 7), 90)
    try:
        return jsonify(client.page_insights(days=days))
    except FacebookClientError as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/posts")
def api_posts():
    limit = min(max(request.args.get("limit", 20, type=int), 1), 50)
    try:
        return jsonify(client.posts(limit=limit))
    except FacebookClientError as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/engaged-users")
def api_engaged_users():
    limit = min(max(request.args.get("limit", 20, type=int), 1), 50)
    try:
        return jsonify(client.engaged_users(limit=limit))
    except FacebookClientError as e:
        return jsonify({"error": str(e)}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
