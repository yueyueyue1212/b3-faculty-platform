<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">职称申报</h2>
        <p class="page-subtitle">
          按批次配置申报要求，自动归集成果、项目、教学与获奖材料，并识别缺项、重复、信息冲突与待核验。
          系统只做材料检查，不验证成果真伪，也不替代评审专家判断。
        </p>
      </div>
      <div class="page-actions">
        <el-button v-if="auth.isEditor" type="primary" :icon="Plus" @click="openBatchCreate">新建申报批次</el-button>
      </div>
    </div>

    <div class="panel filters">
      <el-select v-model="batchId" placeholder="选择申报批次" style="width: 320px" @change="onBatchChange">
        <el-option v-for="item in batches" :key="item.id" :value="item.id"
                   :label="`${item.name}（${item.year} · ${item.title_type}）`" />
      </el-select>
      <el-button v-if="currentBatch && auth.isEditor" :icon="Edit" @click="openBatchEdit">编辑批次</el-button>
      <el-button v-if="currentBatch && auth.isEditor" type="danger" plain :icon="Delete" @click="removeBatch">删除批次</el-button>
      <el-button v-if="currentBatch && auth.isEditor" :icon="Plus" @click="openRequirementCreate">新增申报要求</el-button>
      <span v-if="currentBatch" class="hint" style="margin-left: auto">{{ currentBatch.disclaimer }}</span>
    </div>

    <template v-if="currentBatch">
      <div class="stat-grid">
        <StatCard label="申报批次" :value="currentBatch.title_type" unit=""
                  :sub="`${currentBatch.name} · ${currentBatch.year} 年`" icon="Files" />
        <StatCard label="申报要求" :value="requirements.length" unit="项"
                  :sub="`必填 ${requirements.filter(r => r.mandatory).length} 项`" icon="List" />
        <StatCard label="批次范围" :value="currentBatch.college || '全校'" unit=""
                  :sub="`截止日期 ${currentBatch.deadline || '未设置'}`" icon="OfficeBuilding" accent="info" />
        <StatCard label="批次状态" :value="batchStatusLabel(currentBatch.status)" unit=""
                  :sub="`材料记录 ${currentBatch.material_count || 0} 条`" icon="Stamp"
                  :accent="currentBatch.status === 'open' ? 'success' : 'warning'" />
      </div>

      <div class="panel">
        <div class="panel-title">
          <span>申报要求配置</span>
          <span class="hint">示例条件，可增删改；归集时按类别、时间窗口、关键词与“仅主持”条件匹配</span>
        </div>
        <el-table :data="requirements" size="small" border empty-text="尚未配置申报要求，请先新增">
          <el-table-column label="类别" width="120">
            <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
          </el-table-column>
          <el-table-column prop="name" label="要求名称" min-width="180" show-overflow-tooltip />
          <el-table-column prop="min_count" label="最低数量" width="88" />
          <el-table-column label="必填" width="70">
            <template #default="{ row }">
              <el-tag size="small" :type="row.mandatory ? 'danger' : 'info'" effect="plain">
                {{ row.mandatory ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="时间窗口" width="100">
            <template #default="{ row }">近 {{ row.window_years }} 年</template>
          </el-table-column>
          <el-table-column prop="keywords" label="限定关键词" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.keywords || '不限' }}</template>
          </el-table-column>
          <el-table-column label="仅主持" width="80">
            <template #default="{ row }">{{ row.principal_only ? '是' : '否' }}</template>
          </el-table-column>
          <el-table-column prop="requirement_desc" label="说明" min-width="180" show-overflow-tooltip />
          <el-table-column v-if="auth.isEditor" label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openRequirementEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="removeRequirement(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-tabs v-model="activeTab" class="section-gap">
        <el-tab-pane name="progress" label="教师材料进度">
          <div class="panel">
            <div class="filters" style="margin-bottom: 12px">
              <el-input v-model="teacherQuery.keyword" class="search" placeholder="教师姓名 / 编号" clearable
                        :prefix-icon="Search" @keyup.enter="searchTeachers" />
              <el-button type="primary" :icon="Search" @click="searchTeachers">查询</el-button>
              <el-button v-if="auth.isEditor" type="success" plain :icon="MagicStick"
                         :loading="gatherAllLoading" @click="gatherAll">
                归集本页教师材料
              </el-button>
              <span class="hint" style="margin-left: auto">
                归集会保留人工已确认/已驳回的材料，可重复执行
              </span>
            </div>

            <el-table :data="teachers" v-loading="teacherLoading" size="small" stripe empty-text="该批次范围内暂无教师">
              <el-table-column prop="teacher_no" label="编号" width="110" />
              <el-table-column prop="name" label="姓名" width="90" />
              <el-table-column prop="college" label="学院" min-width="130" show-overflow-tooltip />
              <el-table-column prop="title" label="职称" width="80" />
              <el-table-column label="材料进度" min-width="250">
                <template #default="{ row }">
                  <div class="status-tags">
                    <el-tag v-for="entry in statusEntries(row.material_stats)" :key="entry.key" size="small"
                            :type="entry.type" effect="plain">
                      {{ entry.label }} {{ entry.value }}
                    </el-tag>
                    <span v-if="!row.material_total" class="muted">尚未归集</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="220" fixed="right">
                <template #default="{ row }">
                  <el-button v-if="auth.isEditor" link type="primary" :loading="gatherId === row.id"
                             @click="gatherOne(row)">
                    归集
                  </el-button>
                  <el-button link type="primary" @click="openMaterials(row)">材料核验</el-button>
                  <el-button link @click="openMaterials(row, true)">汇总</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pager-row">
              <el-pagination v-model:current-page="teacherQuery.page" v-model:page-size="teacherQuery.page_size"
                             :total="teacherTotal" layout="total, prev, pager, next"
                             @current-change="loadTeachers" />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane name="materials" label="材料核验与汇总">
          <div class="panel">
            <div class="filters" style="margin-bottom: 12px">
              <el-select v-model="selectedTeacherId" filterable placeholder="选择教师查看材料" style="width: 300px"
                         @change="loadMaterials">
                <el-option v-for="item in batchTeacherOptions" :key="item.id" :value="item.id"
                           :label="`${item.name} · ${item.teacher_no} · ${item.title}`" />
              </el-select>
              <el-button v-if="selectedTeacherId" :icon="Download" @click="exportSummary">导出申报汇总</el-button>
              <span class="hint" style="margin-left: auto">
                人工确认/驳回的状态在再次归集时不会被覆盖
              </span>
            </div>

            <div v-if="!selectedTeacherId" class="empty-block">
              请选择教师，或从“教师材料进度”中点击“材料核验”
            </div>

            <template v-else-if="summary" v-loading="materialLoading">
              <div class="summary-head">
                <div>
                  <div class="summary-name">
                    {{ summary.teacher?.name }}
                    <span class="hint">{{ summary.teacher?.teacher_no }} · {{ summary.teacher?.college }} · {{ summary.teacher?.title }}</span>
                  </div>
                  <div class="hint" style="margin-top: 4px">
                    必填项完成率按“已匹配 + 待核验 + 人工确认”计算，缺项与冲突不计入。
                  </div>
                </div>
                <div class="completion">
                  <el-progress type="circle" :percentage="summary.completion" :width="86"
                               :color="summary.completion >= 80 ? '#5a9e78' : '#d9a45b'" />
                </div>
              </div>

              <div class="count-strip">
                <div v-for="(label, key) in summary.status_labels" :key="key" class="count-item"
                     :class="{ active: summary.counts[key] }">
                  <strong>{{ summary.counts[key] || 0 }}</strong>
                  <span>{{ label }}</span>
                </div>
              </div>

              <div v-if="summary.missing_mandatory.length" class="note warning" style="margin-bottom: 14px">
                <strong>必填项未达标：</strong>
                <span v-for="item in summary.missing_mandatory" :key="item.requirement_id" style="margin-right: 12px">
                  {{ item.name }}（{{ item.present }}/{{ item.min_count }}）
                </span>
              </div>

              <div class="section-title">要求达成情况</div>
              <el-table :data="summary.requirements" size="small" border>
                <el-table-column label="类别" width="120">
                  <template #default="{ row }">{{ row.category_label }}</template>
                </el-table-column>
                <el-table-column prop="name" label="要求" min-width="200" show-overflow-tooltip />
                <el-table-column prop="min_count" label="最低" width="64" />
                <el-table-column prop="present" label="有效" width="64" />
                <el-table-column prop="pending" label="待核验" width="72" />
                <el-table-column prop="duplicates" label="重复" width="64" />
                <el-table-column prop="conflicts" label="冲突" width="64" />
                <el-table-column label="满足" width="80">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.satisfied ? 'success' : 'danger'" effect="plain">
                      {{ row.satisfied ? '是' : '否' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="必填" width="64">
                  <template #default="{ row }">{{ row.mandatory ? '是' : '否' }}</template>
                </el-table-column>
              </el-table>

              <div class="section-title" style="margin-top: 18px">材料明细</div>
              <el-table :data="materials" size="small" stripe empty-text="暂无材料，请先归集" max-height="420">
                <el-table-column label="类别" width="120">
                  <template #default="{ row }">{{ row.category_label }}</template>
                </el-table-column>
                <el-table-column prop="title" label="材料名称" min-width="260" show-overflow-tooltip />
                <el-table-column prop="requirement_name" label="对应要求" min-width="150" show-overflow-tooltip />
                <el-table-column label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag size="small" :type="materialStatusType(row.status)" effect="light">
                      {{ row.status_label || row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="note" label="备注" min-width="180" show-overflow-tooltip />
                <el-table-column v-if="auth.isEditor" label="操作" width="80" fixed="right">
                  <template #default="{ row }">
                    <el-button link type="primary" @click="openMaterial(row)">处理</el-button>
                  </template>
                </el-table-column>
              </el-table>

              <p class="note" style="margin-top: 12px">{{ summary.disclaimer }}</p>
            </template>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>

    <div v-else-if="!loading" class="panel empty-block">
      暂无申报批次。请点击右上角“新建申报批次”，或运行种子脚本生成演示批次。
    </div>

    <!-- 批次表单 -->
    <el-dialog v-model="batchFormVisible" :title="batchEditingId ? '编辑申报批次' : '新建申报批次'" width="560px"
               :close-on-click-modal="false" destroy-on-close>
      <el-form ref="batchFormRef" :model="batchForm" :rules="batchRules" label-width="96px">
        <el-form-item label="批次名称" prop="name"><el-input v-model="batchForm.name" /></el-form-item>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="年份" prop="year">
              <el-input-number v-model="batchForm.year" :min="2000" :max="2100" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="职称类型" prop="title_type"><el-input v-model="batchForm.title_type" placeholder="如 副教授" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="限定学院">
          <el-select v-model="batchForm.college" clearable filterable allow-create default-first-option
                     placeholder="留空表示全校" style="width: 100%">
            <el-option v-for="item in collegeOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="截止日期">
              <el-date-picker v-model="batchForm.deadline" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="batchForm.status" style="width: 100%">
                <el-option label="草稿" value="draft" />
                <el-option label="开放申报" value="open" />
                <el-option label="已完成" value="completed" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="batchFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchSaving" @click="submitBatch">保存</el-button>
      </template>
    </el-dialog>

    <!-- 申报要求表单 -->
    <el-dialog v-model="requirementFormVisible" :title="requirementEditingId ? '编辑申报要求' : '新增申报要求'"
               width="600px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="requirementFormRef" :model="requirementForm" :rules="requirementRules" label-width="100px">
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="类别" prop="category">
              <el-select v-model="requirementForm.category" style="width: 100%">
                <el-option v-for="item in categories" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最低数量" prop="min_count">
              <el-input-number v-model="requirementForm.min_count" :min="1" :max="100" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="要求名称" prop="name"><el-input v-model="requirementForm.name" /></el-form-item>
        <el-form-item label="条件说明">
          <el-input v-model="requirementForm.requirement_desc" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="限定关键词">
          <el-input v-model="requirementForm.keywords" placeholder="匹配材料标题中的关键词，多个用逗号分隔；留空为不限" />
        </el-form-item>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="时间窗口">
              <el-input-number v-model="requirementForm.window_years" :min="1" :max="30" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="仅主持项目">
              <el-switch v-model="requirementForm.principal_only" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="是否必填">
          <el-switch v-model="requirementForm.mandatory" active-text="必填" inactive-text="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="requirementFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="requirementSaving" @click="submitRequirement">保存</el-button>
      </template>
    </el-dialog>

    <!-- 材料处理 -->
    <el-dialog v-model="materialFormVisible" title="处理申报材料" width="520px" :close-on-click-modal="false">
      <div v-if="materialTarget" class="material-target">
        <div class="hint">{{ materialTarget.category_label }} · 当前状态 {{ materialTarget.status_label }}</div>
        <div class="material-title">{{ materialTarget.title }}</div>
      </div>
      <el-form label-width="90px">
        <el-form-item label="处理状态">
          <el-select v-model="materialForm.status" style="width: 100%">
            <el-option v-for="item in statuses" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="materialForm.note" type="textarea" :rows="3"
                    placeholder="如：已核对原文；或与申报要求不符，人工驳回" />
        </el-form-item>
      </el-form>
      <p class="hint">
        人工确认（confirmed）与人工驳回（rejected）会在再次归集时被保留；其他状态可能被系统重新计算。
      </p>
      <template #footer>
        <el-button @click="materialFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="materialSaving" @click="submitMaterial">保存处理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Download, Edit, MagicStick, Plus, Search } from '@element-plus/icons-vue'
import api, { downloadFile } from '../api/client'
import StatCard from '../components/StatCard.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const batches = ref<any[]>([])
const batchId = ref<number | null>(null)
const currentBatch = ref<any>(null)
const requirements = ref<any[]>([])
const categories = ref<Array<{ value: string; label: string }>>([])
const statuses = ref<Array<{ value: string; label: string }>>([])
const collegeOptions = ref<string[]>([])
const activeTab = ref('progress')

const teachers = ref<any[]>([])
const batchTeacherOptions = ref<any[]>([])
const teacherTotal = ref(0)
const teacherLoading = ref(false)
const gatherId = ref<number | null>(null)
const gatherAllLoading = ref(false)
const teacherQuery = reactive({ keyword: '', page: 1, page_size: 10 })

const selectedTeacherId = ref<number | null>(null)
const summary = ref<any>(null)
const materials = ref<any[]>([])
const materialLoading = ref(false)

const batchFormVisible = ref(false)
const batchEditingId = ref<number | null>(null)
const batchSaving = ref(false)
const batchFormRef = ref()
const defaultBatch = () => ({
  name: '', year: new Date().getFullYear(), title_type: '副教授',
  college: '', deadline: '', status: 'draft',
})
const batchForm = reactive<any>(defaultBatch())
const batchRules = {
  name: [{ required: true, message: '请输入批次名称', trigger: 'blur' }],
  year: [{ required: true, message: '请输入年份', trigger: 'change' }],
  title_type: [{ required: true, message: '请输入职称类型', trigger: 'blur' }],
}

const requirementFormVisible = ref(false)
const requirementEditingId = ref<number | null>(null)
const requirementSaving = ref(false)
const requirementFormRef = ref()
const defaultRequirement = () => ({
  category: 'paper', name: '', requirement_desc: '', min_count: 1, mandatory: true,
  keywords: '', window_years: 5, principal_only: false,
})
const requirementForm = reactive<any>(defaultRequirement())
const requirementRules = {
  category: [{ required: true, message: '请选择类别', trigger: 'change' }],
  name: [{ required: true, message: '请输入要求名称', trigger: 'blur' }],
  min_count: [{ required: true, message: '请输入最低数量', trigger: 'change' }],
}

const materialFormVisible = ref(false)
const materialSaving = ref(false)
const materialTarget = ref<any>(null)
const materialForm = reactive({ status: 'confirmed', note: '' })

const currentTeacher = computed(() => summary.value?.teacher)

function categoryLabel(value: string) {
  return categories.value.find((item) => item.value === value)?.label || value
}

function batchStatusLabel(status: string) {
  return { draft: '草稿', open: '开放申报', completed: '已完成' }[status] || status
}

function materialStatusType(status: string) {
  return {
    matched: 'success', confirmed: 'success', pending_verification: 'warning',
    missing: 'danger', duplicate: 'warning', conflict: 'danger', rejected: 'info',
  }[status] || 'info'
}

function statusEntries(stats: Record<string, number>) {
  const typeMap: Record<string, string> = {
    matched: 'success', pending_verification: 'warning', missing: 'danger',
    duplicate: 'warning', conflict: 'danger', confirmed: 'success', rejected: 'info',
  }
  return Object.entries(stats || {}).map(([key, value]) => ({
    key,
    value,
    label: statuses.value.find((s) => s.value === key)?.label || key,
    type: typeMap[key] || 'info',
  }))
}

async function loadBatches() {
  loading.value = true
  try {
    const [batchRes, teacherOptRes] = await Promise.all([
      api.get('/promotion/batches'),
      api.get('/teachers/options'),
    ])
    batches.value = batchRes.data.items
    categories.value = batchRes.data.categories
    statuses.value = batchRes.data.material_statuses
    collegeOptions.value = teacherOptRes.data.colleges
    if (!batchId.value && batches.value.length) {
      batchId.value = batches.value[0].id
    }
    if (batchId.value) await loadBatchDetail()
  } finally {
    loading.value = false
  }
}

async function loadBatchDetail() {
  if (!batchId.value) return
  const { data } = await api.get(`/promotion/batches/${batchId.value}`)
  currentBatch.value = data
  requirements.value = data.requirements || []
  const listItem = batches.value.find((item) => item.id === batchId.value)
  currentBatch.value.material_count = listItem?.material_count || 0
}

async function onBatchChange() {
  selectedTeacherId.value = null
  summary.value = null
  materials.value = []
  teacherQuery.keyword = ''
  teacherQuery.page = 1
  await loadBatchDetail()
  await loadTeachers()
}

async function loadTeachers() {
  if (!batchId.value) return
  teacherLoading.value = true
  try {
    const params: any = { page: teacherQuery.page, page_size: teacherQuery.page_size }
    if (teacherQuery.keyword) params.keyword = teacherQuery.keyword
    const [{ data }, optionsRes] = await Promise.all([
      api.get(`/promotion/batches/${batchId.value}/teachers`, { params }),
      api.get(`/promotion/batches/${batchId.value}/teachers`, { params: { page: 1, page_size: 100 } }),
    ])
    teachers.value = data.items
    teacherTotal.value = data.total
    batchTeacherOptions.value = optionsRes.data.items
  } finally {
    teacherLoading.value = false
  }
}

function searchTeachers() {
  teacherQuery.page = 1
  loadTeachers()
}

async function gatherOne(row: any) {
  if (!batchId.value) return
  gatherId.value = row.id
  try {
    const { data } = await api.post(`/promotion/batches/${batchId.value}/gather`, { teacher_id: row.id })
    const result = data.results?.[0]
    if (result?.error) {
      ElMessage.error(result.error)
    } else {
      ElMessage.success(`已归集 ${result?.created ?? 0} 条材料，完成率 ${result?.completion ?? 0}%`)
    }
    await Promise.all([loadTeachers(), loadBatchDetail()])
    if (selectedTeacherId.value === row.id) await loadMaterials()
  } finally {
    gatherId.value = null
  }
}

async function gatherAll() {
  if (!batchId.value || !teachers.value.length) return
  gatherAllLoading.value = true
  try {
    const ids = teachers.value.map((row) => row.id)
    const { data } = await api.post(`/promotion/batches/${batchId.value}/gather`, { teacher_ids: ids })
    const created = data.results.reduce((sum: number, item: any) => sum + (item.created || 0), 0)
    ElMessage.success(`本页 ${ids.length} 位教师归集完成，共生成 ${created} 条材料`)
    await Promise.all([loadTeachers(), loadBatchDetail()])
    if (selectedTeacherId.value) await loadMaterials()
  } finally {
    gatherAllLoading.value = false
  }
}

async function openMaterials(row: any, summaryOnly = false) {
  activeTab.value = 'materials'
  selectedTeacherId.value = row.id
  await loadMaterials()
}

async function loadMaterials() {
  if (!batchId.value || !selectedTeacherId.value) return
  materialLoading.value = true
  try {
    const [summaryRes, materialsRes] = await Promise.all([
      api.get(`/promotion/batches/${batchId.value}/summary`, { params: { teacher_id: selectedTeacherId.value } }),
      api.get('/promotion/materials', {
        params: { batch_id: batchId.value, teacher_id: selectedTeacherId.value, page_size: 200 },
      }),
    ])
    summary.value = summaryRes.data
    materials.value = materialsRes.data.items
  } finally {
    materialLoading.value = false
  }
}

function openMaterial(row: any) {
  materialTarget.value = row
  materialForm.status = row.status === 'missing' || row.status === 'conflict' ? 'confirmed' : row.status
  materialForm.note = row.note || ''
  materialFormVisible.value = true
}

async function submitMaterial() {
  if (!materialTarget.value) return
  materialSaving.value = true
  try {
    await api.put(`/promotion/materials/${materialTarget.value.id}`, {
      status: materialForm.status,
      note: materialForm.note || null,
    })
    ElMessage.success('材料处理已保存')
    materialFormVisible.value = false
    await Promise.all([loadMaterials(), loadTeachers()])
  } finally {
    materialSaving.value = false
  }
}

async function exportSummary() {
  if (!batchId.value || !selectedTeacherId.value) return
  await downloadFile(`/promotion/batches/${batchId.value}/export`, '职称申报材料汇总.xlsx', {
    teacher_id: selectedTeacherId.value,
  })
  ElMessage.success('申报材料汇总已导出')
}

function openBatchCreate() {
  batchEditingId.value = null
  Object.assign(batchForm, defaultBatch())
  batchFormVisible.value = true
}

function openBatchEdit() {
  if (!currentBatch.value) return
  batchEditingId.value = currentBatch.value.id
  Object.assign(batchForm, defaultBatch(), {
    name: currentBatch.value.name,
    year: currentBatch.value.year,
    title_type: currentBatch.value.title_type,
    college: currentBatch.value.college || '',
    deadline: currentBatch.value.deadline || '',
    status: currentBatch.value.status,
  })
  batchFormVisible.value = true
}

async function submitBatch() {
  await batchFormRef.value?.validate()
  batchSaving.value = true
  try {
    const payload = { ...batchForm, college: batchForm.college || null, deadline: batchForm.deadline || null }
    if (batchEditingId.value) {
      await api.put(`/promotion/batches/${batchEditingId.value}`, payload)
      ElMessage.success('批次已更新')
    } else {
      const { data } = await api.post('/promotion/batches', payload)
      batchId.value = data.id
      ElMessage.success('批次已创建')
    }
    batchFormVisible.value = false
    await loadBatches()
    await Promise.all([loadBatchDetail(), loadTeachers()])
  } finally {
    batchSaving.value = false
  }
}

async function removeBatch() {
  if (!currentBatch.value || !batchId.value) return
  try {
    await ElMessageBox.confirm(
      `确认删除批次“${currentBatch.value.name}”及其申报要求与材料记录吗？此操作不可撤销。`,
      '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await api.delete(`/promotion/batches/${batchId.value}`)
  ElMessage.success('批次已删除')
  batchId.value = null
  currentBatch.value = null
  summary.value = null
  await loadBatches()
}

function openRequirementCreate() {
  requirementEditingId.value = null
  Object.assign(requirementForm, defaultRequirement())
  requirementFormVisible.value = true
}

function openRequirementEdit(row: any) {
  requirementEditingId.value = row.id
  Object.assign(requirementForm, defaultRequirement(), row)
  requirementFormVisible.value = true
}

async function submitRequirement() {
  await requirementFormRef.value?.validate()
  if (!batchId.value) return
  requirementSaving.value = true
  try {
    const payload = { ...requirementForm }
    if (requirementEditingId.value) {
      await api.put(`/promotion/requirements/${requirementEditingId.value}`, payload)
      ElMessage.success('申报要求已更新')
    } else {
      await api.post(`/promotion/batches/${batchId.value}/requirements`, payload)
      ElMessage.success('申报要求已新增')
    }
    requirementFormVisible.value = false
    await Promise.all([loadBatchDetail(), loadBatches()])
  } finally {
    requirementSaving.value = false
  }
}

async function removeRequirement(row: any) {
  try {
    await ElMessageBox.confirm(
      `确认删除申报要求“${row.name}”吗？关联的材料记录也会被删除，需重新归集。`,
      '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await api.delete(`/promotion/requirements/${row.id}`)
  ElMessage.success('申报要求已删除')
  await Promise.all([loadBatchDetail(), loadBatches()])
  if (selectedTeacherId.value) await loadMaterials()
}

onMounted(async () => {
  await loadBatches()
  if (batchId.value) await loadTeachers()
})
</script>

<style scoped>
.pager-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.status-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px dashed #e6ebf3;
}

.summary-name {
  font-size: 17px;
  font-weight: 600;
  color: #1c2f4a;
}

.count-strip {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
  margin: 14px 0;
}

.count-item {
  background: #f8fafd;
  border: 1px solid #eef1f7;
  border-radius: 6px;
  padding: 10px 6px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.count-item strong {
  font-size: 18px;
  color: #7a8797;
}

.count-item span {
  font-size: 11px;
  color: #8494a8;
}

.count-item.active strong {
  color: #2f5597;
}

.material-target {
  background: #f7f9fd;
  border: 1px solid #eef1f7;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 14px;
}

.material-title {
  font-size: 14px;
  font-weight: 600;
  margin-top: 4px;
  color: #23364e;
}
</style>
