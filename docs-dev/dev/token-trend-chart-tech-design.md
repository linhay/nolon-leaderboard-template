# Token 趋势曲线技术设计

## 数据结构
在 `data/snapshots/latest.json` 新增：

- `timeseries.overall`
- `timeseries.byTool.<tool>`

每个 dataset:
- `dates: string[]`（升序，YYYY-MM-DD）
- `users: [{ userId, username, displayName, values: number[] }]`

约束：
- `values[i]` 对应 `dates[i]`
- 缺失日期补 0
- 最多保留最近 90 天

## 构建逻辑
`build_snapshot.py` 新增 `build_timeseries(points, reference_date, max_days=90)`：
1. 复用阈值过滤（`MAX_DAILY_THRESHOLD`）。
2. 产出 overall / byTool 的按日序列。
3. user/date/tool 冲突由已存在去重逻辑保证“最新提交生效”。

## 前端逻辑
- 新增 `window-select`：7/14/30/90
- 新增 `web/trend_logic.js` 作为可测试纯逻辑：
  - `pickTopUsersFromRows`
  - `getTimeseriesDataset`
  - `buildTrendSeriesForTopUsers`
- `web/app.js` 使用原生 SVG 渲染多折线。

## 测试
- Python 单测覆盖 timeseries 结构、补 0、90 天窗口。
- Node 单测覆盖前 5 选人与窗口裁剪逻辑。

## Tooltip 交互
- 在 SVG 图层上监听 `mousemove`/`mouseleave`。
- 根据鼠标横坐标映射到日期索引，调用 `buildTooltipPayload` 生成该日各曲线值。
- tooltip 展示日期与当前索引下的前 5 用户值，按值降序。

## 截图回归校验
新增 `scripts/check_screenshot_regression.py`：
- 校验文件名符合规范：`<YYYYMMDD>-<module>-<scene>-<state>-vNN.png`
- 校验 `before` / `after` 成对存在
- 校验 before/after PNG 尺寸一致

## Mock 截图自动化
新增脚本：`scripts/capture_mock_screenshots.py`

流程：
1. 生成本地 mock snapshot 到 `.local/mock-data/latest.mock.json`
2. 构建 `.site` 并用 mock snapshot 覆盖站点快照
3. 本地起服务并用 Playwright CLI 截图（before: 7d, after: 30d）
4. 执行截图回归校验脚本

输出文件命名：
- `screenshots/YYYYMMDD/leaderboard/YYYYMMDD-leaderboard-trend-window-web-before-v01.png`
- `screenshots/YYYYMMDD/leaderboard/YYYYMMDD-leaderboard-trend-window-web-after-v01.png`

Git 追踪策略：
- `.local/` 与 `screenshots/` 已在 `.gitignore` 中忽略。
