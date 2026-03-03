const toolSelect = document.getElementById("tool-select");
const rankingSelect = document.getElementById("ranking-select");
const rowsEl = document.getElementById("rows");
const metaEl = document.getElementById("meta");

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
    const deltaClass = row.delta > 0 ? "delta-positive" : "";
    tr.innerHTML = `
      <td>${row.rank}</td>
      <td>${row.displayName || row.username}</td>
      <td>${formatNumber(row.value)}</td>
      <td class="${deltaClass}">${row.delta ?? 0}</td>
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
};

const init = async () => {
  const response = await fetch("./data/snapshots/latest.json", { cache: "no-store" });
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
});
