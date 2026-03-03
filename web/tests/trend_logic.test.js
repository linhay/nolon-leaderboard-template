const test = require("node:test");
const assert = require("node:assert/strict");

const {
  pickTopUsersFromRows,
  buildTrendSeriesForTopUsers,
  buildTooltipPayload,
  filterTrendByHiddenUsers,
  formatRelativeTime,
} = require("../trend_logic.js");

test("pickTopUsersFromRows returns first 5 unique userIds", () => {
  const rows = [
    { userId: "u1" },
    { userId: "u2" },
    { userId: "u1" },
    { userId: "u3" },
    { userId: "u4" },
    { userId: "u5" },
    { userId: "u6" },
  ];
  assert.deepEqual(pickTopUsersFromRows(rows), ["u1", "u2", "u3", "u4", "u5"]);
});

test("buildTrendSeriesForTopUsers slices by window and keeps selected users", () => {
  const dataset = {
    dates: ["2026-03-01", "2026-03-02", "2026-03-03", "2026-03-04"],
    users: [
      { userId: "u1", displayName: "alice", values: [10, 20, 30, 40] },
      { userId: "u2", displayName: "bob", values: [1, 2, 3, 4] },
    ],
  };

  const result = buildTrendSeriesForTopUsers(dataset, ["u2", "u1"], 3);
  assert.deepEqual(result.dates, ["2026-03-02", "2026-03-03", "2026-03-04"]);
  assert.equal(result.series.length, 2);
  assert.deepEqual(result.series[0].values, [2, 3, 4]);
  assert.deepEqual(result.series[1].values, [20, 30, 40]);
});

test("buildTrendSeriesForTopUsers fills missing user as zero line", () => {
  const dataset = {
    dates: ["2026-03-01", "2026-03-02"],
    users: [{ userId: "u1", displayName: "alice", values: [5, 8] }],
  };
  const result = buildTrendSeriesForTopUsers(dataset, ["u2"], 7);
  assert.deepEqual(result.dates, ["2026-03-01", "2026-03-02"]);
  assert.equal(result.series.length, 1);
  assert.deepEqual(result.series[0].values, [0, 0]);
});

test("buildTooltipPayload returns date and ordered entries for hover index", () => {
  const trend = {
    dates: ["2026-03-03", "2026-03-04"],
    series: [
      { userId: "u1", displayName: "alice", values: [10, 50] },
      { userId: "u2", displayName: "bob", values: [15, 40] },
    ],
  };
  const payload = buildTooltipPayload(trend, 1);
  assert.equal(payload.date, "2026-03-04");
  assert.deepEqual(payload.entries.map((item) => item.displayName), ["alice", "bob"]);
  assert.deepEqual(payload.entries.map((item) => item.value), [50, 40]);
});

test("filterTrendByHiddenUsers removes hidden user lines", () => {
  const trend = {
    dates: ["2026-03-03", "2026-03-04"],
    series: [
      { userId: "u1", displayName: "alice", values: [10, 50] },
      { userId: "u2", displayName: "bob", values: [15, 40] },
    ],
  };
  const filtered = filterTrendByHiddenUsers(trend, new Set(["u2"]));
  assert.equal(filtered.series.length, 1);
  assert.equal(filtered.series[0].userId, "u1");
});

test("formatRelativeTime returns expected short text", () => {
  const now = Date.parse("2026-03-04T00:10:00Z");
  assert.equal(formatRelativeTime("2026-03-04T00:09:30Z", now), "30s ago");
  assert.equal(formatRelativeTime("2026-03-04T00:05:00Z", now), "5m ago");
  assert.equal(formatRelativeTime("2026-03-03T22:10:00Z", now), "2h ago");
  assert.equal(formatRelativeTime("2026-03-01T00:10:00Z", now), "3d ago");
});
