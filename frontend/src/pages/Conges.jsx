import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, Tooltip, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import api from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Dialogue from '../components/Dialogue'
import { Chargement, Etat } from '../components/Etat'
import { formatDate } from '../utils/format'

function Solde({ employeId }) {
  const [s, setS] = useState(null)
  useEffect(() => { if (employeId) api.get(`/conges/solde/${employeId}`).then((r) => setS(r.data)) }, [employeId])
  if (!s) return null
  return (
    <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, mb: 2 }}>
      {[['Solde disponible', `${s.solde} j`], ['Acquis en ' + s.annee, `${s.acquis} j`], ['Pris', `${s.pris} j`], ['Congés annuels', `${s.prises_annuelles} / ${s.prises_max}`]].map(([t, v]) => (
        <Card key={t}><CardContent><Typography variant="body2" color="text.secondary">{t}</Typography><Typography variant="h5" fontWeight={700}>{v}</Typography></CardContent></Card>
      ))}
    </Box>
  )
}

export default function Conges() {
  const { user, aRole } = useAuth()
  const [onglet, setOnglet] = useState(0)
  const [liste, setListe] = useState(null)
  const [types, setTypes] = useState([])
  const [nouvelle, setNouvelle] = useState(false)
  const [action, setAction] = useState(null) // { conge, genre: 'avis' | 'decision', valeur }
  const vueGlobale = aRole('RH', 'ASSISTANT_RH', 'PDG', 'RESPONSABLE_ACTIVITE', 'DIRECTEUR')

  const filtres = [{ employe_id: user?.employe_id }, { a_traiter: true }, {}]
  const charger = useCallback(() => {
    setListe(null)
    api.get('/conges', { params: filtres[onglet] }).then((r) => setListe(r.data))
  }, [onglet]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { charger() }, [charger])
  useEffect(() => { api.get('/referentiels/types-absence').then((r) => setTypes(r.data)) }, [])

  const envoyerAction = async (v) => {
    const { conge, genre, valeur } = action
    const url = `/conges/${conge.id}/${genre}`
    await api.put(url, genre === 'avis' ? { avis: valeur, motif: v.motif || null } : { decision: valeur, motif: v.motif || null })
    charger()
  }

  return (
    <Box>
      {user?.employe_id && <Solde employeId={user.employe_id} />}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
            <Tabs value={onglet} onChange={(_, v) => setOnglet(v)} sx={{ flexGrow: 1 }}>
              <Tab label="Mes demandes" /><Tab label="À traiter" />{vueGlobale && <Tab label="Toutes" />}
            </Tabs>
            {user?.employe_id && <Button variant="contained" startIcon={<AddIcon />} onClick={() => setNouvelle(true)}>Nouvelle demande</Button>}
          </Box>
          <Alert severity="info" sx={{ my: 2 }}>
            Circuit : vous → avis de votre responsable → décision du RH. Si le responsable est le demandeur, l'avis remonte au supérieur.
          </Alert>
          {!liste ? <Chargement /> : (
            <Table size="small">
              <TableHead><TableRow>
                <TableCell>Employé</TableCell><TableCell>Type</TableCell><TableCell>Du</TableCell><TableCell>Au</TableCell>
                <TableCell align="right">Jours</TableCell><TableCell>Avis</TableCell><TableCell>Statut</TableCell><TableCell>En attente de</TableCell><TableCell />
              </TableRow></TableHead>
              <TableBody>
                {liste.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>{c.employe}</TableCell><TableCell>{c.type}</TableCell>
                    <TableCell>{formatDate(c.date_debut)}</TableCell><TableCell>{formatDate(c.date_fin)}</TableCell>
                    <TableCell align="right">{c.nb_jours}</TableCell>
                    <TableCell>{c.avis_responsable ? <Tooltip title={c.motif_avis || ''}><span>{c.avis_responsable}{c.avis_remonte ? ' (remonté)' : ''}</span></Tooltip> : '—'}</TableCell>
                    <TableCell><Tooltip title={c.motif_decision || ''}><span><Etat valeur={c.statut} /></span></Tooltip></TableCell>
                    <TableCell>{c.en_attente_de?.join(', ') || '—'}</TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      {c.a_traiter_par_moi && c.statut === 'en attente avis' && <>
                        <Button size="small" color="success" onClick={() => setAction({ conge: c, genre: 'avis', valeur: 'favorable' })}>Favorable</Button>
                        <Button size="small" color="error" onClick={() => setAction({ conge: c, genre: 'avis', valeur: 'défavorable' })}>Défavorable</Button>
                      </>}
                      {c.a_traiter_par_moi && c.statut === 'en attente RH' && <>
                        <Button size="small" color="success" onClick={() => setAction({ conge: c, genre: 'decision', valeur: 'accepté' })}>Accepter</Button>
                        <Button size="small" color="error" onClick={() => setAction({ conge: c, genre: 'decision', valeur: 'refusé' })}>Refuser</Button>
                      </>}
                      {c.employe_id === user?.employe_id && ['en attente avis', 'en attente RH'].includes(c.statut) &&
                        <Button size="small" onClick={async () => { await api.put(`/conges/${c.id}/annuler`); charger() }}>Annuler</Button>}
                    </TableCell>
                  </TableRow>
                ))}
                {liste.length === 0 && <TableRow><TableCell colSpan={9} align="center">Aucune demande</TableCell></TableRow>}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialogue open={nouvelle} titre="Nouvelle demande de congé" libelleValider="Envoyer la demande"
        description="Congé annuel : 15 jours avant au minimum, 15 jours maximum par congé, 2 congés annuels par an."
        initial={{ type_absence_id: types.find((t) => t.libelle === 'Congé annuel')?.id ?? '', date_debut: '', date_fin: '', motif: '' }}
        champs={[
          { name: 'type_absence_id', label: 'Type', type: 'select', required: true, options: types.map((t) => ({ value: t.id, label: t.libelle })), large: true },
          { name: 'date_debut', label: 'Du', type: 'date', required: true },
          { name: 'date_fin', label: 'Au (inclus)', type: 'date', required: true },
          { name: 'motif', label: 'Motif', type: 'textarea' },
        ]}
        onClose={() => setNouvelle(false)}
        onValider={async (v) => { await api.post('/conges', { ...v, motif: v.motif || null }); setOnglet(0); charger() }} />

      <Dialogue open={!!action} titre={action ? `${action.genre === 'avis' ? 'Avis' : 'Décision'} : ${action.valeur}` : ''}
        description={action ? `${action.conge.employe} — ${action.conge.type}, ${action.conge.nb_jours} jour(s) à partir du ${formatDate(action.conge.date_debut)}` : ''}
        couleur={action && ['défavorable', 'refusé'].includes(action.valeur) ? 'error' : 'success'}
        initial={{ motif: '' }}
        champs={[{ name: 'motif', label: 'Motif', type: 'textarea', required: !!action && ['défavorable', 'refusé'].includes(action.valeur) }]}
        onClose={() => setAction(null)} onValider={envoyerAction} />
    </Box>
  )
}
