import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('b3_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const response = error.response
    if (response?.status === 401) {
      const isLogin = window.location.pathname.startsWith('/login')
      localStorage.removeItem('b3_token')
      localStorage.removeItem('b3_user')
      if (!isLogin) {
        ElMessage.error('登录已失效，请重新登录')
        window.location.href = '/login'
      }
    } else {
      const detail = response?.data?.detail
      const message = typeof detail === 'string'
        ? detail
        : detail
          ? JSON.stringify(detail)
          : error.message || '网络请求失败'
      if (!error.config?.headers?.['X-Silent']) {
        ElMessage.error(message)
      }
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error: any): string {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail) return JSON.stringify(detail)
  return error?.message || '请求失败'
}

export async function downloadFile(url: string, filename: string, params?: Record<string, any>) {
  const response = await api.get(url, { params, responseType: 'blob' })
  const blob = new Blob([response.data])
  const link = document.createElement('a')
  link.href = window.URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(link.href)
}

export default api
