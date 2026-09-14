# Facebook Page Engagement Dashboard

A professional web dashboard that pulls your Facebook Page's analytics from the
Facebook Graph API and visualizes engagement: reach, impressions, daily
engagement, follower growth, reaction breakdowns, top posts, and the users who
engage most with your page.

![stack](https://img.shields.io/badge/stack-Flask%20%2B%20Chart.js-blue)

## Features

- **Page overview** — likes, followers, "talking about this", ratings
- **KPI tiles** — total engagement, reach, and new page likes for the selected period
- **Time-series charts** — impressions & reach, daily engagement, new likes per day
- **Reaction breakdown** — Like / Love / Haha / Wow / Sad / Angry across recent posts
- **Top posts table** — recent posts ranked by total engagement (reactions + comments + shares)
- **Top engaged users** — commenters and reactors across recent posts, ranked by an engagement score
- **Settings page** — configure your Page ID, access token, API version, and demo mode from the browser (`/settings`), with a "Test connection" check before saving
- **Date-range filter** — 7 / 28 / 90 days
- **Light & dark mode** — follows the OS theme automatically
- **Demo mode** — runs with realistic sample data when no credentials are configured, so you can try the dashboard immediately

## Quick start (demo mode)

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 — with no credentials configured the dashboard runs
on built-in sample data (a "Demo data" badge is shown).

## Connecting your real Facebook Page

1. Create an app at [developers.facebook.com](https://developers.facebook.com/).
2. In the [Graph API Explorer](https://developers.facebook.com/tools/explorer/),
   generate a **Page access token** with these permissions:
   - `pages_read_engagement`
   - `read_insights`
   - `pages_show_list`
3. (Recommended) Exchange it for a long-lived token via the
   [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/).
4. Configure the app — either from the browser at **http://localhost:5000/settings**
   (paste your Page ID and token, click *Test connection*, then *Save settings*),
   or by hand:

```bash
cp .env.example .env
# edit .env:
#   FB_PAGE_ID=<your page id>
#   FB_PAGE_ACCESS_TOKEN=<your page token>
python app.py
```

Settings saved from the browser are written to the same server-side `.env`
file (mode `600`, git-ignored) and take effect immediately without a restart.
The saved token is never sent back to the browser — only a masked preview.
If you deploy the dashboard publicly, put it behind authentication; the
settings page itself is not password-protected.

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /api/overview` | Page profile and headline counters |
| `GET /api/insights?days=28` | Daily impressions, reach, engagements, new likes, video views (7–90 days) |
| `GET /api/posts?limit=20` | Recent posts with reactions, comments, shares, and reaction breakdown |
| `GET /api/engaged-users?limit=15` | Users who engaged with recent posts, ranked by score (2×comments + reactions) |
| `GET/POST /api/settings` | Read (token masked) or save Facebook credentials and demo mode |
| `POST /api/settings/test` | Verify credentials against the Graph API without saving |

## Notes & limitations

- The Graph API restricts some data: reactor/commenter names are only returned
  where the token has permission to read them, and several page insights
  metrics were deprecated or restricted by Meta over time. The client degrades
  gracefully — anything unavailable is simply omitted.
- Insight metrics are fetched with `period=day`; ranges are capped at 90 days
  per request as required by the API.
- Never commit your `.env` — it is git-ignored.

## Project structure

```
app.py                 Flask app + JSON API routes
facebook_client.py     Graph API client with demo-mode fallback
templates/index.html   Dashboard page
static/css/style.css   Theme-aware styling (light/dark)
static/js/dashboard.js Charts (Chart.js) and data loading
```
