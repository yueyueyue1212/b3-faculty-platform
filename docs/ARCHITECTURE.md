# B3 架构、数据模型与算法说明

本文说明系统的分层结构、20 个数据实体、关键业务流程、匹配/画像算法口径、权限边界与可扩展点。所有演示数据均为模拟数据。

## 1. 总体架构

```text
┌──────────────────────────── Browser ────────────────────────────┐
│ Vue 3 + TypeScript + Element Plus + ECharts + Vue Router/Pinia  │
│ 10 个业务页面 · 登录守卫 · 统一 Axios 错误处理 · Excel/CSV 下载   │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTPS /api  (JSON, JWT Bearer)
┌───────────────────────────────▼─────────────────────────────────┐
│                         FastAPI Application                      │
│  main.py: CORS · 校验异常 · 500 兜底 · /api/docs · SPA 静态托管    │
│                                                                  │
│  routers/          auth teachers outputs projects records        │
│                    analytics advisor promotion recruitment       │
│                    imports admin                                 │
│         │                                                        │
│  services/         profile matching promotion analytics imports  │
│                    llm text audit                                │
│         │                                                        │
│  security.py       JWT · PBKDF2 · 角色依赖 · IP                  │
│  schemas.py        Pydantic 请求校验                              │
│  serializers.py    输出结构与 viewer 脱敏                         │
└───────────────┬──────────────────────────────┬──────────────────┘
                │ SQLAlchemy 2 ORM              │ 可选 HTTPS
┌───────────────▼──────────────┐  ┌────────────▼──────────────────┐
│ SQLite / MySQL / PostgreSQL  │  │ OpenAI 兼容 LLM（可选）        │
│ 20 张业务表 + 导入/审计表     │  │ 未配置 Key 时完全本地运行      │
└──────────────────────────────┘  └───────────────────────────────┘
```

### 部署形态

1. **开发模式**：Vite `5173` + FastAPI `8000`，Vite 代理 `/api`。
2. **单服务演示**：`npm run build` 生成 `frontend/dist`，FastAPI 在 `/` 托管静态资源；自定义 `SPAStaticFiles` 对非 `/api/*` 的未知路径回退 `index.html`，支持 Vue History 深链接刷新。未知 `/api/*` 仍返回 JSON 404。

### 后端分层

| 层 | 职责 |
| --- | --- |
| `routers/` | HTTP 协议、查询参数、权限依赖、审计写入；不直接实现复杂算法 |
| `services/` | 画像统计、匹配评分、申报归集、统计报表、导入解析、LLM、审计 |
| `models.py` | SQLAlchemy 实体、约束与关系 |
| `schemas.py` | 请求体校验、枚举与中文字段错误 |
| `serializers.py` | 统一输出；`viewer` 角色手机号/邮箱脱敏 |
| `security.py` | JWT 签发/解析、PBKDF2 哈希、`require_admin/editor/any` |
| `seed.py` | 固定随机种子的幂等模拟数据初始化 |

## 2. 数据模型（20 个实体）

```text
User / SystemSetting / AuditLog / ImportBatch / ImportRowError

Teacher 1─* ResearchOutput
Teacher 1─* TeachingRecord
Teacher 1─* ServiceRecord
Teacher 1─* ResearchProject (principal)
Teacher *─* ResearchProject (ProjectMember)
Teacher 1─* AdvisorMatchResult *─1 AdvisorMatchTask *─1 StudentProfile

PromotionBatch 1─* PromotionRequirement
PromotionBatch 1─* PromotionMaterial *─1 Teacher
PromotionMaterial *─1 PromotionRequirement

JobPosition 1─* CandidateProfile 1─* CandidateEvaluation
```

