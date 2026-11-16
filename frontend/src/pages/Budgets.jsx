import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, LinearProgress, MenuItem,
  Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from '@mui/material'
import api, { messageErreur } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { Chargement } from '../components/Etat'
import { formatMontant } from '../utils/format'

const MOIS = ['Janv.', 'Févr.', 'Mars', 'Avr.', 'Mai', 'Juin', 'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.']
const couleur = (t) => (t > 100 ? 'error' : t >= 80 ? 'warning' : 'primary')

function Taux({ t }) {
  if (t === null || t === undefined) return '—'
  return (
    <Box sx={{ minWidth: 120 }}>
      <LinearProgress variant="determinate" value={Math.min(t, 100)} color={couleur(t)} sx={{ height: 8, borderRadius: 4 }} />
      <Typography variant="caption">{t} %</Typography>
    </Box>
  )
}

function Edition({ exercice, ligne, unites, categories, onClose, onFini }) {
  const [unite, setUnite] = useState(ligne?.unite_id ?? '')
  const [cat, setCat] = useState(ligne?.categorie_depense_id ?? '')
  const [mois, setMois] = useState(() => Object.fromEntries(MOIS.map((_, i) => [i + 1, ligne?.mois?.[i + 1] ?? 0])))
  const [erreur, setErreur] = useState('')
  const enregistrer = async () => {
    if (!unite || !cat) return setErreur('Choisissez une unité et une catégorie')
    try {
      for (const [m, v] of Object.entries(mois)) {
        if (!ligne || Number(v) !== (ligne.mois[m] ?? 0)) {
          await api.post('/budgets', { exercice, unite_id: unite, categorie_depense_id: cat, mois: Number(m), montant_prevu: Number(v) || 0 })
        }
      }
      onFini()
      onClose()
    } catch (err) { setErreur(messageErreur(err)) }
  }
  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>{ligne ? `Budget ${exercice} : ${ligne.unite} / ${ligne.categorie}` : `Nouvelle ligne budgétaire ${exercice}`}</DialogTitle>
      <DialogContent>
        {erreur && <Alert severity="error" sx={{ mb: 2 }}>{erreur}</Alert>}
        {!ligne && (
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, my: 1 }}>
            <TextField select label="Unité" value={unite} onChange={(e) => setUnite(e.target.value)}>{unites.map((u) => <MenuItem key={u.id} value={u.id}>{u.nom}</MenuItem>)}</TextField>
            <TextField select label="Catégorie" value={cat} onChange={(e) => setCat(e.target.value)}>{categories.map((c) => <MenuItem key={c.id} value={c.id}>{c.libelle}</MenuItem>)}</TextField>
          </Box>
        )}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2, mt: 1 }}>
          {MOIS.map((l, i) => (
            <TextField key={l} label={l} type="number" size="small" value={mois[i + 1]} onChange={(e) => setMois({ ...mois, [i + 1]: e.target.value })} />
          ))}
        </Box>
        <Typography variant="body2" sx={{ mt: 2 }}>Total annuel : <b>{formatMontant(Object.values(mois).reduce((s, v) => s + (Number(v) || 0), 0))}</b></Typography>
      </DialogContent>
      <DialogActions><Button onClick={onClose}>Annuler</Button><Button variant="contained" onClick={enregistrer}>Enregistrer</Button></DialogActions>
    </Dialog>
  )
}

export default function Budgets() {
  const { aRole } = useAuth()
  const peutSaisir = aRole('COMPTABLE', 'PDG')
  const [exercice, setExercice] = useState(new Date().getFullYear())
  const [s, setS] = useState(null)
  const [edition, setEdition] = useState(null) // ligne ou 'nouvelle'
  const [unites, setUnites] = useState([])
  const [categories, setCategories] = useState([])
  const charger = useCallback(() => { setS(null); api.get('/budgets/synthese', { params: { exercice } }).then((r) => setS(r.data)).catch(() => setS({ lignes: [] })) }, [exercice])
  useEffect(() => { charger() }, [charger])
  useEffect(() => {
    api.get('/unites', { params: { actif: true } }).then((r) => setUnites(r.data.filter((u) => u.type !== 'groupe')))
    api.get('/referentiels/categories-depense').then((r) => setCategories(r.data))
  }, [])

  const tot = (k) => (s?.lignes ?? []).reduce((a, l) => a + (l[k] || 0), 0)
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2, flexWrap: 'wrap' }}>
          <TextField select size="small" label="Exercice" value={exercice} onChange={(e) => setExercice(e.target.value)}>
            {[2025, 2026, 2027].map((a) => <MenuItem key={a} value={a}>{a}</MenuItem>)}
          </TextField>
          <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
            Consommé = dépenses validées ou payées. Alerte à {80} % du budget du mois (paramètre).
          </Typography>
          {peutSaisir && <Button variant="contained" onClick={() => setEdition('nouvelle')}>Nouvelle ligne</Button>}
        </Box>
        {!s ? <Chargement /> : s.lignes.length === 0 ? <Alert severity="info">Aucun budget saisi pour {exercice} : les alertes budget sont inactives (décision 29).</Alert> : (
          <Table size="small">
            <TableHead><TableRow>
              <TableCell>Unité</TableCell><TableCell>Catégorie</TableCell><TableCell align="right">Prévu annuel</TableCell>
              <TableCell align="right">Prévu à date</TableCell><TableCell align="right">Consommé</TableCell><TableCell>À date</TableCell>
              <TableCell>{MOIS[(s.mois_courant ?? 1) - 1]} (mois en cours)</TableCell>{peutSaisir && <TableCell />}
            </TableRow></TableHead>
            <TableBody>
              {s.lignes.map((l) => (
                <TableRow key={`${l.unite_id}-${l.categorie_depense_id}`}>
                  <TableCell>{l.unite}</TableCell><TableCell>{l.categorie}</TableCell>
                  <TableCell align="right">{formatMontant(l.prevu_annuel)}</TableCell>
                  <TableCell align="right">{formatMontant(l.prevu_a_date)}</TableCell>
                  <TableCell align="right">{formatMontant(l.consomme)}</TableCell>
                  <TableCell><Taux t={l.taux_a_date} /></TableCell>
                  <TableCell><Taux t={l.taux_mois_courant} /></TableCell>
                  {peutSaisir && <TableCell><Button size="small" onClick={() => setEdition(l)}>Modifier</Button></TableCell>}
                </TableRow>
              ))}
              <TableRow sx={{ '& td': { fontWeight: 700 } }}>
                <TableCell colSpan={2}>Total</TableCell>
                <TableCell align="right">{formatMontant(tot('prevu_annuel'))}</TableCell>
                <TableCell align="right">{formatMontant(tot('prevu_a_date'))}</TableCell>
                <TableCell align="right">{formatMontant(tot('consomme'))}</TableCell>
                <TableCell><Taux t={tot('prevu_a_date') ? Math.round((100 * tot('consomme')) / tot('prevu_a_date')) : null} /></TableCell>
                <TableCell colSpan={2} />
              </TableRow>
            </TableBody>
          </Table>
        )}
      </CardContent>
      {edition && <Edition exercice={Number(exercice)} ligne={edition === 'nouvelle' ? null : edition} unites={unites} categories={categories}
        onClose={() => setEdition(null)} onFini={charger} />}
    </Card>
  )
}
