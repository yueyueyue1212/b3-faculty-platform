<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <div>
        <h2 class="page-title">人才盘点</h2>
        <p class="page-subtitle">
          面向学院与学科的人才结构盘点：职称/学历梯队、产出趋势、人才规划缺口与数据质量。
          缺口依据管理员配置的规划目标计算，不由模型推断。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Download" :loading="exporting" @click="exportReport">导出盘点报告（Excel）</el-button>
      </div>
    </div>

    <div class="panel filters">
      <el-select v-model="filters.college" placeholder="全部学院" clearable @change="onCollegeChange">
        <el-option v-for="item in options.colleges" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.discipline" :placeholder="filters.college ? '全部学科' : '请先选择学院'"
                 :disabled="!filters.college" clearable filterable>
        <el-option v-for="item in disciplineOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.title" placeholder="全部职称" clearable>
        <el-option v-for="item in options.titles" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.year_from" placeholder="起始年份" clearable>
        <el-option v-for="year in options.years" :key="year" :label="`${year} 年起`" :value="year" />
      </el-select>
      <el-select v-model="filters.year_to" placeholder="截止年份" clearable>
        <el-option v-for="year in options.years" :key="year" :label="`截至 ${year}`" :value="year" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="load">生成盘点</el-button>
      <el-button :icon="RefreshLeft" @click="reset">重置</el-button>
    </div>

    <template v-if="data">
      <div class="stat-grid">
        <StatCard label="盘点教师范围" :value="overview.total_teachers" unit="人"
                  :sub="`在职 ${overview.active_teachers} 人 · 导师资格 ${overview.advisor_qualified_count} 人`"
                  icon="User" />
        <StatCard label="科研成果" :value="overview.output_total" unit="项"
                  :sub="`统计区间内成果记录`" icon="Document" />
        <StatCard label="科研项目" :value="overview.project_total" unit="项"
                  :sub="`按项目开始时间筛选`" icon="Files" accent="success" />
        <StatCard label="教学工作量" :value="overview.teaching_hours_total" unit="学时"
                  :sub="`平均教学评价 ${overview.avg_evaluation_score ?? '无数据'}`" icon="Reading" />
        <StatCard label="规划缺口项" :value="gapCount" unit="项"
                  :sub="data.talent_plan.length ? `已配置 ${data.talent_plan.length} 条规划` : '尚未配置人才规划'"
                  icon="Aim" accent="warning" />
        <StatCard label="数据待核验" :value="quality.pending_verification_count" unit="人"
                  :sub="`无成果教师 ${quality.teachers_without_outputs} 人`" icon="Warning" accent="danger" />
      </div>

      <div class="chart-grid">
        <div class="chart-box">
          <div class="chart-head"><strong>学院职称结构</strong><span>堆叠人数</span></div>
          <BaseChart :option="titleStackOption" height="300px" />
        </div>
        <div class="chart-box">
          <div class="chart-head"><strong>职称总体结构</strong><span>教师人数</span></div>
          <BaseChart :option="titlePieOption" height="300px" />
        </div>
      </div>

      <div class="chart-grid three">
        <div class="chart-box">
          <div class="chart-head"><strong>学历结构</strong><span>含未填写</span></div>
          <BaseChart :option="degreePieOption" height="260px" />
        </div>
        <div class="chart-box">
          <div class="chart-head"><strong>成果年度趋势</strong><span>成果记录数</span></div>
          <BaseChart :option="outputTrendOption" height="260px" />
        </div>
        <div class="chart-box">
          <div class="chart-head"><strong>项目年度趋势</strong><span>项目数</span></div>
          <BaseChart :option="projectTrendOption" height="260px" />
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">
          <span>人才规划目标与缺口</span>
          <span class="hint">在“系统设置”中维护规划目标</span>
        </div>
        <el-table v-if="data.plan_gaps.length" :data="data.plan_gaps" size="small" stripe>
          <el-table-column prop="college" label="学院" min-width="130" />
          <el-table-column prop="discipline" label="学科" min-width="160" />
          <el-table-column prop="target_count" label="规划目标" width="100" />
          <el-table-column prop="current_count" label="现有教师" width="100" />
          <el-table-column label="达成度" min-width="200">
            <template #default="{ row }">
              <el-progress :percentage="gapPercent(row)" :stroke-width="10"
                           :status="row.gap <= 0 ? 'success' : undefined"
                           :color="row.gap > 0 ? '#d9a45b' : '#5a9e78'" />
            </template>
          </el-table-column>
          <el-table-column label="缺口" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.gap > 0" size="small" type="warning" effect="plain">缺 {{ row.gap }} 人</el-tag>
              <el-tag v-else-if="row.gap === 0" size="small" type="success" effect="plain">已达标</el-tag>
              <el-tag v-else size="small" type="info" effect="plain">超 {{ -row.gap }} 人</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="note" label="备注" min-width="180" show-overflow-tooltip />
        </el-table>
        <div v-else class="empty-block">
          尚未配置人才规划目标。管理员可在“系统设置 → 人才规划”中按学院/学科设定目标人数后重新盘点。
        </div>
        <p class="hint" style="margin: 10px 0 0">{{ data.plan_note }}</p>
      </div>

      <div class="chart-grid section-gap">
        <div class="panel">
          <div class="panel-title">学院职称结构明细</div>
          <el-table :data="data.title_structure_by_college" size="small" border>
            <el-table-column prop="college" label="学院" min-width="130" />
            <el-table-column prop="total" label="合计" width="70" />
            <el-table-column v-for="title in titleOrder" :key="title" :prop="title" :label="title" width="74" />
          </el-table>
        </div>
        <div class="panel">
          <div class="panel-title">学院学历结构明细</div>
          <el-table :data="data.degree_structure_by_college" size="small" border>
            <el-table-column prop="college" label="学院" min-width="130" />
            <el-table-column prop="total" label="合计" width="70" />
            <el-table-column v-for="degree in degreeOrder" :key="degree" :prop="degree" :label="degree" width="74" />
          </el-table>
        </div>
      </div>

      <div class="panel section-gap">
        <div class="panel-title">
          <span>数据质量</span>
          <span class="hint">{{ quality.note }}</span>
        </div>
        <div class="quality-grid">
          <div class="quality-card">
            <div class="qc-title">档案缺字段统计</div>
            <div v-for="item in quality.missing_field_counts" :key="item.field" class="qc-row">
              <span>{{ item.label }}</span>
              <strong :class="{ warn: item.count > 0 }">{{ item.count }}</strong>
            </div>
          </div>
          <div class="quality-card">
            <div class="qc-title">一致性问题</div>
            <div class="qc-row"><span>疑似重复教师组</span><strong :class="{ warn: quality.duplicate_teacher_count }">{{ quality.duplicate_teacher_count }}</strong></div>
            <div class="qc-row"><span>疑似重复成果组</span><strong :class="{ warn: quality.duplicate_output_count }">{{ quality.duplicate_output_count }}</strong></div>
            <div class="qc-row"><span>待核验教师</span><strong :class="{ warn: quality.pending_verification_count }">{{ quality.pending_verification_count }}</strong></div>
            <div class="qc-row"><span>无成果记录教师</span><strong :class="{ warn: quality.teachers_without_outputs }">{{ quality.teachers_without_outputs }}</strong></div>
          </div>
          <div class="quality-card">
            <div class="qc-title">待核验教师（最多 20 人）</div>
            <div v-if="quality.pending_verification.length" class="pending-list">
              <el-tag v-for="item in quality.pending_verification" :key="item.id" size="small" type="warning" effect="plain">
                {{ item.name }} · {{ item.college }}
              </el-tag>
            </div>
            <div v-else class="hint">暂无待核验教师</div>
            <div class="qc-title" style="margin-top: 14px">无成果记录（样例）</div>
            <div v-if="quality.teachers_without_outputs_sample.length" class="pending-list">
              <el-tag v-for="item in quality.teachers_without_outputs_sample" :key="item.id" size="small" type="info" effect="plain">
                {{ item.name }} · {{ item.college }}
              </el-tag>
            </div>
            <div v-else class="hint">无</div>
          </div>
        </div>
      </div>

      <div class="note section-gap">
        {{ overview.stats_scope }} {{ overview.age_note }} 本报告由系统实时生成，规划缺口仅反映配置目标与现有档案人数之差。
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, RefreshLeft, Search } from '@element-plus/icons-vue'
import api, { downloadFile } from '../api/client'
import BaseChart from '../components/BaseChart.vue'
import StatCard from '../components/StatCard.vue'
import { axisStyle, barOption, gridStyle, lineOption, palette, pieOption, tooltipStyle } from '../utils/charts'
import { disciplinesForCollege, type CollegeDisciplineMap } from '../utils/linkage'

