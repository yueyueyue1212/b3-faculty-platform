<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <div>
        <h2 class="page-title">人才驾驶舱</h2>
        <p class="page-subtitle">
          学院人才结构、科研教学产出与数据质量实时概览。所有数字均由数据库查询计算，筛选条件同时作用于教师及其关联记录。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" @click="load('全部刷新')">刷新</el-button>
        <el-button type="primary" plain :icon="PieChart" @click="$router.push('/talent')">人才盘点</el-button>
      </div>
    </div>

    <div class="panel filters">
      <el-select v-model="filters.college" placeholder="全部学院" clearable @change="onCollegeChange">
        <el-option v-for="item in options.colleges" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.discipline" :placeholder="filters.college ? '全部学科' : '请先选择学院'"
                 :disabled="!filters.college" clearable @change="load">
        <el-option v-for="item in disciplineOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.title" placeholder="全部职称" clearable @change="load">
        <el-option v-for="item in options.titles" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.year_from" placeholder="起始年份" clearable @change="load">
        <el-option v-for="year in options.years" :key="year" :label="`${year} 年起`" :value="year" />
      </el-select>
      <el-select v-model="filters.year_to" placeholder="截止年份" clearable @change="load">
        <el-option v-for="year in options.years" :key="year" :label="`截至 ${year}`" :value="year" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="load">查询</el-button>
      <el-button :icon="RefreshLeft" @click="resetFilters">重置</el-button>
      <span class="hint" style="margin-left: auto">当前范围：{{ scopeLabel }}</span>
    </div>

    <template v-if="data">
      <div class="stat-grid">
        <StatCard label="教师总人数" :value="data.total_teachers" unit="人"
                  :sub="`在职 ${data.active_teachers} 人 · 导师资格 ${data.advisor_qualified_count} 人`" icon="User" />
        <StatCard label="科研成果" :value="data.output_total" unit="项"
                  :sub="`统计区间内成果记录 · 来源：科研成果表`" icon="Document" />
        <StatCard label="科研项目" :value="data.project_total" unit="项"
                  :sub="`主持 ${data.principal_project_total} 项 · 经费合计 ${formatMoney(data.project_funding_total)} 万元`"
                  icon="Files" accent="success" />
        <StatCard label="教学工作量" :value="data.teaching_hours_total" unit="学时"
                  :sub="`教学成果 ${data.teaching_achievement_count} 项 · 平均评价 ${data.avg_evaluation_score ?? '无数据'}`"
                  icon="Reading" />
        <StatCard label="社会服务" :value="data.service_total" unit="条"
                  :sub="`获奖 / 学术任职 / 社会服务记录`" icon="Medal" accent="warning" />
        <StatCard label="数据待核验" :value="data.data_quality.pending_verification_count" unit="人"
                  :sub="`疑似重复成果 ${data.data_quality.duplicate_output_count} 组 · 无成果教师 ${data.data_quality.teachers_without_outputs} 人`"
                  icon="Warning" accent="danger" />
      </div>

      <div class="chart-grid">
        <div class="chart-box">
          <div class="chart-head">
            <strong>科研成果年度趋势</strong>
            <span>按 publish_date 年份统计</span>
          </div>
          <BaseChart :option="outputTrendOption" height="300px" />
        </div>
        <div class="chart-box">
          <div class="chart-head">
            <strong>学院人才分布</strong>
            <span>教师人数</span>
          </div>
          <BaseChart :option="collegeOption" height="300px" />
        </div>
      </div>

      <div class="chart-grid three">
        <div class="chart-box">
          <div class="chart-head">
            <strong>职称结构</strong>
            <span>按档案职称</span>
          </div>
          <BaseChart :option="titleOption" height="280px" />
        </div>
        <div class="chart-box">
          <div class="chart-head">
            <strong>成果类型</strong>
            <span>区间内记录</span>
          </div>
          <BaseChart :option="outputTypeOption" height="280px" />
        </div>
        <div class="chart-box">
          <div class="chart-head">
            <strong>学历结构</strong>
            <span>含“未填写”</span>
          </div>
          <BaseChart :option="degreeOption" height="280px" />
        </div>
      </div>

      <div class="chart-grid">
        <div class="chart-box">
          <div class="chart-head">
            <strong>项目年度分布</strong>
            <span>按项目开始时间</span>
          </div>
          <BaseChart :option="projectTrendOption" height="290px" />
        </div>
        <div class="chart-box">
          <div class="chart-head">
            <strong>教学工作量年度分布</strong>
            <span>按学年累计学时</span>
          </div>
          <BaseChart :option="teachingTrendOption" height="290px" />
        </div>
      </div>

      <div class="two-col">
        <div class="chart-box">
          <div class="chart-head">
            <strong>年龄梯队分布</strong>
            <span>数据合规提示</span>
          </div>
          <BaseChart :option="ageOption" height="270px" />
          <p class="hint" style="margin: 0 0 10px">{{ data.age_note }}</p>
        </div>

        <div class="panel">
          <div class="panel-title">
            <span>研究方向关键词</span>
            <span class="hint">教师档案关键词词频</span>
          </div>
          <div v-if="data.top_keywords.length" class="tag-list">
            <el-tag v-for="item in data.top_keywords" :key="item.name" size="large" effect="plain" round>
              {{ item.name }} <span class="muted">{{ item.value }}</span>
            </el-tag>
          </div>
          <div v-else class="empty-block">暂无关键词数据</div>

          <div class="divider-title">数据质量</div>
          <div class="quality-list">
            <div v-for="item in qualityItems" :key="item.label" class="quality-item">
              <span>{{ item.label }}</span>
              <strong :class="item.className">{{ item.value }}</strong>
            </div>
          </div>
          <div class="page-actions" style="justify-content: flex-start; margin-top: 14px">
            <el-button size="small" :icon="UploadFilled" @click="$router.push('/data')">数据管理</el-button>
            <el-button size="small" :icon="Histogram" @click="$router.push('/talent')">查看盘点报告</el-button>
          </div>
        </div>
      </div>

      <div class="note section-gap">{{ data.stats_scope }} 数据来源：模拟数据以“模拟数据（B3演示）”标记。</div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Histogram, PieChart, Refresh, RefreshLeft, Search, UploadFilled } from '@element-plus/icons-vue'
