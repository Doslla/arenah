import { Box, LinearProgress, Typography } from '@mui/material'
import CrudPage from '../components/CrudPage'
import { budgetsService } from '../services'
import { categories, departements } from '../data/mock'
import { formatMontant } from '../utils/format'

const nomDep = (id) => departements.find((d) => d.id === id)?.nom ?? '—'

function Consommation({ r }) {
  const taux = r.montantAlloue ? Math.round((r.montantConsomme / r.montantAlloue) * 100) : 0
  const color = taux >= 90 ? 'error' : taux >= 70 ? 'warning' : 'primary'
  return (
    <Box sx={{ minWidth: 140 }}>
      <LinearProgress variant="determinate" value={Math.min(taux, 100)} color={color} sx={{ height: 8, borderRadius: 4 }} />
      <Typography variant="caption">{taux} %</Typography>
    </Box>
  )
}

const colonnes = [
  { field: 'annee', label: 'Année' },
  { field: 'departementId', label: 'Unité', render: (r) => nomDep(r.departementId), texte: (r) => nomDep(r.departementId) },
  { field: 'categorie', label: 'Catégorie' },
  { field: 'montantAlloue', label: 'Alloué', align: 'right', render: (r) => formatMontant(r.montantAlloue) },
  { field: 'montantConsomme', label: 'Consommé', align: 'right', render: (r) => formatMontant(r.montantConsomme) },
  { field: 'taux', label: 'Consommation', render: (r) => <Consommation r={r} /> },
]
const champs = [
  { name: 'annee', label: 'Année', type: 'number', required: true },
  { name: 'departementId', label: 'Unité', type: 'select', required: true, options: departements.map((d) => ({ value: d.id, label: d.nom })) },
  { name: 'categorie', label: 'Catégorie', type: 'select', required: true, options: categories.map((c) => ({ value: c, label: c })) },
  { name: 'montantAlloue', label: 'Montant alloué', type: 'number', required: true },
  { name: 'montantConsomme', label: 'Montant consommé', type: 'number' },
]
const valeurVide = { annee: new Date().getFullYear(), departementId: '', categorie: '', montantAlloue: '', montantConsomme: 0 }

export default function Budgets() {
  return <CrudPage titre="Budgets (données fictives, branché au J3)" service={budgetsService} colonnes={colonnes} champs={champs} valeurVide={valeurVide} />
}
