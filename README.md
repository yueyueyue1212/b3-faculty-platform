# B3 高校师资/人才智能画像与辅助管理平台

面向高校人事与师资管理场景的全栈演示系统：教师多维档案与画像、人才驾驶舱/盘点、导师—学生智能匹配与匹配度量化、职称申报材料归集、青年人才引进辅助评估，以及数据导入、权限与审计。

> **数据说明**：仓库内的教师、学生、岗位、候选人、申报批次等全部为**模拟数据**，统一带有“模拟数据（B3演示）”来源标记。示例职称申报条件仅用于功能演示，**不代表任何高校的真实政策**。系统输出均为辅助信息，不自动作出录用、淘汰或职称评审决定。

## 目录

- [快速开始](#快速开始)
- [演示账号](#演示账号)
- [功能范围](#功能范围)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [演示数据与初始化](#演示数据与初始化)
- [测试](#测试)
- [API 文档](#api-文档)
- [AI 能力与隐私](#ai-能力与隐私)
- [安全与权限](#安全与权限)
- [配置项](#配置项)
- [文档索引](#文档索引)
- [已知问题与生产化建议](#已知问题与生产化建议)

## 快速开始

### 环境要求

- Python 3.11+（开发与测试使用 Python 3.12）
- Node.js 18+ / npm
- Windows、macOS、Linux 均可；本文命令以 PowerShell / CMD 为主

### 方式一：前后端分离开发（推荐开发调试）

1. 启动后端：

```bat
cd backend
py -m pip install -r requirements.txt
copy .env.example .env
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

2. 另开终端启动前端：

```bat
cd frontend
npm install
npm run dev
```

3. 打开 <http://127.0.0.1:5173>。Vite 已将 `/api` 代理到 `http://127.0.0.1:8000`。

首次启动会自动建表并生成演示数据（幂等，已有教师数据时跳过）。

### 方式二：单服务演示（构建后由 FastAPI 托管）

```bat
cd frontend
npm install
npm run build

cd ..\backend
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 <http://127.0.0.1:8000>。后端会托管 `frontend/dist`，并为 Vue History 路由提供回退，`/login`、`/teachers` 等深链接可直接刷新。若未构建前端，后端仍可独立提供 API。

### 根目录快捷脚本（Windows）

| 脚本 | 作用 |
| --- | --- |
| `start_backend.bat` | 启动后端 8000 端口（首次请先手动安装依赖并复制 `.env`） |
| `start_frontend.bat` | 启动 Vite 开发服务器 5173 端口 |
| `build_frontend.bat` | 构建前端到 `frontend/dist` |
| `run_tests.bat` | 运行后端自动化测试 |
| `start_single_server.bat` | 使用已构建前端启动单服务演示 |

> 脚本只做便捷封装；生产部署请使用进程管理器、HTTPS 与独立数据库。

### 方式三：免安装 Windows 便携包（演示电脑无需环境）

已生成可直接分发的演示包：

- `release/B3-Portable.zip`（约 71 MB）
- `release/B3-Portable.zip.sha256`（传输后可校验完整性）

包内已包含 Python 运行时、后端依赖、构建后的前端和预置演示数据库，目标电脑**无需安装 Python、Node.js、SQLite，也无需联网**。

1. 用 U 盘、网盘或局域网把 ZIP 复制到目标电脑，并**完整解压**。
2. 双击解压目录中的 `START_B3.bat`。
3. 浏览器通常会自动打开 <http://127.0.0.1:8000>；若未打开，请手动访问控制台中显示的地址。
4. 演示结束关闭黑色控制台窗口即可。

注意：不能只复制 `B3Platform.exe`，必须保留同级的 `_internal`、`data` 等文件。适用 64 位 Windows 10/11；未签名 EXE 可能触发 SmartScreen，确认来源可信后选择“更多信息 → 仍要运行”。详见包内 `README-PORTABLE.txt`。

运行日志自动写入便携包内的 `logs/b3.log`（UTF-8、5 MB 轮转、保留 5 份）；启动信息、访问记录和错误堆栈都会保留，出现“拒绝连接”等问题时可提供该文件排查。

## 演示账号

| 用户名 | 密码 | 角色 | 主要能力 |
| --- | --- | --- | --- |
| `admin` | `admin123` | 管理员 | 全部功能；用户、权重、人才规划配置；审计日志 |
| `manager` | `manager123` | 业务人员 | 教师/成果/导入/匹配/申报/引进等业务写入；审计查看 |
| `viewer` | `viewer123` | 只读用户 | 查询与导出；教师手机号、邮箱脱敏；不可写 |

**首次部署必须修改演示密码与 `SECRET_KEY`。**

## 功能范围

左侧导航共 9 个页面，覆盖 9 个业务与支撑模块：

| 页面 | 路径 | 模块能力 |
| --- | --- | --- |
| 人才驾驶舱 | `/dashboard` | 教师/成果/项目/教学/服务统计，学院、学科、职称、年份筛选，数据质量提示，图表联动 |
| 教师档案 | `/teachers` | 教师增删改查、搜索、筛选、排序、分页；关联记录保护 |
| 智能画像 | `/teachers/:id/profile`（教师档案中点“画像”进入） | 五维画像、成果/项目/教学/服务图表、完整度、指标口径、标签、本地或 LLM 摘要 |
| 人才盘点 | `/talent` | 职称/学历结构、年度趋势、人才规划缺口、数据质量、Excel 导出 |
| 导师匹配 | `/advisor` | 学生需求 CRUD、权重配置、硬条件过滤、可解释推荐、人工确认、被排除原因 |
| 师生匹配度 | `/matching` | 0-100 匹配度量化、四维分项贡献、A-D 参考等级、全体教师排序、单教师详情、硬性条件独立校验 |
| 职称申报 | `/promotion` | 批次与要求配置、材料自动归集、缺项/重复/冲突/待核验、人工确认/驳回、Excel 导出 |
| 人才引进 | `/recruitment` | 岗位与候选人管理、候选人 CSV 导入、硬条件校验、多维评分、证据与缺口、人工评审 |
| 数据管理 | `/data` | 教师/成果/候选人 CSV、XLSX 导入，逐行错误、重复检测、批次与错误明细导出、数据质量 |
| 系统设置 | `/settings` | 系统信息、LLM 状态、权重、人才规划、用户管理、审计日志 |

核心业务约束：

- 导师匹配先执行硬条件过滤（在职、导师资格、开放招生、剩余容量），**不满足硬条件的教师不进入推荐排序**，即使加权得分更高。
- 师生匹配度用 0-100 分量化“学生需求—教师档案”的规则契合度，拆分为研究方向、具体主题、培养需求、指导容量四项贡献；**A-D 等级阈值为演示配置**，分数与等级均不自动决定录取、分配或培养结论。
- 职称材料检查只比对数据库已有记录的一致性/完整性，**不验证成果真伪**；所有自动识别结果均可人工确认、驳回、备注。
- 人才引进评估只给出维度分、硬条件结果、证据和排序，**不自动录用或淘汰**；评审状态由人工填写。
- 教师档案、画像、驾驶舱、人才盘点、人才规划与招聘岗位中的学院/学科选择采用联动：**必须先选学院，学科下拉只显示该学院下的选项**；修改学院会清空已选学科，避免产生学院—学科不一致的数据。
- 统计数字全部来自数据库实时查询，不使用前端假数据。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Element Plus、ECharts、Vue Router、Pinia、Axios |
| 后端 | FastAPI、Pydantic v2、SQLAlchemy 2、Uvicorn |
| 数据 | SQLite（开发默认，可通过 `DATABASE_URL` 切换 MySQL/PostgreSQL）；Pandas + openpyxl 处理 CSV/XLSX |
| 安全 | JWT（PyJWT HS256）、PBKDF2-SHA256 密码哈希、角色守卫、审计日志、只读角色敏感字段脱敏 |
| 匹配/画像 | jieba 分词、本地 TF-IDF 余弦相似度、关键词覆盖、规则加权；无 Key 也可运行 |
| AI（可选） | OpenAI Chat Completions 兼容接口，httpx 超时/重试，失败自动回退本地摘要 |
| 测试 | pytest、FastAPI TestClient、独立 SQLite 测试库、openpyxl 导出校验 |

## 项目结构

```text
.
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # FastAPI 入口、异常处理、SPA 托管
│  │  ├─ config.py            # 环境变量与默认权重
│  │  ├─ database.py          # SQLAlchemy engine/session
│  │  ├─ models.py            # 20 个 ORM 实体
│  │  ├─ schemas.py           # Pydantic 请求模型与校验
│  │  ├─ serializers.py       # 输出序列化与 viewer 脱敏
│  │  ├─ security.py          # JWT、密码、角色依赖
│  │  ├─ seed.py              # 幂等演示数据（固定随机种子）
│  │  ├─ routers/             # 认证、教师、成果、项目、记录、统计、导师、申报、引进、导入、管理
│  │  └─ services/            # 画像、匹配、申报、统计、导入、LLM、审计
│  ├─ tests/                  # pytest 端到端测试（18 个用例）
│  ├─ data/                   # SQLite 数据文件（自动创建）
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/
│  │  ├─ api/client.ts        # Axios、JWT、错误提示、文件下载
│  │  ├─ components/          # 图表、统计卡、布局等
│  │  ├─ layouts/             # 左侧导航布局
│  │  ├─ router/              # 路由与登录守卫
│  │  ├─ stores/              # Pinia 登录状态
│  │  ├─ utils/charts.ts      # ECharts 主题与图表工具
│  │  └─ views/               # 10 个业务页面
│  ├─ dist/                   # 构建产物（可删除后重建）
│  ├─ package.json
│  └─ vite.config.ts
├─ samples/                   # 演示用 CSV（正常/重复/错误样例）
├─ docs/
│  ├─ ARCHITECTURE.md         # 架构、数据模型、算法与业务流程
│  ├─ API.md                  # API 端点与示例
│  ├─ DEMO.md                 # 验收演示脚本
│  └─ TESTING.md              # 测试场景与结果
├─ start_backend.bat          # 启动开发后端
├─ start_frontend.bat         # 启动 Vite 开发服务器
├─ build_frontend.bat         # 类型检查并构建前端
├─ run_tests.bat              # 运行后端测试
├─ start_single_server.bat    # 单服务演示启动
├─ release/
│  ├─ B3-Portable/            # 已组装好的免安装演示目录
│  ├─ B3-Portable.zip         # 可直接传输的演示压缩包
│  └─ B3-Portable.zip.sha256  # 压缩包 SHA-256
├─ .gitignore                 # 排除密钥、数据库、依赖与构建产物
└─ README.md
```

## 演示数据与初始化

首次启动后端时，`AUTO_SEED_ON_STARTUP=true` 会自动执行 `seed_all()`。数据使用固定随机种子 `20251025`，便于演示复现。

| 数据 | 数量（首次初始化） |
| --- | --- |
| 教师 | 100 |
| 科研成果 | 450 |
| 科研项目 | 60 |
| 教学记录 | 294 |
| 社会服务/获奖/学术任职 | 173 |
| 学生需求 | 20 |
| 招聘岗位 | 6 |
| 候选人及评估 | 18 |
| 职称申报批次 | 3 |
| 申报要求 | 12 |
| 申报材料 | 104 |

手动初始化：

```bat
cd backend
py -m app.seed            # 空库时生成；已有数据时跳过
py -m app.seed --force    # 危险：drop 全部表并重建演示数据
```

> `--force` 会删除当前数据库中的业务数据，**不要在生产环境执行**。

## 测试

```bat
cd backend
py -m pytest -q
```

当前结果：**18 passed**。测试使用独立的 `backend/data/test_b3.db`，在导入应用前通过环境变量切换数据库，不会污染演示库；会话结束后自动清理。

```bat
cd frontend
npm run type-check
npm run build
```

前端 TypeScript 检查与生产构建均已通过。单服务构建产物另经无头 Chrome 冒烟检查：登录后 10 个业务页面均正常渲染，无前端异常或失败 API 请求。测试场景与验收项对应关系见 [docs/TESTING.md](docs/TESTING.md)。

## API 文档

后端启动后：

- Swagger UI：<http://127.0.0.1:8000/api/docs>
- ReDoc：<http://127.0.0.1:8000/api/redoc>
- OpenAPI JSON：<http://127.0.0.1:8000/api/openapi.json>
- 健康检查：<http://127.0.0.1:8000/api/health>

除登录与健康检查外，接口均需 `Authorization: Bearer <token>`。在 Swagger 中先调用 `POST /api/auth/login`，再点击 **Authorize** 填入 token。常用端点与示例见 [docs/API.md](docs/API.md)。

## AI 能力与隐私

- AI 是可选增强，**未配置 `LLM_API_KEY` 时全部 CRUD、画像统计、导师匹配、申报检查、人才引进评估仍可用**。
- 画像摘要优先调用 OpenAI 兼容接口；超时/网络/鉴权失败或未配置 Key 时自动回退到本地规则摘要。
- 发送给外部模型的内容仅为聚合统计事实（成果数、项目数、教学学时、完整度、研究关键词等），**不包含姓名、手机号、邮箱、身份证号或学生个人信息**。
- `LLM_ALLOW_PERSONAL_DATA` 默认 `false`；当前实现即便置为 `true` 也不会把联系方式加入事实包。
- 前端不保存任何 API Key；密钥仅从后端环境变量读取，`.env` 不应提交到版本库。

## 安全与权限

- 密码使用 PBKDF2-SHA256（120,000 次迭代）加盐存储。
- JWT 默认 12 小时有效，密钥来自 `SECRET_KEY`。
- 角色：
  - `admin`：全部权限（用户、权重、人才规划）。
  - `manager`：业务写入与审计查看。
  - `viewer`：只读；教师列表与详情中的手机号/邮箱脱敏，画像隐藏联系方式。
- 所有写操作记录审计日志（用户、动作、资源、详情、IP、时间）。
- 教师存在成果/项目/教学/服务等关联记录时返回 `409`，避免产生孤立数据。
- 未知 `/api/*` 路径返回 JSON 404，不会被前端 SPA 回退吞掉。

## 配置项

复制 `backend/.env.example` 为 `backend/.env` 后按需修改。关键配置：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | 自动指向 `backend/data/app.db` | 支持 MySQL/PostgreSQL 连接串 |
| `SECRET_KEY` | 开发默认值 | **生产必须替换**为随机长字符串 |
| `TOKEN_EXPIRE_MINUTES` | `720` | JWT 有效期 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 逗号分隔 |
| `AUTO_SEED_ON_STARTUP` | `true` | 空库自动生成演示数据 |
| `MAX_UPLOAD_BYTES` | `5242880` | 上传大小限制 |
| `LLM_API_KEY` | 空 | 为空时使用本地摘要 |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI 兼容地址 |
| `LLM_MODEL` | `gpt-4o-mini` | 模型名 |
| `LLM_TIMEOUT` / `LLM_RETRIES` | `20` / `2` | 超时秒数与重试次数 |
| `LLM_ALLOW_PERSONAL_DATA` | `false` | 默认不发送任何个人数据 |
| `LOG_DIR` | 源码模式 `backend/logs`；便携版 `logs` | 日志目录，文件为 `b3.log`，5 MB 轮转、保留 5 份 |

## 文档索引

- [架构、数据模型与算法](docs/ARCHITECTURE.md)
- [API 端点与调用示例](docs/API.md)
- [验收演示步骤](docs/DEMO.md)
- [测试场景与结果](docs/TESTING.md)

## 已知问题与生产化建议

1. **仅角色级权限，尚无学院/学科数据域隔离**。真实部署需增加数据范围授权，尤其是跨学院人事数据。
2. **未附带 Alembic 迁移版本**。开发期使用 `create_all`；生产改表应引入 Alembic/迁移脚本，并在发布前备份数据库。
3. **JWT 存储于浏览器 localStorage**。存在 XSS 风险；生产建议使用 HTTPS、HttpOnly + Secure Cookie、严格 CSP，并缩短 token 有效期。
4. **匹配与材料归集为同步计算**。演示规模（100 名教师）响应良好；万人级数据建议异步任务队列、缓存与分页评分。
5. **TF-IDF 为轻量本地算法**。同义词、跨语言、语义泛化能力有限；可替换为 embedding 检索，但需保持可解释的硬条件过滤与人工复核。
6. **申报规则是示例配置**。系统不判断成果真伪、不判断申报人是否满足真实政策；导出结果仅用于材料整理。
7. **数据合规需落地制度**。手机号/邮箱、年龄、评审意见属于个人/敏感信息；需明确授权、留存期限、访问审计与脱敏范围。
8. **SQLite 适合演示与单机试用**。并发写入与大数据量场景建议切换 PostgreSQL/MySQL，并配置连接池、备份与监控。
9. **未集成统一身份认证/单点登录**。生产环境需对接学校 CAS/OIDC，并增加密码策略、登录失败锁定等能力。
10. **前端图表为浏览器渲染**。超大数据量时应改为服务端聚合、抽样或分页图表。

---

如用于真实高校业务，请先完成数据合规评估、权限边界设计、安全加固与政策规则审核。
