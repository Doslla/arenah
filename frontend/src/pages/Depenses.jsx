import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Step, StepContent, StepLabel, Stepper,
  Tab, Table, TableBody, TableCell, TableHead, TablePagination, TableRow, Tabs, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import api from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Dialogue from '../components/Dialogue'
import { Chargement, Etat } from '../components/Etat'
import { formatDate, formatMontant } from '../utils/format'

function Detail({ id, onClose, onChange }) {
  const { aRole } = useAuth()
  const [dep, setDep] = useState(null)
  const [action, setAction] = useState(null)
  const charger = useCallback(() => api.get(`/depenses/${id}`).then((r) => setDep(r.data)), [id])
  useEffect(() => { charger() }, [charger])
  const fini = () => { charger(); onChange() }

  const etapeActive = dep?.circuit ? dep.circuit.findIndex((e) => !e.fait) : -1
  const cb = dep?.controle_budget
  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>Dépense n°{id}</DialogTitle>
      <DialogContent>
        {!dep ? <Chargement /> : <>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 1, mb: 2 }}>
            <Typography><b>Objet :</b> {dep.objet}</Typography>
            <Typography><b>Montant :</b> {formatMontant(dep.montant_reel ?? dep.montant_estime)}{dep.urgence && <Chip size="small" color="error" label="Urgent" sx={{ ml: 1 }} />}</Typography>
            <Typography><b>Unité :</b> {dep.unite} · {dep.categorie}</Typography>
            <Typography><b>Demandeur :</b> {dep.demandeur ?? 'Historique importé'}</Typography>
            <Typography><b>Date :</b> {formatDate(dep.date)}</Typography>
            <Typography><b>Statut :</b> <Etat valeur={dep.statut} /></Typography>
          </Box>
          {cb && <Alert severity={!cb.budget_saisi ? 'info' : cb.niveau === 'critique' ? 'error' : cb.niveau === 'attention' ? 'warning' : 'success'} sx={{ mb: 2 }}>
            <b>Contrôle budgétaire :</b> {cb.message}
          </Alert>}
          {dep.erreur_circuit && <Alert severity="error" sx={{ mb: 2 }}>{dep.erreur_circuit}</Alert>}
          {dep.circuit?.length > 0 && <>
            <Typography variant="subtitle2" gutterBottom>Circuit de validation (seuil PDG : {formatMontant(dep.seuil_pdg)})</Typography>
            <Stepper orientation="vertical" activeStep={etapeActive === -1 ? dep.circuit.length : etapeActive}>
              {dep.circuit.map((e) => (
                <Step key={e.code} completed={e.fait}>
                  <StepLabel error={e.decision === 'refusé'} optional={e.remontee && <Typography variant="caption" color="warning.main">Remontée (cumul de fonctions)</Typography>}>
                    {e.libelle} — {e.par ? `${e.decision} par ${e.par} le ${e.date}` : e.valideurs.join(', ')}
                  </StepLabel>
                  <StepContent>{e.motif && <Typography variant="body2">{e.motif}</Typography>}</StepContent>
                </Step>
              ))}
            </Stepper>
          </>}
        </>}
      </DialogContent>
      <DialogActions>
        {dep?.a_traiter_par_moi && dep.statut !== 'validée' && <>
          <Button color="error" onClick={() => setAction('refusé')}>Refuser</Button>
          <Button onClick={() => setAction('partiel')}>Accepter partiellement</Button>
          <Button variant="contained" color="success" onClick={() => setAction('accepté')}>Accepter</Button>
        </>}
        {dep?.statut === 'validée' && aRole('COMPTABLE') && <Button variant="contained" onClick={() => setAction('payer')}>Enregistrer le paiement</Button>}
        <Button onClick={onClose}>Fermer</Button>
      </DialogActions>

      <Dialogue open={['accepté', 'refusé', 'partiel'].includes(action)} titre={`Décision : ${action}`} couleur={action === 'refusé' ? 'error' : 'success'}
        initial={{ montant_accepte: '', motif: '' }}
        champs={[...(action === 'partiel' ? [{ name: 'montant_accepte', label: 'Montant accepté (Ar)', type: 'number', required: true }] : []),
          { name: 'motif', label: 'Motif', type: 'textarea', required: action !== 'accepté' }]}
        onClose={() => setAction(null)}
        onValider={async (v) => { await api.put(`/depenses/${id}/valider`, { decision: action, montant_accepte: v.montant_accepte || null, motif: v.motif || null }); fini() }} />
      <Dialogue open={action === 'payer'} titre="Paiement de la dépense" initial={{ montant_reel: dep?.montant_estime ?? '', mode_paiement: 'espèces' }}
        champs={[{ name: 'montant_reel', label: 'Montant payé (Ar)', type: 'number', required: true },
          { name: 'mode_paiement', label: 'Mode', type: 'select', options: [{ value: 'espèces', label: 'Espèces' }, { value: 'virement', label: 'Virement' }] }]}
        onClose={() => setAction(null)}
        onValider={async (v) => { await api.put(`/depenses/${id}/payer`, v); fini() }} />
    </Dialog>
  )
}

