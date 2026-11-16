import { useEffect, useMemo, useState } from 'react'
import { Chip } from '@mui/material'
import CrudPage from '../components/CrudPage'
import { unitesService } from '../services'
import { useAuth } from '../auth/AuthContext'
import api from '../api/client'

const TYPES = [
  { value: 'direction', label: 'Direction' },
  { value: 'département', label: 'Département' },
  { value: 'groupe', label: 'Groupe (rapports)' },
  { value: 'activité', label: 'Activité' },
]
const valeurVide = { nom: '', type: 'activité', parent_id: '', encaisse: false, actif: true, ordre_affichage: 0 }

export default function Unites() {
  const [toutes, setToutes] = useState([])
  const { aRole } = useAuth()
  useEffect(() => { api.get('/unites').then((r) => setToutes(r.data)) }, [])

  const nomUnite = useMemo(() => Object.fromEntries(toutes.map((u) => [u.id, u.nom])), [toutes])
  const colonnes = useMemo(() => [
    { field: 'nom', label: 'Nom' },
    { field: 'type', label: 'Type', render: (r) => <Chip size="small" label={r.type} variant="outlined" /> },
    { field: 'parent_id', label: 'Rattachée à', render: (r) => nomUnite[r.parent_id] ?? '—', texte: (r) => nomUnite[r.parent_id] ?? '' },
    { field: 'encaisse', label: 'Caisse', render: (r) => (r.encaisse ? <Chip size="small" color="success" label="Oui" /> : '—') },
    { field: 'actif', label: 'Statut', render: (r) => <Chip size="small" color={r.actif ? 'primary' : 'default'} label={r.actif ? 'Active' : 'Désactivée'} /> },
  ], [nomUnite])

  const champs = useMemo(() => [
    { name: 'nom', label: 'Nom', required: true },
    { name: 'type', label: 'Type', type: 'select', required: true, options: TYPES },
    { name: 'parent_id', label: 'Rattachée à', type: 'select', options: [{ value: '', label: '— Aucune (racine)' }, ...toutes.map((u) => ({ value: u.id, label: u.nom }))] },
    { name: 'encaisse', label: 'A une caisse', type: 'select', options: [{ value: true, label: 'Oui' }, { value: false, label: 'Non' }] },
    { name: 'actif', label: 'Statut', type: 'select', options: [{ value: true, label: 'Active' }, { value: false, label: 'Désactivée' }] },
    { name: 'ordre_affichage', label: "Ordre d'affichage", type: 'number' },
  ], [toutes])

  const gestion = aRole('PDG', 'DIRECTEUR', 'RH', 'ADMIN_INFO')
  return (
    <CrudPage titre="Unités" service={unitesService} colonnes={colonnes} champs={champs} valeurVide={valeurVide}
      modifiable={gestion} supprimable={gestion} libelleSuppression="Désactiver"
      confirmationSuppression="Désactiver cette unité ? (elle reste dans l'historique)" />
  )
}
