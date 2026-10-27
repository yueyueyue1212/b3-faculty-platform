import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MainLayout from '../layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/',
      component: MainLayout,
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
          meta: { title: '人才驾驶舱' },
        },
        {
          path: 'teachers',
          name: 'teachers',
          component: () => import('../views/TeachersView.vue'),
          meta: { title: '教师档案' },
        },
        {
          path: 'profiles',
          name: 'profiles',
          component: () => import('../views/ProfilesView.vue'),
          meta: { title: '智能画像' },
        },
        {
          path: 'teachers/:id/profile',
          name: 'teacher-profile',
          component: () => import('../views/TeacherProfileView.vue'),
          meta: { title: '智能画像' },
        },
        {
          path: 'talent',
          name: 'talent',
          component: () => import('../views/TalentReviewView.vue'),
          meta: { title: '人才盘点' },
        },
        {
          path: 'advisor',
          name: 'advisor',
          component: () => import('../views/AdvisorMatchView.vue'),
          meta: { title: '导师匹配' },
        },
        {
          path: 'matching',
          name: 'matching',
          component: () => import('../views/MatchDegreeView.vue'),
          meta: { title: '师生匹配度' },
        },
        {
          path: 'promotion',
          name: 'promotion',
          component: () => import('../views/PromotionView.vue'),
          meta: { title: '职称申报' },
        },
        {
          path: 'recruitment',
          name: 'recruitment',
          component: () => import('../views/RecruitmentView.vue'),
          meta: { title: '人才引进' },
        },
        {
          path: 'data',
          name: 'data',
          component: () => import('../views/DataManagementView.vue'),
          meta: { title: '数据管理' },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('../views/SettingsView.vue'),
          meta: { title: '系统设置' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (to.name === 'login' && auth.token) return { path: '/dashboard' }
    return true
  }
  if (!auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }
  document.title = `${to.meta.title || '工作台'} · B3 高校师资人才智能画像平台`
  return true
})

export default router
