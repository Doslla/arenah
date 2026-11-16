import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Stack, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, TextField, Typography,
} from '@mui/material'
import { QRCodeSVG } from 'qrcode.react'
import { Html5QrcodeScanner } from 'html5-qrcode'
import api, { messageErreur } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Dialogue from '../components/Dialogue'
import { Chargement, Etat } from '../components/Etat'
import { formatDate } from '../utils/format'

const aujourdhui = () => new Date().toLocaleDateString('sv-SE') // date locale AAAA-MM-JJ (pas UTC)

function Pointage({ peutPointer }) {
  const [jour, setJour] = useState(aujourdhui())
  const [lignes, setLignes] = useState(null)
  const [equipe, setEquipe] = useState([])
  const [saisie, setSaisie] = useState(false)
  const charger = useCallback(() => api.get('/presences', { params: { jour } }).then((r) => setLignes(r.data)), [jour])
  useEffect(() => { charger() }, [charger])
  useEffect(() => { if (peutPointer) api.get('/badges').then((r) => setEquipe(r.data)) }, [peutPointer])

  return (
    <Card>
      <CardContent>
        <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <TextField type="date" size="small" label="Jour" value={jour} onChange={(e) => setJour(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
          <Box sx={{ flexGrow: 1 }} />
          {peutPointer && <Button variant="outlined" onClick={() => setSaisie(true)}>Saisie manuelle</Button>}
        </Stack>
        {!lignes ? <Chargement /> : (
          <Table size="small">
            <TableHead><TableRow>
              <TableCell>Employé</TableCell><TableCell>Unité</TableCell><TableCell>Prévue</TableCell><TableCell>Arrivée</TableCell>
              <TableCell>Départ</TableCell><TableCell>Statut</TableCell><TableCell>Saisie</TableCell>
            </TableRow></TableHead>
            <TableBody>
              {lignes.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>{p.employe}</TableCell><TableCell>{p.unite}</TableCell><TableCell>{p.heure_prevue}</TableCell>
                  <TableCell>{p.heure_arrivee ?? '—'}</TableCell><TableCell>{p.heure_depart ?? '—'}</TableCell>
                  <TableCell><Etat valeur={p.statut} />{p.statut === 'absent' && p.absence_justifiee ? ' (justifiée)' : ''}</TableCell>
                  <TableCell>{p.source_saisie}</TableCell>
                </TableRow>
              ))}
              {lignes.length === 0 && <TableRow><TableCell colSpan={7} align="center">Aucun pointage ce jour</TableCell></TableRow>}
            </TableBody>
          </Table>
        )}
      </CardContent>
      <Dialogue open={saisie} titre="Saisie manuelle de présence" description="Badge oublié ou illisible : saisie de secours (tracée)."
        initial={{ date: jour, statut: 'présent', heure_arrivee: '08:00', heure_depart: '' }}
        champs={[
          { name: 'employe_id', label: 'Employé', type: 'select', required: true, options: equipe.map((e) => ({ value: e.employe_id, label: e.nom })) },
          { name: 'date', label: 'Date', type: 'date', required: true },
          { name: 'statut', label: 'Statut', type: 'select', options: ['présent', 'retard', 'absent'].map((s) => ({ value: s, label: s })) },
          { name: 'heure_arrivee', label: 'Arrivée', type: 'time' },
          { name: 'heure_depart', label: 'Départ', type: 'time' },
        ]}
        onClose={() => setSaisie(false)}
        onValider={async (v) => { await api.post('/presences/manuel', { ...v, heure_arrivee: v.heure_arrivee || null, heure_depart: v.heure_depart || null }); charger() }} />
    </Card>
  )
}

function Scanner() {
  const [resultat, setResultat] = useState(null)
  const [code, setCode] = useState('')
  const dernier = useRef({ code: '', t: 0 })

  const envoyer = useCallback(async (token) => {
    const now = Date.now()
    if (token === dernier.current.code && now - dernier.current.t < 5000) return // évite les doubles lectures
    dernier.current = { code: token, t: now }
    try {
      const { data } = await api.post('/presences/scan', { qr_token: token })
      setResultat({ ok: true, texte: `${data.employe} : ${data.action} à ${data.heure}` })
    } catch (err) {
      setResultat({ ok: false, texte: messageErreur(err) })
    }
  }, [])

  useEffect(() => {
    const scanner = new Html5QrcodeScanner('lecteur-qr', { fps: 10, qrbox: 240 }, false)
    scanner.render((texte) => envoyer(texte), () => {})
    return () => { scanner.clear().catch(() => {}) }
  }, [envoyer])

  return (
    <Card>
      <CardContent>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Présentez le badge devant la caméra : 1er passage = arrivée, 2e passage = départ. Sur téléphone, la caméra exige une adresse HTTPS (ou localhost).
        </Typography>
        {resultat && <Alert severity={resultat.ok ? 'success' : 'error'} sx={{ mb: 2 }}>{resultat.texte}</Alert>}
        <Box id="lecteur-qr" sx={{ maxWidth: 420 }} />
        <Stack direction="row" spacing={1} sx={{ mt: 2, maxWidth: 420 }}>
          <TextField size="small" fullWidth label="Ou saisir le code du badge" value={code} onChange={(e) => setCode(e.target.value)} />
          <Button variant="contained" disabled={!code} onClick={() => { envoyer(code.trim()); setCode('') }}>Pointer</Button>
        </Stack>
      </CardContent>
    </Card>
  )
}

