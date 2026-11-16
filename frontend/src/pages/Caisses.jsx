import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, MenuItem, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from '@mui/material'
import api, { messageErreur } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Dialogue from '../components/Dialogue'
import { Chargement, Etat } from '../components/Etat'
import { formatDate, formatMontant } from '../utils/format'

const aujourdhui = () => new Date().toLocaleDateString('sv-SE') // date locale AAAA-MM-JJ (pas UTC)

function Chiffre({ titre, valeur, fort }) {
  return (
    <Card variant={fort ? 'elevation' : 'outlined'} sx={fort ? { bgcolor: 'primary.main', color: '#fff' } : undefined}>
      <CardContent sx={{ py: 1.5 }}>
        <Typography variant="caption" sx={{ opacity: 0.8 }}>{titre}</Typography>
        <Typography variant="h6" fontWeight={700}>{formatMontant(valeur)}</Typography>
      </CardContent>
    </Card>
  )
}

export default function Caisses() {
  const { aRole } = useAuth()
  const estComptable = aRole('COMPTABLE', 'ASSISTANT_COMPTABLE', 'PDG')
  const [caisses, setCaisses] = useState([])
  const [caisseId, setCaisseId] = useState('')
  const [jour, setJour] = useState(aujourdhui())
  const [j, setJ] = useState(null)
  const [clotures, setClotures] = useState([])
  const [remises, setRemises] = useState([])
  const [dialogue, setDialogue] = useState(null) // 'encaissement' | 'sortie' | 'cloture' | { controle } | { inverse }
  const [message, setMessage] = useState(null)

  useEffect(() => {
    api.get('/caisses').then((r) => { setCaisses(r.data); if (r.data.length) setCaisseId(r.data[0].id) })
  }, [])
  const charger = useCallback(() => {
    if (!caisseId) return
    api.get(`/caisses/${caisseId}/journee`, { params: { jour } }).then((r) => setJ(r.data))
    api.get('/clotures', { params: { caisse_id: caisseId, limite: 30 } }).then((r) => setClotures(r.data))
    if (estComptable) api.get('/remises', { params: { a_confirmer: true } }).then((r) => setRemises(r.data))
  }, [caisseId, jour, estComptable])
  useEffect(() => { charger() }, [charger])

  const agir = async (fn, texte) => {
    try { await fn(); setMessage({ ok: true, texte }); charger() } catch (err) { setMessage({ ok: false, texte: messageErreur(err) }) }
  }

  if (!caisses.length) return <Alert severity="info">Aucune caisse dans votre périmètre.</Alert>
  const estAujourdhui = jour === aujourdhui()
  const cloturee = !!j?.cloture

  return (
    <Box>
      <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <TextField select size="small" label="Caisse" value={caisseId} onChange={(e) => setCaisseId(e.target.value)} sx={{ minWidth: 220 }}>
          {caisses.map((c) => <MenuItem key={c.id} value={c.id}>{c.nom}</MenuItem>)}
        </TextField>
        <TextField type="date" size="small" label="Journée" value={jour} onChange={(e) => setJour(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
        <Box sx={{ flexGrow: 1 }} />
        {estAujourdhui && !cloturee && <>
          <Button variant="contained" color="success" onClick={() => setDialogue('encaissement')}>Encaissement</Button>
          <Button variant="outlined" color="warning" onClick={() => setDialogue('sortie')}>Sortie</Button>
        </>}
        {!cloturee && j && <Button variant="contained" onClick={() => setDialogue('cloture')}>Clôturer la journée</Button>}
        {cloturee && !j.remise && j.cloture.montant_compte > j.caisse.fonds &&
          <Button variant="outlined" onClick={() => agir(() => api.post(`/caisses/${caisseId}/remise`, null, { params: { jour } }), 'Remise enregistrée, en attente de confirmation du comptable')}>
            Remettre au comptable
          </Button>}
      </Stack>
      {message && <Alert severity={message.ok ? 'success' : 'error'} onClose={() => setMessage(null)} sx={{ mb: 2 }}>{message.texte}</Alert>}

      {!j ? <Chargement /> : <>
        <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(5, 1fr)' }, mb: 2 }}>
          <Chiffre titre="Fonds de caisse" valeur={j.caisse.fonds} />
          <Chiffre titre="Report depuis la dernière remise" valeur={j.report} />
          <Chiffre titre="Encaissements" valeur={j.total_encaissements} />
          <Chiffre titre="Sorties" valeur={j.total_sorties} />
          <Chiffre titre="Montant attendu en caisse" valeur={j.montant_theorique} fort />
        </Box>
        {cloturee && (
          <Alert severity={j.cloture.ecart === 0 ? 'success' : Math.abs(j.cloture.ecart) > 10000 ? 'error' : 'warning'} sx={{ mb: 2 }}>
            Journée clôturée : compté {formatMontant(j.cloture.montant_compte)}, écart {formatMontant(j.cloture.ecart)} — <Etat valeur={j.cloture.statut} />
            {j.remise && ` · Remise de ${formatMontant(j.remise.montant)} ${j.remise.confirmee ? 'confirmée' : 'en attente de confirmation'}`}
          </Alert>
        )}
        <Typography variant="caption" color="text.secondary">Remise au comptable chaque {j.jour_remise} (tout sauf le fonds).</Typography>

        <Card sx={{ mt: 1 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Mouvements du {formatDate(j.date)}</Typography>
            <Table size="small">
              <TableHead><TableRow><TableCell>Heure</TableCell><TableCell>Type</TableCell><TableCell>Catégorie / motif</TableCell><TableCell>Autorisé par</TableCell><TableCell align="right">Montant</TableCell>{estComptable && <TableCell />}</TableRow></TableHead>
              <TableBody>
                {j.mouvements.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>{m.heure}</TableCell>
                    <TableCell><Etat valeur={m.type === 'encaissement' ? 'encaissement' : 'sortie'} /></TableCell>
                    <TableCell>{m.categorie} {m.motif ? `— ${m.motif}` : ''} {m.nb_transactions > 1 ? `(${m.nb_transactions} tickets)` : ''}</TableCell>
                    <TableCell>{m.autorise_par ?? '—'}</TableCell>
                    <TableCell align="right" sx={{ color: m.type === 'sortie' ? 'error.main' : 'success.main' }}>{m.type === 'sortie' ? '−' : '+'} {formatMontant(Math.abs(m.montant))}{m.montant < 0 ? ' (inverse)' : ''}</TableCell>
                    {estComptable && <TableCell>{cloturee && m.montant > 0 && <Button size="small" onClick={() => setDialogue({ inverse: m })}>Écriture inverse</Button>}</TableCell>}
                  </TableRow>
                ))}
                {j.mouvements.length === 0 && <TableRow><TableCell colSpan={6} align="center">Aucun mouvement</TableCell></TableRow>}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </>}

      {estComptable && remises.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Remises à confirmer</Typography>
            {remises.map((r) => (
              <Stack key={r.id} direction="row" spacing={2} sx={{ alignItems: 'center', py: 0.5 }}>
                <Typography sx={{ flexGrow: 1 }}>{r.caisse} — {formatDate(r.date)} — {formatMontant(r.montant)}</Typography>
                <Button size="small" variant="contained" onClick={() => agir(() => api.put(`/remises/${r.id}/confirmer`), 'Remise confirmée : espèces entrées au coffre')}>Confirmer la réception</Button>
              </Stack>
            ))}
          </CardContent>
        </Card>
      )}

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Dernières clôtures</Typography>
          <Table size="small">
            <TableHead><TableRow><TableCell>Date</TableCell><TableCell align="right">Attendu</TableCell><TableCell align="right">Compté</TableCell><TableCell align="right">Écart</TableCell><TableCell>Statut</TableCell><TableCell>Explication</TableCell>{estComptable && <TableCell />}</TableRow></TableHead>
            <TableBody>
              {clotures.map((c) => (
                <TableRow key={c.id} hover sx={{ cursor: 'pointer' }} onClick={() => setJour(c.date)}>
                  <TableCell>{formatDate(c.date)}</TableCell>
                  <TableCell align="right">{formatMontant(c.montant_theorique)}</TableCell>
                  <TableCell align="right">{formatMontant(c.montant_compte)}</TableCell>
                  <TableCell align="right" sx={{ color: c.ecart < 0 ? 'error.main' : c.ecart > 0 ? 'warning.main' : undefined }}>{formatMontant(c.ecart)}</TableCell>
                  <TableCell><Etat valeur={c.statut} /></TableCell>
                  <TableCell sx={{ maxWidth: 260, whiteSpace: 'pre-line' }}>{c.explication ?? ''}</TableCell>
                  {estComptable && <TableCell onClick={(e) => e.stopPropagation()}>{c.statut !== 'contrôlée' && <Button size="small" onClick={() => setDialogue({ controle: c })}>Contrôler</Button>}</TableCell>}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialogue open={dialogue === 'encaissement'} titre="Nouvel encaissement" libelleValider="Enregistrer"
        initial={{ categorie_recette_id: j?.categories_recette?.[0]?.id ?? '', montant: '', numero_piece: '', motif: '' }}
        champs={[
          { name: 'categorie_recette_id', label: 'Catégorie', type: 'select', required: true, options: (j?.categories_recette ?? []).map((c) => ({ value: c.id, label: c.libelle })) },
          { name: 'montant', label: 'Montant (Ar)', type: 'number', required: true },
          { name: 'numero_piece', label: 'N° ticket' },
          { name: 'motif', label: 'Commentaire' },
        ]}
        onClose={() => setDialogue(null)}
        onValider={async (v) => { await api.post(`/caisses/${caisseId}/mouvements`, { type: 'encaissement', ...v }); charger() }} />

      <Dialogue open={dialogue === 'sortie'} titre="Sortie de caisse" libelleValider="Enregistrer" couleur="warning"
        description="Motif obligatoire. L'autorisation revient au responsable de l'activité (au supérieur si c'est vous)."
        initial={{ montant: '', motif: '', numero_piece: '' }}
        champs={[
          { name: 'montant', label: 'Montant (Ar)', type: 'number', required: true },
          { name: 'numero_piece', label: 'N° de pièce / facture' },
          { name: 'motif', label: 'Motif', type: 'textarea', required: true },
        ]}
        onClose={() => setDialogue(null)}
        onValider={async (v) => { await api.post(`/caisses/${caisseId}/mouvements`, { type: 'sortie', ...v }); charger() }} />

      <Dialogue open={dialogue === 'cloture'} titre={`Clôture du ${formatDate(jour)}`} libelleValider="Clôturer"
        description={j ? `Montant attendu : ${formatMontant(j.montant_theorique)}. Comptez les espèces : l'écart est calculé automatiquement. Les espèces restent en caisse jusqu'à la remise.` : ''}
        initial={{ montant_compte: '', explication: '' }}
        champs={[
          { name: 'montant_compte', label: 'Montant compté (Ar)', type: 'number', required: true },
          { name: 'explication', label: 'Explication (obligatoire en cas d\'écart)', type: 'textarea' },
        ]}
        onClose={() => setDialogue(null)}
        onValider={async (v) => {
          const { data } = await api.post(`/caisses/${caisseId}/cloture`, { date: jour, ...v, explication: v.explication || null })
          setMessage({ ok: data.ecart === 0, texte: `Clôture enregistrée — écart : ${formatMontant(data.ecart)} (${data.statut})` })
          charger()
        }} />

      <Dialogue open={!!dialogue?.controle} titre="Contrôle de la clôture" libelleValider="Enregistrer"
        description={dialogue?.controle ? `${formatDate(dialogue.controle.date)} — écart ${formatMontant(dialogue.controle.ecart)}` : ''}
        initial={{ statut: 'contrôlée', explication: '' }}
        champs={[
          { name: 'statut', label: 'Résultat', type: 'select', options: [{ value: 'contrôlée', label: 'Contrôlée' }, { value: 'écart à traiter', label: 'Écart à traiter' }] },
          { name: 'explication', label: 'Commentaire', type: 'textarea' },
        ]}
        onClose={() => setDialogue(null)}
        onValider={async (v) => { await api.put(`/clotures/${dialogue.controle.id}/controle`, { ...v, explication: v.explication || null }); charger() }} />

      <Dialogue open={!!dialogue?.inverse} titre="Écriture inverse" couleur="error" libelleValider="Passer l'écriture"
        description="Après clôture, aucune modification : une écriture inverse est créée et tracée dans le journal (décision 5)."
        initial={{ motif: '' }} champs={[{ name: 'motif', label: 'Motif', type: 'textarea', required: true }]}
        onClose={() => setDialogue(null)}
        onValider={async (v) => { await api.post(`/mouvements/${dialogue.inverse.id}/ecriture-inverse`, v); charger() }} />
    </Box>
  )
}
