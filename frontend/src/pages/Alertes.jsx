import { useCallback, useEffect, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, Typography } from '@mui/material'
import api from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { Chargement, Etat } from '../components/Etat'

export default function Alertes() {
  const { aRole } = useAuth()
  const [onglet, setOnglet] = useState(0)
  const [liste, setListe] = useState(null)
  const [info, setInfo] = useState('')
  const charger = useCallback(() => {
    setListe(null)
    api.get('/alertes', { params: onglet === 0 ? { statut: 'nouvelle' } : {} }).then((r) => setListe(r.data))
  }, [onglet])
  useEffect(() => { charger() }, [charger])

  const recalculer = async () => {
    const { data } = await api.post('/alertes/recalculer')
    setInfo('Alertes recalculées : ' + Object.entries(data).map(([k, v]) => `${k} ${v}`).join(' · '))
    charger()
  }
  const marquer = async (id, statut) => { await api.put(`/alertes/${id}`, { statut }); charger() }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
          <Tabs value={onglet} onChange={(_, v) => setOnglet(v)} sx={{ flexGrow: 1 }}><Tab label="Nouvelles" /><Tab label="Toutes" /></Tabs>
          {aRole('COMPTABLE', 'RH', 'PDG', 'DIRECTEUR', 'ADMIN_INFO') && <Button variant="outlined" onClick={recalculer}>Recalculer maintenant</Button>}
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ my: 1 }}>
          Alertes par règles : budget du mois au-delà du seuil, écarts de caisse, fins de contrat et d'essai, absences non justifiées. Chaque alerte indique sa justification.
        </Typography>
        {info && <Alert severity="success" onClose={() => setInfo('')} sx={{ mb: 2 }}>{info}</Alert>}
        {!liste ? <Chargement /> : (
          <Table size="small">
            <TableHead><TableRow><TableCell>Date</TableCell><TableCell>Type</TableCell><TableCell>Niveau</TableCell><TableCell>Message</TableCell><TableCell>Justification</TableCell><TableCell>Pour</TableCell><TableCell>Statut</TableCell><TableCell /></TableRow></TableHead>
            <TableBody>
              {liste.map((a) => (
                <TableRow key={a.id}>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{a.date}</TableCell><TableCell>{a.type}</TableCell><TableCell><Etat valeur={a.niveau} /></TableCell>
                  <TableCell>{a.message}</TableCell><TableCell sx={{ color: 'text.secondary' }}>{a.justification}</TableCell>
                  <TableCell>{a.role_destinataire}</TableCell><TableCell><Etat valeur={a.statut} /></TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {a.statut === 'nouvelle' && <Button size="small" onClick={() => marquer(a.id, 'vue')}>Vue</Button>}
                    {a.statut !== 'traitée' && <Button size="small" color="success" onClick={() => marquer(a.id, 'traitée')}>Traitée</Button>}
                  </TableCell>
                </TableRow>
              ))}
              {liste.length === 0 && <TableRow><TableCell colSpan={8} align="center">Aucune alerte</TableCell></TableRow>}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
