<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">师生匹配度</h2>
        <p class="page-subtitle">
          用 0-100 分量化学生培养需求与教师档案的契合程度，拆分为研究方向、具体主题、培养需求与指导容量四个维度。
          硬性条件独立校验，分数不替代人工判断。
        </p>
      </div>
      <div class="page-actions">
        <el-tag effect="plain" type="info">规则量化 · 非自动决策</el-tag>
      </div>
    </div>

    <div class="panel" v-loading="baseLoading">
      <el-form label-width="92px" class="query-form">
        <el-row :gutter="18">
          <el-col :xs="24" :md="14" :lg="10">
            <el-form-item label="学生需求">
              <el-select v-model="studentId" filterable clearable style="width: 100%"
                         placeholder="选择学生需求档案" @change="invalidate">
                <el-option v-for="item in students" :key="item.id" :value="item.id"
                           :label="`${item.name} · ${item.student_no} · ${item.major}`" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="10" :lg="7">
            <el-form-item label="量化范围">
              <el-radio-group v-model="scope" @change="invalidate">
                <el-radio-button value="all">全部教师</el-radio-button>
                <el-radio-button value="single">指定教师</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col v-if="scope === 'single'" :xs="24" :md="24" :lg="7">
            <el-form-item label="教师">
              <el-select v-model="teacherId" filterable clearable style="width: 100%"
                         placeholder="选择教师" @change="invalidate">
                <el-option v-for="item in teachers" :key="item.id" :value="item.id"
                           :label="`${item.name} · ${item.college} · ${item.title}`" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <div v-if="selectedStudent" class="student-summary">
          <el-tag size="small" effect="plain">{{ selectedStudent.student_no }}</el-tag>
          <strong>{{ selectedStudent.name }}</strong>
          <span class="hint">{{ selectedStudent.major }} · {{ selectedStudent.discipline }}</span>
          <span class="hint">期望方向：{{ selectedStudent.desired_direction || '未填写' }}</span>
        </div>

        <el-collapse class="weight-panel">
          <el-collapse-item title="评分权重（提交时按合计自动归一化）" name="weights">
            <div v-for="key in weightKeys" :key="key" class="weight-row">
              <span>{{ weightLabels[key] }}</span>
              <el-slider v-model="weights[key]" :min="0" :max="100" :step="5" show-input
                         :show-input-controls="false" style="flex: 1" @change="invalidate" />
            </div>
          </el-collapse-item>
        </el-collapse>

        <div class="actions-row">
          <el-button type="primary" :icon="Search" :loading="loading" @click="calculate">开始量化</el-button>
          <el-button :icon="RefreshLeft" @click="resetQuery">重置</el-button>
          <span class="hint">当前权重合计 {{ weightSum }}，归一化后计入总分。</span>
        </div>
      </el-form>
    </div>

    <div v-if="result" class="panel result-panel">
      <div class="result-title">
        <span>量化结果</span>
        <span class="hint">
          {{ result.student.name }} · {{ result.scope === 'single' ? '指定教师' : '全部教师' }}
        </span>
      </div>

      <div class="summary-row">
        <div class="summary-box">
          <strong>{{ result.summary.teacher_count }}</strong>
          <span>参与量化教师</span>
        </div>
        <div class="summary-box">
          <strong>{{ result.summary.qualified_count }}</strong>
          <span>满足硬性条件</span>
        </div>
        <div class="summary-box warn">
          <strong>{{ result.summary.excluded_count }}</strong>
          <span>硬性条件排除</span>
        </div>
        <div class="summary-box">
          <strong>{{ fmt(result.summary.highest_qualified_score ?? result.summary.highest_score) }}</strong>
          <span>{{ result.summary.highest_qualified_score != null ? '最高有效分' : '最高规则分' }}</span>
        </div>
      </div>

      <el-alert class="result-note" type="info" :closable="false" :title="result.note" />
      <div class="grade-scale">演示分级阈值：{{ gradeScale }}（可按学校规则调整）</div>

      <template v-if="result.scope === 'single' && singleItem">
        <div class="hero-card" :class="{ excluded: !singleItem.qualified }">
          <div class="hero-person">
            <div class="hero-avatar">{{ singleItem.teacher.name.slice(0, 1) }}</div>
            <div>
              <div class="hero-name">
                <strong>{{ singleItem.teacher.name }}</strong>
                <el-tag size="small" :type="gradeTagType(singleItem.grade)" effect="light">
                  {{ singleItem.grade }} · {{ singleItem.grade_label }}
                </el-tag>
                <el-tag v-if="singleItem.qualified" size="small" type="success" effect="plain">满足硬性条件</el-tag>
                <el-tag v-else size="small" type="warning" effect="plain">硬性条件未通过</el-tag>
              </div>
              <div class="hint">
                {{ singleItem.teacher.college }} · {{ singleItem.teacher.title }} ·
                {{ singleItem.teacher.research_direction || '研究方向未填写' }}
              </div>
              <div class="hint">
                学生 {{ result.student.name }} → 教师 {{ singleItem.teacher.name }}
                <template v-if="singleItem.rank"> · 全部有效推荐中排名第 {{ singleItem.rank }}</template>
              </div>
            </div>
          </div>
          <div class="hero-score">
            <div><strong>{{ fmt(singleItem.total_score) }}</strong><span> / 100</span></div>
            <span class="hint">综合匹配度</span>
          </div>
        </div>

        <el-alert v-if="!singleItem.qualified" class="condition-alert" type="warning" :closable="false"
                  title="该教师不满足硬性条件，规则分仅作核对，不进入有效推荐"
                  :description="singleItem.disqualifiers" />

        <div class="dimension-grid">
          <div v-for="dim in dimensionRows(singleItem)" :key="dim.key" class="dimension-card">
            <div class="dimension-head">
              <span>{{ dim.label }}</span>
              <b>{{ fmt(dim.contribution) }} 分</b>
            </div>
            <el-progress :percentage="Math.min(100, dim.score)" :stroke-width="8" :show-text="false" />
            <div class="hint">
              维度得分 {{ fmt(dim.score) }} × 权重 {{ pct(dim.weight) }} = 贡献 {{ fmt(dim.contribution) }}
            </div>
          </div>
        </div>

        <div class="formula-box">{{ singleItem.formula }}</div>

        <div v-if="singleItem.matched_terms?.length" class="matched-row">
          <span class="hint">命中兴趣词：</span>
          <el-tag v-for="term in singleItem.matched_terms" :key="term" size="small" effect="plain">
            {{ term }}
          </el-tag>
        </div>

        <el-alert class="grade-note" type="success" :closable="false"
                  :title="`${singleItem.grade} · ${singleItem.grade_label}`"
                  :description="singleItem.grade_description" />

        <el-collapse class="reason-collapse">
          <el-collapse-item title="查看完整评分理由与数据依据" name="single">
            <pre class="reason-text">{{ singleItem.reasons }}</pre>
          </el-collapse-item>
        </el-collapse>
      </template>

      <template v-else>
        <p class="hint table-hint">
          按“满足硬性条件优先、总分从高到低”排列。硬性条件不通过的教师显示规则分，但不作为有效推荐。
        </p>
        <el-table :data="result.items" size="small" stripe max-height="520" empty-text="没有可展示的教师">
          <el-table-column label="排名" width="64">
            <template #default="{ row }">{{ row.rank ? `#${row.rank}` : '—' }}</template>
          </el-table-column>
          <el-table-column label="教师" min-width="140">
            <template #default="{ row }">
              <div><strong>{{ row.teacher.name }}</strong></div>
              <div class="hint">{{ row.teacher.teacher_no }}</div>
            </template>
          </el-table-column>
          <el-table-column label="学院 / 学科" min-width="190" show-overflow-tooltip>
            <template #default="{ row }">{{ row.teacher.college }} · {{ row.teacher.discipline }}</template>
          </el-table-column>
          <el-table-column label="综合分" width="82" align="center">
            <template #default="{ row }"><strong class="score-value">{{ fmt(row.total_score) }}</strong></template>
          </el-table-column>
          <el-table-column label="等级" width="116">
            <template #default="{ row }">
              <el-tag size="small" :type="gradeTagType(row.grade)" effect="light">
                {{ row.grade }} · {{ row.grade_label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="分项得分（方向 / 主题 / 需求 / 容量）" min-width="245">
            <template #default="{ row }">
              <span class="hint">
                {{ fmt(row.dimensions.direction.score) }} / {{ fmt(row.dimensions.topic.score) }} /
                {{ fmt(row.dimensions.needs.score) }} / {{ fmt(row.dimensions.capacity.score) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="硬性条件" width="108">
            <template #default="{ row }">
              <el-tag v-if="row.qualified" size="small" type="success" effect="plain">满足</el-tag>
              <el-tooltip v-else :content="row.disqualifiers" placement="top">
                <el-tag size="small" type="warning" effect="plain">不满足</el-tag>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="88" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDetail(row)">查看依据</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </div>

    <div v-else class="panel empty-panel">
      <div class="empty-mark">0—100</div>
      <div>
        <strong>选择学生后开始量化</strong>
        <p class="hint" style="margin: 6px 0 0">
          系统按研究方向相似度、具体主题匹配度、培养需求匹配度和指导容量适配度计算加权总分，
          并校验导师资格、招生状态和剩余容量。量化不会自动给出录取或培养结论。
        </p>
      </div>
    </div>

    <el-drawer v-model="detailVisible" title="匹配度计算依据" size="620px">
      <template v-if="detailRow">
        <div class="drawer-head">
          <div>
            <div class="drawer-name">
              {{ detailRow.teacher.name }}
              <el-tag size="small" :type="gradeTagType(detailRow.grade)" effect="light">
                {{ detailRow.grade }} · {{ detailRow.grade_label }}
              </el-tag>
            </div>
            <div class="hint">{{ detailRow.teacher.college }} · {{ detailRow.teacher.title }} · {{ detailRow.teacher.discipline }}</div>
          </div>
          <div class="drawer-score">
            <strong>{{ fmt(detailRow.total_score) }}</strong><span>/100</span>
          </div>
        </div>

        <el-alert v-if="!detailRow.qualified" type="warning" :closable="false"
                  title="不满足硬性条件，不进入有效推荐" :description="detailRow.disqualifiers" />

        <div class="drawer-dims">
          <div v-for="dim in dimensionRows(detailRow)" :key="dim.key" class="drawer-dim">
            <span>{{ dim.label }}</span>
            <el-progress :percentage="Math.min(100, dim.score)" :stroke-width="7" :show-text="false" style="flex: 1" />
            <b>{{ fmt(dim.contribution) }} 分</b>
          </div>
        </div>

        <div class="formula-box">{{ detailRow.formula }}</div>

        <div v-if="detailRow.matched_terms?.length" class="matched-row">
          <span class="hint">命中兴趣词：</span>
          <el-tag v-for="term in detailRow.matched_terms" :key="term" size="small" effect="plain">{{ term }}</el-tag>
        </div>

        <el-alert type="success" :closable="false"
                  :title="`${detailRow.grade} · ${detailRow.grade_label}`"
                  :description="detailRow.grade_description" />

        <h4 class="drawer-subtitle">完整评分理由</h4>
        <pre class="reason-text">{{ detailRow.reasons }}</pre>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshLeft, Search } from '@element-plus/icons-vue'
import api from '../api/client'

type Scope = 'all' | 'single'

const students = ref<any[]>([])
const teachers = ref<any[]>([])
const studentId = ref<number | null>(null)
const teacherId = ref<number | null>(null)
const scope = ref<Scope>('all')
const baseLoading = ref(false)
const loading = ref(false)
const result = ref<any>(null)
const detailVisible = ref(false)
const detailRow = ref<any>(null)

const weightKeys = ['direction', 'topic', 'needs', 'capacity'] as const
const weightLabels = reactive<Record<string, string>>({
  direction: '研究方向相似度',
  topic: '具体主题匹配度',
  needs: '培养需求匹配度',
  capacity: '指导容量适配度',
})
const weights = reactive<Record<string, number>>({
  direction: 40,
  topic: 25,
  needs: 20,
  capacity: 15,
})

const weightSum = computed(() => weightKeys.reduce((sum, key) => sum + Number(weights[key] || 0), 0))
const selectedStudent = computed(() => students.value.find((item) => item.id === studentId.value) || null)
const singleItem = computed(() => result.value?.items?.[0] || null)
const gradeScale = computed(() => {
  const rules = result.value?.grade_rules || []
  return rules
    .map((rule: any, index: number) => index < rules.length - 1
      ? `${rule.grade} ≥ ${rule.min_score}`
      : `${rule.grade} < ${rules[index - 1]?.min_score ?? 0}`)
    .join(' · ')
})

function pct(value: number | undefined) {
  return `${Math.round((value || 0) * 100)}%`
}

function fmt(value: number | null | undefined) {
  return typeof value === 'number' ? value.toFixed(1) : '—'
}

function gradeTagType(grade: string) {
  return grade === 'A' ? 'success' : grade === 'B' ? 'primary' : grade === 'C' ? 'warning' : 'danger'
}

function dimensionRows(item: any) {
  return weightKeys.map((key) => ({ key, ...item.dimensions[key] }))
}

function invalidate() {
  result.value = null
  detailVisible.value = false
}

function openDetail(row: any) {
  detailRow.value = row
  detailVisible.value = true
}

function resetQuery() {
  const first = students.value.find((item) => item.desired_direction || item.research_interest) || students.value[0]
  studentId.value = first?.id || null
  teacherId.value = teachers.value[0]?.id || null
  scope.value = 'all'
  result.value = null
  for (const key of weightKeys) {
    weights[key] = { direction: 40, topic: 25, needs: 20, capacity: 15 }[key]
  }
}

async function loadBase() {
  baseLoading.value = true
  try {
    const [studentRes, teacherRes, weightRes] = await Promise.all([
      api.get('/students', { params: { page: 1, page_size: 100 } }),
      api.get('/teachers', { params: { page: 1, page_size: 100 } }),
      api.get('/advisor/weights'),
    ])
    students.value = studentRes.data.items || []
    teachers.value = teacherRes.data.items || []
    Object.assign(weightLabels, weightRes.data.labels || {})
    for (const key of weightKeys) {
      const value = weightRes.data.weights?.[key]
      if (typeof value === 'number') weights[key] = Math.round(value * 100)
    }
    const first = students.value.find((item) => item.desired_direction || item.research_interest) || students.value[0]
    studentId.value = first?.id || null
    teacherId.value = teachers.value[0]?.id || null
  } finally {
    baseLoading.value = false
  }
}

async function calculate() {
  if (!studentId.value) {
    ElMessage.warning('请先选择学生需求档案')
    return
  }
  if (scope.value === 'single' && !teacherId.value) {
    ElMessage.warning('请选择要量化的教师')
    return
  }
  if (weightSum.value <= 0) {
    ElMessage.warning('权重合计必须大于 0')
    return
  }
  loading.value = true
  try {
    const payload: any = {
      student_id: studentId.value,
      weights: { ...weights },
    }
    if (scope.value === 'single') payload.teacher_id = teacherId.value
    const { data } = await api.post('/advisor/score', payload)
    result.value = data
    ElMessage.success(
      `量化完成：${data.summary.qualified_count} 位教师满足硬性条件`,
    )
  } finally {
    loading.value = false
  }
}

onMounted(loadBase)
</script>

<style scoped>
.query-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.student-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  background: #f7f9fd;
  border: 1px dashed #dce5f1;
  border-radius: 6px;
  padding: 8px 10px;
  margin: 2px 0 10px;
  font-size: 13px;
}

.weight-panel {
  margin-bottom: 8px;
  border-top: none;
  border-bottom: none;
}

.weight-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 6px;
}

.weight-row > span {
  width: 112px;
  font-size: 13px;
  color: #4a5b72;
  text-align: right;
}

.actions-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding-top: 10px;
  border-top: 1px dashed #eef1f6;
}

