# 测试说明与结果

## 运行方式

```bat
cd backend
py -m pytest -q
```

当前结果（2026-10-25）：

```text
.................                                                        [100%]
18 passed, 1 warning in 4.49s
```

唯一警告为 FastAPI/Starlette TestClient 关于 httpx 兼容层的上游弃用提示，不影响测试结果。

前端静态检查：

```bat
cd frontend
npm run type-check
npm run build
```

两项均已通过（Vue 3 + vue-tsc + Vite 生产构建）。

本次交付另使用无头 Chrome 对单服务构建产物做了页面冒烟检查：以 `admin` 登录后依次打开 10 个业务页面，均成功渲染，未捕获前端异常、错误提示或失败的 API 请求。该检查为交付时人工执行，未纳入自动化测试套件。

## 测试隔离

`backend/tests/conftest.py` 在导入 `app` 之前：

1. 删除旧的 `backend/data/test_b3.db`（含 `-wal/-shm`）。
2. 设置 `DATABASE_URL=sqlite:///.../test_b3.db`、`AUTO_SEED_ON_STARTUP=true`、`LLM_API_KEY=""`。
3. 通过 `TestClient` 触发应用生命周期，自动建表并生成 100 名教师的模拟数据。
4. 会话结束后关闭引擎并删除测试库。

因此测试不会读写演示库 `backend/data/app.db`，也不依赖外部网络或 LLM Key。

## 场景覆盖矩阵

| # | 验收/测试场景 | 自动化测试 | 关键断言 |
| --- | --- | --- | --- |
| 1 | 健康检查、首页与前端深链接 | `test_health_and_frontend_routes` | `/api/health`、`/`、`/login`、`/teachers` 均 200；未知 API 返回 JSON 404 |
| 2 | 登录、未登录拦截、中文错误 | `test_auth_and_error_messages` | 401 未登录；错误密码 401；manager 角色正确 |
| 3 | 教师新增、修改、搜索、分页、删除 | `test_teacher_crud_search_and_pagination` | 编号唯一、容量校验、详情计数、删除后 404 |
| 4 | 关联数据保护 | `test_teacher_delete_is_blocked_by_related_records` | 有成果时删除 409；先删成果后可删教师 |
| 5 | 参数校验与重复约束 | `test_teacher_validation_and_duplicate` | 非法职称/邮箱 422；容量错误 400；重复编号 400 |
| 6 | CSV 导入成功/失败/重复与错误导出 | `test_teacher_and_output_imports` | 教师 1/1/1；成果 1/1/1；错误明细与 UTF-8 BOM CSV |
| 7 | XLSX 导入 | `test_teacher_and_output_imports` | Excel 教师导入成功 1 行 |
| 8 | 演示样例文件可直接导入 | `test_demo_sample_files_are_importable` | 教师 1/1/1、成果 1/1/1、候选人成功 1 / 重复 1 |
| 9 | 画像统计与数据库一致 | `test_profile_statistics_match_database` | 成果数/类型和/教学学时/服务分类/完整度与明细一致；viewer 隐藏联系方式 |
| 10 | 驾驶舱筛选与人才盘点 | `test_dashboard_talent_filters_plan_and_export` | 学院筛选人数、分布和、盘点结构、人才规划缺口；学院—学科映射完整且学科属于学院 |
| 10b | 师生匹配度量化 | `test_match_degree_quantification` | 单教师/全体教师 0-100 分、四维贡献之和、A-D 等级、硬条件标记、排序；viewer 联系方式脱敏；非法学生/教师 404、非法权重 400 |
| 11 | Excel 导出可读 | `test_dashboard_talent_filters_plan_and_export` | 工作表名称、关键中文表头存在 |
| 12 | 数据质量接口 | `test_data_quality_endpoint` | 7 类缺字段、重复/待核验/无成果结构 |
| 13 | 导师推荐、解释与排名 | `test_advisor_matching_hard_filters_and_explanations` | 合格人数、分数降序、排名连续、原因含各维度与权重 |
| 14 | 导师硬条件排除 | 同上 | 无资格/未开放/容量满均被排除且 `rank=null`；高分但不推荐 |
| 15 | 导师人工确认 | 同上 | 确认与备注持久化 |
| 16 | 职称材料归集全状态 | `test_promotion_gather_checks_and_export` | matched/duplicate/pending/conflict/missing 均出现 |
| 17 | 职称完整率与人工确认 | 同上 | 初始 50%，确认缺项后 100%；驳回非法状态 400 |
| 18 | 职称 Excel 导出 | 同上 | 三张工作表与中文表头 |
| 19 | 人才引进硬条件与维度分 | `test_recruitment_evaluation_review_and_import` | 1 通过 / 2 淘汰；学历/成果缺口；证据、原因、排名 |
| 20 | 人才引进人工评审 | 同上 | shortlisted、reviewer、note；其他候选人不会被自动淘汰 |
| 21 | 候选人 CSV 导入与岗位删除保护 | 同上 | 成功 1 / 重复 1；有候选人时删岗位 409 |
| 22 | 角色权限 | `test_permissions_masking_settings_and_audit` | viewer/manager/admin 边界；403 中文提示 |
| 23 | 敏感字段脱敏 | 同上 | viewer 手机/邮箱掩码；admin 明文 |
| 24 | 权重与人才规划配置 | `test_dashboard_talent_filters_plan_and_export`、`test_permissions_masking_settings_and_audit` | admin 可改、manager 403、非法维度 400、归一化 |
| 25 | 审计日志 | `test_permissions_masking_settings_and_audit` | manager 可查、viewer 403、包含教师创建记录 |
| 26 | LLM 无 Key 本地回退 | `test_llm_fallback_and_system_info` | `mode=local`、警告文案、`sensitive_data_sent=false` |
| 27 | 系统信息与模拟数据标记 | 同上 | sqlite、计数、`模拟数据（B3演示）` |
| 28 | 重启后数据持久化 | `test_data_persists_across_restart` | 新生命周期/新 TestClient 仍能读取记录，种子跳过 |
| 29 | 错误提示可理解 | `test_clear_errors_for_bad_requests` | 404、422、非法扩展名、空文件中文提示 |

