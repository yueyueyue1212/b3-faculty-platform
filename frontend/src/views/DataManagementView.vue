<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">数据管理</h2>
        <p class="page-subtitle">
          通过 CSV / Excel 批量导入教师档案与科研成果，逐行校验并记录错误明细；支持下载模板、追溯导入批次与检查数据质量。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane name="import" label="批量导入">
        <div class="upload-grid">
          <div class="panel upload-card">
            <div class="upload-head">
              <div class="upload-icon"><el-icon><User /></el-icon></div>
              <div>
                <div class="upload-title">教师档案导入</div>
                <div class="hint">支持 CSV / Excel，≤ 5MB，≤ 5000 行；必填：编号、姓名、学院、学科、职称</div>
              </div>
            </div>
            <div class="upload-actions">
              <el-button :icon="Download" @click="downloadTemplate('teachers')">下载教师模板</el-button>
              <el-upload v-if="auth.isEditor" :show-file-list="false" accept=".csv,.xlsx,.xls"
                         :http-request="(options: any) => uploadFile(options, 'teachers')">
                <el-button type="primary" :icon="Upload" :loading="uploadingKind === 'teachers'">上传教师档案</el-button>
              </el-upload>
              <span v-else class="hint">只读用户不可导入数据</span>
            </div>
            <p class="hint">
              重复教师编号会作为“重复记录”跳过，不覆盖已有档案。每位成功导入的教师将生成一条导入批次记录。
            </p>
          </div>

          <div class="panel upload-card">
            <div class="upload-head">
              <div class="upload-icon"><el-icon><Document /></el-icon></div>
              <div>
                <div class="upload-title">科研成果导入</div>
                <div class="hint">必填：教师编号、成果类型、标题；成果类型支持 paper/patent/book/report 或中文</div>
              </div>
            </div>
            <div class="upload-actions">
              <el-button :icon="Download" @click="downloadTemplate('research_outputs')">下载成果模板</el-button>
              <el-upload v-if="auth.isEditor" :show-file-list="false" accept=".csv,.xlsx,.xls"
                         :http-request="(options: any) => uploadFile(options, 'research_outputs')">
                <el-button type="primary" :icon="Upload" :loading="uploadingKind === 'research_outputs'">上传科研成果</el-button>
              </el-upload>
              <span v-else class="hint">只读用户不可导入数据</span>
            </div>
            <p class="hint">
              成果通过教师编号关联档案；同一教师下标题完全相同的成果会标记为疑似重复并跳过。候选人导入请前往“人才引进”岗位工作台。
            </p>
          </div>
        </div>

        <div v-if="lastResult" class="panel section-gap">
          <div class="panel-title">
            <span>最近一次导入结果</span>
            <el-link type="primary" :underline="false" @click="activeTab = 'batches'">查看全部导入批次 →</el-link>
          </div>
          <div class="import-result-head">
            <div>
              <strong>{{ lastResult.filename }}</strong>
              <span class="hint"> · 批次 #{{ lastResult.id }} · {{ importTypeLabel(lastResult.import_type) }}</span>
            </div>
            <el-tag size="small" :type="lastResult.status === 'completed' ? 'success' : 'danger'" effect="plain">
              {{ lastResult.status === 'completed' ? '已完成' : '失败' }}
            </el-tag>
          </div>
          <div class="import-stats">
            <div><strong>{{ lastResult.total_rows }}</strong><span>总行数</span></div>
            <div><strong class="ok">{{ lastResult.success_rows }}</strong><span>成功</span></div>
            <div><strong class="warn">{{ lastResult.failed_rows }}</strong><span>失败</span></div>
            <div><strong class="warn">{{ lastResult.duplicate_rows }}</strong><span>重复</span></div>
          </div>
          <p v-if="lastResult.message" class="note">{{ lastResult.message }}</p>
          <div class="page-actions" style="justify-content: flex-start; margin-top: 12px">
            <el-button v-if="lastResult.failed_rows || lastResult.duplicate_rows" size="small" type="warning" plain
                       @click="openErrors(lastResult)">
              查看错误明细
            </el-button>
            <el-button size="small" @click="activeTab = 'batches'">导入批次</el-button>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="batches" label="导入批次">
        <div class="panel">
          <div class="filters" style="margin-bottom: 12px">
            <el-select v-model="batchFilter" placeholder="导入类型" clearable style="width: 180px">
              <el-option label="教师档案" value="teachers" />
              <el-option label="科研成果" value="research_outputs" />
              <el-option label="候选人" value="candidates" />
            </el-select>
            <el-button type="primary" :icon="Search" @click="loadBatches">查询</el-button>
          </div>

          <el-table :data="batches" v-loading="batchLoading" size="small" stripe empty-text="暂无导入批次">
            <el-table-column prop="id" label="批次" width="80">
              <template #default="{ row }">#{{ row.id }}</template>
            </el-table-column>
            <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
            <el-table-column label="类型" width="110">
              <template #default="{ row }">{{ importTypeLabel(row.import_type) }}</template>
            </el-table-column>
            <el-table-column prop="total_rows" label="总行" width="70" />
            <el-table-column prop="success_rows" label="成功" width="70">
              <template #default="{ row }">
                <span style="color: #1f9d72">{{ row.success_rows }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="failed_rows" label="失败" width="70">
              <template #default="{ row }">
                <span :style="{ color: row.failed_rows ? '#c46f1f' : '' }">{{ row.failed_rows }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="duplicate_rows" label="重复" width="70" />
            <el-table-column prop="error_count" label="错误条目" width="84" />
            <el-table-column prop="status" label="状态" width="88">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'completed' ? 'success' : 'danger'" effect="plain">
                  {{ row.status === 'completed' ? '已完成' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_by" label="操作人" width="100" />
            <el-table-column label="时间" width="160">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" :disabled="!row.error_count" @click="openErrors(row)">
                  错误明细
                </el-button>
                <el-button link :disabled="!row.error_count" @click="exportErrors(row)">导出 CSV</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager-row">
            <el-pagination v-model:current-page="batchPage" :page-size="20" :total="batchTotal"
                           layout="total, prev, pager, next" @current-change="loadBatches" />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="quality" label="数据质量">
        <div v-loading="qualityLoading">
          <div class="stat-grid">
            <StatCard label="疑似重复教师组" :value="quality.duplicate_teacher_count" unit="组"
                      :sub="`按姓名 + 学院匹配`" icon="Warning" accent="warning" />
            <StatCard label="疑似重复成果组" :value="quality.duplicate_output_count" unit="组"
                      :sub="`同一教师标题相同`" icon="Document" accent="warning" />
            <StatCard label="待核验教师" :value="quality.pending_verification_count" unit="人"
                      :sub="`核验状态非 verified`" icon="Stamp" accent="danger" />
            <StatCard label="无成果记录教师" :value="quality.teachers_without_outputs" unit="人"
                      :sub="`仅表示系统未归集成果`" icon="User" accent="info" />
          </div>

          <div class="chart-grid">
            <div class="chart-box">
              <div class="chart-head"><strong>档案缺字段统计</strong><span>缺失人数</span></div>
              <BaseChart :option="missingOption" height="290px" />
            </div>
            <div class="panel">
              <div class="panel-title">重复与待核验明细</div>
              <div class="quality-section">
                <div class="mini-title">疑似重复教师（姓名 + 学院）</div>
                <div v-if="quality.duplicate_teachers.length" class="quality-list">
                  <div v-for="item in quality.duplicate_teachers" :key="`${item.name}-${item.college}`" class="quality-item">
                    <span>{{ item.name }} · {{ item.college }}</span>
                    <span class="hint">{{ item.teacher_nos.join(' / ') }}</span>
                  </div>
                </div>
                <div v-else class="hint">未发现疑似重复教师</div>
              </div>
              <div class="quality-section">
                <div class="mini-title">待核验教师</div>
                <div v-if="quality.pending_verification.length" class="tag-list">
                  <el-tag v-for="item in quality.pending_verification" :key="item.id" size="small" type="warning" effect="plain">
                    {{ item.name }} · {{ item.college }}（{{ item.verification_status }}）
                  </el-tag>
                </div>
                <div v-else class="hint">无待核验教师</div>
              </div>
            </div>
          </div>

          <div class="panel section-gap">
            <div class="panel-title">疑似重复成果</div>
            <el-table :data="quality.duplicate_outputs" size="small" border empty-text="未发现疑似重复成果">
              <el-table-column prop="teacher_name" label="教师" width="110" />
              <el-table-column prop="title" label="成果标题" min-width="320" show-overflow-tooltip />
              <el-table-column prop="count" label="重复条数" width="100" />
              <el-table-column label="记录 ID" width="180">
                <template #default="{ row }">{{ row.ids.join(', ') }}</template>
              </el-table-column>
            </el-table>
            <p class="note" style="margin-top: 12px">{{ quality.note }}</p>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 错误明细 -->
    <el-dialog v-model="errorsVisible" title="导入错误明细" width="760px">
      <template v-if="errorBatch">
        <div class="error-head">
          <div>
            <strong>{{ errorBatch.filename }}</strong>
            <span class="hint"> · 批次 #{{ errorBatch.id }} · {{ importTypeLabel(errorBatch.import_type) }}</span>
          </div>
          <el-button size="small" :icon="Download" @click="exportErrors(errorBatch)">下载 CSV</el-button>
        </div>
        <el-table :data="errorRows" size="small" border max-height="440" empty-text="该批次没有错误记录">
          <el-table-column prop="row_number" label="行号" width="70" />
          <el-table-column prop="column_name" label="字段" width="140" />
          <el-table-column prop="error_message" label="错误原因" min-width="300" show-overflow-tooltip />
          <el-table-column prop="raw_value" label="原始值" width="150" show-overflow-tooltip />
        </el-table>
        <p class="hint" style="margin-top: 10px">
          CSV 错误文件为 UTF-8 BOM 编码，可直接用 Excel 打开。修正后重新上传即可；已成功的行不会被重复写入。
        </p>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Refresh, Search, Upload } from '@element-plus/icons-vue'
import api, { downloadFile } from '../api/client'
import BaseChart from '../components/BaseChart.vue'
import StatCard from '../components/StatCard.vue'
import { barOption } from '../utils/charts'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const activeTab = ref('import')
const uploadingKind = ref('')
const lastResult = ref<any>(null)

const batches = ref<any[]>([])
const batchTotal = ref(0)
const batchPage = ref(1)
const batchLoading = ref(false)
const batchFilter = ref('')

const errorsVisible = ref(false)
const errorBatch = ref<any>(null)
const errorRows = ref<any[]>([])

const qualityLoading = ref(false)
const quality = ref<any>({
  missing_field_counts: [], duplicate_teacher_count: 0, duplicate_teachers: [],
  duplicate_output_count: 0, duplicate_outputs: [], pending_verification_count: 0,
  pending_verification: [], teachers_without_outputs: 0, teachers_without_outputs_sample: [],
  note: '',
})

const missingOption = computed(() =>
  barOption(
    (quality.value.missing_field_counts || []).map((item: any) => item.label),
    (quality.value.missing_field_counts || []).map((item: any) => item.count),
    { name: '缺失人数', color: '#d9a45b' },
  ),
)

function importTypeLabel(type: string) {
  return { teachers: '教师档案', research_outputs: '科研成果', candidates: '候选人' }[type] || type
}

function formatTime(value: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

async function downloadTemplate(kind: string) {
  const names: Record<string, string> = {
    teachers: '教师档案导入模板.csv',
    research_outputs: '科研成果导入模板.csv',
    candidates: '候选人档案导入模板.csv',
  }
  await downloadFile(`/imports/templates/${kind}`, names[kind] || `${kind}_template.csv`)
}

async function uploadFile(options: any, kind: 'teachers' | 'research_outputs') {
  const file = options.file as File
  const form = new FormData()
  form.append('file', file)
  uploadingKind.value = kind
  try {
    const { data } = await api.post(`/imports/${kind === 'teachers' ? 'teachers' : 'research-outputs'}`, form)
    lastResult.value = data
    ElMessage.success(`导入完成：成功 ${data.success_rows} 行，失败 ${data.failed_rows} 行，重复 ${data.duplicate_rows} 行`)
    await Promise.all([loadBatches(), loadQuality()])
  } finally {
    uploadingKind.value = ''
  }
}

async function loadBatches() {
  batchLoading.value = true
  try {
    const params: any = { page: batchPage.value, page_size: 20 }
    if (batchFilter.value) params.import_type = batchFilter.value
    const { data } = await api.get('/imports/batches', { params })
    batches.value = data.items
    batchTotal.value = data.total
  } finally {
    batchLoading.value = false
  }
}

async function openErrors(row: any) {
  const { data } = await api.get(`/imports/batches/${row.id}/errors`, { params: { page: 1, page_size: 200 } })
  errorBatch.value = data.batch
  errorRows.value = data.items
  errorsVisible.value = true
}

async function exportErrors(row: any) {
  await downloadFile(`/imports/batches/${row.id}/errors/export`, `导入错误明细_批次${row.id}.csv`)
}

async function loadQuality() {
  qualityLoading.value = true
  try {
    const { data } = await api.get('/analytics/data-quality')
    quality.value = data
  } finally {
    qualityLoading.value = false
  }
}

async function refreshAll() {
  await Promise.all([loadBatches(), loadQuality()])
  ElMessage.success('数据已刷新')
}

onMounted(async () => {
  await Promise.all([loadBatches(), loadQuality()])
})
</script>

<style scoped>
.upload-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 1100px) {
  .upload-grid {
    grid-template-columns: 1fr;
  }
}

.upload-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.upload-head {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.upload-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: #eef3fb;
  color: #2f5597;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.upload-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
}

.upload-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.upload-actions .el-upload {
  display: inline-block;
}

.import-result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.import-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.import-stats div {
  background: #f7f9fd;
  border: 1px solid #eef1f7;
  border-radius: 8px;
  padding: 14px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.import-stats strong {
  font-size: 22px;
  color: #2f5597;
}

.import-stats strong.ok {
  color: #1f9d72;
}

.import-stats strong.warn {
  color: #c46f1f;
}

.import-stats span {
  font-size: 11px;
  color: #7a8797;
}

.pager-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.error-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px dashed #e6ebf3;
}

.quality-section {
  margin-bottom: 14px;
}

.mini-title {
  font-size: 12px;
  font-weight: 600;
  color: #2f5597;
  margin-bottom: 8px;
}

.quality-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 170px;
  overflow-y: auto;
}

.quality-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  background: #f8fafd;
  border: 1px solid #eef1f7;
  border-radius: 6px;
  padding: 6px 10px;
}
</style>
