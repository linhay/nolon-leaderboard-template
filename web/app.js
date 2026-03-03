const toolSelect = document.getElementById("tool-select");
const rankingSelect = document.getElementById("ranking-select");
const windowSelect = document.getElementById("window-select");
const rowsEl = document.getElementById("rows");
const metaEl = document.getElementById("meta");
const repoLinkEl = document.getElementById("repo-link");
const summaryRankingEl = document.getElementById("summary-ranking");
const summaryToolEl = document.getElementById("summary-tool");
const summaryCountEl = document.getElementById("summary-count");
const summaryTopEl = document.getElementById("summary-top");
const trendSvgEl = document.getElementById("trend-svg");
const trendLegendEl = document.getElementById("trend-legend");
const trendEmptyEl = document.getElementById("trend-empty");
const trendTooltipEl = document.getElementById("trend-tooltip");

const TREND_COLORS = ["#0f766e", "#2563eb", "#d97706", "#9333ea", "#dc2626"];
const query = new URLSearchParams(window.location.search);
const hiddenTrendUsers = new Set();


const formatNumber = (value) => {
  if (value >= 100000000) return `${(value / 100000000).toFixed(1)}亿`;
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return `${value}`;
};

const renderRows = (rows) => {
  rowsEl.innerHTML = "";
  if (!rows || rows.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 5;
    td.className = "empty-row";
    td.textContent = "No data";
    tr.appendChild(td);
    rowsEl.appendChild(tr);
    return;
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    const rankClass = row.rank <= 3 ? `rank-badge rank-${row.rank}` : "rank-badge";
    const totalTokens = row.totalTokens ?? row.value ?? 0;
    const inputTokens = row.inputTokens ?? 0;
    const outputTokens = row.outputTokens ?? 0;
    const primaryTool = row.primaryTool || "-";
    const relativeUpdated = window.TrendLogic?.formatRelativeTime
      ? window.TrendLogic.formatRelativeTime(row.lastUpdated)
      : (row.lastUpdated || "-");
    tr.innerHTML = `
      <td><span class="${rankClass}">${row.rank}</span></td>
      <td>${row.displayName || row.username}</td>
      <td><strong>${primaryTool}</strong> / <span class="value-cell">${formatNumber(totalTokens)}</span></td>
      <td>In <span class="value-cell">${formatNumber(inputTokens)}</span> / Out <span class="value-cell">${formatNumber(outputTokens)}</span></td>
      <td title="${row.lastUpdated || "-"}">${relativeUpdated}</td>
    `;
    rowsEl.appendChild(tr);
  });
};

const resolveRows = (snapshot) => {
  const rankingType = rankingSelect.value;
  const selectedTool = toolSelect.value;
  if (selectedTool === "all") {
    return snapshot.rankings?.overall?.[rankingType] || [];
  }
  return snapshot.rankings?.byTool?.[selectedTool]?.[rankingType] || [];
};

const clearTrend = (message) => {
  if (trendSvgEl) trendSvgEl.innerHTML = "";
  if (trendLegendEl) trendLegendEl.innerHTML = "";
  if (trendTooltipEl) trendTooltipEl.hidden = true;
  if (trendEmptyEl) {
    trendEmptyEl.hidden = false;
    trendEmptyEl.textContent = message;
  }
};