export default function Depenses() {
  const { user, aRole } = useAuth()
  const [onglet, setOnglet] = useState(0)
  const [liste, setListe] = useState(null)
  const [page, setPage] = useState(0)
  const [detail, setDetail] = useState(null)
  const [nouvelle, setNouvelle] = useState(false)
  const [unites, setUnites] = useState([])
  const [categories, setCategories] = useState([])
  const peutDemander = aRole('RESPONSABLE_ACTIVITE', 'DIRECTEUR', 'PDG', 'COMPTABLE', 'RESP_ACHATS', 'RH') && !!user?.employe_id

  const charger = useCallback(() => {
    setListe(null)
    api.get('/depenses', { params: onglet === 0 ? { a_traiter: true } : { limite: 500 } }).then((r) => { setListe(r.data); setPage(0) })
  }, [onglet])
  useEffect(() => { charger() }, [charger])
  useEffect(() => {
    api.get('/unites', { params: { actif: true } }).then((r) => setUnites(r.data.filter((u) => u.type !== 'groupe' && (user?.portee_globale || user?.unites_portee?.includes(u.id)))))
    api.get('/referentiels/categories-depense').then((r) => setCategories(r.data))
  }, [user])

  const visibles = (liste ?? []).slice(page * 15, page * 15 + 15)
  return (
    <Box>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
            <Tabs value={onglet} onChange={(_, v) => setOnglet(v)} sx={{ flexGrow: 1 }}>
              <Tab label="À traiter par moi" /><Tab label="Toutes les dépenses" />
            </Tabs>
            {peutDemander && <Button variant="contained" startIcon={<AddIcon />} onClick={() => setNouvelle(true)}>Nouvelle demande</Button>}
          </Box>
          <Alert severity="info" sx={{ my: 2 }}>Circuit : responsable → Resp. Achats (étude) → comptable → PDG au-dessus du seuil. Cliquez sur une ligne pour voir le détail.</Alert>
          {!liste ? <Chargement /> : <>
            <Table size="small">
              <TableHead><TableRow>
                <TableCell>Date</TableCell><TableCell>Objet</TableCell><TableCell>Unité</TableCell><TableCell>Catégorie</TableCell>
                <TableCell align="right">Montant</TableCell><TableCell>Statut</TableCell><TableCell>Étape</TableCell>
              </TableRow></TableHead>
              <TableBody>
                {visibles.map((d) => (
                  <TableRow key={d.id} hover sx={{ cursor: 'pointer' }} onClick={() => setDetail(d.id)}>
                    <TableCell>{formatDate(d.date)}</TableCell><TableCell>{d.objet}</TableCell><TableCell>{d.unite}</TableCell><TableCell>{d.categorie}</TableCell>
                    <TableCell align="right">{formatMontant(d.montant_reel ?? d.montant_estime)}</TableCell>
                    <TableCell><Etat valeur={d.statut} /></TableCell>
                    <TableCell>{d.etape ? `${d.etape}${d.en_attente_de ? ' : ' + d.en_attente_de.join(', ') : ''}` : '—'}</TableCell>
                  </TableRow>
                ))}
                {liste.length === 0 && <TableRow><TableCell colSpan={7} align="center">{onglet === 0 ? 'Rien à traiter' : 'Aucune dépense'}</TableCell></TableRow>}
              </TableBody>
            </Table>
            <TablePagination component="div" count={liste.length} page={page} onPageChange={(_, p) => setPage(p)} rowsPerPage={15} rowsPerPageOptions={[15]} />
          </>}
        </CardContent>
      </Card>

      {detail && <Detail id={detail} onClose={() => setDetail(null)} onChange={charger} />}
      <Dialogue open={nouvelle} titre="Nouvelle demande de dépense" libelleValider="Soumettre"
        initial={{ unite_id: unites[0]?.id ?? '', categorie_depense_id: '', objet: '', montant_estime: '', urgence: false }}
        champs={[
          { name: 'unite_id', label: 'Unité', type: 'select', required: true, options: unites.map((u) => ({ value: u.id, label: u.nom })) },
          { name: 'categorie_depense_id', label: 'Catégorie', type: 'select', required: true, options: categories.map((c) => ({ value: c.id, label: c.libelle })) },
          { name: 'objet', label: 'Objet', required: true, large: true },
          { name: 'montant_estime', label: 'Montant estimé (Ar)', type: 'number', required: true },
          { name: 'urgence', label: 'Urgent', type: 'select', options: [{ value: false, label: 'Non' }, { value: true, label: 'Oui' }] },
        ]}
        onClose={() => setNouvelle(false)}
        onValider={async (v) => { const { data } = await api.post('/depenses', v); setOnglet(1); charger(); setDetail(data.id) }} />
    </Box>
  )
}