function Badges() {
  const [badges, setBadges] = useState(null)
  useEffect(() => { api.get('/badges').then((r) => setBadges(r.data)) }, [])
  if (!badges) return <Chargement />
  return (
    <Box>
      <Button variant="outlined" sx={{ mb: 2, '@media print': { display: 'none' } }} onClick={() => window.print()}>Imprimer les badges</Button>
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
        {badges.map((b) => (
          <Card key={b.employe_id} variant="outlined" sx={{ textAlign: 'center', breakInside: 'avoid' }}>
            <CardContent>
              <Typography variant="subtitle2" color="primary" fontWeight={700}>ARENAH</Typography>
              <Box sx={{ my: 1 }}><QRCodeSVG value={b.qr_token} size={140} /></Box>
              <Typography fontWeight={700}>{b.nom}</Typography>
              <Typography variant="caption" color="text.secondary">{b.matricule} · {b.unite}</Typography>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  )
}

function Avertissements({ estRH }) {
  const [liste, setListe] = useState(null)
  const charger = useCallback(() => api.get('/avertissements').then((r) => setListe(r.data)), [])
  useEffect(() => { charger() }, [charger])
  const decider = async (id, statut) => { await api.put(`/avertissements/${id}`, { statut }); charger() }
  if (!liste) return <Chargement />
  return (
    <Card>
      <CardContent>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Proposés automatiquement après 48 h sans justificatif (1re absence : rappel à l'ordre ; 3e du mois : avertissement). Le RH décide. Aucun effet sur la paie.
        </Typography>
        <Table size="small">
          <TableHead><TableRow><TableCell>Date</TableCell><TableCell>Employé</TableCell><TableCell>Type</TableCell><TableCell>Motif</TableCell><TableCell>Statut</TableCell>{estRH && <TableCell />}</TableRow></TableHead>
          <TableBody>
            {liste.map((a) => (
              <TableRow key={a.id}>
                <TableCell>{formatDate(a.date)}</TableCell><TableCell>{a.employe}</TableCell><TableCell>{a.type}</TableCell>
                <TableCell>{a.motif}</TableCell><TableCell><Etat valeur={a.statut} /></TableCell>
                {estRH && <TableCell sx={{ whiteSpace: 'nowrap' }}>{a.statut === 'proposé' && <>
                  <Button size="small" color="error" onClick={() => decider(a.id, 'émis')}>Émettre</Button>
                  <Button size="small" onClick={() => decider(a.id, 'annulé')}>Annuler</Button>
                </>}</TableCell>}
              </TableRow>
            ))}
            {liste.length === 0 && <TableRow><TableCell colSpan={6} align="center">Aucun avertissement</TableCell></TableRow>}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

export default function Presences() {
  const { aRole } = useAuth()
  const peutPointer = aRole('RESPONSABLE_ACTIVITE', 'DIRECTEUR', 'RH', 'ASSISTANT_RH', 'PDG', 'ADMIN_INFO')
  const [onglet, setOnglet] = useState(0)
  const onglets = [['Pointage', <Pointage key="p" peutPointer={peutPointer} />]]
  if (peutPointer) onglets.push(['Scanner un badge', <Scanner key="s" />])
  onglets.push(['Badges QR', <Badges key="b" />], ['Avertissements', <Avertissements key="a" estRH={aRole('RH', 'ASSISTANT_RH')} />])
  return (
    <Box>
      <Tabs value={onglet} onChange={(_, v) => setOnglet(v)} sx={{ mb: 2, '@media print': { display: 'none' } }}>
        {onglets.map(([l]) => <Tab key={l} label={l} />)}
      </Tabs>
      {onglets[onglet][1]}
    </Box>
  )
}
