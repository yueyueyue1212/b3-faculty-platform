# 代码变更记录（CHANGELOG）

本项目不使用 Git，源码变更依靠 `backups/` 里的快照和本文件留痕。**最新记录在最上面。**

## 记录规则

每次修改代码（含文档、脚本、配置模板）都按以下顺序执行：

1. 改动前，在项目根目录生成快照：

   ```bat
   py backup_source.py <英文短标签>
   ```

   标签只用英文、数字和短横线，例如 `fix-login-timeout`、`feat-export-excel`。

2. 改动后，在下面“变更记录”顶部新增一条，必须包含：
   - 时间与目的（修什么问题、加什么功能）
   - 改动方面：涉及文件、函数/页面、行为变化
   - 验证结果：执行过的测试或手动检查
   - 改动前备份文件名
   - 回退方法
3. 涉及便携版时，重新构建 `release/B3-Portable.zip` 并记录新的 SHA-256。
4. 涉及数据库结构时，单独备份 `backend/data/app.db` 或 `release/B3-Portable/data/app.db`（源码备份不含数据库）。

## 回退（简要）

详细步骤见 [`backups/README.md`](../backups/README.md)。

## 现有备份

| 备份文件 | 时间 | 说明 |
| --- | --- | --- |
| `b3-source-20261026-161926-remove-profile-nav-rename-teacher-profile.zip` | 2026-10-26 16:19 | 精简导航、画像页改名之前 |
| `b3-source-20261026-152946-before-changelog-and-rollback-doc.zip` | 2026-10-26 15:29 | 建立变更记录之前的基线 |
| `b3-source-20261025-200048-before-match-degree-feature.zip` | 2026-10-25 20:00 | 师生匹配度功能加入之前 |

> 注意：2026-10-25 的备份早于当前代码，**不能当作“最新版本”**；日常回退请使用最近一次改动前的快照。

## 变更记录

### 2026-10-26 16:21 — 精简左侧导航并将教师画像页统一为“智能画像”

- **目的**：按要求在网页排版中删除左侧独立的“智能画像”导航项，避免与“教师档案”入口重复；画像详情页标题由“教师智能画像”改为“智能画像”。
- **改动方面**：
  - `frontend/src/layouts/MainLayout.vue`：删除指向 `/profiles` 的“智能画像”菜单项，左侧导航由 10 项变为 9 项；从教师档案进入画像详情时仍高亮“教师档案”。
  - `frontend/src/views/TeacherProfileView.vue`：页面标题“教师智能画像”→“智能画像”；“返回画像列表”仍指向 `/profiles`（列表页保留，只是不再占用导航项）。
  - `frontend/src/router/index.ts`：`teacher-profile` 路由的 `meta.title` 改为“智能画像”，顶栏标题同步变化。
  - `frontend/src/views/TeachersView.vue`：导出提示文案改为点击列表中的“画像”查看个人统计详情，与导航调整一致。
  - `README.md`、`docs/DEMO.md`：导航页面数 10→9，更新画像入口说明。
  - 重新构建 `frontend/dist`；将新前端、`README.md` 与 `docs/DEMO.md` 同步进 `release/B3-Portable`，并重建便携压缩包。
- **验证**：
  - `npm run type-check` 通过，`npm run build` 成功（vite 6.4.5，2276 modules）。
  - 后端 `py -m pytest -q`：18 passed。
  - `frontend/dist` 与便携包内前端均已搜索不到“教师智能画像”字样。
  - `release/B3-Portable.zip` 完整性校验通过（909 个文件，`testzip` 返回 None）。
- **改动前备份**：`backups/b3-source-20261026-161926-remove-profile-nav-rename-teacher-profile.zip`
  - SHA-256：`ddf53785a57ed9e6e0a3de71eb1fce3169f16f5b93339fa2209d0dab962a5fde`
- **便携包**：`release/B3-Portable.zip` 已重建，74,369,827 字节，SHA-256 `0fd80cd72b0f18ddf654ab100383f439ac70940588c65c1f41a2eecaacd1827d`；`release/B3-Portable.zip.sha256` 已同步更新。旧便携包未单独留档，可由旧源码 + `build_frontend.bat` 重新生成。
- **回退方法**：
  1. 解压上述备份并覆盖项目根目录，重点恢复 `frontend/src/layouts/MainLayout.vue`、`frontend/src/views/TeacherProfileView.vue`、`frontend/src/router/index.ts`、`frontend/src/views/TeachersView.vue`、`README.md`、`docs/DEMO.md`。
  2. 在 `frontend` 下执行 `npm run build`（或运行 `build_frontend.bat`）恢复 `frontend/dist`。
  3. 如需恢复便携版，用回退后的 `frontend/dist` 覆盖 `release/B3-Portable/_internal/frontend/dist`，再重新压缩 `release/B3-Portable` 并更新 `release/B3-Portable.zip.sha256`。

### 2026-10-26 15:29 — 建立代码变更记录与回退机制（仅文档）

- **目的**：做到每次改代码都有记录、可回退、可复查。
- **改动方面**：
  - 新增 `docs/CHANGELOG.md`：记录规范、备份索引与每次变更的明细。
  - 修改 `backups/README.md`：补充具体回退步骤、备份命名说明和“回退前先备份”的要求。
  - 未修改后端、前端、启动脚本或便携包的任何业务代码。
- **验证**：本次仅文档改动，未运行测试；确认备份 zip 与 manifest 均生成成功（84 个文件）。
- **改动前备份**：`backups/b3-source-20261026-152946-before-changelog-and-rollback-doc.zip`
  - SHA-256：`771532800a4dcc7a4100852c13e5552bcf2bfcf9d17971bd60c9313a2645abc6`
- **回退方法**：删除 `docs/CHANGELOG.md`；从上述备份中恢复 `backups/README.md`。

### 2026-10-26 15:17 — 排查“网站无法打开”（无代码改动）

- **现象**：浏览器无法打开本地站点。
- **原因**：8000 端口没有进程监听，后端未运行；日志在 2026-10-25 20:59 启动后即无后续记录，属于进程/控制台被关闭，而非代码崩溃。
- **处理**：重新启动后端，`/api/health` 返回 `status: ok`，首页、静态资源、登录接口均验证正常。
- **代码改动**：无，因此未生成备份。
- **经验**：访问用 `http://127.0.0.1:8000`（本机 IPv6 `::1` 不通）；启动服务的黑色窗口不能关闭。