| # | 实体 | 说明 | 关键约束 |
| --- | --- | --- | --- |
| 1 | `User` | 登录用户与角色 | `username` 唯一；`admin/manager/viewer` |
| 2 | `SystemSetting` | 权重、人才规划等 JSON 配置 | `key` 唯一 |
| 3 | `Teacher` | 教师主档案 | `teacher_no` 唯一；学院/学科/职称索引 |
| 4 | `ResearchOutput` | 论文/专利/著作/报告 | 教师外键；`(teacher_id,title)` 索引 |
| 5 | `ResearchProject` | 科研项目 | `project_no` 唯一；主持人外键 |
| 6 | `ProjectMember` | 项目成员 | `(project_id,teacher_id)` 唯一 |
| 7 | `TeachingRecord` | 教学工作量与评价 | 教师外键；学年索引 |
| 8 | `ServiceRecord` | 获奖/学术任职/社会服务 | 教师外键；类型索引 |
| 9 | `StudentProfile` | 学生需求与培养目标 | `student_no` 唯一 |
| 10 | `AdvisorMatchTask` | 匹配任务与权重快照 | 状态 `pending/running/completed/failed` |
| 11 | `AdvisorMatchResult` | 每位教师的结果、原因、排除项、人工确认 | 任务/教师外键 |
| 12 | `PromotionBatch` | 职称申报批次 | 状态 `draft/open/completed` |
| 13 | `PromotionRequirement` | 批次申报要求 | 类别 `paper/project/award/teaching/service` |
| 14 | `PromotionMaterial` | 归集材料与核验状态 | 7 种状态，见 5.3 |
| 15 | `JobPosition` | 招聘岗位与评分权重 | 学历、最低成果数、权重 JSON |
| 16 | `CandidateProfile` | 候选人档案与证据 | 岗位外键 |
| 17 | `CandidateEvaluation` | 硬条件、维度分、证据、人工评审 | `(candidate_id,position_id)` 唯一 |
| 18 | `ImportBatch` | 导入批次统计 | 类型 `teachers/research_outputs/candidates` |
| 19 | `ImportRowError` | 逐行错误明细 | 行号、字段、原因、原值 |
| 20 | `AuditLog` | 写操作审计 | 用户、动作、资源、详情、IP、时间 |

> 迁移说明：模型通过 `DATABASE_URL` 适配 SQLite/MySQL/PostgreSQL；开发期 `create_all` 建表，生产应补充 Alembic 迁移与备份流程。

## 3. 前端结构

- `layouts/MainLayout.vue`：左侧 9 项导航、顶部用户菜单、内容区。
- `router/index.ts`：History 路由；未登录跳转 `/login?redirect=...`；登录后校验 `/api/auth/me`。
- `stores/auth.ts`：token/user 持久化到 localStorage；角色控制按钮可见性。
- `api/client.ts`：统一 `/api` 基地址、JWT 注入、401 跳登录、错误消息解析、Blob 下载。
- `components/BaseChart.vue`：ECharts 容器，`ResizeObserver` 自适应。
- `utils/charts.ts`：统一配色、坐标轴、Tooltip、折线/柱状/饼图工厂。
- 页面数据全部来自 API；无前端硬编码统计数。

## 4. 关键流程

### 4.1 数据导入与质量治理

```text
上传 CSV/XLSX
  → 后缀/大小/空文件校验
  → Pandas 解析（CSV 尝试 UTF-8-SIG/UTF-8/GBK/GB18030）
  → 必需列校验
  → 逐行字段校验（必填、枚举、日期、数字、邮箱、重复）
  → 成功记录入库（教师 verification_status=pending，来源=导入:文件名）
  → 失败/重复写 ImportRowError
  → 返回批次统计；可查看/导出错误 CSV
  → 数据质量：缺字段、同名教师、同教师同名成果、待核验、无成果
```

重复判定：

- 教师：`teacher_no` 已存在或文件内重复。
- 成果：同一教师、标题去空白小写后相同、年份相同。
- 候选人：同一岗位下姓名已存在或文件内重复。

### 4.2 教师画像

画像完全由数据库聚合：

- 成果数、成果类型/年度/级别分布。
- 项目数（主持或参与去重）、主持项目数、经费合计。
- 教学记录、课程门数、总学时、平均评价、教学成果数。
- 获奖/学术任职/社会服务计数。
- 11 项档案字段完整度；缺失字段明细。
- 标签（科研活跃、高水平论文、项目负责人、教学突出等）。
- 指标口径随响应返回，便于用户理解数字来源。
- 摘要：配置 LLM 时调用兼容接口；无 Key/失败自动使用本地规则摘要。

