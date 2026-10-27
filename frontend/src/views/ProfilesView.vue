<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">智能画像</h2>
        <p class="page-subtitle">
          从科研成果、项目、教学、社会服务与档案完整度五个维度，按数据库记录实时生成教师画像。
          画像中的每一个数字均可追溯到原始业务记录。
        </p>
      </div>
      <div class="page-actions">
        <el-select v-model="quickId" filterable clearable placeholder="直接选择教师" style="width: 260px" @change="goQuick">
          <el-option v-for="item in allTeachers" :key="item.id" :value="item.id"
                     :label="`${item.name} · ${item.college} · ${item.title}`" />
        </el-select>
      </div>
    </div>

    <div class="panel filters">
      <el-input v-model="query.keyword" class="search" placeholder="搜索姓名、研究方向、关键词" clearable
                :prefix-icon="Search" @keyup.enter="search" />
      <el-select v-model="query.college" placeholder="学院" clearable @change="onCollegeChange">
        <el-option v-for="item in options.colleges" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="query.discipline" :placeholder="query.college ? '学科' : '请先选择学院'"
                 :disabled="!query.college" clearable filterable>
        <el-option v-for="item in disciplineOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="query.title" placeholder="职称" clearable>
        <el-option v-for="item in options.titles" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="query.advisor_qualified" placeholder="导师资格" clearable>
        <el-option label="具有导师资格" :value="true" />
        <el-option label="无导师资格" :value="false" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="search">查询</el-button>
      <el-button :icon="RefreshLeft" @click="reset">重置</el-button>
    </div>

    <div v-loading="loading" class="profile-grid">
      <div v-for="teacher in rows" :key="teacher.id" class="teacher-card">
        <div class="card-head">
          <div class="avatar">{{ teacher.name?.slice(0, 1) }}</div>
          <div class="card-name">
            <div class="name-line">
              {{ teacher.name }}
              <el-tag size="small" effect="plain">{{ teacher.title }}</el-tag>
            </div>
            <div class="hint">{{ teacher.college }} · {{ teacher.discipline }}</div>
          </div>
        </div>
        <div class="direction">{{ teacher.research_direction || '研究方向未填写' }}</div>
        <div class="card-tags">
          <el-tag v-if="teacher.advisor_qualified" size="small" type="success" effect="plain">
            导师 {{ teacher.current_students }}/{{ teacher.capacity }}
          </el-tag>
          <el-tag v-if="teacher.verification_status !== 'verified'" size="small" type="warning" effect="plain">
            数据待核验
          </el-tag>
          <el-tag v-if="!teacher.research_keywords" size="small" type="info" effect="plain">缺关键词</el-tag>
          <el-tag v-if="teacher.status !== 'active'" size="small" type="info" effect="plain">
            {{ teacher.status_label }}
          </el-tag>
        </div>
        <div class="card-foot">
          <span class="hint">编号 {{ teacher.teacher_no }}</span>
          <el-button type="primary" link @click="$router.push(`/teachers/${teacher.id}/profile`)">
            查看多维画像 →
          </el-button>
        </div>
      </div>
      <div v-if="!loading && !rows.length" class="empty-block" style="grid-column: 1 / -1">
        未找到符合条件的教师
      </div>
    </div>

    <div class="panel pager-row">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[12, 24, 48]"
        layout="total, sizes, prev, pager, next"
        @size-change="load"
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { RefreshLeft, Search } from '@element-plus/icons-vue'
import api from '../api/client'
import { disciplinesForCollege, type CollegeDisciplineMap } from '../utils/linkage'

const router = useRouter()
const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const allTeachers = ref<any[]>([])
const quickId = ref<number | null>(null)
const options = reactive({
  colleges: [] as string[],
  disciplines: [] as string[],
  disciplinesByCollege: {} as CollegeDisciplineMap,
  titles: [] as string[],
})
const query = reactive({
  keyword: '', college: '', discipline: '', title: '',
  advisor_qualified: null as boolean | null, page: 1, page_size: 12,
})
const disciplineOptions = computed(() =>
  disciplinesForCollege(options.disciplinesByCollege, query.college, query.discipline),
)

async function load() {
  loading.value = true
  try {
    const params: any = { ...query }
    if (params.advisor_qualified === null) delete params.advisor_qualified
    const { data } = await api.get('/teachers', { params })
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  const [optionsRes, listRes] = await Promise.all([
    api.get('/teachers/options'),
    api.get('/teachers', { params: { page: 1, page_size: 100, sort_by: 'name', sort_order: 'asc' } }),
  ])
  options.colleges = optionsRes.data.colleges
  options.disciplines = optionsRes.data.disciplines
  options.disciplinesByCollege = optionsRes.data.disciplines_by_college || {}
  options.titles = optionsRes.data.titles
  allTeachers.value = listRes.data.items
}

function onCollegeChange() {
  query.discipline = ''
}

function search() {
  query.page = 1
  load()
}

function reset() {
  Object.assign(query, {
    keyword: '', college: '', discipline: '', title: '',
    advisor_qualified: null, page: 1, page_size: 12,
  })
  load()
}

function goQuick(id: number) {
  if (id) router.push(`/teachers/${id}/profile`)
}

onMounted(async () => {
  await Promise.all([loadMeta(), load()])
})
</script>

<style scoped>
.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  min-height: 120px;
}

.teacher-card {
  background: #fff;
  border: 1px solid var(--b3-border);
  border-radius: 10px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.teacher-card:hover {
  box-shadow: 0 8px 24px rgba(24, 52, 94, 0.08);
  transform: translateY(-1px);
}

.card-head {
  display: flex;
  gap: 12px;
  align-items: center;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4d7ac9, #2f5597);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
}

.card-name {
  flex: 1;
  min-width: 0;
}

.name-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1f3350;
}

.hint {
  font-size: 12px;
  color: #8494a8;
}

.direction {
  font-size: 13px;
  color: #4a5b72;
  min-height: 38px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 24px;
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px dashed #eef1f6;
  padding-top: 10px;
}

.pager-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