const titleOrder = ['教授', '副教授', '讲师', '助教']
const degreeOrder = ['博士', '硕士', '学士', '其他']
const loading = ref(false)
const exporting = ref(false)
const data = ref<any>(null)
const options = reactive({
  colleges: [] as string[],
  disciplines: [] as string[],
  disciplinesByCollege: {} as CollegeDisciplineMap,
  titles: [] as string[],
  years: [] as number[],
})
const filters = reactive({
  college: '', discipline: '', title: '',
  year_from: null as number | null, year_to: null as number | null,
})
const disciplineOptions = computed(() =>
  disciplinesForCollege(options.disciplinesByCollege, filters.college, filters.discipline),
)

const overview = computed(() => data.value?.overview || {})
const quality = computed(() => data.value?.data_quality || {
  missing_field_counts: [], duplicate_teacher_count: 0, duplicate_output_count: 0,
  pending_verification_count: 0, pending_verification: [],
  teachers_without_outputs: 0, teachers_without_outputs_sample: [], note: '',
})
const gapCount = computed(() =>
  (data.value?.plan_gaps || []).filter((row: any) => row.gap > 0).length,
)

function params() {
  return {
    college: filters.college || undefined,
    discipline: filters.discipline || undefined,
    title: filters.title || undefined,
    year_from: filters.year_from || undefined,
    year_to: filters.year_to || undefined,
  }
}

