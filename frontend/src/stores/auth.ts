import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import api from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('b3_token') || '')
  const user = ref<any>(JSON.parse(localStorage.getItem('b3_user') || 'null'))

  const isLoggedIn = computed(() => Boolean(token.value))
  const isEditor = computed(() => ['admin', 'manager'].includes(user.value?.role))
  const isAdmin = computed(() => user.value?.role === 'admin')
  const roleLabel = computed(() => user.value?.role_label || user.value?.role || '')

  function setSession(accessToken: string, profile: any) {
    token.value = accessToken
    user.value = profile
    localStorage.setItem('b3_token', accessToken)
    localStorage.setItem('b3_user', JSON.stringify(profile))
  }

  async function login(username: string, password: string) {
    const { data } = await api.post('/auth/login', { username, password })
    setSession(data.access_token, data.user)
    return data.user
  }

  async function fetchMe() {
    const { data } = await api.get('/auth/me')
    user.value = data
    localStorage.setItem('b3_user', JSON.stringify(data))
    return data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('b3_token')
    localStorage.removeItem('b3_user')
  }

  return { token, user, isLoggedIn, isEditor, isAdmin, roleLabel, login, fetchMe, logout }
})
