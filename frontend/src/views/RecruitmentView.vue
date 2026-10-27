<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">人才引进</h2>
        <p class="page-subtitle">
          岗位与候选人档案管理、学历/成果硬性条件校验、四维加权评估与证据展示。
          系统只给出辅助评估建议，不自动作出录用或淘汰决定，最终结论由人工填写。
        </p>
      </div>
      <div class="page-actions">
        <el-button v-if="auth.isEditor" type="primary" :icon="Plus" @click="openPositionCreate">新增招聘岗位</el-button>
      </div>
    </div>

    <div class="panel" v-loading="positionLoading">
      <div class="panel-title">
        <span>招聘岗位</span>
        <span class="hint">点击“候选人”管理工作台；删除有候选人的岗位会被拒绝</span>
      </div>
      <el-table :data="positions" size="small" stripe empty-text="暂无招聘岗位">
        <el-table-column prop="name" label="岗位名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="selectPosition(row)">{{ row.name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="college" label="学院" min-width="120" show-overflow-tooltip />
        <el-table-column prop="discipline" label="学科" min-width="150" show-overflow-tooltip />
        <el-table-column prop="required_degree" label="学历要求" width="90" />
        <el-table-column prop="min_outputs" label="最低成果" width="84" />
        <el-table-column label="方向" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.research_direction || '—' }}</template>
        </el-table-column>
        <el-table-column label="候选人" width="82">
          <template #default="{ row }">{{ row.candidate_count }}</template>
        </el-table-column>
        <el-table-column label="已评估" width="82">
          <template #default="{ row }">{{ row.evaluated_count }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'open' ? 'success' : 'info'" effect="plain">
              {{ row.status === 'open' ? '招聘中' : '已关闭' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="selectPosition(row)">候选人</el-button>
            <el-button v-if="auth.isEditor" link type="primary" @click="openPositionEdit(row)">编辑</el-button>
            <el-button v-if="auth.isEditor" link type="success" @click="quickEvaluate(row)">执行评估</el-button>
            <el-button v-if="auth.isEditor" link type="danger" @click="removePosition(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div v-if="selectedPosition" class="panel section-gap" v-loading="candidateLoading">
      <div class="candidate-head">
        <div>
          <div class="position-title">
            {{ selectedPosition.name }}
            <el-tag size="small" :type="selectedPosition.status === 'open' ? 'success' : 'info'" effect="plain">
              {{ selectedPosition.status === 'open' ? '招聘中' : '已关闭' }}
            </el-tag>
          </div>
          <div class="hint" style="margin-top: 4px">
            {{ selectedPosition.college }} · {{ selectedPosition.discipline }} ·
            要求 {{ selectedPosition.required_degree }} · 最低成果 {{ selectedPosition.min_outputs }} 项
          </div>
          <div class="tag-list" style="margin-top: 8px">
            <el-tag size="small" effect="plain">方向权重 {{ pct(selectedPosition.weights.direction) }}</el-tag>
            <el-tag size="small" effect="plain">成果权重 {{ pct(selectedPosition.weights.outputs) }}</el-tag>
            <el-tag size="small" effect="plain">项目权重 {{ pct(selectedPosition.weights.projects) }}</el-tag>
            <el-tag size="small" effect="plain">教学权重 {{ pct(selectedPosition.weights.teaching) }}</el-tag>
          </div>
        </div>
        <div class="page-actions">
          <el-button v-if="auth.isEditor" :icon="Plus" @click="openCandidateCreate">新增候选人</el-button>
          <el-button :icon="Download" @click="downloadTemplate">下载导入模板</el-button>
          <el-upload v-if="auth.isEditor" :show-file-list="false" accept=".csv,.xlsx,.xls"
                     :http-request="uploadCandidates" style="display: inline-block">
            <el-button :icon="Upload" :loading="uploading">导入候选人</el-button>
          </el-upload>
          <el-button v-if="auth.isEditor" type="primary" :icon="DataAnalysis" :loading="evaluating"
                     @click="evaluateSelected">
            执行岗位评估
          </el-button>
          <el-button :icon="Refresh" @click="loadEvaluations">刷新评估结果</el-button>
        </div>
      </div>

      <el-tabs v-model="candidateTab">
        <el-tab-pane name="candidates" :label="`候选人档案（${candidates.length}）`">
          <el-table :data="candidates" size="small" stripe empty-text="暂无候选人，可新增或导入 CSV/Excel">
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="degree" label="学历" width="80" />
            <el-table-column prop="graduate_school" label="毕业院校" min-width="150" show-overflow-tooltip />
            <el-table-column prop="major" label="专业" min-width="130" show-overflow-tooltip />
            <el-table-column prop="research_direction" label="研究方向" min-width="170" show-overflow-tooltip />
            <el-table-column prop="outputs_count" label="成果" width="64" />
            <el-table-column prop="projects_count" label="项目" width="64" />
            <el-table-column prop="teaching_years" label="教龄" width="64" />
            <el-table-column label="资料核验" width="90">
              <template #default="{ row }">
                <el-tag v-if="row.unverified_fields" size="small" type="warning" effect="plain">待核验</el-tag>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="source" label="来源" min-width="110" show-overflow-tooltip />
            <el-table-column v-if="auth.isEditor" label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openCandidateEdit(row)">编辑</el-button>
                <el-button link type="danger" @click="removeCandidate(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <p class="hint" style="margin: 10px 0 0">
            评估前请先确认候选人记录与证据来源；系统按导入/录入的记录数评分，不对证据真伪作判定。
          </p>
        </el-tab-pane>

        <el-tab-pane name="evaluations" :label="`评估结果（${evaluations.length}）`">
          <div v-if="!evaluations.length" class="empty-block">
            尚未执行岗位评估。点击“执行岗位评估”后，系统会按硬性条件过滤并计算辅助得分。
          </div>
          <template v-else>
            <div class="eval-summary">
              <div><strong>{{ evaluations.length }}</strong><span>候选人总数</span></div>
              <div><strong class="ok">{{ evaluations.filter(e => e.hard_pass).length }}</strong><span>硬性条件通过</span></div>
              <div><strong class="warn">{{ evaluations.filter(e => !e.hard_pass).length }}</strong><span>硬性条件未通过</span></div>
              <div><strong>{{ evaluations.filter(e => e.review_status !== 'pending').length }}</strong><span>已人工评审</span></div>
            </div>
            <p class="note" style="margin-bottom: 12px">
              排名仅针对通过硬性条件的候选人；未通过的候选人保留规则分供核对，但不进入推荐排名。
              系统不自动录用或淘汰任何人。
            </p>

            <el-table :data="evaluations" size="small" border>
              <el-table-column type="expand">
                <template #default="{ row }">
                  <div class="eval-detail">
                    <div class="eval-scores">
                      <div v-for="item in evaluationScores(row)" :key="item.label" class="eval-score-item">
                        <span>{{ item.label }}</span>
                        <el-progress :percentage="item.value" :stroke-width="7" :show-text="false"
                                     :color="item.value >= 60 ? '#5a9e78' : '#d9a45b'" />
                        <b>{{ item.value }}</b>
                      </div>
                    </div>
                    <div class="eval-columns">
                      <div>
                        <div class="mini-title">评分理由</div>
                        <pre class="pre-wrap eval-text">{{ row.reasons }}</pre>
                        <div class="mini-title" style="margin-top: 10px">差距与待核验</div>
                        <pre class="pre-wrap eval-text">{{ row.gaps || '无' }}</pre>
                      </div>
                      <div>
                        <div class="mini-title">证据与来源</div>
                        <pre class="pre-wrap eval-text">{{ row.evidence }}</pre>
                      </div>
                    </div>
                    <div class="review-line">
                      <el-tag size="small" :type="reviewType(row.review_status)" effect="light">
                        {{ reviewLabel(row.review_status) }}
                      </el-tag>
                      <span class="hint">评审人：{{ row.reviewer || '—' }}</span>
                      <span class="hint">备注：{{ row.review_note || '—' }}</span>
                      <el-button v-if="auth.isEditor" size="small" link type="primary" @click="openReview(row)">
                        填写评审意见
                      </el-button>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="排名" width="70">
                <template #default="{ row }">
                  <span v-if="row.rank" class="rank-badge" :class="{ top: row.rank === 1 }">{{ row.rank }}</span>
                  <span v-else class="muted">—</span>
                </template>
              </el-table-column>
              <el-table-column label="候选人" min-width="150">
                <template #default="{ row }">
                  {{ row.candidate?.name }}
                  <span class="hint">{{ row.candidate?.degree }}</span>
                </template>
              </el-table-column>
              <el-table-column label="硬性条件" width="110">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.hard_pass ? 'success' : 'danger'" effect="plain">
                    {{ row.hard_pass ? '通过' : '未通过' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="方向" width="70">
                <template #default="{ row }">{{ row.direction_score }}</template>
              </el-table-column>
              <el-table-column label="成果" width="70">
                <template #default="{ row }">{{ row.outputs_score }}</template>
              </el-table-column>
              <el-table-column label="项目" width="70">
                <template #default="{ row }">{{ row.projects_score }}</template>
              </el-table-column>
              <el-table-column label="教学" width="70">
                <template #default="{ row }">{{ row.teaching_score }}</template>
              </el-table-column>
              <el-table-column label="综合分" width="88">
                <template #default="{ row }">
                  <strong :style="{ color: row.hard_pass ? '#2f5597' : '#9aa7b8' }">{{ row.total_score }}</strong>
                </template>
              </el-table-column>
              <el-table-column label="评审状态" width="110">
                <template #default="{ row }">
                  <el-tag size="small" :type="reviewType(row.review_status)" effect="plain">
                    {{ reviewLabel(row.review_status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column v-if="auth.isEditor" label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openReview(row)">评审</el-button>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 岗位表单 -->
    <el-dialog v-model="positionFormVisible" :title="positionEditingId ? '编辑招聘岗位' : '新增招聘岗位'" width="720px"
               :close-on-click-modal="false" destroy-on-close>
      <el-form ref="positionFormRef" :model="positionForm" :rules="positionRules" label-width="100px">
        <el-form-item label="岗位名称" prop="name"><el-input v-model="positionForm.name" /></el-form-item>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="学院" prop="college">
              <el-select v-model="positionForm.college" filterable allow-create default-first-option
                         style="width: 100%" @change="onPositionCollegeChange">
                <el-option v-for="item in collegeOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学科" prop="discipline">
              <el-select v-model="positionForm.discipline" filterable allow-create default-first-option
                         :disabled="!positionForm.college"
                         :placeholder="positionForm.college ? '请选择学科' : '请先选择学院'"
                         style="width: 100%">
                <el-option v-for="item in positionDisciplines" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="学历要求">
              <el-select v-model="positionForm.required_degree" style="width: 100%">
                <el-option v-for="item in ['博士', '硕士', '学士']" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="最低成果">
              <el-input-number v-model="positionForm.min_outputs" :min="0" :max="100" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="状态">
              <el-select v-model="positionForm.status" style="width: 100%">
                <el-option label="招聘中" value="open" />
                <el-option label="已关闭" value="closed" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="研究方向"><el-input v-model="positionForm.research_direction" /></el-form-item>
        <el-form-item label="研究主题">
          <el-input v-model="positionForm.research_topics" placeholder="用于 TF-IDF 方向匹配，可填多个主题" />
        </el-form-item>
        <el-form-item label="岗位要求">
          <el-input v-model="positionForm.requirements_desc" type="textarea" :rows="2" />
        </el-form-item>

        <div class="weight-box">
          <div class="weight-box-title">评分权重（提交时自动归一化）</div>
          <div v-for="key in weightKeys" :key="key" class="weight-row">
            <span>{{ candidateWeightLabels[key] }}</span>
            <el-slider v-model="positionForm.weights[key]" :min="0" :max="100" :step="5" show-input
                       :show-input-controls="false" style="flex: 1" />
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="positionFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="positionSaving" @click="submitPosition">保存</el-button>
      </template>
    </el-dialog>

    <!-- 候选人表单 -->
    <el-dialog v-model="candidateFormVisible" :title="candidateEditingId ? '编辑候选人' : '新增候选人'" width="720px"
               :close-on-click-modal="false" destroy-on-close>
      <el-form ref="candidateFormRef" :model="candidateForm" :rules="candidateRules" label-width="100px">
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="姓名" prop="name"><el-input v-model="candidateForm.name" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学历">
              <el-select v-model="candidateForm.degree" clearable style="width: 100%">
                <el-option v-for="item in ['博士', '硕士', '学士']" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="毕业院校"><el-input v-model="candidateForm.graduate_school" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="专业"><el-input v-model="candidateForm.major" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="研究方向"><el-input v-model="candidateForm.research_direction" /></el-form-item>
        <el-form-item label="关键词"><el-input v-model="candidateForm.keywords" placeholder="逗号分隔" /></el-form-item>
        <el-row :gutter="14">
          <el-col :span="8">
            <el-form-item label="成果数量">
              <el-input-number v-model="candidateForm.outputs_count" :min="0" :max="1000" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="项目数量">
              <el-input-number v-model="candidateForm.projects_count" :min="0" :max="1000" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="教学年限">
              <el-input-number v-model="candidateForm.teaching_years" :min="0" :max="80" :precision="1" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="成果证据">
          <el-input v-model="candidateForm.output_evidence" type="textarea" :rows="2" placeholder="如：SCI 论文 3 篇（列表见附件）" />
        </el-form-item>
        <el-form-item label="项目证据">
          <el-input v-model="candidateForm.project_evidence" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="教学证据">
          <el-input v-model="candidateForm.teaching_evidence" type="textarea" :rows="2" />
        </el-form-item>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="资料来源"><el-input v-model="candidateForm.source" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="待核验字段"><el-input v-model="candidateForm.unverified_fields" placeholder="如：项目数量、获奖" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="candidateFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="candidateSaving" @click="submitCandidate">保存</el-button>
      </template>
    </el-dialog>

    <!-- 人工评审 -->
    <el-dialog v-model="reviewVisible" title="人工评审意见" width="520px">
      <div v-if="reviewTarget" class="review-target">
        <strong>{{ reviewTarget.candidate?.name }}</strong>
        <span class="hint">
          硬性条件{{ reviewTarget.hard_pass ? '通过' : '未通过' }} · 综合分 {{ reviewTarget.total_score }}
          <template v-if="reviewTarget.rank"> · 排名 {{ reviewTarget.rank }}</template>
        </span>
      </div>
      <el-form label-width="90px">
        <el-form-item label="评审状态">
          <el-select v-model="reviewForm.review_status" style="width: 100%">
            <el-option label="待评审" value="pending" />
            <el-option label="已评审" value="reviewed" />
            <el-option label="进入短名单" value="shortlisted" />
            <el-option label="不进入下一环节" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="评审备注">
          <el-input v-model="reviewForm.review_note" type="textarea" :rows="3"
                    placeholder="记录人工判断依据、面试情况或需补充的材料" />
        </el-form-item>
      </el-form>
      <p class="hint">
        人工评审状态独立于系统得分；系统不会因得分高低自动改变评审状态。
      </p>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="primary" :loading="reviewSaving" @click="submitReview">保存评审</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importResultVisible" title="候选人导入结果" width="520px">
      <template v-if="importResult">
        <div class="import-stats">
          <div><strong>{{ importResult.total_rows }}</strong><span>总行数</span></div>
          <div><strong class="ok">{{ importResult.success_rows }}</strong><span>成功</span></div>
          <div><strong class="warn">{{ importResult.failed_rows }}</strong><span>失败</span></div>
          <div><strong class="warn">{{ importResult.duplicate_rows }}</strong><span>重复</span></div>
        </div>
        <p class="hint">
          导入批次 #{{ importResult.id }} 已记录。若有失败行，可在“数据管理 → 导入批次”查看并下载错误明细 CSV。
        </p>
      </template>
      <template #footer>
        <el-button @click="importResultVisible = false">关闭</el-button>
        <el-button type="primary" @click="$router.push('/data'); importResultVisible = false">前往数据管理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DataAnalysis, Download, Plus, Refresh, Upload,
} from '@element-plus/icons-vue'
import api, { downloadFile } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { disciplinesForCollege, type CollegeDisciplineMap } from '../utils/linkage'

const auth = useAuthStore()
const positions = ref<any[]>([])
const positionLoading = ref(false)
const selectedPosition = ref<any>(null)
const candidates = ref<any[]>([])
const candidateLoading = ref(false)
const candidateTab = ref('candidates')
const evaluations = ref<any[]>([])
const evaluating = ref(false)
const uploading = ref(false)
const collegeOptions = ref<string[]>([])
const disciplineMap = ref<CollegeDisciplineMap>({})

const weightKeys = ['direction', 'outputs', 'projects', 'teaching']
const candidateWeightLabels: Record<string, string> = {
  direction: '研究方向相似度',
  outputs: '科研成果',
  projects: '项目经历',
  teaching: '教学经历',
}

const positionFormVisible = ref(false)
const positionEditingId = ref<number | null>(null)
const positionSaving = ref(false)
const positionFormRef = ref()
const defaultPosition = () => ({
  name: '', college: '', discipline: '', research_direction: '', required_degree: '博士',
  min_outputs: 2, research_topics: '', requirements_desc: '', status: 'open',
  weights: { direction: 45, outputs: 25, projects: 20, teaching: 10 } as Record<string, number>,
})
const positionForm = reactive<any>(defaultPosition())
const positionDisciplines = computed(() =>
  disciplinesForCollege(disciplineMap.value, positionForm.college, positionForm.discipline),
)
const positionRules = {
  name: [{ required: true, message: '请输入岗位名称', trigger: 'blur' }],
  college: [{ required: true, message: '请选择学院', trigger: 'change' }],
  discipline: [{ required: true, message: '请选择学科', trigger: 'change' }],
}

const candidateFormVisible = ref(false)
const candidateEditingId = ref<number | null>(null)
const candidateSaving = ref(false)
const candidateFormRef = ref()
const defaultCandidate = () => ({
  name: '', degree: '博士', graduate_school: '', major: '', research_direction: '',
  keywords: '', outputs_count: 0, projects_count: 0, teaching_years: 0,
  output_evidence: '', project_evidence: '', teaching_evidence: '',
  source: '手动录入', unverified_fields: '',
})
const candidateForm = reactive<any>(defaultCandidate())
const candidateRules = {
  name: [{ required: true, message: '请输入候选人姓名', trigger: 'blur' }],
}

const reviewVisible = ref(false)
const reviewSaving = ref(false)
const reviewTarget = ref<any>(null)
const reviewForm = reactive({ review_status: 'reviewed', review_note: '' })

const importResultVisible = ref(false)
const importResult = ref<any>(null)

function pct(value: number | undefined) {
  return `${Math.round((value || 0) * 100)}%`
}

function reviewLabel(status: string) {
  return {
    pending: '待评审', reviewed: '已评审', shortlisted: '进入短名单', rejected: '不进入下一环节',
  }[status] || status
}

function reviewType(status: string) {
  return { pending: 'info', reviewed: '', shortlisted: 'success', rejected: 'danger' }[status] || 'info'
}

function evaluationScores(row: any) {
  return [
    { label: '研究方向', value: row.direction_score || 0 },
    { label: '科研成果', value: row.outputs_score || 0 },
    { label: '项目经历', value: row.projects_score || 0 },
    { label: '教学经历', value: row.teaching_score || 0 },
  ]
}

async function loadOptions() {
  const { data } = await api.get('/teachers/options')
  collegeOptions.value = data.colleges
  disciplineMap.value = data.disciplines_by_college || {}
}

function onPositionCollegeChange() {
  positionForm.discipline = ''
}

async function loadPositions() {
  positionLoading.value = true
  try {
    const { data } = await api.get('/recruitment/positions')
    positions.value = data.items
    if (selectedPosition.value) {
      const refreshed = positions.value.find((row) => row.id === selectedPosition.value.id)
      if (refreshed) selectedPosition.value = refreshed
    }
  } finally {
    positionLoading.value = false
  }
}

async function selectPosition(row: any) {
  selectedPosition.value = row
  candidateTab.value = 'candidates'
  await Promise.all([loadCandidates(), loadEvaluations()])
}

async function loadCandidates() {
  if (!selectedPosition.value) return
  candidateLoading.value = true
  try {
    const { data } = await api.get('/recruitment/candidates', {
      params: { position_id: selectedPosition.value.id, page: 1, page_size: 100 },
    })
    candidates.value = data.items
  } finally {
    candidateLoading.value = false
  }
}

async function loadEvaluations() {
  if (!selectedPosition.value) return
  const { data } = await api.get(`/recruitment/positions/${selectedPosition.value.id}/evaluations`)
  evaluations.value = data.items
}

async function evaluateSelected() {
  if (!selectedPosition.value) return
  if (!candidates.value.length) {
    ElMessage.warning('该岗位暂无候选人')
    return
  }
  evaluating.value = true
  try {
    const { data } = await api.post(`/recruitment/positions/${selectedPosition.value.id}/evaluate`)
    evaluations.value = data.items
    candidateTab.value = 'evaluations'
    ElMessage.success(`评估完成：${data.summary.hard_pass} 人通过硬性条件，${data.summary.hard_fail} 人未通过`)
    await loadPositions()
  } finally {
    evaluating.value = false
  }
}

async function quickEvaluate(row: any) {
  selectedPosition.value = row
  await loadCandidates()
  await evaluateSelected()
}

function openPositionCreate() {
  positionEditingId.value = null
  Object.assign(positionForm, defaultPosition())
  positionFormVisible.value = true
}

function openPositionEdit(row: any) {
  positionEditingId.value = row.id
  Object.assign(positionForm, defaultPosition(), {
    ...row,
    weights: { ...defaultPosition().weights, ...(row.weights || {}) },
  })
  positionFormVisible.value = true
}

async function submitPosition() {
  await positionFormRef.value?.validate()
  positionSaving.value = true
  try {
    if (positionEditingId.value) {
      await api.put(`/recruitment/positions/${positionEditingId.value}`, { ...positionForm })
      ElMessage.success('岗位已更新')
    } else {
      await api.post('/recruitment/positions', { ...positionForm })
      ElMessage.success('岗位已创建')
    }
    positionFormVisible.value = false
    await loadPositions()
    if (selectedPosition.value) {
      const refreshed = positions.value.find((row) => row.id === selectedPosition.value.id)
      if (refreshed) selectedPosition.value = refreshed
    }
  } finally {
    positionSaving.value = false
  }
}

async function removePosition(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除招聘岗位“${row.name}”吗？已有候选人的岗位不能删除。`,
      '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch {
    return
  }
  await api.delete(`/recruitment/positions/${row.id}`)
  ElMessage.success('岗位已删除')
  if (selectedPosition.value?.id === row.id) selectedPosition.value = null
  await loadPositions()
}

function openCandidateCreate() {
  candidateEditingId.value = null
  Object.assign(candidateForm, defaultCandidate())
  candidateFormVisible.value = true
}

function openCandidateEdit(row: any) {
  candidateEditingId.value = row.id
  Object.assign(candidateForm, defaultCandidate(), row)
  candidateFormVisible.value = true
}

async function submitCandidate() {
  await candidateFormRef.value?.validate()
  candidateSaving.value = true
  try {
    if (candidateEditingId.value) {
      const { position_id, ...payload } = candidateForm
      await api.put(`/recruitment/candidates/${candidateEditingId.value}`, payload)
      ElMessage.success('候选人已更新')
    } else {
      await api.post('/recruitment/candidates', {
        ...candidateForm,
        position_id: selectedPosition.value.id,
      })
      ElMessage.success('候选人已创建')
    }
    candidateFormVisible.value = false
    await Promise.all([loadCandidates(), loadPositions()])
  } finally {
    candidateSaving.value = false
  }
}

async function removeCandidate(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除候选人“${row.name}”吗？其评估记录也会被删除。`,
      '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch {
    return
  }
  await api.delete(`/recruitment/candidates/${row.id}`)
  ElMessage.success('候选人已删除')
  await Promise.all([loadCandidates(), loadEvaluations(), loadPositions()])
}

function openReview(row: any) {
  reviewTarget.value = row
  reviewForm.review_status = row.review_status || 'reviewed'
  reviewForm.review_note = row.review_note || ''
  reviewVisible.value = true
}

async function submitReview() {
  if (!reviewTarget.value) return
  reviewSaving.value = true
  try {
    await api.put(`/recruitment/evaluations/${reviewTarget.value.id}/review`, {
      review_status: reviewForm.review_status,
      review_note: reviewForm.review_note || null,
    })
    ElMessage.success('评审意见已保存')
    reviewVisible.value = false
    await loadEvaluations()
  } finally {
    reviewSaving.value = false
  }
}

async function downloadTemplate() {
  await downloadFile('/imports/templates/candidates', '候选人档案导入模板.csv')
}

async function uploadCandidates(options: any) {
  if (!selectedPosition.value) return
  const file = options.file as File
  const form = new FormData()
  form.append('file', file)
  uploading.value = true
  try {
    const { data } = await api.post('/imports/candidates', form, {
      params: { position_id: selectedPosition.value.id },
    })
    importResult.value = data
    importResultVisible.value = true
    ElMessage.success(`导入完成：成功 ${data.success_rows} 行，失败 ${data.failed_rows} 行`)
    await Promise.all([loadCandidates(), loadPositions()])
  } finally {
    uploading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadOptions(), loadPositions()])
})
</script>

<style scoped>
.candidate-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px dashed #e6ebf3;
  margin-bottom: 8px;
}

.position-title {
  font-size: 17px;
  font-weight: 600;
  color: #1c2f4a;
  display: flex;
  align-items: center;
  gap: 8px;
}

.eval-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.eval-summary div {
  background: #f7f9fd;
  border: 1px solid #eef1f7;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.eval-summary strong {
  font-size: 21px;
  color: #2f5597;
}

.eval-summary strong.ok {
  color: #1f9d72;
}

.eval-summary strong.warn {
  color: #c46f1f;
}

.eval-summary span {
  font-size: 11px;
  color: #7a8797;
}

.eval-detail {
  padding: 8px 18px 14px 48px;
  background: #fafcff;
}

.eval-scores {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 12px;
}

.eval-score-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: #7a8797;
}

.eval-score-item b {
  align-self: flex-end;
  font-size: 12px;
  color: #4a5b72;
}

.eval-columns {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 20px;
}

.mini-title {
  font-size: 12px;
  font-weight: 600;
  color: #2f5597;
  margin-bottom: 6px;
}

.eval-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.75;
  color: #4a5b72;
  white-space: pre-wrap;
  font-family: inherit;
}

.review-line {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  border-top: 1px dashed #e6ebf3;
  padding-top: 10px;
  margin-top: 12px;
}

.review-line .el-button {
  margin-left: auto;
}

.weight-box {
  background: #f7f9fd;
  border: 1px solid #eef1f7;
  border-radius: 8px;
  padding: 12px 14px;
}

.weight-box-title {
  font-size: 12px;
  color: #2f5597;
  font-weight: 600;
  margin-bottom: 8px;
}

.weight-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.weight-row > span {
  width: 110px;
  font-size: 12px;
  color: #5c6c82;
  text-align: right;
}

.review-target {
  display: flex;
  align-items: baseline;
  gap: 12px;
  background: #f7f9fd;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 14px;
}

.import-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}

.import-stats div {
  background: #f7f9fd;
  border: 1px solid #eef1f7;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.import-stats strong {
  font-size: 20px;
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
</style>
