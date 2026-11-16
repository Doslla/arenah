import { useEffect, useState } from 'react'
import { Alert, Box, Card, CardContent, Chip, CircularProgress, Typography } from '@mui/material'
import api, { messageErreur } from '../api/client'

const COULEURS = { direction: '#1e3a8a', département: '#0d9488', groupe: '#64748b', activité: '#b45309' }

function Poste({ p }) {
  const noms = p.titulaires.map((t) => t.nom + (t.interim ? ' (intérim)' : '')).join(', ')
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, py: 0.5, borderBottom: '1px dashed #e2e8f0', fontSize: 14 }}>
      <Typography variant="body2" color="text.secondary">{p.intitule}{p.est_responsable ? ' ★' : ''}</Typography>
      <Typography variant="body2" sx={{ fontWeight: p.vacant ? 400 : 600, color: p.vacant ? 'text.disabled' : 'text.primary', fontStyle: p.vacant ? 'italic' : 'normal' }}>
        {p.vacant ? 'À définir' : noms}
      </Typography>
    </Box>
  )
}

function Noeud({ n, niveau = 0 }) {
  const couleur = COULEURS[n.type] ?? '#334155'
  const estGroupe = n.type === 'groupe'
  return (
    <Box sx={{ ml: niveau ? 3 : 0, mt: 2, pl: niveau ? 2 : 0, borderLeft: niveau ? '2px solid #e2e8f0' : 'none' }}>
      {estGroupe ? (
        <Typography variant="overline" sx={{ color: couleur, fontWeight: 700 }}>{n.nom}</Typography>
      ) : (
        <Card variant="outlined" sx={{ borderTop: `4px solid ${couleur}`, maxWidth: 560 }}>
          <CardContent sx={{ pb: '12px !important' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
              <Typography variant="subtitle1" fontWeight={700}>{n.nom}</Typography>
              <Chip size="small" label={n.type} sx={{ bgcolor: couleur, color: '#fff' }} />
              {n.encaisse && <Chip size="small" label="Caisse" color="success" variant="outlined" />}
            </Box>
            {n.postes.length ? n.postes.map((p) => <Poste key={p.poste_id} p={p} />) : (
              <Typography variant="body2" color="text.disabled">Aucun poste défini</Typography>
            )}
          </CardContent>
        </Card>
      )}
      {n.enfants.map((e) => <Noeud key={e.id} n={e} niveau={niveau + 1} />)}
    </Box>
  )
}

export default function Organigramme() {
  const [arbre, setArbre] = useState(null)
  const [erreur, setErreur] = useState('')
  useEffect(() => {
    api.get('/organigramme').then((r) => setArbre(r.data)).catch((e) => setErreur(messageErreur(e)))
  }, [])

  if (erreur) return <Alert severity="error">{erreur}</Alert>
  if (!arbre) return <Box sx={{ py: 8, display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>
  return (
    <Box>
      <Typography variant="body2" color="text.secondary">
        Généré automatiquement à partir des affectations en cours. ★ = poste responsable. Les groupes servent uniquement aux regroupements de rapports.
      </Typography>
      {arbre.map((n) => <Noeud key={n.id} n={n} />)}
    </Box>
  )
}
