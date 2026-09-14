/* Facebook Page Engagement Dashboard */

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const state = { days: 28, charts: {} };

const fmt = (n) => {
  if (n == null) return "–";
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e4) return (n / 1e3).toFixed(1) + "K";
  return n.toLocaleString();
};

const sum = (arr) => (arr || []).reduce((a, b) => a + b, 0);

function chartDefaults() {
  Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", sans-serif';
  Chart.defaults.color = css("--muted");
  Chart.defaults.borderColor = css("--grid");
}

function baseOptions(showLegend) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        display: showLegend,
        labels: { color: css("--text-secondary"), boxWidth: 12, boxHeight: 12, usePointStyle: true },
      },
      tooltip: {
        backgroundColor: css("--surface"),
        titleColor: css("--text-primary"),
        bodyColor: css("--text-secondary"),
        borderColor: css("--border"),
        borderWidth: 1,
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
      y: { beginAtZero: true, grid: { color: css("--grid") }, ticks: { callback: (v) => fmt(v) } },
    },
  };
}

function renderChart(id, config) {
  if (state.charts[id]) state.charts[id].destroy();
  state.charts[id] = new Chart(document.getElementById(id), config);
}

function shortDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

async function getJSON(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function showError(msg) {
  let el = document.querySelector(".error-banner");
  if (!el) {
    el = document.createElement("div");
    el.className = "error-banner";
    document.querySelector("main").prepend(el);
  }
  el.textContent = "Facebook API error: " + msg;
}

/* ------------------------------------------------------------------ */

async function loadOverview() {
  const d = await getJSON("/api/overview");
  document.getElementById("page-name").textContent = d.name;
  document.getElementById("page-category").textContent =
    [d.category, d.about].filter(Boolean).join(" · ");
  document.getElementById("kpi-fans").textContent = fmt(d.fan_count);
  document.getElementById("kpi-followers").textContent = fmt(d.followers_count);
  document.getElementById("kpi-talking").textContent = fmt(d.talking_about_count);
  document.getElementById("demo-badge").hidden = !d.demo;
}

async function loadInsights() {
  const d = await getJSON(`/api/insights?days=${state.days}`);
  const labels = d.dates.map(shortDate);

  const noteId = "metrics-note";
  document.getElementById(noteId)?.remove();
  if (d.unavailable && d.unavailable.length) {
    const note = document.createElement("p");
    note.id = noteId;
    note.style.cssText = "color:var(--muted);font-size:12px;margin:0 0 12px";
    note.textContent =
      "Not provided by the Facebook API for this page/API version: " +
      d.unavailable.join(", ").replaceAll("_", " ") + ".";
    document.querySelector("main").prepend(note);
  }

  document.getElementById("kpi-engagement").textContent = fmt(sum(d.engagements));
  document.getElementById("kpi-reach").textContent = fmt(sum(d.reach));
  document.getElementById("kpi-newfans").textContent = fmt(sum(d.fan_adds));

  renderChart("chart-reach", {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Impressions",
          data: d.impressions,
          borderColor: css("--series-1"),
          backgroundColor: css("--series-1"),
          borderWidth: 2, pointRadius: 0, pointHitRadius: 12, tension: 0.3,
        },
        {
          label: "Reach",
          data: d.reach,
          borderColor: css("--series-2"),
          backgroundColor: css("--series-2"),
          borderWidth: 2, pointRadius: 0, pointHitRadius: 12, tension: 0.3,
        },
      ],
    },
    options: baseOptions(true),
  });

  renderChart("chart-engagement", {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Engagements",
        data: d.engagements,
        backgroundColor: css("--series-3"),
        borderRadius: 4,
        maxBarThickness: 18,
      }],
    },
    options: baseOptions(false),
  });

  renderChart("chart-fans", {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "New likes",
        data: d.fan_adds,
        backgroundColor: css("--series-1"),
        borderRadius: 4,
        maxBarThickness: 18,
      }],
    },
    options: baseOptions(false),
  });
}

async function loadPosts() {
  const d = await getJSON("/api/posts?limit=20");
  const posts = d.posts.slice().sort((a, b) => b.total_engagement - a.total_engagement);

  const tbody = document.querySelector("#posts-table tbody");
  tbody.innerHTML = "";
  for (const p of posts) {
    const tr = document.createElement("tr");
    const msg = p.message || "(no text)";
    tr.innerHTML = `
      <td><div class="post-msg"><a href="${p.permalink_url}" target="_blank" rel="noopener"></a></div></td>
      <td class="post-date">${shortDate(p.created_time)}</td>
      <td class="num">${fmt(p.reactions)}</td>
      <td class="num">${fmt(p.comments)}</td>
      <td class="num">${fmt(p.shares)}</td>
      <td class="num total-cell">${fmt(p.total_engagement)}</td>`;
    tr.querySelector("a").textContent = msg;
    tbody.appendChild(tr);
  }
  document.querySelectorAll("#posts-table th").forEach((th, i) => {
    if (i >= 2) th.classList.add("num");
  });

  // Aggregate reaction breakdown across recent posts
  const agg = { like: 0, love: 0, haha: 0, wow: 0, sad: 0, angry: 0 };
  for (const p of d.posts) {
    for (const k of Object.keys(agg)) agg[k] += (p.reaction_breakdown || {})[k] || 0;
  }
  renderChart("chart-reactions", {
    type: "doughnut",
    data: {
      labels: ["👍 Like", "❤️ Love", "😆 Haha", "😮 Wow", "😢 Sad", "😡 Angry"],
      datasets: [{
        data: [agg.like, agg.love, agg.haha, agg.wow, agg.sad, agg.angry],
        backgroundColor: [
          css("--series-1"), css("--series-2"), css("--series-3"),
          css("--series-4"), css("--series-5"), css("--series-6"),
        ],
        borderColor: css("--surface"),
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      cutout: "62%",
      plugins: {
        legend: {
          position: "right",
          labels: { color: css("--text-secondary"), boxWidth: 12, usePointStyle: true },
        },
        tooltip: {
          backgroundColor: css("--surface"),
          titleColor: css("--text-primary"),
          bodyColor: css("--text-secondary"),
          borderColor: css("--border"),
          borderWidth: 1,
        },
      },
    },
  });
}

async function loadEngagedUsers() {
  const d = await getJSON("/api/engaged-users?limit=15");
  const list = document.getElementById("engaged-users");
  list.innerHTML = "";
  d.users.forEach((u, i) => {
    const initials = u.name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="rank">${i + 1}</span>
      ${u.picture
        ? `<img class="avatar" alt="" src="${u.picture}">`
        : `<span class="avatar"></span>`}
      <div class="user-meta">
        <div class="user-name"></div>
        <div class="user-stats">${u.comments} comments · ${u.reactions} reactions</div>
      </div>
      <span class="user-score" title="Engagement score">${u.score}</span>`;
    li.querySelector(".user-name").textContent = u.name;
    if (!u.picture) li.querySelector(".avatar").textContent = initials;
    list.appendChild(li);
  });
}

/* ------------------------------------------------------------------ */

async function loadAll() {
  chartDefaults();
  const jobs = [loadOverview(), loadInsights(), loadPosts(), loadEngagedUsers()];
  const results = await Promise.allSettled(jobs);
  const firstError = results.find((r) => r.status === "rejected");
  if (firstError) showError(firstError.reason.message);
}

document.querySelectorAll(".range-picker button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".range-picker button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.days = parseInt(btn.dataset.days, 10);
    loadInsights().catch((e) => showError(e.message));
  });
});

window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", loadAll);

loadAll();