const renderTrend = (snapshot, rows) => {
  if (!trendSvgEl || !trendLegendEl || !window.TrendLogic) return;

  const topUserIds = window.TrendLogic.pickTopUsersFromRows(rows);
  if (topUserIds.length === 0) {
    clearTrend("No trend data");
    return;
  }

  const dataset = window.TrendLogic.getTimeseriesDataset(snapshot, toolSelect.value);
  const windowDays = Number.parseInt(windowSelect?.value || "7", 10);
  const trend = window.TrendLogic.buildTrendSeriesForTopUsers(dataset, topUserIds, windowDays);
  [...hiddenTrendUsers].forEach((userId) => {
    if (!topUserIds.includes(userId)) hiddenTrendUsers.delete(userId);
  });
  const visibleTrend = window.TrendLogic.filterTrendByHiddenUsers(trend, hiddenTrendUsers);
  if (!trend.dates.length || !trend.series.length) {
    clearTrend("No trend data");
    return;
  }
  if (!visibleTrend.series.length) {
    clearTrend("All trend lines are hidden");
    return;
  }

  if (trendEmptyEl) trendEmptyEl.hidden = true;
  trendSvgEl.innerHTML = "";
  trendLegendEl.innerHTML = "";

  const width = 760;
  const height = 280;
  const margin = { top: 16, right: 12, bottom: 34, left: 48 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const allValues = visibleTrend.series.flatMap((item) => item.values);
  const maxValue = Math.max(...allValues, 0);
  const yMax = maxValue > 0 ? maxValue : 1;

  const xAt = (index) => {
    if (trend.dates.length <= 1) return margin.left + innerWidth / 2;
    return margin.left + (index / (trend.dates.length - 1)) * innerWidth;
  };
  const yAt = (value) => margin.top + innerHeight - (value / yMax) * innerHeight;
  const indexFromClientX = (clientX) => {
    const rect = trendSvgEl.getBoundingClientRect();
    if (!rect.width || visibleTrend.dates.length <= 1) return 0;
    const x = ((clientX - rect.left) / rect.width) * width;
    const clampedX = Math.max(margin.left, Math.min(margin.left + innerWidth, x));
    const ratio = (clampedX - margin.left) / innerWidth;
    return Math.round(ratio * (visibleTrend.dates.length - 1));
  };

  const ns = "http://www.w3.org/2000/svg";
  const make = (tag, attrs) => {
    const el = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([key, value]) => {
      el.setAttribute(key, String(value));
    });
    return el;
  };

  trendSvgEl.appendChild(make("line", {
    x1: margin.left,
    y1: margin.top + innerHeight,
    x2: margin.left + innerWidth,
    y2: margin.top + innerHeight,
    stroke: "#cbd5e1",
    "stroke-width": 1,
  }));
  trendSvgEl.appendChild(make("line", {
    x1: margin.left,
    y1: margin.top,
    x2: margin.left,
    y2: margin.top + innerHeight,
    stroke: "#cbd5e1",
    "stroke-width": 1,
  }));

  [0, 0.25, 0.5, 0.75, 1].forEach((step) => {
    const val = Math.round(yMax * step);
    const y = yAt(val);
    trendSvgEl.appendChild(make("line", {
      x1: margin.left,
      y1: y,
      x2: margin.left + innerWidth,
      y2: y,
      stroke: "#e2e8f0",
      "stroke-width": 1,
    }));
    const text = make("text", {
      x: margin.left - 8,
      y: y + 4,
      "text-anchor": "end",
      fill: "#64748b",
      "font-size": 11,
    });
    text.textContent = formatNumber(val);
    trendSvgEl.appendChild(text);
  });

  const startDate = visibleTrend.dates[0] || "";
  const endDate = visibleTrend.dates[visibleTrend.dates.length - 1] || "";
  const startText = make("text", {
    x: margin.left,
    y: height - 10,
    fill: "#64748b",
    "font-size": 11,
  });
  startText.textContent = startDate;
  trendSvgEl.appendChild(startText);

  const endText = make("text", {
    x: margin.left + innerWidth,
    y: height - 10,
    "text-anchor": "end",
    fill: "#64748b",
    "font-size": 11,
  });
  endText.textContent = endDate;
  trendSvgEl.appendChild(endText);

  visibleTrend.series.forEach((item) => {
    const originalIndex = trend.series.findIndex((source) => source.userId === item.userId);
    const color = TREND_COLORS[(originalIndex >= 0 ? originalIndex : 0) % TREND_COLORS.length];
    const points = item.values.map((value, valueIndex) => `${xAt(valueIndex)},${yAt(value)}`).join(" ");
    trendSvgEl.appendChild(make("polyline", {
      points,
      fill: "none",
      stroke: color,
      "stroke-width": 2.5,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    }));

    const lastValue = item.values[item.values.length - 1] || 0;
    trendSvgEl.appendChild(make("circle", {
      cx: xAt(item.values.length - 1),
      cy: yAt(lastValue),
      r: 3.5,
      fill: color,
    }));

  });

  trend.series.forEach((item, index) => {
    const color = TREND_COLORS[index % TREND_COLORS.length];
    const lastValue = item.values[item.values.length - 1] || 0;
    const legendItem = document.createElement("button");
    legendItem.type = "button";
    legendItem.className = "trend-legend-item";
    if (hiddenTrendUsers.has(item.userId)) {
      legendItem.classList.add("is-hidden");
    }
    legendItem.innerHTML = `
      <span class="trend-dot" style="background:${color}"></span>
      <span>${item.displayName}</span>
      <strong>${formatNumber(lastValue)}</strong>
    `;
    legendItem.addEventListener("click", () => {
      if (hiddenTrendUsers.has(item.userId)) hiddenTrendUsers.delete(item.userId);
      else hiddenTrendUsers.add(item.userId);
      renderTrend(snapshot, rows);
    });
    trendLegendEl.appendChild(legendItem);
  });

  const renderTooltipAtIndex = (hoverIndex, clientX, clientY) => {
    if (!trendTooltipEl) return;
    const payload = window.TrendLogic.buildTooltipPayload(visibleTrend, hoverIndex);
    if (!payload.entries.length) {
      trendTooltipEl.hidden = true;
      return;
    }

    const rowsHtml = payload.entries.map((entry) => {
      const originalIndex = trend.series.findIndex((source) => source.userId === entry.userId);
      const color = TREND_COLORS[(originalIndex >= 0 ? originalIndex : entry.colorIndex) % TREND_COLORS.length];
      return `
        <div class="trend-tooltip-row">
          <span class="trend-dot" style="background:${color}"></span>
          <span>${entry.displayName}</span>
          <strong>${formatNumber(entry.value)}</strong>
        </div>
      `;
    }).join("");
    trendTooltipEl.innerHTML = `
      <p class="trend-tooltip-date">${payload.date}</p>
      ${rowsHtml}
    `;
    trendTooltipEl.hidden = false;

    const chartRect = trendSvgEl.getBoundingClientRect();
    const shellRect = trendSvgEl.parentElement?.getBoundingClientRect() || chartRect;
    const desiredLeft = clientX - shellRect.left + 12;
    const desiredTop = clientY - shellRect.top - 12;
    const maxLeft = shellRect.width - trendTooltipEl.offsetWidth - 8;
    const maxTop = shellRect.height - trendTooltipEl.offsetHeight - 8;
    trendTooltipEl.style.left = `${Math.max(8, Math.min(maxLeft, desiredLeft))}px`;
    trendTooltipEl.style.top = `${Math.max(8, Math.min(maxTop, desiredTop))}px`;
  };

  trendSvgEl.onmousemove = (event) => {
    renderTooltipAtIndex(indexFromClientX(event.clientX), event.clientX, event.clientY);
  };
  trendSvgEl.onmouseleave = () => {
    if (trendTooltipEl) trendTooltipEl.hidden = true;
  };
};