async function load(message?: string) {
  loading.value = true
  try {
    const [reviewRes, filterRes] = await Promise.all([
      api.get('/analytics/talent-review', { params: params() }),
      api.get('/analytics/filters'),
    ])
    data.value = reviewRes.data
    options.colleges = filterRes.data.colleges
    options.disciplines = filterRes.data.disciplines
    options.disciplinesByCollege = filterRes.data.disciplines_by_college || {}
    options.titles = filterRes.data.titles
    options.years = filterRes.data.years
    if (message) ElMessage.success(message)
  } finally {
    loading.value = false
  }
}

function onCollegeChange() {
  filters.discipline = ''
}

function reset() {
  Object.assign(filters, { college: '', discipline: '', title: '', year_from: null, year_to: null })
  load()
}

function gapPercent(row: any) {
  if (!row.target_count) return 0
  return Math.min(100, Math.round((row.current_count / row.target_count) * 100))
}

async function exportReport() {
  exporting.value = true
  try {
    await downloadFile('/analytics/talent-review/export', '人才盘点报告.xlsx', params())
    ElMessage.success('盘点报告已导出')
  } finally {
    exporting.value = false
  }
}

const titleStackOption = computed(() => {
  const rows = data.value?.title_structure_by_college || []
  return {
    color: palette,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, ...tooltipStyle },
    legend: { top: 0, right: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 11, color: '#5f6f85' } },
    grid: { ...gridStyle, top: 34 },
    xAxis: {
      type: 'category', data: rows.map((r: any) => r.college), ...axisStyle,
      splitLine: { show: false },
      axisLabel: { color: '#7a8797', fontSize: 10, interval: 0, rotate: rows.length > 5 ? 25 : 0 },
    },
    yAxis: { type: 'value', ...axisStyle },
    series: titleOrder.map((title) => ({
      name: title,
      type: 'bar',
      stack: 'total',
      barMaxWidth: 30,
      data: rows.map((r: any) => r[title] || 0),
    })),
  }
})

const titlePieOption = computed(() => pieOption(overview.value.title_distribution || [], '教师人数'))
const degreePieOption = computed(() => pieOption(overview.value.degree_distribution || [], '教师人数'))

const outputTrendOption = computed(() => {
  const rows = overview.value.output_by_year || []
  return lineOption(rows.map((r: any) => r.year), [
    { name: '成果数', data: rows.map((r: any) => r.value), color: '#2f5597' },
  ])
})

const projectTrendOption = computed(() => {
  const rows = overview.value.project_by_year || []
  return barOption(rows.map((r: any) => r.year), rows.map((r: any) => r.value), {
    name: '项目数', color: '#6fa8a0',
  })
})

onMounted(() => load())
</script>

<style scoped>
.quality-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

@media (max-width: 1100px) {
  .quality-grid {
    grid-template-columns: 1fr;
  }
}

.quality-card {
  background: #f8fafd;
  border: 1px solid #eef1f7;
  border-radius: 8px;
  padding: 14px;
}

.qc-title {
  font-size: 12px;
  color: #2f5597;
  font-weight: 600;
  margin-bottom: 10px;
}

.qc-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #5c6c82;
  padding: 5px 0;
  border-bottom: 1px dashed #e9eef5;
}

.qc-row:last-child {
  border-bottom: none;
}

.qc-row strong {
  color: #23364e;
}

.qc-row strong.warn {
  color: #c46f1f;
}

.pending-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 130px;
  overflow-y: auto;
}
</style>
