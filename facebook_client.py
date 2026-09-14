"""Facebook Graph API client with a built-in demo mode.

When FB_PAGE_ID / FB_PAGE_ACCESS_TOKEN are missing (or DEMO_MODE=true),
every method returns realistic sample data so the dashboard is fully
usable without credentials.
"""

import os
import random
import hashlib
from datetime import datetime, timedelta, timezone

import requests

GRAPH_URL = "https://graph.facebook.com"


class FacebookClientError(Exception):
    """Raised when the Graph API returns an error."""


class FacebookClient:
    def __init__(self):
        self.page_id = os.getenv("FB_PAGE_ID", "").strip()
        self.token = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
        self.api_version = os.getenv("FB_API_VERSION", "v21.0").strip()
        forced_demo = os.getenv("DEMO_MODE", "false").lower() == "true"
        self.demo = forced_demo or not (self.page_id and self.token)

    # ------------------------------------------------------------------ #
    # HTTP helper
    # ------------------------------------------------------------------ #
    def _get(self, path, **params):
        params["access_token"] = self.token
        url = f"{GRAPH_URL}/{self.api_version}/{path}"
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        if "error" in data:
            raise FacebookClientError(data["error"].get("message", "Graph API error"))
        return data

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def page_overview(self):
        """Page profile + headline counters."""
        if self.demo:
            return _demo_page_overview()
        fields = (
            "id,name,about,category,fan_count,followers_count,link,"
            "picture{url},cover{source},website,rating_count,overall_star_rating,"
            "talking_about_count,checkins"
        )
        d = self._get(self.page_id, fields=fields)
        return {
            "id": d.get("id"),
            "name": d.get("name"),
            "about": d.get("about", ""),
            "category": d.get("category", ""),
            "fan_count": d.get("fan_count", 0),
            "followers_count": d.get("followers_count", 0),
            "talking_about_count": d.get("talking_about_count", 0),
            "checkins": d.get("checkins", 0),
            "rating": d.get("overall_star_rating"),
            "rating_count": d.get("rating_count", 0),
            "link": d.get("link", ""),
            "website": d.get("website", ""),
            "picture": (d.get("picture") or {}).get("data", {}).get("url", ""),
            "cover": (d.get("cover") or {}).get("source", ""),
            "demo": False,
        }

    def page_insights(self, days=28):
        """Daily time series: impressions, reach, engaged users, new fans."""
        if self.demo:
            return _demo_insights(days)
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        metrics = (
            "page_impressions,page_impressions_unique,"
            "page_post_engagements,page_fan_adds,page_video_views"
        )
        d = self._get(
            f"{self.page_id}/insights",
            metric=metrics, period="day", since=since, until=until,
        )
        series = {}
        dates = []
        for m in d.get("data", []):
            values = m.get("values", [])
            key = m["name"]
            series[key] = [v.get("value", 0) for v in values]
            if not dates:
                dates = [v.get("end_time", "")[:10] for v in values]
        return {
            "dates": dates,
            "impressions": series.get("page_impressions", []),
            "reach": series.get("page_impressions_unique", []),
            "engagements": series.get("page_post_engagements", []),
            "fan_adds": series.get("page_fan_adds", []),
            "video_views": series.get("page_video_views", []),
            "demo": False,
        }

    def posts(self, limit=25):
        """Recent posts with engagement metrics."""
        if self.demo:
            return _demo_posts(limit)
        fields = (
            "id,message,created_time,permalink_url,full_picture,status_type,"
            "shares,comments.summary(true).limit(0),"
            "reactions.summary(true).limit(0),"
            "reactions.type(LIKE).summary(true).limit(0).as(like),"
            "reactions.type(LOVE).summary(true).limit(0).as(love),"
            "reactions.type(HAHA).summary(true).limit(0).as(haha),"
            "reactions.type(WOW).summary(true).limit(0).as(wow),"
            "reactions.type(SAD).summary(true).limit(0).as(sad),"
            "reactions.type(ANGRY).summary(true).limit(0).as(angry)"
        )
        d = self._get(f"{self.page_id}/posts", fields=fields, limit=limit)
        out = []
        for p in d.get("data", []):
            def _count(key):
                return ((p.get(key) or {}).get("summary") or {}).get("total_count", 0)
            reactions = _count("reactions")
            comments = _count("comments")
            shares = (p.get("shares") or {}).get("count", 0)
            out.append({
                "id": p.get("id"),
                "message": p.get("message", ""),
                "created_time": p.get("created_time", ""),
                "permalink_url": p.get("permalink_url", ""),
                "picture": p.get("full_picture", ""),
                "type": p.get("status_type", ""),
                "reactions": reactions,
                "comments": comments,
                "shares": shares,
                "total_engagement": reactions + comments + shares,
                "reaction_breakdown": {
                    "like": _count("like"), "love": _count("love"),
                    "haha": _count("haha"), "wow": _count("wow"),
                    "sad": _count("sad"), "angry": _count("angry"),
                },
            })
        return {"posts": out, "demo": False}

    def engaged_users(self, limit=25):
        """People who engaged with recent posts (commenters + reactors).

        The Graph API does not expose a page-level 'engaged users' list, so
        this aggregates commenters and reactors across recent posts. Names
        require the posts' comments/reactions to be readable by the token.
        """
        if self.demo:
            return _demo_engaged_users(limit)
        posts = self._get(f"{self.page_id}/posts", fields="id", limit=15)
        users = {}
        for p in posts.get("data", []):
            pid = p["id"]
            try:
                comments = self._get(f"{pid}/comments", fields="from{id,name,picture}", limit=100)
                for c in comments.get("data", []):
                    frm = c.get("from")
                    if frm:
                        u = users.setdefault(frm["id"], {
                            "id": frm["id"], "name": frm.get("name", "Unknown"),
                            "picture": (frm.get("picture") or {}).get("data", {}).get("url", ""),
                            "comments": 0, "reactions": 0,
                        })
                        u["comments"] += 1
                reactions = self._get(f"{pid}/reactions", fields="id,name,type,pic_small", limit=100)
                for r in reactions.get("data", []):
                    u = users.setdefault(r["id"], {
                        "id": r["id"], "name": r.get("name", "Unknown"),
                        "picture": r.get("pic_small", ""),
                        "comments": 0, "reactions": 0,
                    })
                    u["reactions"] += 1
            except FacebookClientError:
                continue
        ranked = sorted(
            users.values(),
            key=lambda u: (u["comments"] * 2 + u["reactions"]),
            reverse=True,
        )[:limit]
        for u in ranked:
            u["score"] = u["comments"] * 2 + u["reactions"]
        return {"users": ranked, "demo": False}


