import { createContext, useContext, useEffect, useState } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)       // profil renvoyé par /auth/moi
  const [chargement, setChargement] = useState(!!localStorage.getItem('token'))

  const chargerProfil = async () => {
    const { data } = await api.get('/auth/moi')
    setUser(data)
    return data
  }

  // Au démarrage : si un jeton existe, on recharge le profil
  useEffect(() => {
    if (!localStorage.getItem('token')) return
    chargerProfil()
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setChargement(false))
  }, [])

  const login = async (identifiant, motDePasse) => {
    const form = new URLSearchParams({ username: identifiant, password: motDePasse })
    const { data } = await api.post('/auth/login', form)
    localStorage.setItem('token', data.access_token)
    return chargerProfil()
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  // Raccourcis pour l'affichage selon les droits
  const aRole = (...codes) =>
    !!user && (user.superutilisateur || [...user.roles, ...user.roles_delegues].some((r) => codes.includes(r)))

  return (
    <AuthContext.Provider value={{ user, chargement, login, logout, chargerProfil, aRole }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
