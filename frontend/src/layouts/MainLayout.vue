<template>
  <el-container class="layout">
    <el-aside width="236px" class="sidebar">
      <div class="brand">
        <div class="brand-mark">B3</div>
        <div class="brand-text">
          <strong>师资人才平台</strong>
          <span>智能画像与辅助管理</span>
        </div>
      </div>

      <el-menu :default-active="activeMenu" router class="side-menu" :collapse="false">
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon><span>人才驾驶舱</span>
        </el-menu-item>
        <el-menu-item index="/teachers">
          <el-icon><User /></el-icon><span>教师档案</span>
        </el-menu-item>
        <el-menu-item index="/talent">
          <el-icon><PieChart /></el-icon><span>人才盘点</span>
        </el-menu-item>
        <el-menu-item index="/advisor">
          <el-icon><Connection /></el-icon><span>导师匹配</span>
        </el-menu-item>
        <el-menu-item index="/matching">
          <el-icon><Aim /></el-icon><span>师生匹配度</span>
        </el-menu-item>
        <el-menu-item index="/promotion">
          <el-icon><DocumentChecked /></el-icon><span>职称申报</span>
        </el-menu-item>
        <el-menu-item index="/recruitment">
          <el-icon><UserFilled /></el-icon><span>人才引进</span>
        </el-menu-item>
        <el-menu-item index="/data">
          <el-icon><UploadFilled /></el-icon><span>数据管理</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon><span>系统设置</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-foot">
        <span class="dot" />演示数据已标记
        <div>B3 · v1.0.0</div>
      </div>
    </el-aside>

    <el-container class="right-area">
      <el-header class="topbar">
        <div class="topbar-left">
          <h1>{{ route.meta.title || '工作台' }}</h1>
          <el-tag size="small" effect="plain" class="demo-tag">演示环境 · 模拟数据</el-tag>
        </div>
        <div class="topbar-right">
          <el-tag size="small" :type="auth.isAdmin ? 'danger' : 'info'" effect="light">
            {{ auth.roleLabel }}
          </el-tag>
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-chip">
              <el-avatar :size="30">{{ initials }}</el-avatar>
              <span class="user-name">{{ auth.user?.display_name || auth.user?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ auth.user?.username }}</el-dropdown-item>
                <el-dropdown-item command="password" divided>
                  <el-icon><Lock /></el-icon>修改密码
                </el-dropdown-item>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="passwordVisible" title="修改密码" width="440px" :close-on-click-modal="false">
    <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="90px">
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="passwordForm.old_password" type="password" show-password autocomplete="current-password" />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="passwordForm.new_password" type="password" show-password autocomplete="new-password" />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm">
        <el-input v-model="passwordForm.confirm" type="password" show-password autocomplete="new-password" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="passwordVisible = false">取消</el-button>
      <el-button type="primary" :loading="passwordSaving" @click="submitPassword">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import api from '../api/client'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => {
  if (route.path.startsWith('/teachers/')) return '/teachers'
  return route.path
})

const initials = computed(() => {
  const name = auth.user?.display_name || auth.user?.username || 'U'
  return String(name).slice(0, 1)
})

const passwordVisible = ref(false)
const passwordSaving = ref(false)
const passwordFormRef = ref()
const passwordForm = reactive({ old_password: '', new_password: '', confirm: '' })
const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: any) => {
        if (value !== passwordForm.new_password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

function handleCommand(command: string) {
  if (command === 'logout') {
    ElMessageBox.confirm('确认退出当前账号？', '退出登录', { type: 'warning' })
      .then(() => {
        auth.logout()
        router.push('/login')
      })
      .catch(() => undefined)
  } else if (command === 'password') {
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm = ''
    passwordVisible.value = true
  }
}

async function submitPassword() {
  await passwordFormRef.value?.validate()
  passwordSaving.value = true
  try {
    await api.post('/auth/change-password', {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码已修改，请重新登录')
    passwordVisible.value = false
    auth.logout()
    router.push('/login')
  } finally {
    passwordSaving.value = false
  }
}
</script>

<style scoped>
.layout {
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  background: linear-gradient(180deg, #13294b 0%, #0e2039 100%);
  color: #dce6f5;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 18px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4d7ac9, #2f5597);
  color: #fff;
  font-weight: 700;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}

.brand-text strong {
  color: #fff;
  font-size: 15px;
  letter-spacing: 0.5px;
}

.brand-text span {
  color: #8ea4c4;
  font-size: 11px;
}

.side-menu {
  border-right: none;
  background: transparent;
  padding: 12px 10px;
  flex: 1;
  overflow-y: auto;
}

.side-menu :deep(.el-menu-item) {
  color: #b8c7dc;
  height: 44px;
  border-radius: 8px;
  margin-bottom: 4px;
  font-size: 14px;
}

.side-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.side-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(77, 122, 201, 0.95), rgba(47, 85, 151, 0.9));
  color: #fff;
  box-shadow: 0 4px 12px rgba(10, 25, 48, 0.35);
}

.sidebar-foot {
  padding: 14px 18px 18px;
  color: #7f95b5;
  font-size: 11px;
  line-height: 1.9;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.sidebar-foot .dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #62c79b;
  margin-right: 6px;
}

.right-area {
  height: 100vh;
  overflow: hidden;
}

.topbar {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid var(--b3-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-left h1 {
  font-size: 17px;
  margin: 0;
  font-weight: 600;
}

.demo-tag {
  border-color: #d8e2f2;
  color: #5a6f8f;
  background: #f7f9fd;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #37475d;
  font-size: 13px;
  outline: none;
}

.user-chip .el-avatar {
  background: #2f5597;
  color: #fff;
  font-size: 13px;
}

.user-name {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.main {
  padding: 0;
  background: var(--b3-bg);
  overflow-y: auto;
  height: calc(100vh - 60px);
}
</style>
