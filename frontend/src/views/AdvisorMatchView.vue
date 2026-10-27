<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">导师匹配</h2>
        <p class="page-subtitle">
          先以导师资格、招生状态与指导容量做硬性过滤，再按研究方向、具体主题、培养需求与容量计算加权得分。
          不满足硬性条件的教师不会进入推荐排序，解释理由均来自数据库字段。
        </p>
      </div>
      <div class="page-actions">
        <el-button v-if="auth.isEditor" type="primary" :icon="Plus" @click="openStudentCreate">新增学生需求</el-button>
        <el-button v-if="auth.isEditor" :icon="Connection" @click="openTaskCreate">新建匹配任务</el-button>
      </div>
    </div>

    <div class="panel">
      <el-tabs v-model="activeTab">
        <el-tab-pane name="students" label="学生需求档案">
          <div class="filters" style="margin-bottom: 12px">
            <el-input v-model="studentQuery.keyword" class="search" placeholder="姓名 / 编号 / 兴趣 / 方向" clearable
                      :prefix-icon="Search" @keyup.enter="loadStudents" />
            <el-input v-model="studentQuery.discipline" placeholder="学科" clearable style="width: 180px" />
            <el-button type="primary" :icon="Search" @click="searchStudents">查询</el-button>
            <el-button :icon="RefreshLeft" @click="resetStudents">重置</el-button>
          </div>

          <el-table :data="students" v-loading="studentLoading" size="small" stripe empty-text="暂无学生需求档案">
            <el-table-column prop="student_no" label="学生编号" width="120" />
            <el-table-column prop="name" label="姓名" width="90" />
            <el-table-column prop="major" label="专业" min-width="130" show-overflow-tooltip />
            <el-table-column prop="discipline" label="学科" min-width="140" show-overflow-tooltip />
            <el-table-column prop="desired_direction" label="期望方向" min-width="180" show-overflow-tooltip />
            <el-table-column prop="keywords" label="兴趣关键词" min-width="180" show-overflow-tooltip />
            <el-table-column prop="degree_goal" label="培养目标" min-width="130" show-overflow-tooltip />
            <el-table-column v-if="auth.isEditor" label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openStudentEdit(row)">编辑</el-button>
                <el-button link type="primary" @click="openTaskCreate(row)">匹配</el-button>
                <el-button link type="danger" @click="removeStudent(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pager-row">
            <el-pagination v-model:current-page="studentQuery.page" v-model:page-size="studentQuery.page_size"
                           :total="studentTotal" layout="total, prev, pager, next"
                           @current-change="loadStudents" />
          </div>
        </el-tab-pane>

        <el-tab-pane name="tasks" label="匹配任务与结果">
          <div class="filters" style="margin-bottom: 12px">
            <el-select v-model="taskQuery.status" placeholder="任务状态" clearable style="width: 160px">
              <el-option label="待执行" value="pending" />
              <el-option label="执行中" value="running" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
            <el-button type="primary" :icon="Search" @click="loadTasks">查询</el-button>
          </div>

          <el-table :data="tasks" v-loading="taskLoading" size="small" stripe empty-text="暂无匹配任务">
            <el-table-column prop="id" label="任务" width="70">
              <template #default="{ row }">#{{ row.id }}</template>
            </el-table-column>
            <el-table-column prop="name" label="任务名称" min-width="200" show-overflow-tooltip />
            <el-table-column label="学生" min-width="180">
              <template #default="{ row }">
                <template v-if="row.student">
                  {{ row.student.name }}<span class="muted"> · {{ row.student.major }}</span>
                </template>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
            <el-table-column label="权重" min-width="220">
              <template #default="{ row }">
                <span class="hint">
                  方向 {{ pct(row.weights.direction) }} · 主题 {{ pct(row.weights.topic) }} ·
                  需求 {{ pct(row.weights.needs) }} · 容量 {{ pct(row.weights.capacity) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="taskStatusType(row.status)" effect="light">
                  {{ taskStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="有效推荐" width="90">
              <template #default="{ row }">{{ row.qualified_count ?? '—' }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="168">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openTask(row)">查看结果</el-button>
                <el-button v-if="auth.isEditor" link type="primary" :loading="runningId === row.id"
                           @click="runTask(row)">
                  {{ row.status === 'completed' ? '重新执行' : '执行匹配' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pager-row">
            <el-pagination v-model:current-page="taskQuery.page" v-model:page-size="taskQuery.page_size"
                           :total="taskTotal" layout="total, prev, pager, next"
                           @current-change="loadTasks" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 学生需求编辑 -->
    <el-dialog v-model="studentFormVisible" :title="studentEditingId ? '编辑学生需求' : '新增学生需求'" width="640px"
               :close-on-click-modal="false" destroy-on-close>
      <el-form ref="studentFormRef" :model="studentForm" :rules="studentRules" label-width="96px">
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="学生编号" prop="student_no">
              <el-input v-model="studentForm.student_no" :disabled="!!studentEditingId" placeholder="如 B3S021" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名" prop="name"><el-input v-model="studentForm.name" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="专业" prop="major"><el-input v-model="studentForm.major" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学科" prop="discipline"><el-input v-model="studentForm.discipline" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="研究兴趣"><el-input v-model="studentForm.research_interest" /></el-form-item>
        <el-form-item label="兴趣关键词">
          <el-input v-model="studentForm.keywords" placeholder="用逗号/顿号分隔，将参与主题匹配" />
        </el-form-item>
        <el-form-item label="期望方向"><el-input v-model="studentForm.desired_direction" /></el-form-item>
        <el-form-item label="培养需求">
          <el-input v-model="studentForm.training_needs" type="textarea" :rows="2"
                    placeholder="如：希望获得工程实践与论文写作训练" />
        </el-form-item>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="培养目标"><el-input v-model="studentForm.degree_goal" placeholder="如：学术型硕士" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="其他条件"><el-input v-model="studentForm.other_conditions" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="studentFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="studentSaving" @click="submitStudent">保存</el-button>
      </template>
    </el-dialog>

    <!-- 创建匹配任务 -->
    <el-dialog v-model="taskFormVisible" title="新建导师匹配任务" width="620px"
               :close-on-click-modal="false" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="学生需求" required>
          <el-select v-model="taskForm.student_id" filterable style="width: 100%" placeholder="选择学生">
            <el-option v-for="item in allStudents" :key="item.id" :value="item.id"
                       :label="`${item.name} · ${item.student_no} · ${item.major}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务名称">
          <el-input v-model="taskForm.name" placeholder="留空则自动生成" />
        </el-form-item>
        <div class="weight-note">
          权重会在提交时自动归一化；权重越高，该维度对总分影响越大。硬性条件与权重无关。
        </div>
        <div v-for="key in weightKeys" :key="key" class="weight-row">
          <span>{{ weightLabels[key] || key }}</span>
          <el-slider v-model="taskForm.weights[key]" :min="0" :max="100" :step="5" show-input
                     :show-input-controls="false" style="flex: 1" />
        </div>
        <div class="hint" style="margin-top: 8px">
          当前输入合计 {{ weightSum }}，提交后按合计归一化为 100%。
        </div>
      </el-form>
      <template #footer>
        <el-button @click="taskFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="taskCreating" @click="submitTask(false)">创建任务</el-button>
        <el-button type="success" :loading="taskCreating" @click="submitTask(true)">创建并执行</el-button>
      </template>
    </el-dialog>

    <!-- 结果抽屉 -->
    <el-drawer v-model="resultVisible" :title="resultTask ? `匹配结果 · ${resultTask.name}` : '匹配结果'" size="860px">
      <template v-if="resultTask">
        <div class="result-head">
          <div>
            <div class="result-student">
              {{ resultTask.student?.name || '学生' }}
              <span class="hint">{{ resultTask.student?.student_no }} · {{ resultTask.student?.major }}</span>
            </div>
            <div class="hint" style="margin-top: 4px">
              期望方向：{{ resultTask.student?.desired_direction || '—' }}
            </div>
          </div>
          <div class="result-meta">
            <el-tag :type="taskStatusType(resultTask.status)" effect="light">
              {{ taskStatusLabel(resultTask.status) }}
            </el-tag>
            <span class="hint">执行于 {{ formatTime(resultTask.completed_at) }}</span>
          </div>
        </div>

        <div class="summary-row">
          <div class="summary-box">
            <strong>{{ resultTask.summary?.qualified_count ?? recommendations.length }}</strong>
            <span>满足硬性条件的教师</span>
          </div>
          <div class="summary-box warn">
            <strong>{{ resultTask.summary?.excluded_count ?? excluded.length }}</strong>
            <span>被硬性条件排除</span>
          </div>
          <div class="summary-box">
            <strong>{{ recommendations.filter(r => r.human_confirmed).length }}</strong>
            <span>已人工确认</span>
          </div>
        </div>

        <p class="note">{{ resultTask.summary?.note }}</p>

        <div class="weight-chips">
          <span class="hint">本次权重：</span>
          <el-tag v-for="key in weightKeys" :key="key" size="small" effect="plain">
            {{ weightLabels[key] }} {{ pct(resultTask.weights[key]) }}
          </el-tag>
        </div>

        <el-tabs v-model="resultTab" style="margin-top: 10px">
          <el-tab-pane name="recommend" :label="`有效推荐（${recommendations.length}）`">
            <div v-if="!recommendations.length" class="empty-block">
              没有教师同时满足导师资格、招生开放与剩余容量要求。建议先补充导师或调整招生计划。
            </div>
            <div v-for="item in recommendations" :key="item.id" class="match-card">
              <div class="match-head">
                <span class="rank-badge" :class="{ top: item.rank === 1 }">{{ item.rank }}</span>
                <div class="match-person">
                  <div>
                    <strong>{{ item.teacher?.name }}</strong>
                    <span class="hint"> {{ item.teacher?.college }} · {{ item.teacher?.title }} · {{ item.teacher?.research_direction || '方向未填写' }}</span>
                  </div>
                  <div class="hint">
                    剩余容量 {{ item.teacher?.available_capacity }}/{{ item.teacher?.capacity }}
                    · {{ item.teacher?.enrollment_label }}
                  </div>
                </div>
                <div class="match-score">
                  <strong>{{ item.total_score }}</strong><span>综合分</span>
                </div>
              </div>

              <div class="score-grid">
                <div v-for="dim in dimensionRows(item)" :key="dim.key" class="score-item">
                  <span>{{ dim.label }}</span>
                  <el-progress :percentage="dim.value" :stroke-width="7" :show-text="false" />
                  <b>{{ dim.value }}</b>
                </div>
              </div>

              <el-collapse class="reason-collapse">
                <el-collapse-item title="查看评分理由与数据依据" :name="item.id">
                  <pre class="pre-wrap reason-text">{{ item.reasons }}</pre>
                </el-collapse-item>
              </el-collapse>

              <div class="confirm-row">
                <el-tag v-if="item.human_confirmed" size="small" type="success" effect="light">
                  已人工确认
                </el-tag>
                <el-tag v-else size="small" type="info" effect="plain">待人工确认</el-tag>
                <span v-if="item.note" class="hint">备注：{{ item.note }}</span>
                <el-button v-if="auth.isEditor" size="small" link type="primary" @click="openConfirm(item)">
                  填写人工结论
                </el-button>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane name="excluded" :label="`硬性条件排除（${excluded.length}）`">
            <p class="hint" style="margin-top: 0">
              以下教师不满足至少一项硬性条件，因此不参与推荐排序。表格按规则分从高到低展示，仅为核对数据，非推荐顺序。
            </p>
            <el-table :data="excluded" size="small" stripe max-height="480">
              <el-table-column prop="teacher.name" label="教师" width="100" />
              <el-table-column prop="teacher.college" label="学院" min-width="130" show-overflow-tooltip />
              <el-table-column label="规则分" width="80">
                <template #default="{ row }">{{ row.total_score }}</template>
              </el-table-column>
              <el-table-column prop="disqualifiers" label="未满足的硬性条件" min-width="260" show-overflow-tooltip />
              <el-table-column label="人工备注" width="120">
                <template #default="{ row }">
                  <el-button v-if="auth.isEditor" link size="small" @click="openConfirm(row)">备注</el-button>
                  <span v-else class="muted">{{ row.note || '—' }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-drawer>

    <!-- 人工确认 -->
    <el-dialog v-model="confirmVisible" title="人工确认结论" width="480px">
      <p class="hint" style="margin-top: 0">
        人工确认不会改变系统规则分，只记录使用者的判断与备注，便于后续审计。
      </p>
      <el-form label-width="90px">
        <el-form-item label="教师">
          <span>{{ confirmTarget?.teacher?.name }}</span>
        </el-form-item>
        <el-form-item label="结论">
          <el-radio-group v-model="confirmForm.human_confirmed">
            <el-radio :value="true">确认推荐</el-radio>
            <el-radio :value="false">不采用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="confirmForm.note" type="textarea" :rows="3"
                    placeholder="如：已与导师沟通，同意指导；或方向存在偏差，人工排除" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="confirmVisible = false">取消</el-button>
        <el-button type="primary" :loading="confirmSaving" @click="submitConfirm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Plus, RefreshLeft, Search } from '@element-plus/icons-vue'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const activeTab = ref('students')

const students = ref<any[]>([])
const studentTotal = ref(0)
const studentLoading = ref(false)
const studentQuery = reactive({ keyword: '', discipline: '', page: 1, page_size: 10 })
const allStudents = ref<any[]>([])

const tasks = ref<any[]>([])
const taskTotal = ref(0)
const taskLoading = ref(false)
const runningId = ref<number | null>(null)
const taskQuery = reactive({ status: '', page: 1, page_size: 10 })

const weightKeys = ['direction', 'topic', 'needs', 'capacity']
const weightLabels = reactive<Record<string, string>>({
  direction: '研究方向相似度',
  topic: '具体主题匹配度',
  needs: '培养需求匹配度',
  capacity: '指导容量适配度',
})

const studentFormVisible = ref(false)
const studentEditingId = ref<number | null>(null)
const studentSaving = ref(false)
const studentFormRef = ref()
const defaultStudent = () => ({
  student_no: '', name: '', major: '', discipline: '', research_interest: '',
  keywords: '', desired_direction: '', training_needs: '', degree_goal: '', other_conditions: '',
})
const studentForm = reactive<any>(defaultStudent())
const studentRules = {
  student_no: [{ required: true, message: '请输入学生编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  major: [{ required: true, message: '请输入专业', trigger: 'blur' }],
  discipline: [{ required: true, message: '请输入学科', trigger: 'blur' }],
}

const taskFormVisible = ref(false)
const taskCreating = ref(false)
const taskForm = reactive({
  student_id: null as number | null,
  name: '',
  weights: { direction: 40, topic: 25, needs: 20, capacity: 15 } as Record<string, number>,
})
const weightSum = computed(() => weightKeys.reduce((sum, key) => sum + Number(taskForm.weights[key] || 0), 0))

const resultVisible = ref(false)
const resultTask = ref<any>(null)
const resultTab = ref('recommend')
const recommendations = computed<any[]>(() => resultTask.value?.recommendations || [])
const excluded = computed<any[]>(() => resultTask.value?.excluded || [])

const confirmVisible = ref(false)
const confirmSaving = ref(false)
const confirmTarget = ref<any>(null)
const confirmForm = reactive({ human_confirmed: true, note: '' })

function pct(value: number | undefined) {
  return `${Math.round((value || 0) * 100)}%`
}

function formatTime(value: string | null) {
  if (!value) return '—'
  return value.replace('T', ' ').slice(0, 16)
}

function taskStatusLabel(status: string) {
  return { pending: '待执行', running: '执行中', completed: '已完成', failed: '失败' }[status] || status
}

function taskStatusType(status: string) {
  return status === 'completed' ? 'success' : status === 'failed' ? 'danger' : status === 'running' ? 'warning' : 'info'
}

function dimensionRows(item: any) {
  return [
    { key: 'direction', label: '方向相似', value: item.direction_score || 0 },
    { key: 'topic', label: '主题匹配', value: item.topic_score || 0 },
    { key: 'needs', label: '培养需求', value: item.need_score || 0 },
    { key: 'capacity', label: '容量适配', value: item.capacity_score || 0 },
  ]
}

async function loadStudents() {
  studentLoading.value = true
  try {
    const params: any = { ...studentQuery }
    if (!params.keyword) delete params.keyword
    if (!params.discipline) delete params.discipline
    const { data } = await api.get('/students', { params })
    students.value = data.items
    studentTotal.value = data.total
  } finally {
    studentLoading.value = false
  }
}

async function loadAllStudents() {
  const { data } = await api.get('/students', { params: { page: 1, page_size: 100 } })
  allStudents.value = data.items
}

function searchStudents() {
  studentQuery.page = 1
  loadStudents()
}

function resetStudents() {
  studentQuery.keyword = ''
  studentQuery.discipline = ''
  studentQuery.page = 1
  loadStudents()
}

function openStudentCreate() {
  studentEditingId.value = null
  Object.assign(studentForm, defaultStudent())
  studentFormVisible.value = true
}

function openStudentEdit(row: any) {
  studentEditingId.value = row.id
  Object.assign(studentForm, defaultStudent(), row)
  studentFormVisible.value = true
}

async function submitStudent() {
  await studentFormRef.value?.validate()
  studentSaving.value = true
  try {
    if (studentEditingId.value) {
      const { student_no, ...payload } = studentForm
      await api.put(`/students/${studentEditingId.value}`, payload)
      ElMessage.success('学生需求已更新')
    } else {
      await api.post('/students', { ...studentForm })
      ElMessage.success('学生需求已创建')
    }
    studentFormVisible.value = false
    await Promise.all([loadStudents(), loadAllStudents()])
  } finally {
    studentSaving.value = false
  }
}

async function removeStudent(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除学生“${row.name}”的需求档案吗？已有匹配任务时不能删除。`,
      '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch {
    return
  }
  await api.delete(`/students/${row.id}`)
  ElMessage.success('学生档案已删除')
  await Promise.all([loadStudents(), loadAllStudents()])
}

async function loadTasks() {
  taskLoading.value = true
  try {
    const params: any = { ...taskQuery }
    if (!params.status) delete params.status
    const { data } = await api.get('/advisor/tasks', { params })
    tasks.value = data.items
    taskTotal.value = data.total
  } finally {
    taskLoading.value = false
  }
}

async function loadWeights() {
  const { data } = await api.get('/advisor/weights')
  Object.assign(weightLabels, data.labels)
  for (const key of weightKeys) {
    if (typeof data.weights[key] === 'number') {
      taskForm.weights[key] = Math.round(data.weights[key] * 100)
    }
  }
}

function openTaskCreate(student?: any) {
  taskForm.student_id = student?.id || null
  taskForm.name = ''
  taskFormVisible.value = true
  if (!allStudents.value.length) loadAllStudents()
}

async function submitTask(runNow: boolean) {
  if (!taskForm.student_id) {
    ElMessage.warning('请选择学生需求档案')
    return
  }
  if (weightSum.value <= 0) {
    ElMessage.warning('权重合计必须大于 0')
    return
  }
  taskCreating.value = true
  try {
    const { data } = await api.post('/advisor/tasks', {
      student_id: taskForm.student_id,
      name: taskForm.name || null,
      weights: taskForm.weights,
    })
    taskFormVisible.value = false
    ElMessage.success('匹配任务已创建')
    await loadTasks()
    if (runNow) {
      await runTask(data, true)
    }
  } finally {
    taskCreating.value = false
  }
}

async function runTask(row: any, openAfter = false) {
  runningId.value = row.id
  try {
    await api.post(`/advisor/tasks/${row.id}/run`)
    ElMessage.success(openAfter ? '匹配完成，已展示结果' : '匹配已重新执行')
    await loadTasks()
    if (openAfter) await openTaskById(row.id)
  } finally {
    runningId.value = null
  }
}

async function openTaskById(id: number) {
  const { data } = await api.get(`/advisor/tasks/${id}`)
  resultTask.value = data
  resultTab.value = 'recommend'
  resultVisible.value = true
}

async function openTask(row: any) {
  await openTaskById(row.id)
}

function openConfirm(item: any) {
  confirmTarget.value = item
  confirmForm.human_confirmed = item.human_confirmed !== false
  confirmForm.note = item.note || ''
  confirmVisible.value = true
}

async function submitConfirm() {
  if (!confirmTarget.value) return
  confirmSaving.value = true
  try {
    await api.put(`/advisor/results/${confirmTarget.value.id}/confirm`, {
      human_confirmed: confirmForm.human_confirmed,
      note: confirmForm.note || null,
    })
    ElMessage.success('人工结论已记录')
    confirmVisible.value = false
    if (resultTask.value) await openTaskById(resultTask.value.id)
  } finally {
    confirmSaving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadStudents(), loadAllStudents(), loadTasks(), loadWeights()])
})
</script>

<style scoped>
.pager-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.weight-note {
  font-size: 12px;
  color: #7a8797;
  background: #f7f9fd;
  border: 1px dashed #dce5f1;
  border-radius: 6px;
  padding: 8px 10px;
  margin: 0 0 12px;
  line-height: 1.6;
}

.weight-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}

.weight-row > span {
  width: 112px;
  font-size: 13px;
  color: #4a5b72;
  text-align: right;
}

.result-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px dashed #e6ebf3;
}

.result-student {
  font-size: 18px;
  font-weight: 600;
  color: #1c2f4a;
}

.result-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin: 14px 0;
}

.summary-box {
  background: #f7f9fd;
  border: 1px solid #eef1f7;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.summary-box strong {
  display: block;
  font-size: 22px;
  color: #2f5597;
}

.summary-box span {
  font-size: 11px;
  color: #7a8797;
}

.summary-box.warn strong {
  color: #c46f1f;
}

.weight-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin: 12px 0;
}

.match-card {
  border: 1px solid #e6ebf3;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 12px;
  background: #fff;
}

.match-card:hover {
  border-color: #c6d4e9;
}

.match-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.match-person {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.match-person strong {
  font-size: 15px;
}

.match-score {
  text-align: right;
  display: flex;
  flex-direction: column;
}

.match-score strong {
  font-size: 24px;
  color: #2f5597;
  line-height: 1.1;
}

.match-score span {
  font-size: 11px;
  color: #8494a8;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin: 12px 0 6px;
}

.score-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: #7a8797;
}

.score-item b {
  color: #4a5b72;
  font-size: 12px;
  align-self: flex-end;
}

.reason-collapse {
  margin-top: 6px;
  border-top: none;
}

.reason-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.8;
  color: #4a5b72;
  white-space: pre-wrap;
  font-family: inherit;
}

.confirm-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  border-top: 1px dashed #eef1f6;
  padding-top: 10px;
  margin-top: 6px;
}

.confirm-row .el-button {
  margin-left: auto;
}
</style>
