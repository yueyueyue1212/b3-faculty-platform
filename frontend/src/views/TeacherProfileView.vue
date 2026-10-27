<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <div>
        <h2 class="page-title">智能画像</h2>
        <p class="page-subtitle">
          画像由教师档案、科研成果、项目、教学与社会服务记录实时汇总；AI 摘要仅作辅助表述，不改变任何统计口径。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Back" @click="$router.push('/profiles')">返回画像列表</el-button>
        <el-button v-if="profile" type="primary" :icon="MagicStick" :loading="summaryLoading" @click="openSummary">
          生成画像摘要
        </el-button>
      </div>
    </div>

    <template v-if="profile">
      <div class="panel profile-head">
        <div class="avatar">{{ profile.teacher.name?.slice(0, 1) }}</div>
        <div class="head-main">
          <div class="name-line">
            <span class="name">{{ profile.teacher.name }}</span>
            <el-tag effect="plain">{{ profile.teacher.title }}</el-tag>
            <el-tag v-if="profile.teacher.degree" effect="plain" type="info">{{ profile.teacher.degree }}</el-tag>
            <el-tag v-if="profile.teacher.advisor_qualified" effect="plain" type="success">
              导师 {{ profile.teacher.current_students }}/{{ profile.teacher.capacity }}
            </el-tag>
            <el-tag v-if="profile.teacher.verification_status !== 'verified'" effect="plain" type="warning">
              数据待核验
            </el-tag>
          </div>
          <div class="meta-line">
            {{ profile.teacher.teacher_no }} · {{ profile.teacher.college }}
            <template v-if="profile.teacher.department"> / {{ profile.teacher.department }}</template>
            · {{ profile.teacher.discipline }}
            <template v-if="profile.teacher.hire_date"> · 入职 {{ profile.teacher.hire_date }}</template>
          </div>
          <div class="direction-line">
            <strong>研究方向：</strong>{{ profile.research_direction || '未填写' }}
          </div>
          <div v-if="profile.research_keywords.length" class="tag-list" style="margin-top: 8px">
            <el-tag v-for="kw in profile.research_keywords" :key="kw" size="small" effect="plain" round>{{ kw }}</el-tag>
          </div>
        </div>
        <div class="head-side">
          <div class="completeness-label">档案完整度</div>
          <el-progress type="dashboard" :percentage="profile.completeness" :width="104"
                       :color="profile.completeness >= 80 ? '#5a9e78' : '#d9a45b'" />
          <div v-if="profile.missing_fields.length" class="missing">
            待补充：{{ profile.missing_fields.join('、') }}
          </div>
          <div v-else class="missing" style="color: #5a9e78">档案字段完整</div>
        </div>
      </div>

      <div class="tag-list profile-tags">
        <el-tag v-for="tag in profile.tags" :key="tag" type="warning" effect="light" round>{{ tag }}</el-tag>
        <span v-if="!profile.tags.length" class="muted">暂无可归纳的标签</span>
      </div>

      <div class="stat-grid">
        <StatCard label="科研成果" :value="profile.output_count" unit="项"
                  :sub="`近三年 ${profile.recent_three_year_outputs} 项`" icon="Document" />
        <StatCard label="科研项目" :value="profile.project_count" unit="项"
                  :sub="`主持 ${profile.principal_project_count} 项 · 经费 ${profile.project_funding_total} 万元`"
                  icon="Files" accent="success" />
        <StatCard label="教学工作量" :value="profile.teaching_hours_total" unit="学时"
                  :sub="`${profile.course_count} 门课程 · 平均评价 ${profile.avg_evaluation_score ?? '无数据'}`"
                  icon="Reading" />
        <StatCard label="社会服务" :value="profile.service_count" unit="条"
                  :sub="`获奖 ${profile.award_count} · 学术任职 ${profile.academic_post_count}`"
                  icon="Medal" accent="warning" />
        <StatCard label="最近更新" :value="formatDate(profile.last_updated)" unit=""
                  :sub="`数据来源：${profile.data_source}`" icon="Clock" accent="info" />
      </div>

      <div class="chart-grid">
        <div class="chart-box">
          <div class="chart-head"><strong>科研成果年度趋势</strong><span>按发表日期年份</span></div>
          <BaseChart :option="outputOption" height="280px" />
        </div>
        <div class="chart-box">
          <div class="chart-head"><strong>成果类型结构</strong><span>记录数</span></div>
          <BaseChart :option="outputTypeOption" height="280px" />
        </div>
      </div>

      <div class="chart-grid">
        <div class="chart-box">
          <div class="chart-head"><strong>教学工作量年度分布</strong><span>累计学时</span></div>
          <BaseChart :option="teachingOption" height="260px" />
        </div>
        <div class="chart-box">
          <div class="chart-head"><strong>项目年度分布</strong><span>主持 + 参与，按开始年份</span></div>
          <BaseChart :option="projectOption" height="260px" />
        </div>
      </div>

      <div class="panel">
        <el-tabs v-model="activeTab">
          <el-tab-pane name="outputs" :label="`科研成果（${profile.outputs.length}）`">
            <el-table :data="profile.outputs" size="small" stripe empty-text="暂无成果记录">
              <el-table-column label="类型" width="90">
                <template #default="{ row }">{{ row.output_type_label }}</template>
              </el-table-column>
              <el-table-column prop="title" label="标题" min-width="300" show-overflow-tooltip />
              <el-table-column prop="venue" label="发表载体" min-width="160" show-overflow-tooltip />
              <el-table-column prop="level" label="级别" width="100" />
              <el-table-column prop="publish_date" label="日期" width="112" />
            </el-table>
            <p class="hint" style="margin: 10px 0 0">
              此处展示最近 20 条记录；完整成果台账位于教师档案与数据管理模块。
            </p>
          </el-tab-pane>

          <el-tab-pane name="projects" :label="`科研项目（${profile.projects.length}）`">
            <el-table :data="profile.projects" size="small" stripe empty-text="暂无项目记录">
              <el-table-column prop="project_no" label="编号" width="130" />
              <el-table-column prop="name" label="项目名称" min-width="280" show-overflow-tooltip />
              <el-table-column prop="level" label="级别" width="110" />
              <el-table-column label="角色" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.role === '主持人' ? 'success' : 'info'" effect="plain">
                    {{ row.role }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="经费（万元）" width="110">
                <template #default="{ row }">{{ row.funding ?? '—' }}</template>
              </el-table-column>
              <el-table-column label="起止" min-width="180">
                <template #default="{ row }">{{ row.start_date || '—' }} ~ {{ row.end_date || '—' }}</template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="90" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane name="teaching" :label="`教学记录（${profile.teaching_record_count}）`">
            <el-table :data="profile.teaching_records" size="small" stripe empty-text="暂无教学记录">
              <el-table-column prop="course_name" label="课程名称" min-width="180" />
              <el-table-column prop="academic_year" label="学年" width="120" />
              <el-table-column prop="semester" label="学期" width="100" />
              <el-table-column prop="hours" label="学时" width="90" />
              <el-table-column label="评价分" width="90">
                <template #default="{ row }">{{ row.evaluation_score ?? '—' }}</template>
              </el-table-column>
              <el-table-column prop="achievement" label="教学成果" min-width="220" show-overflow-tooltip />
            </el-table>
          </el-tab-pane>

          <el-tab-pane name="services" :label="`社会服务（${profile.service_count}）`">
            <el-table :data="profile.service_records" size="small" stripe empty-text="暂无社会服务记录">
              <el-table-column prop="service_type" label="类型" width="100">
                <template #default="{ row }">{{ serviceTypeLabel(row.service_type) }}</template>
              </el-table-column>
              <el-table-column prop="name" label="名称" min-width="240" show-overflow-tooltip />
              <el-table-column prop="organization" label="单位" min-width="170" show-overflow-tooltip />
              <el-table-column prop="role" label="角色" width="110" />
              <el-table-column prop="start_date" label="开始日期" width="112" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane name="metrics" label="指标口径">
            <el-table :data="profile.metric_definitions" size="small" border>
              <el-table-column prop="metric" label="指标" width="140" />
              <el-table-column prop="definition" label="计算口径" min-width="360" />
              <el-table-column prop="source" label="数据来源" width="190" />
            </el-table>
            <p class="note" style="margin-top: 12px">
              画像只反映系统已归集的数据，不对教师个人能力作确定性评价。未关联记录的指标显示为 0，不能据此推断真实产出为空。
            </p>
          </el-tab-pane>
        </el-tabs>
      </div>

      <div class="two-col">
        <div class="panel">
          <div class="panel-title">档案完整度明细</div>
          <div class="field-grid">
            <div v-for="item in profile.completeness_detail" :key="item.field" class="field-item">
              <el-icon :color="item.present ? '#5a9e78' : '#c46f1f'">
                <CircleCheck v-if="item.present" /><Warning v-else />
              </el-icon>
              <span>{{ item.label }}</span>
              <span class="hint">{{ item.present ? '已填写' : '缺失' }}</span>
            </div>
          </div>
          <p class="hint" style="margin: 12px 0 0">
            完整度按 11 项关键字段计算；敏感联系方式不在此画像中直接展示。
          </p>
        </div>

        <div class="panel">
          <div class="panel-title">
            <span>画像摘要（本地规则）</span>
            <el-tag size="small" effect="plain" type="info">无需外部接口</el-tag>
          </div>
          <pre class="pre-wrap summary-text">{{ profile.local_summary }}</pre>
          <p v-if="profile.sensitive_hidden" class="note">
            当前账号为只读角色，画像中的敏感联系方式已按权限策略隐藏。
          </p>
        </div>
      </div>
    </template>

    <el-dialog v-model="summaryVisible" title="画像摘要" width="620px">
      <div v-loading="summaryLoading">
        <template v-if="summary">
          <div class="summary-meta">
            <el-tag :type="summary.mode === 'llm' ? 'success' : 'info'" effect="plain">
              {{ summary.mode === 'llm' ? '大模型生成' : '本地规则生成' }}
            </el-tag>
            <span class="hint">依据：成果 {{ summary.basis.output_count }} 项 · 项目 {{ summary.basis.project_count }} 项 · 完整度 {{ summary.basis.completeness }}%</span>
            <span class="hint">敏感数据外发：{{ summary.basis.sensitive_data_sent ? '是' : '否' }}</span>
          </div>
          <div class="pre-wrap summary-body">{{ summary.text }}</div>
          <p v-if="summary.warning" class="note">{{ summary.warning }}</p>
          <p class="note">
            AI 摘要仅用于辅助撰写，不参与人才评价、职称或录用决策；如需正式材料请以数据库原始记录为准。
          </p>
        </template>
      </div>
      <template #footer>
        <el-button @click="summaryVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Back, MagicStick } from '@element-plus/icons-vue'
import api from '../api/client'
import BaseChart from '../components/BaseChart.vue'
import StatCard from '../components/StatCard.vue'
import { barOption, lineOption, pieOption } from '../utils/charts'

const route = useRoute()
const loading = ref(false)
const profile = ref<any>(null)
const activeTab = ref('outputs')
const summaryVisible = ref(false)
const summaryLoading = ref(false)
const summary = ref<any>(null)

function formatDate(value: string | null) {
  if (!value) return '—'
  return value.slice(0, 10)
}

function serviceTypeLabel(value: string) {
  return { award: '获奖', academic_post: '学术任职', social_service: '社会服务' }[value] || value
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/teachers/${route.params.id}/profile`)
    profile.value = data
  } finally {
    loading.value = false
  }
}

const outputOption = computed(() => {
  const rows = profile.value?.output_by_year || {}
  const years = Object.keys(rows)
  return lineOption(years, [{ name: '成果数', data: years.map((y) => rows[y]), color: '#2f5597' }])
})

const outputTypeOption = computed(() => {
  const rows = profile.value?.output_by_type || {}
  return pieOption(Object.keys(rows).map((name) => ({ name, value: rows[name] })), '成果数')
})

const teachingOption = computed(() => {
  const rows = profile.value?.teaching_by_year || {}
  const years = Object.keys(rows)
  return lineOption(years, [{ name: '学时', data: years.map((y) => rows[y]), color: '#d9a45b' }])
})

const projectOption = computed(() => {
  const rows = profile.value?.project_by_year || {}
  const years = Object.keys(rows)
  return barOption(years, years.map((y) => rows[y]), { name: '项目数', color: '#6fa8a0' })
})

async function openSummary() {
  summaryVisible.value = true
  summaryLoading.value = true
  try {
    const { data } = await api.post(`/teachers/${route.params.id}/ai-summary`)
    summary.value = data
  } finally {
    summaryLoading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.profile-head {
  display: flex;
  gap: 18px;
  align-items: center;
  padding: 22px;
}

.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4d7ac9, #2f5597);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
  flex-shrink: 0;
}

.head-main {
  flex: 1;
  min-width: 0;
}

.name-line {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.name {
  font-size: 22px;
  font-weight: 650;
  color: #1c2f4a;
}

.meta-line {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7c92;
}

.direction-line {
  margin-top: 8px;
  font-size: 13px;
  color: #4a5b72;
}

.head-side {
  width: 200px;
  text-align: center;
  border-left: 1px dashed #e6ebf3;
  padding-left: 16px;
}

.completeness-label {
  font-size: 12px;
  color: #8494a8;
  margin-bottom: 4px;
}

.missing {
  font-size: 11px;
  color: #c46f1f;
  margin-top: 4px;
  line-height: 1.5;
}

.profile-tags {
  margin: -2px 0 16px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.field-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 8px 10px;
  background: #f8fafd;
  border: 1px solid #eef1f7;
  border-radius: 6px;
}

.field-item .hint {
  margin-left: auto;
}

.summary-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.9;
  color: #3f5068;
  white-space: pre-wrap;
  font-family: inherit;
}

.summary-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px dashed #e6ebf3;
  margin-bottom: 12px;
}

.summary-body {
  font-size: 13px;
  line-height: 1.9;
  color: #3f5068;
  white-space: pre-wrap;
  max-height: 380px;
  overflow-y: auto;
}
</style>
