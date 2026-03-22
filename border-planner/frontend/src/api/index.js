import axios from 'axios'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 300000,
  headers: { 'Content-Type': 'application/json' }
})

service.interceptors.response.use(
  response => response.data?.data ?? response.data,
  error => {
    console.error('API error:', error)
    return Promise.reject(error)
  }
)

export default service
