# B3 API 说明

- Base URL（开发）：`http://127.0.0.1:8000`
- 交互式文档：`/api/docs`（Swagger）、`/api/redoc`、`/api/openapi.json`
- 所有业务接口前缀：`/api`
- 除 `POST /api/auth/login` 与 `/api/health` 外，均需请求头：

```http
Authorization: Bearer <access_token>
```

## 1. 认证

### 登录

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"manager","password":"manager123"}'
```

响应：

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 2,
    "username": "manager",
    "display_name": "人事业务员",
    "role": "manager",
    "role_label": "业务人员",
    "is_active": true,
    "created_at": "2026-10-25T11:00:00"
  }
}
```

在 Swagger 中点击 **Authorize**，填入 token（不需要再写 `Bearer`，Swagger 会自动添加）。

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | 公开 | 登录 |
| GET | `/api/auth/me` | 登录 | 当前用户 |
| POST | `/api/auth/change-password` | 登录 | 修改本人密码 |

## 2. 教师、成果、项目、教学、服务

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/teachers` | 登录 | 列表；`keyword/college/discipline/title/status/advisor_qualified/enrollment_status/verification_status/page/page_size/sort_by/sort_order` |
| GET | `/api/teachers/options` | 登录 | 筛选选项 |
| POST | `/api/teachers` | admin/manager | 新增教师 |
| GET | `/api/teachers/{id}` | 登录 | 详情与关联计数 |
| PUT | `/api/teachers/{id}` | admin/manager | 修改 |
| DELETE | `/api/teachers/{id}` | admin/manager | 删除；有关联记录返回 409 |
| GET | `/api/teachers/{id}/profile` | 登录 | 多维画像（实时统计） |
| POST | `/api/teachers/{id}/ai-summary` | 登录 | 画像摘要；无 Key 时本地生成 |
| GET | `/api/research-outputs` | 登录 | 成果列表与筛选 |
| POST/PUT/DELETE | `/api/research-outputs...` | admin/manager | 成果增改删 |
| GET | `/api/research-projects` | 登录 | 项目列表 |
| GET | `/api/research-projects/{id}` | 登录 | 项目详情（含成员） |
| POST/PUT/DELETE | `/api/research-projects...` | admin/manager | 项目增改删 |
| GET | `/api/teaching-records` | 登录 | 教学记录 |
| POST/PUT/DELETE | `/api/teaching-records...` | admin/manager | 教学记录增改删 |
| GET | `/api/service-records` | 登录 | 获奖/学术任职/社会服务 |
| POST/PUT/DELETE | `/api/service-records...` | admin/manager | 服务记录增改删 |

分页响应：

```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "pages": 10
}
```

新增教师示例：

```bash
curl -X POST http://127.0.0.1:8000/api/teachers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "teacher_no":"B3T9001",
    "name":"测试教师",
    "college":"计算机学院",
    "discipline":"计算机科学与技术",
    "title":"副教授",
    "degree":"博士",
    "research_direction":"人工智能 数据治理",
    "advisor_qualified":true,
    "enrollment_status":"open",
    "capacity":5,
    "current_students":1
  }'
```

## 3. 统计与人才盘点

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/analytics/filters` | 登录 | 学院/学科/职称/年份选项 |
| GET | `/api/analytics/dashboard` | 登录 | 驾驶舱；`college/discipline/title/status/year_from/year_to` |
| GET | `/api/analytics/data-quality` | 登录 | 数据质量检查 |
| GET | `/api/analytics/talent-review` | 登录 | 盘点报告数据 |
| GET | `/api/analytics/talent-review/export` | 登录 | Excel 导出（同名筛选参数） |

## 4. 学生需求、导师匹配与匹配度量化

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/students` | 登录 | 学生列表 |
| POST | `/api/students` | admin/manager | 新增学生需求 |
| PUT/DELETE | `/api/students/{id}` | admin/manager | 修改/删除；已有任务时删除 409 |
| GET | `/api/advisor/weights` | 登录 | 默认权重与中文标签 |
| POST | `/api/advisor/score` | 登录 | 即时量化师生匹配度；`student_id` 必填，`teacher_id` 可选（不传则量化全部教师），`weights` 可选；不创建任务、不写库 |
| GET | `/api/advisor/tasks` | 登录 | 任务列表 |
| POST | `/api/advisor/tasks` | admin/manager | 创建任务（可选权重快照） |
| POST | `/api/advisor/tasks/{id}/run` | admin/manager | 执行匹配 |
| GET | `/api/advisor/tasks/{id}` | 登录 | 推荐与被排除结果 |
| PUT | `/api/advisor/results/{id}/confirm` | admin/manager | 人工确认/备注 |

创建并执行：

```bash
curl -X POST http://127.0.0.1:8000/api/advisor/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id":1,
    "name":"测试匹配",
    "weights":{"direction":1,"topic":1,"needs":1,"capacity":1}
  }'

curl -X POST http://127.0.0.1:8000/api/advisor/tasks/1/run \
  -H "Authorization: Bearer $TOKEN"
