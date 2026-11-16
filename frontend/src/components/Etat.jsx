import { Box, Chip, CircularProgress } from '@mui/material'

// Couleur des statuts utilisés dans toute la plateforme
const COULEURS = {
  'accepté': 'success', 'validée': 'success', 'payée': 'success', 'contrôlée': 'success', 'présent': 'success', 'émis': 'error', 'traitée': 'success',
  'refusé': 'error', 'refusée': 'error', 'absent': 'error', 'écart à traiter': 'error', 'critique': 'error',
  'retard': 'warning', 'attention': 'warning', 'proposé': 'warning', 'nouvelle': 'warning',
  'en attente avis': 'info', 'en attente RH': 'info', 'en étude achats': 'info', 'à valider comptable': 'info', 'à valider PDG': 'info', 'soumise': 'info',
}

export function Etat({ valeur, taille = 'small' }) {
  if (!valeur) return '—'
  return <Chip size={taille} label={valeur} color={COULEURS[valeur] ?? 'default'} variant={COULEURS[valeur] ? 'filled' : 'outlined'} />
}

export function Chargement() {
  return <Box sx={{ py: 6, display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>
}