.actions-row .hint {
  margin-left: 4px;
}

.result-panel {
  margin-top: 14px;
}

.result-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 600;
  color: #1c2f4a;
  margin-bottom: 10px;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}

.summary-box {
  background: #f7f9fd;
  border: 1px solid #eef1f7;
  border-radius: 8px;
  padding: 10px;
  text-align: center;
}

.summary-box strong {
  display: block;
  font-size: 21px;
  color: #2f5597;
}

.summary-box span {
  font-size: 11px;
  color: #7a8797;
}

.summary-box.warn strong {
  color: #c46f1f;
}

.result-note {
  margin-bottom: 8px;
}

.grade-scale {
  font-size: 12px;
  color: #7a8797;
  margin: 0 0 12px;
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid #dbe6f5;
  border-radius: 10px;
  padding: 16px;
  background: linear-gradient(135deg, #f8fbff, #f1f6ff);
}

.hero-card.excluded {
  border-color: #f0d9b8;
  background: linear-gradient(135deg, #fffaf4, #fff5e8);
}

.hero-person {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
}

.hero-avatar {
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  border-radius: 50%;
  background: #2f5597;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
}

.hero-name {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 5px;
}

.hero-name strong {
  font-size: 17px;
  color: #1c2f4a;
}

.hero-score {
  text-align: right;
  flex: 0 0 auto;
}

.hero-score strong {
  font-size: 34px;
  color: #2f5597;
  line-height: 1;
}

.hero-score span {
  color: #8494a8;
  font-size: 13px;
}

.condition-alert {
  margin-top: 12px;
}

.dimension-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-top: 14px;
}

.dimension-card {
  border: 1px solid #eef1f7;
  border-radius: 8px;
  padding: 10px 12px;
}

.dimension-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: #4a5b72;
  margin-bottom: 7px;
}

