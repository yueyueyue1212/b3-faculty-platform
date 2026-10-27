<template>
  <div class="login-page">
    <div class="login-left">
      <div class="brand-row">
        <div class="brand-mark">B3</div>
        <div>
          <div class="brand-name">高校师资 / 人才智能画像与辅助管理平台</div>
          <div class="brand-sub">Faculty Intelligence · Talent Insight</div>
        </div>
      </div>

      <div class="hero">
        <h1>以数据看见人才<br />以规则解释匹配</h1>
        <p>
          教师多维画像、人才结构分析、导师智能匹配、职称材料归集与青年人才引进评估，
          所有统计均可从数据库复现，AI 仅作辅助，不做自动决策。
        </p>
        <div class="feature-grid">
          <div class="feature">
            <el-icon><DataAnalysis /></el-icon>
            <div><strong>真实统计</strong><span>驾驶舱与画像由数据库实时计算</span></div>
          </div>
          <div class="feature">
            <el-icon><Connection /></el-icon>
            <div><strong>可解释匹配</strong><span>硬性条件过滤 + 分项得分与理由</span></div>
          </div>
          <div class="feature">
            <el-icon><DocumentChecked /></el-icon>
            <div><strong>材料归集</strong><span>缺项、重复、冲突与待核验识别</span></div>
          </div>
          <div class="feature">
            <el-icon><Lock /></el-icon>
            <div><strong>权限与审计</strong><span>三级角色、敏感信息脱敏与操作留痕</span></div>
          </div>
        </div>
      </div>

      <div class="left-foot">
        演示数据均标记为“模拟数据（B3演示）”，不代表任何真实高校或个人信息。
      </div>
    </div>

    <div class="login-right">
      <div class="login-card">
        <h2>账号登录</h2>
        <p class="login-hint">请使用系统分配的账号登录。演示环境可使用下方快捷账号。</p>

        <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="submit">
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" autocomplete="username" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              prefix-icon="Lock"
              show-password
              autocomplete="current-password"
            />
          </el-form-item>
          <el-button type="primary" class="login-button" :loading="loading" @click="submit">
            登 录
          </el-button>
        </el-form>

        <div class="demo-accounts">
          <div class="demo-title">演示账号（点击填充）</div>
          <div class="account-list">
            <button v-for="account in accounts" :key="account.username" class="account" @click="fill(account)">
              <span class="account-role">{{ account.role }}</span>
              <span class="account-name">{{ account.username }}</span>
              <span class="account-pwd">{{ account.password }}</span>
            </button>
          </div>
        </div>

        <div class="login-note">
          只读用户无法修改数据，敏感联系方式将脱敏展示。生产环境请替换默认密码与 SECRET_KEY。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const formRef = ref()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin123' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const accounts = [
  { role: '管理员', username: 'admin', password: 'admin123' },
  { role: '业务人员', username: 'manager', password: 'manager123' },
  { role: '只读用户', username: 'viewer', password: 'viewer123' },
]

function fill(account: { username: string; password: string }) {
  form.username = account.username
  form.password = account.password
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    router.push(redirect)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(420px, 0.85fr);
  background: #f6f8fc;
}

.login-left {
  background:
    radial-gradient(circle at 15% 20%, rgba(90, 130, 200, 0.35), transparent 45%),
    linear-gradient(150deg, #0f2443 0%, #18365f 55%, #214472 100%);
  color: #e8effa;
  padding: 40px 56px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
}

.login-left::after {
  content: "";
  position: absolute;
  right: -140px;
  bottom: -180px;
  width: 520px;
  height: 520px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 50%;
  box-shadow: 0 0 0 70px rgba(255, 255, 255, 0.028), 0 0 0 150px rgba(255, 255, 255, 0.02);
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 14px;
  position: relative;
  z-index: 1;
}

.brand-mark {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  letter-spacing: 0.5px;
}

.brand-name {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.brand-sub {
  font-size: 11px;
  color: #9fb5d6;
  letter-spacing: 1.2px;
  margin-top: 3px;
  text-transform: uppercase;
}

.hero {
  max-width: 600px;
  position: relative;
  z-index: 1;
  margin: 32px 0;
}

.hero h1 {
  font-size: 38px;
  line-height: 1.35;
  margin: 0 0 18px;
  font-weight: 650;
  letter-spacing: 1px;
}

.hero p {
  color: #b7c8e0;
  line-height: 1.9;
  font-size: 14px;
  margin: 0 0 30px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.feature {
  display: flex;
  gap: 12px;
  padding: 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.feature .el-icon {
  font-size: 20px;
  color: #8fb4ee;
  margin-top: 2px;
}

.feature div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.feature strong {
  font-size: 13px;
  color: #fff;
}

.feature span {
  font-size: 12px;
  color: #a7bad6;
  line-height: 1.5;
}

.left-foot {
  font-size: 12px;
  color: #8da4c4;
  position: relative;
  z-index: 1;
}

.login-right {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border: 1px solid #e7ecf4;
  border-radius: 16px;
  padding: 36px 36px 28px;
  box-shadow: 0 18px 50px rgba(22, 45, 82, 0.08);
}

.login-card h2 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #1c2f4a;
}

.login-hint {
  margin: 0 0 24px;
  color: #8494a8;
  font-size: 13px;
  line-height: 1.7;
}

.login-button {
  width: 100%;
  margin-top: 4px;
  height: 44px;
  font-size: 15px;
  letter-spacing: 4px;
}

.demo-accounts {
  margin-top: 26px;
  padding-top: 20px;
  border-top: 1px dashed #e3e9f2;
}

.demo-title {
  font-size: 12px;
  color: #93a1b4;
  margin-bottom: 10px;
}

.account-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.account {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border: 1px solid #e6ebf3;
  border-radius: 8px;
  background: #fafbfe;
  cursor: pointer;
  font-size: 12px;
  color: #4a5b72;
  text-align: left;
  transition: all 0.15s ease;
}

.account:hover {
  border-color: #b9c9e3;
  background: #f2f6fd;
}

.account-role {
  background: #eef3fb;
  color: #2f5597;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
}

.account-name {
  flex: 1;
}

.account-pwd {
  color: #93a1b4;
  font-family: Consolas, monospace;
}

.login-note {
  margin-top: 18px;
  font-size: 11px;
  line-height: 1.7;
  color: #9aa8ba;
}

@media (max-width: 1024px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .login-left {
    display: none;
  }
}
</style>
