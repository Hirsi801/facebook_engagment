"""Facebook Page Engagement Dashboard — Flask app."""

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, render_template, request

from facebook_client import FacebookClient, FacebookClientError

app = Flask(__name__)
client = FacebookClient()


@app.route("/")
def index():
    return render_template("index.html")


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