import api from '../api/client'
import StatCard from '../components/StatCard.vue'
import BaseChart from '../components/BaseChart.vue'
import { barOption, lineOption, pieOption, palette } from '../utils/charts'
import { disciplinesForCollege, type CollegeDisciplineMap } from '../utils/linkage'

const loading = ref(false)
const data = ref<any>(null)
const options = reactive({
  colleges: [] as string[],
  disciplines: [] as string[],
  disciplinesByCollege: {} as CollegeDisciplineMap,
  titles: [] as string[],
  years: [] as number[],
})
const filters = reactive({ college: '', discipline: '', title: '', year_from: null as number | null, year_to: null as number | null })
const disciplineOptions = computed(() =>
  disciplinesForCollege(options.disciplinesByCollege, filters.college, filters.discipline),
)

const scopeLabel = computed(() => {
  const parts = []
  if (filters.college) parts.push(filters.college)
  if (filters.discipline) parts.push(filters.discipline)
  if (filters.title) parts.push(filters.title)
  if (filters.year_from || filters.year_to) parts.push(`${filters.year_from || '不限'} - ${filters.year_to || '不限'}`)
  return parts.length ? parts.join(' / ') : '全部教师与全部年份'
})

function formatMoney(value: number | null) {
  if (value === null || value === undefined) return '0'
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 1 })
}

async function load(message?: string) {
  loading.value = true
  try {
    const params = {
      college: filters.college || undefined,
      discipline: filters.discipline || undefined,
      title: filters.title || undefined,
      year_from: filters.year_from || undefined,
      year_to: filters.year_to || undefined,
    }
    const [dashboardRes, filterRes] = await Promise.all([
      api.get('/analytics/dashboard', { params }),
      api.get('/analytics/filters'),
    ])
    data.value = dashboardRes.data
    options.colleges = filterRes.data.colleges
    options.disciplines = filterRes.data.disciplines
    options.disciplinesByCollege = filterRes.data.disciplines_by_college || {}
    options.titles = filterRes.data.titles
    options.years = filterRes.data.years
    if (message) ElMessage.success('数据已刷新')
  } finally {
    loading.value = false
  }
}

function onCollegeChange() {
  filters.discipline = ''
  load()
}

function resetFilters() {
  filters.college = ''
  filters.discipline = ''
  filters.title = ''
  filters.year_from = null
  filters.year_to = null
  load()
}

const outputTrendOption = computed(() => {
  const rows = data.value?.output_by_year || []
  return lineOption(rows.map((r: any) => r.year), [
    { name: '成果数', data: rows.map((r: any) => r.value), color: '#2f5597' },
  ])
})

const collegeOption = computed(() =>
  barOption(
    (data.value?.college_distribution || []).map((r: any) => r.name),
    (data.value?.college_distribution || []).map((r: any) => r.value),
    { name: '教师人数', horizontal: true, color: '#3c66a9' },
  ),
)

const titleOption = computed(() => pieOption(data.value?.title_distribution || [], '教师人数'))

const outputTypeOption = computed(() => pieOption(data.value?.output_by_type || [], '成果数'))

const degreeOption = computed(() => pieOption(data.value?.degree_distribution || [], '教师人数'))

const projectTrendOption = computed(() => {
  const rows = data.value?.project_by_year || []
  return barOption(rows.map((r: any) => r.year), rows.map((r: any) => r.value), {
    name: '项目数', color: '#6fa8a0',
  })
})

const teachingTrendOption = computed(() => {
  const rows = data.value?.teaching_by_year || []
  return lineOption(rows.map((r: any) => r.year), [
    { name: '学时', data: rows.map((r: any) => r.value), color: '#d9a45b' },
  ])
})

const ageOption = computed(() => {
  const rows = data.value?.age_distribution || []
  return barOption(rows.map((r: any) => r.name), rows.map((r: any) => r.value), {
    name: '人数', color: palette[4],
  })
})

const qualityItems = computed(() => {
  const q = data.value?.data_quality
  if (!q) return []
  return [
    { label: '疑似重复教师组', value: `${q.duplicate_teacher_count} 组`, className: q.duplicate_teacher_count ? 'warn' : '' },
    { label: '疑似重复成果组', value: `${q.duplicate_output_count} 组`, className: q.duplicate_output_count ? 'warn' : '' },
    { label: '待核验教师', value: `${q.pending_verification_count} 人`, className: q.pending_verification_count ? 'warn' : '' },
    { label: '无成果记录教师', value: `${q.teachers_without_outputs} 人`, className: q.teachers_without_outputs ? 'warn' : '' },
  ]
})

onMounted(() => load())
</script>

<style scoped>
.quality-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.quality-item {
  background: #f8fafd;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #5c6c82;
}

.quality-item strong {
  font-size: 15px;
  color: #23364e;
}

.quality-item strong.warn {
  color: #c46f1f;
}
</style>