const render = (snapshot) => {
  const rows = resolveRows(snapshot);
  renderRows(rows);

  const rankingLabel = rankingSelect.options[rankingSelect.selectedIndex]?.textContent || "Daily";
  const selectedTool = toolSelect.value === "all"
    ? "All tools"
    : (toolSelect.options[toolSelect.selectedIndex]?.textContent || toolSelect.value);

  if (summaryRankingEl) summaryRankingEl.textContent = rankingLabel;
  if (summaryToolEl) summaryToolEl.textContent = selectedTool;
  if (summaryCountEl) summaryCountEl.textContent = String(rows.length);
  if (summaryTopEl) summaryTopEl.textContent = rows.length > 0 ? formatNumber(rows[0].totalTokens ?? rows[0].value ?? 0) : "0";

  renderTrend(snapshot, rows);
};

const resolveGitHubRepoURL = () => {
  const { hostname, pathname } = window.location;
  const pathParts = pathname.split("/").filter(Boolean);

  if (hostname.endsWith(".github.io")) {
    const owner = hostname.replace(".github.io", "");
    const repo = pathParts[0];
    if (owner && repo) {
      return `https://github.com/${owner}/${repo}`;
    }
  }
  return repoLinkEl?.href || "https://github.com/";
};

const init = async () => {
  if (repoLinkEl) {
    repoLinkEl.href = resolveGitHubRepoURL();
  }
  const response = await fetch("./data/snapshots/latest.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const snapshot = await response.json();
  metaEl.textContent = `Reference: ${snapshot.referenceDate} | Version: ${snapshot.version}`;

  const tools = ["all", ...Object.keys(snapshot.rankings?.byTool || {})];
  tools.forEach((tool) => {
    const option = document.createElement("option");
    option.value = tool;
    option.textContent = tool === "all" ? "All tools" : tool;
    toolSelect.appendChild(option);
  });

  const initialTool = query.get("tool");
  const initialRanking = query.get("ranking");
  const initialWindow = query.get("window");
  if (initialTool && tools.includes(initialTool)) {
    toolSelect.value = initialTool;
  }
  if (initialRanking && ["daily", "7d", "rising"].includes(initialRanking)) {
    rankingSelect.value = initialRanking;
  }
  if (initialWindow && windowSelect && ["7", "14", "30", "90"].includes(initialWindow)) {
    windowSelect.value = initialWindow;
  }

  const onChange = () => render(snapshot);
  toolSelect.addEventListener("change", onChange);
  rankingSelect.addEventListener("change", onChange);
  if (windowSelect) {
    windowSelect.addEventListener("change", onChange);
  }

  render(snapshot);
};

init().catch((error) => {
  metaEl.textContent = `Failed to load snapshot: ${error.message}`;
  renderRows([]);
  clearTrend("No trend data");
});
