import { Chip } from '@mui/material'
const map = { ACTIF: ['Actif', 'success'], INACTIF: ['Inactif', 'default'], EN_ATTENTE: ['En attente', 'warning'], APPROUVE: ['Approuvé', 'success'], REFUSE: ['Refusé', 'error'], VALIDEE: ['Validée', 'success'], REJETEE: ['Rejetée', 'error'] }
export default function StatutChip({ statut }) { const [label, color] = map[statut] ?? [statut, 'default']; return <Chip size="small" label={label} color={color} /> }