.dimension-head b {
  color: #2f5597;
}

.dimension-card .hint {
  margin-top: 6px;
  font-size: 11px;
}

.formula-box {
  margin-top: 12px;
  background: #f7f9fd;
  border: 1px dashed #dce5f1;
  border-radius: 6px;
  padding: 9px 11px;
  font-size: 12px;
  color: #4a5b72;
}

.matched-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.grade-note {
  margin-top: 10px;
}

.reason-collapse {
  margin-top: 10px;
  border-top: none;
}

.reason-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.8;
  color: #4a5b72;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}

.table-hint {
  margin: 2px 0 10px;
}

.score-value {
  color: #2f5597;
  font-size: 14px;
}

.empty-panel {
  display: flex;
  align-items: center;
  gap: 22px;
  margin-top: 14px;
  padding: 28px;
}

.empty-mark {
  flex: 0 0 auto;
  font-size: 24px;
  font-weight: 700;
  color: #2f5597;
  background: #eef3fb;
  border-radius: 12px;
  padding: 16px 20px;
}

.drawer-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed #e6ebf3;
}

.drawer-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1c2f4a;
  margin-bottom: 4px;
}

.drawer-score {
  flex: 0 0 auto;
  color: #2f5597;
}

.drawer-score strong {
  font-size: 30px;
}

.drawer-score span {
  color: #8494a8;
  font-size: 12px;
}

.drawer-dims {
  margin: 14px 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.drawer-dim {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #4a5b72;
}

.drawer-dim > span {
  width: 104px;
  flex: 0 0 104px;
}

.drawer-dim > b {
  width: 60px;
  text-align: right;
  color: #2f5597;
}

.drawer-subtitle {
  font-size: 13px;
  color: #1c2f4a;
  margin: 16px 0 6px;
}

@media (max-width: 1100px) {
  .summary-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .dimension-grid {
    grid-template-columns: 1fr;
  }
}
</style>