# ---------------------------------------------------------------------- #
# Demo data
# ---------------------------------------------------------------------- #
_rng = random.Random(42)

_DEMO_POST_MESSAGES = [
    "🎉 Big announcement! We're launching our new community program next week. Stay tuned for details.",
    "Behind the scenes at our office — meet the team that makes it all happen! 📸",
    "What feature would you like to see next? Drop your ideas in the comments 👇",
    "Throwback to last month's meetup. Over 300 of you showed up — thank you! 🙌",
    "Quick tip Tuesday: 5 ways to get more out of our product. Thread below 🧵",
    "We just hit 50,000 followers! Thank you for being part of this journey ❤️",
    "Live Q&A this Friday at 6 PM. Bring your toughest questions!",
    "Customer spotlight: how Amina grew her business 3x using our platform 🚀",
    "Weekend vibes ☀️ What are you all up to?",
    "New blog post: The complete guide to social media analytics in 2026.",
    "Poll time! Which do you prefer — video tutorials or written guides?",
    "Our team volunteered at the local food bank today. Giving back matters 💚",
    "Flash sale! 24 hours only — 30% off everything. Link in bio.",
    "Monday motivation: 'The best way to predict the future is to create it.'",
    "Sneak peek at what we've been building... 👀 Can you guess?",
    "Thank you to everyone who joined yesterday's webinar. Recording is now up!",
    "Big news: we're expanding to three new cities this quarter 🌍",
    "How it started vs. how it's going 😄 Swipe to see our journey.",
    "Reminder: applications for our ambassador program close this Sunday.",
    "We read every single comment. Keep the feedback coming — it shapes what we build!",
]