```

结果关键字段：

```json
{
  "recommendations": [
    {
      "id": 10,
      "teacher_id": 3,
      "teacher": {"teacher_no": "B3T0003", "name": "…"},
      "total_score": 78.4,
      "direction_score": 71.2,
      "topic_score": 90.0,
      "need_score": 62.5,
      "capacity_score": 87.5,
      "qualified": true,
      "disqualifiers": "",
      "reasons": "研究方向相似度 71.2%…\n评分权重：…",
      "rank": 1,
      "human_confirmed": false,
      "note": null
    }
  ],
  "excluded": [
    {
      "teacher_id": 9,
      "total_score": 55.0,
      "qualified": false,
      "disqualifiers": "未取得导师指导资格",
      "rank": null
    }
  ],
  "summary": {
    "qualified_count": 12,
    "excluded_count": 88,
    "note": "仅满足导师资格、招生状态、指导容量的候选教师进入有效推荐排序；…"
  }
}
```

权重非法返回 `400`（未知维度、非数字、负数、全零）。

即时量化（不创建任务）：

```bash
curl -X POST http://127.0.0.1:8000/api/advisor/score \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"student_id":1,"teacher_id":3,"weights":{"direction":40,"topic":25,"needs":20,"capacity":15}}'
```

返回节选：

```json
{
  "scope": "single",
  "student": {"student_no": "B3S0008", "name": "…", "desired_direction": "…"},
  "items": [
    {
      "teacher_id": 3,
      "teacher": {"name": "…", "college": "…", "title": "教授"},
      "total_score": 56.7,
      "grade": "A",
      "grade_label": "高度匹配",
      "qualified": true,
      "rank": 1,
      "dimensions": {
        "direction": {"score": 63.0, "weight": 0.4, "contribution": 25.2},
        "topic": {"score": 80.0, "weight": 0.25, "contribution": 20.0},
        "needs": {"score": 35.0, "weight": 0.2, "contribution": 7.0},
        "capacity": {"score": 30.0, "weight": 0.15, "contribution": 4.5}
      },
      "formula": "总分 56.7 = 研究方向 25.2 + 具体主题 20.0 + 培养需求 7.0 + 容量适配 4.5",
      "disqualifiers": ""
    }
  ],
  "summary": {"teacher_count": 1, "qualified_count": 1, "excluded_count": 0, "highest_qualified_score": 56.7},
  "grade_rules": [{"min_score": 55.0, "grade": "A", "label": "高度匹配"}],
  "note": "匹配度为档案字段的规则量化结果…"
}
```

`teacher_id` 不传时 `scope=all`，返回全部教师的 0-100 分、分项贡献、A-D 参考等级和硬条件结果。A-D 阈值（当前演示为 A≥55、B≥40、C≥25、D<25）仅用于本项目演示，不是真实高校录取或导师分配政策。

## 5. 职称申报

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/promotion/batches` | 登录 | 批次、类别/状态字典、免责声明 |
| POST | `/api/promotion/batches` | admin/manager | 新增批次 |
| GET | `/api/promotion/batches/{id}` | 登录 | 批次详情与要求 |
| PUT/DELETE | `/api/promotion/batches/{id}` | admin/manager | 修改/删除 |
| POST | `/api/promotion/batches/{id}/requirements` | admin/manager | 新增要求 |
| PUT/DELETE | `/api/promotion/requirements/{id}` | admin/manager | 修改/删除要求 |
| GET | `/api/promotion/batches/{id}/teachers` | 登录 | 范围内教师与材料进度 |
| POST | `/api/promotion/batches/{id}/gather` | admin/manager | 自动归集 |
| GET | `/api/promotion/materials` | 登录 | 材料列表（`batch_id` 必填） |
| PUT | `/api/promotion/materials/{id}` | admin/manager | 人工确认/驳回/备注 |
| GET | `/api/promotion/batches/{id}/summary` | 登录 | 汇总检查（`teacher_id` 必填） |
| GET | `/api/promotion/batches/{id}/export` | 登录 | Excel 导出（`teacher_id` 必填） |

归集示例：

```bash
curl -X POST http://127.0.0.1:8000/api/promotion/batches/1/gather \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"teacher_id":1}'
```

材料更新：

```bash
curl -X PUT http://127.0.0.1:8000/api/promotion/materials/10 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"confirmed","note":"已人工核对原件"}'
```

`status` 允许：`matched/missing/pending_verification/duplicate/conflict/confirmed/rejected`。

