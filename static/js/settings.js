/* Settings page — Facebook authentication */

const form = document.getElementById("settings-form");
const banner = document.getElementById("status-banner");
const pageIdEl = document.getElementById("page-id");
const tokenEl = document.getElementById("access-token");
const tokenHint = document.getElementById("token-hint");
const apiVersionEl = document.getElementById("api-version");
const demoEl = document.getElementById("demo-mode");

function show(kind, msg) {
  banner.hidden = false;
  banner.className = kind === "ok" ? "banner banner-ok" : "banner banner-err";
  banner.textContent = msg;
}

async function getJSON(url, opts) {
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function load() {
  try {
    const s = await getJSON("/api/settings");
    pageIdEl.value = s.page_id || "";
    apiVersionEl.value = s.api_version || "v21.0";
    demoEl.checked = s.demo_mode;
    tokenHint.textContent = s.has_token
      ? `A token is saved (${s.token_masked}). Leave this field empty to keep it.`
      : "No token saved yet.";
    if (s.effective_demo && !s.demo_mode) {
      show("err", "The dashboard is currently showing demo data because no valid credentials are configured.");
    }
  } catch (e) {
    show("err", e.message);
  }
}

document.getElementById("toggle-token").addEventListener("click", (ev) => {
  const showing = tokenEl.type === "text";
  tokenEl.type = showing ? "password" : "text";
  ev.target.textContent = showing ? "Show" : "Hide";
});

document.getElementById("test-btn").addEventListener("click", async (ev) => {
  ev.target.disabled = true;
  ev.target.textContent = "Testing…";
  try {
    const d = await getJSON("/api/settings/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        page_id: pageIdEl.value,
        access_token: tokenEl.value,
        api_version: apiVersionEl.value,
      }),
    });
    if (d.ok) {
      show("ok", `Connection successful — page "${d.page_name}". Profile, posts, and insights are all readable.`);
    } else if (d.checks) {
      const lines = [];
      if (d.error) lines.push(d.error);
      if (d.page_name) lines.push(`Page profile: ok ("${d.page_name}")`);
      for (const [check, result] of Object.entries(d.checks)) {
        if (check === "profile") continue;
        lines.push(result === "ok" ? `${check}: ok` : `${check}: ${result}`);
      }
      show("err", lines.join("\n"));
      banner.style.whiteSpace = "pre-line";
    } else {
      show("err", d.error);
    }
  } catch (e) {
    show("err", e.message);
  } finally {
    ev.target.disabled = false;
    ev.target.textContent = "Test connection";
  }
});

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const btn = document.getElementById("save-btn");
  btn.disabled = true;
  btn.textContent = "Saving…";
  try {
    const d = await getJSON("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        page_id: pageIdEl.value,
        access_token: tokenEl.value,
        api_version: apiVersionEl.value,
        demo_mode: demoEl.checked,
      }),
    });
    tokenEl.value = "";
    await load();
    show("ok", d.effective_demo
      ? "Settings saved. The dashboard is in demo mode (sample data)."
      : "Settings saved. The dashboard is now using your Facebook Page data.");
  } catch (e) {
    show("err", e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Save settings";
  }
});

load();
