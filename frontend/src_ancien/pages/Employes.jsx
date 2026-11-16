import { Box, Chip } from '@mui/material'
import CrudPage from '../components/CrudPage'
import { employesService } from '../services'
import { useAuth } from '../auth/AuthContext'
import { formatDate } from '../utils/format'

const colonnes = [
  { field: 'matricule', label: 'Matricule' },
  { field: 'nom', label: 'Nom', render: (r) => `${r.civilite ? r.civilite + ' ' : ''}${r.nom} ${r.prenom}`.trim(), texte: (r) => `${r.nom} ${r.prenom}` },
  {
    field: 'postes', label: 'Postes occupés', texte: (r) => r.postes.join(' '),
    render: (r) => (
      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', maxWidth: 420 }}>
        {r.postes.length ? r.postes.map((p) => <Chip key={p} size="small" label={p} variant="outlined" />) : '—'}
      </Box>
    ),
  },
  { field: 'telephone', label: 'Téléphone', render: (r) => r.telephone || '—' },
  { field: 'date_embauche', label: 'Embauche', render: (r) => formatDate(r.date_embauche) },
  { field: 'login', label: 'Identifiant', render: (r) => r.login || '—' },
  { field: 'statut', label: 'Statut', render: (r) => <Chip size="small" color={r.statut === 'actif' ? 'success' : 'default'} label={r.statut === 'actif' ? 'Actif' : 'Sorti'} /> },
]

const champs = [
  { name: 'matricule', label: 'Matricule', required: true },
  { name: 'civilite', label: 'Civilité', type: 'select', options: [{ value: '', label: '—' }, { value: 'Mr', label: 'Mr' }, { value: 'Mme', label: 'Mme' }] },
  { name: 'nom', label: 'Nom', required: true },
  { name: 'prenom', label: 'Prénom' },
  { name: 'cin', label: 'CIN' },
  { name: 'date_naissance', label: 'Date de naissance', type: 'date' },
  { name: 'telephone', label: 'Téléphone' },
  { name: 'email', label: 'Email', type: 'email' },
  { name: 'adresse', label: 'Adresse' },
  { name: 'contact_urgence_nom', label: "Contact d'urgence (nom)" },
  { name: 'contact_urgence_tel', label: "Contact d'urgence (téléphone)" },
  { name: 'numero_cnaps', label: 'N° CNaPS' },
  { name: 'langue_preferee', label: 'Langue', type: 'select', options: [{ value: 'fr', label: 'Français' }, { value: 'mg', label: 'Malagasy' }] },
  { name: 'date_embauche', label: "Date d'embauche", type: 'date', required: true },
]

const valeurVide = { matricule: '', civilite: '', nom: '', prenom: '', langue_preferee: 'fr', date_embauche: '' }

export default function Employes() {
  const { aRole } = useAuth()
  // Les postes s'attribuent dans l'organigramme / les affectations ; la sortie d'un employé arrive au J3
  return (
    <CrudPage titre="Employés" service={employesService} colonnes={colonnes} champs={champs} valeurVide={valeurVide}
      modifiable={aRole('RH', 'ASSISTANT_RH', 'PDG', 'DIRECTEUR', 'ADMIN_INFO')} supprimable={false} />
  )
}