## 6. 人才引进

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/recruitment/positions` | 登录 | 岗位列表与候选人数 |
| POST | `/api/recruitment/positions` | admin/manager | 新增岗位 |
| PUT/DELETE | `/api/recruitment/positions/{id}` | admin/manager | 修改/删除；有候选人时 409 |
| GET | `/api/recruitment/positions/{id}` | 登录 | 岗位详情 |
| GET | `/api/recruitment/candidates` | 登录 | 候选人列表 |
| POST | `/api/recruitment/candidates` | admin/manager | 新增候选人 |
| PUT/DELETE | `/api/recruitment/candidates/{id}` | admin/manager | 修改/删除（删除同时清理评估） |
| POST | `/api/recruitment/positions/{id}/evaluate` | admin/manager | 执行评估 |
| GET | `/api/recruitment/positions/{id}/evaluations` | 登录 | 评估结果 |
| PUT | `/api/recruitment/evaluations/{id}/review` | admin/manager | 人工评审 |

评估示例：

```bash
curl -X POST http://127.0.0.1:8000/api/recruitment/positions/1/evaluate \
  -H "Authorization: Bearer $TOKEN"
```

返回：

```json
{
  "position": {"id": 1, "name": "…", "required_degree": "博士", "min_outputs": 4},
  "items": [
    {
      "id": 1,
      "hard_pass": true,
      "direction_score": 82.1,
      "outputs_score": 100.0,
      "projects_score": 80.0,
      "teaching_score": 100.0,
      "total_score": 89.4,
      "rank": 1,
      "gaps": "",
      "reasons": "研究方向相似度…\n权重：…",
      "evidence": "研究方向/关键词：…\n成果证据：…",
      "review_status": "pending"
    }
  ],
  "summary": {
    "total": 3,
    "hard_pass": 1,
    "hard_fail": 2,
    "note": "系统仅提供辅助评估建议，不自动作出录用或淘汰决定。"
  }
}
```

人工评审：

```json
{"review_status":"shortlisted","review_note":"同意进入面试"}
```

允许状态：`pending/reviewed/shortlisted/rejected`。

## 7. 数据导入

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/imports/templates/{kind}` | 登录 | CSV 模板；`teachers/research_outputs/candidates` |
| POST | `/api/imports/teachers` | admin/manager | 教师 CSV/XLSX |
| POST | `/api/imports/research-outputs` | admin/manager | 成果 CSV/XLSX |
| POST | `/api/imports/candidates?position_id=1` | admin/manager | 候选人 CSV/XLSX |
| GET | `/api/imports/batches` | 登录 | 批次列表 |
| GET | `/api/imports/batches/{id}/errors` | 登录 | 逐行错误 |
| GET | `/api/imports/batches/{id}/errors/export` | 登录 | 错误 CSV（UTF-8 BOM） |

上传示例：

```bash
curl -X POST http://127.0.0.1:8000/api/imports/teachers \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@teachers.csv"
```

结果：

```json
{
  "id": 1,
  "filename": "teachers.csv",
  "import_type": "teachers",
  "total_rows": 3,
  "success_rows": 1,
  "failed_rows": 1,
  "duplicate_rows": 1,
  "status": "completed",
  "created_by": "manager",
  "created_at": "2026-10-25T12:00:00",
  "message": "导入完成：成功 1 行，失败 1 行，重复 1 行"
}
```

限制：

- 仅 `.csv` / `.xlsx`；默认最大 5 MB、单次最多 5000 行。
- CSV 自动尝试 `utf-8-sig / utf-8 / gbk / gb18030`。
- 教师必填列：`teacher_no,name,college,discipline,title`。
- 成果必填列：`teacher_no,output_type,title`。
- 候选人必填列：`name,degree,major,research_direction`。

## 8. 系统管理

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/users` | admin | 用户列表 |
| POST | `/api/users` | admin | 新增用户 |
| PUT | `/api/users/{id}` | admin | 修改用户；不能停用自己/撤销自己的管理员角色 |
| GET | `/api/audit-logs` | admin/manager | 审计日志筛选分页 |
| GET | `/api/settings` | 登录 | 权重、人才规划、LLM 状态、是否可编辑 |
| PUT | `/api/settings/weights` | admin | 修改默认权重 |
| PUT | `/api/settings/talent-plan` | admin | 配置人才规划目标 |
| GET | `/api/system/info` | 登录 | 版本、数据库、数据量、演示标记、LLM 状态 |
| GET | `/api/health` | 公开 | 健康检查 |

## 9. 通用错误格式

业务错误：

```json
{"detail": "教师编号已存在"}
```

参数校验错误：

```json
{
  "detail": "参数校验失败：title: Value error, 职称必须是：教授/副教授/讲师/助教；email: Value error, 邮箱格式不正确",
  "errors": [
    "title: Value error, 职称必须是：教授/副教授/讲师/助教",
    "email: Value error, 邮箱格式不正确"
  ]
}
```

| 状态码 | 场景 |
| --- | --- |
| 400 | 业务参数不合法（重复编号、权重非法、岗位不存在等） |
| 401 | 未登录、token 失效、账号停用 |
| 403 | 当前角色无权操作 |
| 404 | 资源不存在 |
| 409 | 关联数据阻止删除 |
| 422 | Pydantic 参数校验失败 |
| 500 | 未处理异常（日志记录，返回中文兜底信息） |

未知 `/api/*` 路径返回 JSON `404`，不会回退到前端页面。