_DEMO_NAMES = [
    "Amina Hassan", "James Okoro", "Fatima Ali", "David Kim", "Sofia Martinez",
    "Mohamed Abdi", "Emily Chen", "Ahmed Yusuf", "Grace Njeri", "Omar Farah",
    "Layla Ibrahim", "Daniel Osei", "Hodan Warsame", "Lucas Silva", "Zainab Noor",
    "Michael Brown", "Sagal Ahmed", "Priya Patel", "Abdi Rahman", "Nora Hussein",
    "Khalid Jama", "Ifrah Mohamud", "Peter Kamau", "Maryam Said", "Liban Dahir",
]


def _demo_page_overview():
    return {
        "id": "1234567890",
        "name": "Horizon Digital",
        "about": "We help businesses grow through smart digital marketing and community building.",
        "category": "Marketing Agency",
        "fan_count": 52480,
        "followers_count": 54912,
        "talking_about_count": 3862,
        "checkins": 1204,
        "rating": 4.7,
        "rating_count": 318,
        "link": "https://facebook.com/horizondigital",
        "website": "https://horizondigital.example.com",
        "picture": "",
        "cover": "",
        "demo": True,
    }


def _demo_insights(days=28):
    rng = random.Random(7)
    today = datetime.now(timezone.utc).date()
    dates, impressions, reach, engagements, fan_adds, video_views = [], [], [], [], [], []
    base_imp = 8200.0
    for i in range(days, 0, -1):
        day = today - timedelta(days=i)
        dates.append(day.isoformat())
        # gentle upward trend + weekly cycle + noise
        weekly = 1.25 if day.weekday() in (4, 5) else (0.85 if day.weekday() == 0 else 1.0)
        base_imp *= 1.004
        imp = int(base_imp * weekly * rng.uniform(0.82, 1.18))
        impressions.append(imp)
        reach.append(int(imp * rng.uniform(0.58, 0.72)))
        engagements.append(int(imp * rng.uniform(0.055, 0.095)))
        fan_adds.append(int(imp * rng.uniform(0.004, 0.009)))
        video_views.append(int(imp * rng.uniform(0.22, 0.38)))
    return {
        "dates": dates,
        "impressions": impressions,
        "reach": reach,
        "engagements": engagements,
        "fan_adds": fan_adds,
        "video_views": video_views,
        "demo": True,
    }


def _demo_posts(limit=25):
    rng = random.Random(11)
    now = datetime.now(timezone.utc)
    posts = []
    for i, msg in enumerate(_DEMO_POST_MESSAGES[:limit]):
        created = now - timedelta(days=i * 1.6 + rng.uniform(0, 1), hours=rng.randint(0, 12))
        popularity = rng.uniform(0.4, 3.2)
        like = int(180 * popularity * rng.uniform(0.7, 1.3))
        love = int(like * rng.uniform(0.15, 0.45))
        haha = int(like * rng.uniform(0.02, 0.2))
        wow = int(like * rng.uniform(0.01, 0.12))
        sad = int(like * rng.uniform(0.0, 0.03))
        angry = int(like * rng.uniform(0.0, 0.02))
        reactions = like + love + haha + wow + sad + angry
        comments = int(reactions * rng.uniform(0.08, 0.3))
        shares = int(reactions * rng.uniform(0.04, 0.18))
        ptype = rng.choice(["added_photos", "mobile_status_update", "added_video", "shared_story"])
        posts.append({
            "id": f"1234567890_{1000 + i}",
            "message": msg,
            "created_time": created.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "permalink_url": "https://facebook.com/horizondigital",
            "picture": "",
            "type": ptype,
            "reactions": reactions,
            "comments": comments,
            "shares": shares,
            "total_engagement": reactions + comments + shares,
            "reaction_breakdown": {
                "like": like, "love": love, "haha": haha,
                "wow": wow, "sad": sad, "angry": angry,
            },
        })
    return {"posts": posts, "demo": True}


def _demo_engaged_users(limit=25):
    rng = random.Random(23)
    users = []
    for i, name in enumerate(_DEMO_NAMES[:limit]):
        comments = max(0, int(rng.gauss(6, 4)))
        reactions = max(1, int(rng.gauss(18, 10)))
        uid = hashlib.md5(name.encode()).hexdigest()[:12]
        users.append({
            "id": uid, "name": name, "picture": "",
            "comments": comments, "reactions": reactions,
            "score": comments * 2 + reactions,
        })
    users.sort(key=lambda u: u["score"], reverse=True)
    return {"users": users, "demo": True}