## 手工验收建议

自动化测试覆盖接口与关键算法；以下内容建议结合浏览器检查：

1. 10 个左侧导航页面均可打开，图表随筛选刷新。
2. 表格分页、搜索、清空筛选、按钮角色可见性。
3. 上传控件、进度提示、错误弹窗、下载文件名。
4. 浏览器刷新 `/teachers/:id/profile` 等深链接不 404。
5. 1024/1440 宽度下的布局与图表自适应。
6. viewer 登录后写按钮隐藏；直接调用写接口 403。
7. 教师档案筛选和新增/编辑表单中，未选学院时学科不可用；选定学院后只显示该学院学科，换学院会清空原学科。
8. 画像、驾驶舱、人才盘点、人才规划与招聘岗位表单同样验证学院→学科联动。
9. 师生匹配度页选择学生后执行“全部教师”量化：查看 0-100 总分、四维贡献、A-D 等级和硬条件列；切换“指定教师”后查看单教师详情与完整评分理由。

## 未纳入自动化的边界

- 真实 LLM 服务调用（测试强制无 Key，避免外部依赖与费用）。
- MySQL/PostgreSQL 实库迁移（当前默认 SQLite）。
- 浏览器端 E2E（Playwright/Cypress）与视觉回归。
- 大规模并发、性能压测、故障注入。
- 真实高校政策/材料真伪校验（属业务与制度边界，系统明确不承担）。

## 上游警告说明

`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自当前 FastAPI/Starlette 与 httpx 的测试客户端兼容层。系统运行不依赖该弃用路径；升级依赖时可按上游指引迁移。
