<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <div>
        <h2 class="page-title">系统设置</h2>
        <p class="page-subtitle">
          查看运行状态、维护评分权重与人才规划目标、管理账号与审计日志。所有配置修改均记录操作人、IP 与时间。
        </p>
      </div>
      <div class="page-actions">
        <el-tag effect="plain" :type="auth.isAdmin ? 'danger' : 'info'">
          当前角色：{{ auth.roleLabel }}
        </el-tag>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane name="overview" label="系统概览">
        <div v-if="info" class="stat-grid">
          <StatCard label="教师档案" :value="info.counts.teachers" unit="人" sub="含模拟数据标记" icon="User" />
          <StatCard label="科研成果" :value="info.counts.research_outputs" unit="项"
                    :sub="`项目 ${info.counts.research_projects} 项`" icon="Document" />
          <StatCard label="学生需求" :value="info.counts.students" unit="人"
                    :sub="`申报批次 ${info.counts.promotion_batches} 个`" icon="Reading" accent="success" />
          <StatCard label="招聘岗位" :value="info.counts.job_positions" unit="个"
                    :sub="`候选人 ${info.counts.candidates} 人`" icon="UserFilled" accent="warning" />
        </div>

        <div v-if="info" class="two-col">
          <div class="panel">
            <div class="panel-title">运行环境</div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="系统名称">{{ info.app }}</el-descriptions-item>
              <el-descriptions-item label="项目编号">{{ info.project_no }}</el-descriptions-item>
              <el-descriptions-item label="版本">{{ info.version }}</el-descriptions-item>
              <el-descriptions-item label="数据库">
                {{ info.database.backend }} · {{ info.database.name }}
                <div class="hint">{{ info.database.note }}</div>
              </el-descriptions-item>
              <el-descriptions-item label="演示数据">
                <el-tag v-if="info.demo_data.enabled" size="small" type="warning" effect="plain">
                  {{ info.demo_data.marker }}
                </el-tag>
                <span v-else>未导入</span>
                <div class="hint">{{ info.demo_data.note }}</div>
              </el-descriptions-item>
              <el-descriptions-item label="当前账号角色">{{ roleLabel(info.role) }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="panel">
            <div class="panel-title">
              <span>AI 服务状态</span>
              <el-tag size="small" :type="info.llm.configured ? 'success' : 'info'" effect="plain">
                {{ info.llm.configured ? '已配置' : '未配置（本地模式）' }}
              </el-tag>
            </div>
            <div class="kv-list">
              <div class="kv-item"><label>运行模式</label><span>{{ info.llm.mode === 'llm' ? '大模型辅助' : '本地规则' }}</span></div>
              <div class="kv-item"><label>模型</label><span>{{ info.llm.model || '—' }}</span></div>
              <div class="kv-item"><label>服务地址</label><span>{{ info.llm.base_url || '—' }}</span></div>
              <div class="kv-item"><label>允许个人数据外发</label><span>{{ info.llm.allow_personal_data ? '是' : '否' }}</span></div>
            </div>
            <p class="note" style="margin-top: 12px">{{ info.llm.note }}</p>
            <p class="hint" style="margin-top: 10px">
              所有业务功能在未配置 API Key 时均可正常使用；AI 摘要会自动回退到本地规则生成，且不发送姓名、电话、邮箱等个人数据。
            </p>
          </div>
        </div>

        <div class="panel section-gap">
          <div class="panel-title">安全与合规提示</div>
          <div class="notice-list">
            <div class="notice-item">
              <strong>账号与密钥</strong>
              <span>演示账号密码仅用于本地演示；部署前须修改默认密码与 SECRET_KEY，并通过环境变量配置，不得提交到代码仓库。</span>
            </div>
            <div class="notice-item">
              <strong>敏感信息</strong>
              <span>只读角色查看教师档案时，手机与邮箱自动脱敏；AI 摘要不发送联系方式。</span>
            </div>
            <div class="notice-item">
              <strong>辅助决策边界</strong>
              <span>导师推荐、人才引进与职称材料检查均为辅助结果，不自动作出录用、淘汰或评审决定。</span>
            </div>
            <div class="notice-item">
              <strong>模拟数据声明</strong>
              <span>演示数据由脚本随机生成并标记“模拟数据（B3演示）”，不代表任何真实高校、教师或候选人。</span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="weights" label="评分权重">
        <div class="two-col">
          <div class="panel">
            <div class="panel-title">
              <span>导师匹配权重</span>
              <span class="hint">合计 {{ advisorSum }}</span>
            </div>
            <div v-for="key in advisorKeys" :key="key" class="weight-row">
              <span>{{ advisorLabels[key] }}</span>
              <el-slider v-model="advisorWeights[key]" :min="0" :max="100" :step="5"
                         :disabled="!auth.isAdmin" show-input :show-input-controls="false" style="flex: 1" />
            </div>
            <p class="hint">
              权重会在保存与执行任务时归一化；示例：合计 100 时即按百分比直接使用。硬性条件过滤与权重无关。
            </p>
            <p class="note" style="margin-top: 10px">
              修改后仅影响之后新建的匹配任务；已有任务保留创建时的权重快照，以保证结果可复现。
            </p>
          </div>

          <div class="panel">
            <div class="panel-title">
              <span>人才引进评估权重</span>
              <span class="hint">合计 {{ candidateSum }}</span>
            </div>
            <div v-for="key in candidateKeys" :key="key" class="weight-row">
              <span>{{ candidateLabels[key] }}</span>
              <el-slider v-model="candidateWeights[key]" :min="0" :max="100" :step="5"
                         :disabled="!auth.isAdmin" show-input :show-input-controls="false" style="flex: 1" />
            </div>
            <p class="hint">
              岗位可在自身表单中覆盖默认权重；未通过学历/成果硬性条件的候选人不会进入排名。
            </p>
            <div v-if="auth.isAdmin" class="page-actions" style="justify-content: flex-start; margin-top: 14px">
              <el-button type="primary" :loading="weightsSaving" @click="saveWeights">保存默认权重</el-button>
              <el-button @click="resetWeights">恢复当前值</el-button>
            </div>
            <p v-else class="hint" style="margin-top: 10px">仅管理员可以修改评分权重。</p>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="plan" label="人才规划">
        <div class="panel">
          <div class="panel-title">
            <span>人才规划目标</span>
            <span class="hint">用于人才盘点中的“规划缺口”计算</span>
          </div>
          <el-table :data="planRows" size="small" border empty-text="尚未配置人才规划目标">
            <el-table-column label="学院" min-width="160">
              <template #default="{ row }">
                <el-select v-if="auth.isAdmin" v-model="row.college" filterable allow-create default-first-option
                           size="small" style="width: 100%" @change="onPlanCollegeChange(row)">
                  <el-option v-for="item in collegeOptions" :key="item" :label="item" :value="item" />
                </el-select>
                <span v-else>{{ row.college }}</span>
              </template>
            </el-table-column>
            <el-table-column label="学科" min-width="200">
              <template #default="{ row }">
                <el-select v-if="auth.isAdmin" v-model="row.discipline" filterable allow-create default-first-option
                           size="small" style="width: 100%" :disabled="!row.college"
                           :placeholder="row.college ? '请选择学科' : '请先选择学院'">
                  <el-option v-for="item in planDisciplineOptions(row)" :key="item" :label="item" :value="item" />
                </el-select>
                <span v-else>{{ row.discipline }}</span>
              </template>
            </el-table-column>
            <el-table-column label="目标人数" width="130">
              <template #default="{ row }">
                <el-input-number v-if="auth.isAdmin" v-model="row.target_count" :min="0" :max="10000"
                                 size="small" controls-position="right" style="width: 100%" />
                <span v-else>{{ row.target_count }}</span>
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="220">
              <template #default="{ row }">
                <el-input v-if="auth.isAdmin" v-model="row.note" size="small" />
                <span v-else>{{ row.note || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column v-if="auth.isAdmin" label="操作" width="80">
              <template #default="{ $index }">
                <el-button link type="danger" @click="planRows.splice($index, 1)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="auth.isAdmin" class="page-actions" style="justify-content: flex-start; margin-top: 12px">
            <el-button :icon="Plus" @click="addPlanRow">添加规划行</el-button>
            <el-button type="primary" :loading="planSaving" @click="savePlan">保存人才规划</el-button>
          </div>
          <p v-else class="hint" style="margin-top: 12px">仅管理员可以编辑人才规划；当前为只读视图。</p>
          <p class="note" style="margin-top: 12px">
            规划缺口 = 目标人数 − 当前档案人数，仅按学院 + 学科精确匹配统计；未配置规划时人才盘点不会产生缺口数据。
          </p>
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="auth.isAdmin" name="users" label="用户管理">
        <div class="panel">
          <div class="panel-title">
            <span>系统账号</span>
            <el-button type="primary" size="small" :icon="Plus" @click="openUserCreate">新增用户</el-button>
          </div>
          <el-table :data="users" size="small" stripe empty-text="暂无用户">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="username" label="用户名" width="140" />
            <el-table-column prop="display_name" label="显示名称" min-width="140" />
            <el-table-column label="角色" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="row.role === 'admin' ? 'danger' : row.role === 'manager' ? '' : 'info'"
                        effect="plain">
                  {{ row.role_label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.is_active ? 'success' : 'info'" effect="light">
                  {{ row.is_active ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="170">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button link type="primary" @click="openUserEdit(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
          <p class="hint" style="margin-top: 10px">
            管理员可管理全部账号；业务人员可维护业务数据但不能管理用户；只读用户只能查看且联系方式脱敏。
            当前登录账号不能停用自己或降低自己的管理员角色。
          </p>
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="auth.isEditor" name="audit" label="审计日志">
        <div class="panel">
          <div class="filters" style="margin-bottom: 12px">
            <el-input v-model="auditQuery.username" placeholder="操作人" clearable style="width: 140px" />
            <el-select v-model="auditQuery.action" placeholder="操作类型" clearable style="width: 150px">
              <el-option v-for="item in actionOptions" :key="item" :label="actionLabel(item)" :value="item" />
            </el-select>
            <el-input v-model="auditQuery.resource_type" placeholder="资源类型" clearable style="width: 160px" />
            <el-date-picker v-model="auditDateRange" type="daterange" value-format="YYYY-MM-DD"
                            start-placeholder="开始日期" end-placeholder="结束日期" style="width: 240px" />
            <el-button type="primary" :icon="Search" @click="searchAudit">查询</el-button>
            <el-button :icon="RefreshLeft" @click="resetAudit">重置</el-button>
          </div>

          <el-table :data="logs" v-loading="logLoading" size="small" stripe empty-text="暂无审计日志">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="username" label="操作人" width="100" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-tag size="small" :type="actionType(row.action)" effect="plain">{{ actionLabel(row.action) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="resource_type" label="资源类型" width="150" />
            <el-table-column prop="resource_id" label="资源ID" width="80" />
            <el-table-column prop="detail" label="详情" min-width="320" show-overflow-tooltip />
            <el-table-column prop="ip" label="IP" width="125" />
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <div class="pager-row">
            <el-pagination v-model:current-page="auditQuery.page" :page-size="20" :total="logTotal"
                           layout="total, prev, pager, next" @current-change="loadLogs" />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 用户表单 -->
    <el-dialog v-model="userFormVisible" :title="userEditingId ? '编辑用户' : '新增用户'" width="480px"
               :close-on-click-modal="false" destroy-on-close>
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" :disabled="!!userEditingId" />
        </el-form-item>
        <el-form-item label="显示名称"><el-input v-model="userForm.display_name" /></el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="业务人员" value="manager" />
            <el-option label="只读用户" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="密码" :prop="userEditingId ? '' : 'password'">
          <el-input v-model="userForm.password" type="password" show-password autocomplete="new-password"
                    :placeholder="userEditingId ? '留空表示不修改密码' : '至少 6 位'" />
        </el-form-item>
        <el-form-item v-if="userEditingId" label="启用">
          <el-switch v-model="userForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="userSaving" @click="submitUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, RefreshLeft, Search } from '@element-plus/icons-vue'
import api from '../api/client'
import StatCard from '../components/StatCard.vue'
import { useAuthStore } from '../stores/auth'
import { disciplinesForCollege, type CollegeDisciplineMap } from '../utils/linkage'

const auth = useAuthStore()
const activeTab = ref('overview')
const loading = ref(false)
const info = ref<any>(null)
const settings = ref<any>(null)
const roleLabelMap: Record<string, string> = { admin: '管理员', manager: '业务人员', viewer: '只读用户' }

const advisorKeys = ['direction', 'topic', 'needs', 'capacity']
const advisorLabels: Record<string, string> = {
  direction: '研究方向相似度', topic: '具体主题匹配度', needs: '培养需求匹配度', capacity: '指导容量适配度',
}
const candidateKeys = ['direction', 'outputs', 'projects', 'teaching']
const candidateLabels: Record<string, string> = {
  direction: '研究方向相似度', outputs: '科研成果', projects: '项目经历', teaching: '教学经历',
}
const advisorWeights = reactive<Record<string, number>>({ direction: 40, topic: 25, needs: 20, capacity: 15 })
const candidateWeights = reactive<Record<string, number>>({ direction: 45, outputs: 25, projects: 20, teaching: 10 })
const weightsSaving = ref(false)
const advisorSum = computed(() => advisorKeys.reduce((sum, key) => sum + Number(advisorWeights[key] || 0), 0))
const candidateSum = computed(() => candidateKeys.reduce((sum, key) => sum + Number(candidateWeights[key] || 0), 0))

const planRows = ref<any[]>([])
const planSaving = ref(false)
const collegeOptions = ref<string[]>([])
const disciplineMap = ref<CollegeDisciplineMap>({})

const users = ref<any[]>([])
const userFormVisible = ref(false)
const userEditingId = ref<number | null>(null)
const userSaving = ref(false)
const userFormRef = ref()
const userForm = reactive<any>({ username: '', display_name: '', role: 'viewer', password: '', is_active: true })
const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [{ required: true, min: 6, message: '密码至少 6 位', trigger: 'blur' }],
}

const logs = ref<any[]>([])
const logTotal = ref(0)
const logLoading = ref(false)
const auditQuery = reactive({ username: '', action: '', resource_type: '', page: 1 })
const auditDateRange = ref<[string, string] | null>(null)
const actionOptions = [
  'create', 'update', 'delete', 'import', 'run', 'gather', 'confirm', 'review',
  'evaluate', 'ai_summary', 'update_setting',
]

function roleLabel(value: string) {
  return roleLabelMap[value] || value
}

function formatTime(value: string | null) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

function actionLabel(action: string) {
  return {
    create: '新增', update: '修改', delete: '删除', import: '导入', run: '执行匹配',
    gather: '归集材料', confirm: '人工确认', review: '人工评审', evaluate: '岗位评估',
    ai_summary: '生成摘要', update_setting: '修改配置',
  }[action] || action
}

function actionType(action: string) {
  if (['delete', 'review'].includes(action)) return 'danger'
  if (['create', 'import', 'gather'].includes(action)) return 'success'
  if (['update', 'confirm', 'evaluate', 'update_setting', 'run', 'ai_summary'].includes(action)) return 'warning'
  return 'info'
}

async function loadInfo() {
  const { data } = await api.get('/system/info')
  info.value = data
}

async function loadSettings() {
  const { data } = await api.get('/settings')
  settings.value = data
  for (const key of advisorKeys) {
    advisorWeights[key] = Math.round((data.advisor_weights[key] || 0) * 100)
  }
  for (const key of candidateKeys) {
    candidateWeights[key] = Math.round((data.candidate_weights[key] || 0) * 100)
  }
  planRows.value = (data.talent_plan || []).map((item: any) => ({ ...item }))
}

async function loadOptions() {
  const { data } = await api.get('/teachers/options')
  collegeOptions.value = data.colleges
  disciplineMap.value = data.disciplines_by_college || {}
}

function planDisciplineOptions(row: any) {
  return disciplinesForCollege(disciplineMap.value, row.college, row.discipline)
}

function onPlanCollegeChange(row: any) {
  row.discipline = ''
}

async function saveWeights() {
  if (advisorSum.value <= 0 || candidateSum.value <= 0) {
    ElMessage.warning('每组权重合计必须大于 0')
    return
  }
  weightsSaving.value = true
  try {
    await api.put('/settings/weights', {
      advisor_weights: { ...advisorWeights },
      candidate_weights: { ...candidateWeights },
    })
    ElMessage.success('默认权重已保存并归一化')
    await loadSettings()
  } finally {
    weightsSaving.value = false
  }
}

async function resetWeights() {
  await loadSettings()
  ElMessage.info('已恢复为当前保存的权重')
}

function addPlanRow() {
  planRows.value.push({ college: '', discipline: '', target_count: 0, note: '' })
}

async function savePlan() {
  for (const row of planRows.value) {
    if (!row.college || !row.discipline) {
      ElMessage.warning('每行规划都必须填写学院和学科')
      return
    }
  }
  planSaving.value = true
  try {
    await api.put('/settings/talent-plan', { items: planRows.value })
    ElMessage.success('人才规划已保存，人才盘点将按新目标计算缺口')
    await loadSettings()
  } finally {
    planSaving.value = false
  }
}

async function loadUsers() {
  if (!auth.isAdmin) return
  const { data } = await api.get('/users')
  users.value = data.items
}

function openUserCreate() {
  userEditingId.value = null
  Object.assign(userForm, { username: '', display_name: '', role: 'viewer', password: '', is_active: true })
  userFormVisible.value = true
}

function openUserEdit(row: any) {
  userEditingId.value = row.id
  Object.assign(userForm, {
    username: row.username, display_name: row.display_name, role: row.role,
    password: '', is_active: row.is_active,
  })
  userFormVisible.value = true
}

async function submitUser() {
  await userFormRef.value?.validate()
  userSaving.value = true
  try {
    if (userEditingId.value) {
      const payload: any = {
        display_name: userForm.display_name || null,
        role: userForm.role,
        is_active: userForm.is_active,
      }
      if (userForm.password) payload.password = userForm.password
      await api.put(`/users/${userEditingId.value}`, payload)
      ElMessage.success('用户已更新')
    } else {
      await api.post('/users', {
        username: userForm.username,
        display_name: userForm.display_name || userForm.username,
        role: userForm.role,
        password: userForm.password,
      })
      ElMessage.success('用户已创建')
    }
    userFormVisible.value = false
    await loadUsers()
  } finally {
    userSaving.value = false
  }
}

async function loadLogs() {
  if (!auth.isEditor) return
  logLoading.value = true
  try {
    const params: any = { page: auditQuery.page, page_size: 20 }
    if (auditQuery.username) params.username = auditQuery.username
    if (auditQuery.action) params.action = auditQuery.action
    if (auditQuery.resource_type) params.resource_type = auditQuery.resource_type
    if (auditDateRange.value?.length === 2) {
      params.date_from = auditDateRange.value[0]
      params.date_to = auditDateRange.value[1]
    }
    const { data } = await api.get('/audit-logs', { params })
    logs.value = data.items
    logTotal.value = data.total
  } finally {
    logLoading.value = false
  }
}

function searchAudit() {
  auditQuery.page = 1
  loadLogs()
}

function resetAudit() {
  auditQuery.username = ''
  auditQuery.action = ''
  auditQuery.resource_type = ''
  auditQuery.page = 1
  auditDateRange.value = null
  loadLogs()
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([loadInfo(), loadSettings(), loadOptions()])
    await Promise.all([loadUsers(), loadLogs()])
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.weight-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
}

.weight-row > span {
  width: 118px;
  font-size: 12px;
  color: #5c6c82;
  text-align: right;
}

.notice-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

@media (max-width: 1000px) {
  .notice-list {
    grid-template-columns: 1fr;
  }
}

.notice-item {
  border-left: 3px solid #9db4d8;
  background: #f8fafd;
  border-radius: 0 8px 8px 0;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.notice-item strong {
  font-size: 13px;
  color: #2f5597;
}

.notice-item span {
  font-size: 12px;
  color: #64748a;
  line-height: 1.7;
}

.pager-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
