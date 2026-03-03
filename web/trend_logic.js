(function (global) {
  const pickTopUsersFromRows = (rows) => {
    const out = [];
    const seen = new Set();
    for (const row of rows || []) {
      const userId = row?.userId;
      if (!userId || seen.has(userId)) continue;
      seen.add(userId);
      out.push(userId);
      if (out.length === 5) break;
    }
    return out;
  };

  const getTimeseriesDataset = (snapshot, selectedTool) => {
    if (!snapshot?.timeseries) return { dates: [], users: [] };
    if (selectedTool === "all") {
      return snapshot.timeseries.overall || { dates: [], users: [] };
    }
    return snapshot.timeseries.byTool?.[selectedTool] || { dates: [], users: [] };
  };

  const buildTrendSeriesForTopUsers = (dataset, topUserIds, windowDays) => {
    const dates = Array.isArray(dataset?.dates) ? dataset.dates : [];
    const users = Array.isArray(dataset?.users) ? dataset.users : [];
    const takeDays = Number.isFinite(windowDays) ? Math.max(1, windowDays) : 7;
    const sliceStart = Math.max(0, dates.length - takeDays);
    const slicedDates = dates.slice(sliceStart);

    const userMap = new Map(users.map((item) => [item.userId, item]));
    const series = (topUserIds || []).map((userId) => {
      const user = userMap.get(userId);
      const name = user?.displayName || user?.username || userId;
      const values = Array.isArray(user?.values) ? user.values.slice(sliceStart) : new Array(slicedDates.length).fill(0);
      if (values.length < slicedDates.length) {
        return {
          userId,
          displayName: name,
          values: [...new Array(slicedDates.length - values.length).fill(0), ...values],
        };
      }
      return { userId, displayName: name, values };
    });

    return { dates: slicedDates, series };
  };

  const buildTooltipPayload = (trend, hoverIndex) => {
    const dates = Array.isArray(trend?.dates) ? trend.dates : [];
    const series = Array.isArray(trend?.series) ? trend.series : [];
    if (!dates.length || !series.length) {
      return { date: "", entries: [] };
    }
    const safeIndex = Math.max(0, Math.min(dates.length - 1, hoverIndex));
    const entries = series.map((item, idx) => ({
      userId: item.userId,
      displayName: item.displayName || item.userId,
      value: Number(item.values?.[safeIndex] || 0),
      colorIndex: idx,
    }));
    entries.sort((a, b) => b.value - a.value || a.displayName.localeCompare(b.displayName));
    return {
      date: dates[safeIndex],
      entries,
    };
  };

  const filterTrendByHiddenUsers = (trend, hiddenUsers) => {
    const dates = Array.isArray(trend?.dates) ? trend.dates : [];
    const series = Array.isArray(trend?.series) ? trend.series : [];
    const hidden = hiddenUsers instanceof Set ? hiddenUsers : new Set();
    return {
      dates,
      series: series.filter((item) => !hidden.has(item.userId)),
    };
  };

  const formatRelativeTime = (isoTime, nowMs = Date.now()) => {
    if (!isoTime) return "-";
    const ts = Date.parse(isoTime);
    if (!Number.isFinite(ts)) return isoTime;
    const delta = Math.max(0, Math.floor((nowMs - ts) / 1000));
    if (delta < 60) return `${delta}s ago`;
    if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
    if (delta < 86400) return `${Math.floor(delta / 3600)}h ago`;
    return `${Math.floor(delta / 86400)}d ago`;
  };

  const api = {
    pickTopUsersFromRows,
    getTimeseriesDataset,
    buildTrendSeriesForTopUsers,
    buildTooltipPayload,
    filterTrendByHiddenUsers,
    formatRelativeTime,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  global.TrendLogic = api;
})(typeof window !== "undefined" ? window : globalThis);