完整度公式：

```text
completeness = (11 - 缺失字段数) / 11 × 100%
```

### 4.3 导师匹配

**第一步：硬条件过滤（一票否决）**

1. 教师状态必须为 `active`。
2. `advisor_qualified = true`。
3. `enrollment_status = open`。
4. `capacity > 0` 且 `capacity - current_students > 0`。

不满足任一条件 → `qualified=false`、`rank=null`，记录 `disqualifiers`，**不进入推荐列表**。

**第二步：加权评分（权重可配置，自动归一化）**

| 维度 | 含义 | 默认权重 |
| --- | --- | --- |
| direction | 学生期望方向/兴趣/关键词 vs 导师方向、关键词、简介、技能、近 15 条成果标题的 TF-IDF 余弦 | 40% |
| topic | 学生兴趣词在导师关键词、方向与成果标题中的覆盖率/部分覆盖率 | 25% |
| needs | 学生培养需求/学位目标/其他条件 vs 导师技能、简介、方向的 TF-IDF 余弦 | 20% |
| capacity | 剩余容量 / 总容量 | 15% |

```text
total = 100 × (direction×w1 + topic×w2 + needs×w3 + capacity×w4)
```

- 权重来自系统设置或任务快照；负值/非数字/未知维度拒绝，权重和归一并保留 4 位小数。
- 每位教师返回各维度得分、命中关键词、排除原因和人类可读解释。
- 排序只针对合格教师；人工确认/备注单独记录，不改变算法分。

### 4.4 师生匹配度量化

`POST /api/advisor/score` 在不创建匹配任务、不写数据库的前提下，返回单教师或全体教师的 0-100 匹配度。算法复用 4.3 的硬条件与四项维度，避免“两套分数”：

```text
contribution_i = dimension_score_i × normalized_weight_i
total = Σ contribution_i
```

- 每项贡献分与总分一并返回，前端展示“维度得分 × 权重 = 贡献分”，可核对加权过程。
- 参考等级为演示配置：A≥55、B≥40、C≥25、D<25；等级不替代人工判断。
- 未通过硬条件的教师仍返回规则分与排除原因，但 `qualified=false`、`rank=null`，不进入有效推荐和最高有效分统计。
- 接口为只读计算，登录用户均可访问；viewer 返回的教师联系方式继续脱敏。
- 全体教师模式按“合格优先、总分降序”返回；单教师模式返回该教师及其在全体有效推荐中的排名。

### 4.5 职称申报材料归集

批次要求可配置：类别、最低数量、是否必填、关键词、回看年限、是否仅主持人。

材料来源：

- 论文/著作/专利/报告：成果标题关键词 + 年份窗口。
- 项目：项目名称关键词 + 开始/结束年份，可选仅主持人。
- 获奖：获奖记录 + 教学成果（`achievement`）。
- 教学：课程名称关键词 + 学年。
- 服务：学术任职/社会服务名称 + 时间窗口。

材料状态：

| 状态 | 触发条件 |
| --- | --- |
| `matched` | 正常匹配 |
| `missing` | 有效数量不足最低要求，系统生成“缺项”记录 |
| `pending_verification` | 来源含“待核验”或日期缺失 |
| `duplicate` | 同一要求内标题归一化后重复 |
| `conflict` | 材料日期晚于批次截止日期 |
| `confirmed` | 人工确认 |
| `rejected` | 人工驳回 |

- 自动归集会删除上次自动结果，但**保留人工确认/驳回记录**，避免覆盖人工意见。
- 完成率 = 满足的必填要求数 / 必填要求总数；已确认的人工记录计入满足。
- 所有检查仅基于已入库数据，不验证成果真伪；导出 Excel 包含汇总、要求达成、材料明细三张表。

### 4.5 人才引进评估

**硬条件**：学历等级 ≥ 岗位要求；成果数 ≥ 岗位最低成果数。任一不满足 → `hard_pass=false`、`rank=null`。

