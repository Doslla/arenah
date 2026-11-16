import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
})

// Ajoute le jeton à chaque requête
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Session expirée : retour à la page de connexion
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && !error.config.url.includes('/auth/login')) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Message d'erreur lisible renvoyé par FastAPI
export function messageErreur(error) {
  const d = error?.response?.data?.detail
  if (Array.isArray(d)) return d.map((e) => `${e.loc?.slice(-1)[0]} : ${e.msg}`).join(' · ')
  return d || error?.message || 'Erreur inconnue'
}

export default api
