const toolSelect = document.getElementById("tool-select");
const rankingSelect = document.getElementById("ranking-select");
const rowsEl = document.getElementById("rows");
const metaEl = document.getElementById("meta");
const repoLinkEl = document.getElementById("repo-link");
const summaryRankingEl = document.getElementById("summary-ranking");
const summaryToolEl = document.getElementById("summary-tool");
const summaryCountEl = document.getElementById("summary-count");
const summaryTopEl = document.getElementById("summary-top");

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
    const deltaClass = row.delta > 0 ? "delta-positive" : (row.delta < 0 ? "delta-negative" : "");
    const rankClass = row.rank <= 3 ? `rank-badge rank-${row.rank}` : "rank-badge";
    const deltaPrefix = row.delta > 0 ? "+" : "";
    tr.innerHTML = `
      <td><span class="${rankClass}">${row.rank}</span></td>
      <td>${row.displayName || row.username}</td>
      <td class="value-cell">${formatNumber(row.value)}</td>
      <td class="${deltaClass}">${deltaPrefix}${row.delta ?? 0}</td>
      <td>${row.lastUpdated || "-"}</td>
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
  if (summaryTopEl) summaryTopEl.textContent = rows.length > 0 ? formatNumber(rows[0].value) : "0";
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

  const onChange = () => render(snapshot);
  toolSelect.addEventListener("change", onChange);
  rankingSelect.addEventListener("change", onChange);

  render(snapshot);
};

init().catch((error) => {
  metaEl.textContent = `Failed to load snapshot: ${error.message}`;
  renderRows([]);
});