**维度评分（默认权重）**：

| 维度 | 计算 | 默认权重 |
| --- | --- | --- |
| direction | 岗位方向/主题/要求/学科 vs 候选人方向/关键词/专业/成果证据的 TF-IDF 余弦 | 45% |
| outputs | `min(1, 成果数 / max(最低成果数×2, 6))` | 25% |
| projects | `min(1, 项目数 / 5)` | 20% |
| teaching | `min(1, 教学年限 / 5)` | 10% |

- 仅硬条件通过者参与排名。
- 返回维度分、总分、证据、缺口、待核验字段和排序。
- 人工评审状态：`pending/reviewed/shortlisted/rejected`；系统**不自动录用或淘汰**。

### 4.6 统计与人才盘点

- 驾驶舱：教师数、在职、导师资格、成果、项目、教学学时、服务、数据质量；按学院/学科/职称/年份同时过滤关联记录。
- 人才盘点：职称/学历结构（按学院）、年度成果/项目、关键词、人才规划缺口、数据质量。
- 人才规划缺口来自管理员配置的目标人数，不是模型推断。
- 导出 Excel：概览、学院职称结构、学院学历结构、年度成果、人才规划缺口、数据质量。

### 4.7 认证、权限与审计

```text
登录 → 校验 PBKDF2 → 签发 JWT(sub, username, role, exp)
请求 → HTTPBearer → 解析 JWT → 校验用户存在且 active → 角色依赖
写操作 → 业务提交 → write_audit(...)
```

- `viewer` 在教师列表/详情中手机号、邮箱脱敏；画像不返回联系方式。
- 审计日志可按用户、动作、资源类型、日期过滤；仅管理员/业务人员可查看。
- 删除教师/岗位/学生时检查关联记录，存在依赖返回 409 与中文原因。

## 5. 算法实现与降级

### 5.1 分词与 TF-IDF

- 优先使用 `jieba` 中文分词；不可用时退化为英文/数字词 + 中文二元组。
- 停用词表过滤“研究、应用、技术、方法”等泛词。
- TF 使用词频/总词数，IDF 使用 `ln((N+1)/(df+1))+1`（查询也计入文档频率）。
- 余弦相似度截断到 `[0,1]`，保留 4 位小数。

### 5.2 关键词覆盖

- 学生兴趣按标点/空格拆分，并补充分词结果。
- 完全命中计 1，分词部分命中计 0.5，得分 = 命中分 / 词数，上限 1。
- 返回命中的前 12 个词，写入解释文本。

### 5.3 降级策略

| 依赖 | 不可用时 |
| --- | --- |
| jieba | 使用正则 + 中文二元组分词 |
| LLM | 返回本地规则摘要，`mode=local` 并提示原因 |
| 前端构建产物 | 后端仅提供 API，不影响测试与接口 |
| 外部数据库 | 默认 SQLite；连接串可切换 |

## 6. 可扩展点

1. **数据域权限**：在 `Teacher.college/discipline` 上增加用户数据范围，并在查询层统一注入。
2. **语义匹配**：将 `tfidf_similarities` 替换为 embedding 检索，保留硬条件过滤、解释字段与人工确认。
3. **异步任务**：匹配、批量归集、导入改为任务队列；前端轮询任务状态。
4. **迁移管理**：引入 Alembic，按环境执行迁移；生产禁用自动建表与自动种子。
5. **单点登录**：对接 CAS/OIDC，替换本地账号；增加密码策略与失败锁定。
6. **对象存储**：将申报佐证材料（PDF/图片）上传至对象存储，数据库保存引用与校验状态。
7. **可观测性**：结构化日志、请求 ID、指标与审计告警。

## 7. 非目标与边界

- 不判断成果真伪、不替代职称评审委员会。
- 不自动作出招聘录用/淘汰决定。
- 不提供真实高校政策解释；申报规则仅为可配置示例。
- 不以模型输出对教师能力作确定性评价；所有画像结论标注数据来源与口径。
- 演示数据不得用于真实人事决策。
