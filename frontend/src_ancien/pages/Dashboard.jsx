import { useEffect, useState } from 'react'
import {
  Alert, Box, Card, CardContent, Chip, CircularProgress, LinearProgress,
  Table, TableBody, TableCell, TableHead, TableRow, Typography,
} from '@mui/material'
import api, { messageErreur } from '../api/client'
import { formatDate, formatMontant } from '../utils/format'
import StatutChip from '../components/StatutChip'

function KpiCard({ titre, valeur, sousTitre, couleurSousTitre = 'text.secondary' }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="body2" color="text.secondary">{titre}</Typography>
        <Typography variant="h5" fontWeight={700} my={0.5}>{valeur}</Typography>
        <Typography variant="caption" color={couleurSousTitre}>{sousTitre}</Typography>
      </CardContent>
    </Card>
  )
}

const couleurTaux = (t) => (t >= 90 ? 'error' : t >= 70 ? 'warning' : 'primary')
const STATUTS = { 'payée': 'VALIDEE', 'refusée': 'REJETEE' }

export default function Dashboard() {
  const [d, setD] = useState(null)
  const [erreur, setErreur] = useState('')
  useEffect(() => {
    api.get('/tableau-de-bord').then((r) => setD(r.data)).catch((e) => setErreur(messageErreur(e)))
  }, [])

  if (erreur) return <Alert severity="error">{erreur}</Alert>
  if (!d) return <Box sx={{ py: 8, display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>

  const evolution = d.encaissements_mois_precedent
    ? Math.round(((d.encaissements_mois - d.encaissements_mois_precedent) / d.encaissements_mois_precedent) * 100)
    : null

  return (
    <Box>
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', lg: 'repeat(4, 1fr)' } }}>
        <KpiCard titre="Effectif" valeur={d.effectif_actif} sousTitre="employés actifs" />
        <KpiCard titre="Encaissements du mois" valeur={formatMontant(d.encaissements_mois)}
          sousTitre={evolution === null ? '—' : `${evolution >= 0 ? '+' : ''}${evolution} % vs même période du mois précédent`}
          couleurSousTitre={evolution >= 0 ? 'success.main' : 'error.main'} />
        <KpiCard titre={`Budget ${d.budget.exercice ?? ''} consommé`} valeur={d.budget.taux === null ? '—' : `${d.budget.taux} %`}
          sousTitre={`${formatMontant(d.budget.consomme)} sur ${formatMontant(d.budget.prevu)}`} />
        <KpiCard titre="Clôtures à traiter" valeur={d.clotures_ecart_a_traiter} sousTitre="écart de caisse supérieur au seuil"
          couleurSousTitre={d.clotures_ecart_a_traiter ? 'warning.main' : 'text.secondary'} />
      </Box>

      <Box sx={{ display: 'grid', gap: 2, mt: 3, gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' } }}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Encaissements du mois par activité</Typography>
            <Table size="small">
              <TableHead>
                <TableRow><TableCell>Activité</TableCell><TableCell align="right">Ce mois</TableCell><TableCell align="right">Mois précédent*</TableCell></TableRow>
              </TableHead>
              <TableBody>
                {d.encaissements_par_activite.map((a) => (
                  <TableRow key={a.unite_id}>
                    <TableCell>{a.activite}</TableCell>
                    <TableCell align="right">{formatMontant(a.montant)}</TableCell>
                    <TableCell align="right" sx={{ color: 'text.secondary' }}>{formatMontant(a.mois_precedent)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Typography variant="caption" color="text.secondary">* même nombre de jours</Typography>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Consommation du budget par unité</Typography>
            {d.budget.par_unite.length === 0 && <Typography color="text.secondary">Budget non saisi : alertes inactives (décision 29).</Typography>}
            {d.budget.par_unite.map((b) => (
              <Box key={b.unite_id} sx={{ mb: 1.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
                  <span>{b.unite}</span>
                  <span>{b.taux === null ? '—' : `${b.taux} %`}</span>
                </Box>
                <LinearProgress variant="determinate" value={Math.min(b.taux ?? 0, 100)} color={couleurTaux(b.taux ?? 0)} sx={{ height: 8, borderRadius: 4 }} />
              </Box>
            ))}
          </CardContent>
        </Card>
      </Box>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Dernières dépenses</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell><TableCell>Objet</TableCell><TableCell>Unité</TableCell>
                <TableCell>Catégorie</TableCell><TableCell align="right">Montant</TableCell><TableCell>Statut</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {d.dernieres_depenses.map((x) => (
                <TableRow key={x.id}>
                  <TableCell>{formatDate(x.date)}</TableCell>
                  <TableCell>{x.objet}</TableCell>
                  <TableCell>{x.unite}</TableCell>
                  <TableCell>{x.categorie}</TableCell>
                  <TableCell align="right">{formatMontant(x.montant)}</TableCell>
                  <TableCell>{STATUTS[x.statut] ? <StatutChip statut={STATUTS[x.statut]} /> : <Chip size="small" color="warning" label={x.statut} />}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  )
}
