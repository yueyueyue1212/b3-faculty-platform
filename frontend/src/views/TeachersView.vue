<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">教师档案</h2>
        <p class="page-subtitle">
          教师基础档案、研究方向与导师资格管理。删除前会检查成果、项目与教学记录关联，避免产生孤立数据。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Download" @click="exportVisible = true">导出说明</el-button>
        <el-button v-if="auth.isEditor" type="primary" :icon="Plus" @click="openCreate">新增教师</el-button>
      </div>
    </div>

    <div class="panel filters">
      <el-input v-model="query.keyword" class="search" placeholder="姓名 / 编号 / 研究方向 / 关键词" clearable
                :prefix-icon="Search" @keyup.enter="search" />
      <el-select v-model="query.college" placeholder="学院" clearable @change="onFilterCollegeChange">
        <el-option v-for="item in options.colleges" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="query.discipline" :placeholder="query.college ? '学科' : '请先选择学院'"
                 :disabled="!query.college" clearable filterable>
        <el-option v-for="item in filterDisciplines" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="query.title" placeholder="职称" clearable>
        <el-option v-for="item in options.titles" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="query.status" placeholder="状态" clearable>
        <el-option label="在职" value="active" />
        <el-option label="休假/进修" value="on_leave" />
        <el-option label="退休" value="retired" />
      </el-select>
      <el-select v-model="query.advisor_qualified" placeholder="导师资格" clearable>
        <el-option label="具有导师资格" :value="true" />
        <el-option label="无导师资格" :value="false" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="search">查询</el-button>
      <el-button :icon="RefreshLeft" @click="reset">重置</el-button>
    </div>

    <div class="panel" v-loading="loading">
      <div class="panel-title">
        <span>教师列表 <span class="muted" style="font-weight: 400">共 {{ total }} 人</span></span>
        <span class="hint">只读用户查看时联系方式自动脱敏</span>
      </div>

      <el-table :data="rows" stripe style="width: 100%" @sort-change="onSortChange" empty-text="暂无教师数据">
        <el-table-column prop="teacher_no" label="教师编号" width="112" sortable="custom" />
        <el-table-column prop="name" label="姓名" width="100" sortable="custom">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="openDetail(row)">{{ row.name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="college" label="学院" min-width="130" sortable="custom" show-overflow-tooltip />
        <el-table-column prop="discipline" label="学科" min-width="150" show-overflow-tooltip />
        <el-table-column prop="title" label="职称" width="90" sortable="custom">
          <template #default="{ row }">
            <el-tag size="small" :type="titleTagType(row.title)" effect="plain">{{ row.title }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="degree" label="学历" width="80">
          <template #default="{ row }">{{ row.degree || '—' }}</template>
        </el-table-column>
        <el-table-column label="导师 / 招生" min-width="150">
          <template #default="{ row }">
            <template v-if="row.advisor_qualified">
              <el-tag size="small" type="success" effect="plain">导师</el-tag>
              <el-tag size="small" :type="row.enrollment_status === 'open' ? 'success' : 'info'" effect="plain">
                {{ row.enrollment_label }}
              </el-tag>
              <span class="hint"> {{ row.current_students }}/{{ row.capacity }}</span>
            </template>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="96">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'" effect="light">
              {{ row.status_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="联系方式" min-width="150">
          <template #default="{ row }">
            <div class="contact-line">{{ row.phone || '—' }}</div>
            <div class="contact-line muted">{{ row.email || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="196" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/teachers/${row.id}/profile`)">画像</el-button>
            <el-button link @click="openDetail(row)">详情</el-button>
            <el-button v-if="auth.isEditor" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="auth.isEditor" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager-row">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="load"
          @current-change="load"
        />
      </div>
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="formVisible" :title="editingId ? '编辑教师档案' : '新增教师档案'" width="820px"
               :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <div class="form-section">基本信息</div>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="教师编号" prop="teacher_no">
              <el-input v-model="form.teacher_no" placeholder="如 B3T0101" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="姓名" prop="name"><el-input v-model="form.name" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="性别">
              <el-select v-model="form.gender" clearable style="width: 100%">
                <el-option label="男" value="男" /><el-option label="女" value="女" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="出生年份">
              <el-input-number v-model="form.birth_year" :min="1900" :max="2010" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="学院" prop="college">
              <el-select v-model="form.college" filterable allow-create default-first-option
                         style="width: 100%" @change="onFormCollegeChange">
                <el-option v-for="item in options.colleges" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="院系"><el-input v-model="form.department" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="学科" prop="discipline">
              <el-select v-model="form.discipline" filterable allow-create default-first-option
                         :disabled="!form.college" :placeholder="form.college ? '请选择学科' : '请先选择学院'"
                         style="width: 100%">
                <el-option v-for="item in formDisciplines" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="学历">
              <el-select v-model="form.degree" clearable style="width: 100%">
                <el-option v-for="item in ['博士', '硕士', '学士', '其他']" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="职称" prop="title">
              <el-select v-model="form.title" style="width: 100%">
                <el-option v-for="item in ['教授', '副教授', '讲师', '助教']" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="职务"><el-input v-model="form.position" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="入职时间">
              <el-date-picker v-model="form.hire_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option label="在职" value="active" />
                <el-option label="休假/进修" value="on_leave" />
                <el-option label="退休" value="retired" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="联系电话">
              <el-input v-model="form.phone" />
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="邮箱" prop="email"><el-input v-model="form.email" /></el-form-item>
          </el-col>
        </el-row>

        <div class="form-section">研究方向与画像</div>
        <el-form-item label="研究方向">
          <el-input v-model="form.research_direction" placeholder="如：机器学习与数据挖掘" />
        </el-form-item>
        <el-form-item label="研究关键词">
          <el-input v-model="form.research_keywords" placeholder="用顿号或逗号分隔，匹配算法会使用" />
        </el-form-item>
        <el-form-item label="专业技能"><el-input v-model="form.skills" /></el-form-item>
        <el-form-item label="个人简介">
          <el-input v-model="form.bio" type="textarea" :rows="3" />
        </el-form-item>

        <div class="form-section">导师资格</div>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="导师资格">
              <el-switch v-model="form.advisor_qualified" active-text="具有" inactive-text="无" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="招生状态">
              <el-select v-model="form.enrollment_status" style="width: 100%">
                <el-option label="开放招生" value="open" />
                <el-option label="已满" value="full" />
                <el-option label="未开放" value="closed" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="容量">
              <el-input-number v-model="form.capacity" :min="0" :max="100" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="在读">
              <el-input-number v-model="form.current_students" :min="0" :max="100" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="数据来源">
          <el-input v-model="form.data_source" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-drawer v-model="detailVisible" title="教师档案详情" size="560px">
      <template v-if="detail">
        <div class="detail-head">
          <div class="detail-avatar">{{ detail.name?.slice(0, 1) }}</div>
          <div>
            <div class="detail-name">{{ detail.name }} <span class="muted">{{ detail.teacher_no }}</span></div>
            <div class="hint">{{ detail.college }} · {{ detail.discipline }} · {{ detail.title }}</div>
            <div class="tag-list" style="margin-top: 8px">
              <el-tag size="small" :type="detail.status === 'active' ? 'success' : 'info'">{{ detail.status_label }}</el-tag>
              <el-tag v-if="detail.advisor_qualified" size="small" type="success" effect="plain">导师资格</el-tag>
              <el-tag v-if="detail.verification_status !== 'verified'" size="small" type="warning" effect="plain">待核验</el-tag>
            </div>
          </div>
        </div>

        <el-descriptions :column="1" border size="small" class="section-gap">
          <el-descriptions-item label="研究方向">{{ detail.research_direction || '—' }}</el-descriptions-item>
          <el-descriptions-item label="研究关键词">{{ detail.research_keywords || '—' }}</el-descriptions-item>
          <el-descriptions-item label="专业技能">{{ detail.skills || '—' }}</el-descriptions-item>
          <el-descriptions-item label="个人简介">{{ detail.bio || '—' }}</el-descriptions-item>
          <el-descriptions-item label="入职时间">{{ detail.hire_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="职务">{{ detail.position || '—' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ detail.phone || '—' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ detail.email || '—' }}</el-descriptions-item>
          <el-descriptions-item label="导师容量">
            {{ detail.advisor_qualified ? `${detail.current_students}/${detail.capacity}（${detail.enrollment_label}）` : '无导师资格' }}
          </el-descriptions-item>
          <el-descriptions-item label="数据来源">{{ detail.data_source }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatTime(detail.updated_at) }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-counts" v-if="detail.counts">
          <div><strong>{{ detail.counts.outputs }}</strong><span>科研成果</span></div>
          <div><strong>{{ detail.counts.projects }}</strong><span>主持项目</span></div>
          <div><strong>{{ detail.counts.teaching }}</strong><span>教学记录</span></div>
          <div><strong>{{ detail.counts.services }}</strong><span>社会服务</span></div>
        </div>

        <div class="page-actions" style="justify-content: flex-start; margin-top: 18px">
          <el-button type="primary" @click="$router.push(`/teachers/${detail.id}/profile`); detailVisible = false">
            查看多维画像
          </el-button>
          <el-button v-if="auth.isEditor" @click="openEdit(detail); detailVisible = false">编辑档案</el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="exportVisible" title="关于导出" width="460px">
      <p class="pre-wrap">
        教师档案列表暂不提供原始 Excel 导出，以避免批量泄露联系方式等敏感信息。
        可按当前筛选条件点击列表中的“画像”查看单个人物的统计详情，或在“人才盘点”中导出聚合层面的报告。
      </p>
      <template #footer><el-button type="primary" @click="exportVisible = false">知道了</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Plus, RefreshLeft, Search } from '@element-plus/icons-vue'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import { disciplinesForCollege, type CollegeDisciplineMap } from '../utils/linkage'

const auth = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const options = reactive({
  colleges: [] as string[],
  disciplines: [] as string[],
  disciplinesByCollege: {} as CollegeDisciplineMap,
  titles: [] as string[],
})
const query = reactive({
  keyword: '',
  college: '',
  discipline: '',
  title: '',
  status: '',
  advisor_qualified: null as boolean | null,
  page: 1,
  page_size: 10,
  sort_by: 'teacher_no',
  sort_order: 'asc',
})
const filterDisciplines = computed(() =>
  disciplinesForCollege(options.disciplinesByCollege, query.college, query.discipline),
)

const formVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const defaultForm = () => ({
  teacher_no: '', name: '', gender: '', birth_year: null as number | null,
  college: '', department: '', discipline: '', degree: '', title: '讲师', position: '',
  hire_date: '', research_direction: '', bio: '', skills: '', research_keywords: '',
  status: 'active', advisor_qualified: false, enrollment_status: 'closed',
  capacity: 0, current_students: 0, phone: '', email: '',
  data_source: '手动录入', verification_status: 'verified',
})
const form = reactive<any>(defaultForm())
const formDisciplines = computed(() =>
  disciplinesForCollege(options.disciplinesByCollege, form.college, form.discipline),
)
const formRules = {
  teacher_no: [{ required: true, message: '请输入教师编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  college: [{ required: true, message: '请选择学院', trigger: 'change' }],
  discipline: [{ required: true, message: '请选择学科', trigger: 'change' }],
  title: [{ required: true, message: '请选择职称', trigger: 'change' }],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
}

const detailVisible = ref(false)
const detail = ref<any>(null)
const exportVisible = ref(false)

function titleTagType(title: string) {
  return title === '教授' ? 'danger' : title === '副教授' ? 'warning' : title === '讲师' ? '' : 'info'
}

function formatTime(value: string | null) {
  if (!value) return '—'
  return value.replace('T', ' ').slice(0, 19)
}

async function load() {
  loading.value = true
  try {
    const params: any = { ...query }
    if (params.advisor_qualified === null || params.advisor_qualified === '') delete params.advisor_qualified
    if (!params.keyword) delete params.keyword
    if (!params.status) delete params.status
    const { data } = await api.get('/teachers', { params })
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadOptions() {
  const { data } = await api.get('/teachers/options')
  options.colleges = data.colleges
  options.disciplines = data.disciplines
  options.disciplinesByCollege = data.disciplines_by_college || {}
  options.titles = data.titles
}

function onFilterCollegeChange() {
  query.discipline = ''
}

function onFormCollegeChange() {
  form.discipline = ''
}

function search() {
  query.page = 1
  load()
}

function reset() {
  Object.assign(query, {
    keyword: '', college: '', discipline: '', title: '', status: '',
    advisor_qualified: null, page: 1, page_size: 10, sort_by: 'teacher_no', sort_order: 'asc',
  })
  load()
}

function onSortChange({ prop, order }: { prop: string; order: string | null }) {
  query.sort_by = prop || 'teacher_no'
  query.sort_order = order === 'descending' ? 'desc' : 'asc'
  load()
}

function openCreate() {
  editingId.value = null
  Object.assign(form, defaultForm())
  formVisible.value = true
}

async function openEdit(row: any) {
  editingId.value = row.id
  const { data } = await api.get(`/teachers/${row.id}`)
  Object.assign(form, defaultForm(), {
    ...data,
    hire_date: data.hire_date || '',
    birth_year: data.birth_year || null,
  })
  formVisible.value = true
}

async function openDetail(row: any) {
  const { data } = await api.get(`/teachers/${row.id}`)
  detail.value = data
  detailVisible.value = true
}

async function submitForm() {
  await formRef.value?.validate()
  if (form.capacity < form.current_students) {
    ElMessage.warning('指导容量不能小于当前在读人数')
    return
  }
  saving.value = true
  try {
    const payload = { ...form, hire_date: form.hire_date || null, birth_year: form.birth_year || null }
    if (editingId.value) {
      await api.put(`/teachers/${editingId.value}`, payload)
      ElMessage.success('教师档案已更新')
    } else {
      await api.post('/teachers', payload)
      ElMessage.success('教师档案已创建')
    }
    formVisible.value = false
    await Promise.all([load(), loadOptions()])
  } finally {
    saving.value = false
  }
}

async function remove(row: any) {
  try {
    await ElMessageBox.confirm(
      `确认删除教师“${row.name}（${row.teacher_no}）”吗？若存在关联成果或项目，系统将拒绝删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await api.delete(`/teachers/${row.id}`)
    ElMessage.success('教师已删除')
    if (rows.value.length === 1 && query.page > 1) query.page -= 1
    await load()
  } catch {
    /* 错误提示由拦截器展示（如 409 关联记录） */
  }
}

onMounted(async () => {
  await loadOptions()
  await load()
})
</script>

<style scoped>
.contact-line {
  font-size: 12px;
  line-height: 1.6;
}

.pager-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.form-section {
  font-size: 13px;
  font-weight: 600;
  color: #2f5597;
  border-left: 3px solid #2f5597;
  padding-left: 8px;
  margin: 6px 0 16px;
}

.detail-head {
  display: flex;
  gap: 14px;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #eef1f6;
}

.detail-avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4d7ac9, #2f5597);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
}

.detail-name {
  font-size: 18px;
  font-weight: 600;
}

.detail-counts {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-top: 18px;
}

.detail-counts div {
  background: #f7f9fd;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-counts strong {
  font-size: 20px;
  color: #2f5597;
}

.detail-counts span {
  font-size: 11px;
  color: #7a8797;
}
</style>
