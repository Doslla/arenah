import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './auth/ProtectedRoute'
import MainLayout from './layouts/MainLayout'
import Login from './pages/Login'
import ChangerMotDePasse from './pages/ChangerMotDePasse'
import Dashboard from './pages/Dashboard'
import Organigramme from './pages/Organigramme'
import Unites from './pages/Unites'
import Employes from './pages/Employes'
import Conges from './pages/Conges'
import Budgets from './pages/Budgets'
import Depenses from './pages/Depenses'
import EnConstruction from './components/EnConstruction'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/changer-mot-de-passe" element={<ChangerMotDePasse />} />
        <Route element={<MainLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/organigramme" element={<Organigramme />} />
          <Route path="/unites" element={<Unites />} />
          <Route path="/employes" element={<Employes />} />
          <Route path="/conges" element={<Conges />} />
          <Route path="/budgets" element={<Budgets />} />
          <Route path="/depenses" element={<Depenses />} />
          <Route path="/previsions" element={<EnConstruction titre="Prévisions IA (J5)" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
