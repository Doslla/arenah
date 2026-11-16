import { useEffect, useState } from 'react'
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, TextField, Typography } from '@mui/material'
import { messageErreur } from '../api/client'

/**
 * Petit formulaire en fenêtre, réutilisable.
 * champs : [{ name, label, type?: 'text'|'number'|'date'|'time'|'select'|'textarea', options?, required?, aide? }]
 * onValider(valeurs) : fonction async ; une erreur API s'affiche dans la fenêtre.
 */
export default function Dialogue({ open, titre, description, champs, initial = {}, libelleValider = 'Valider', couleur = 'primary', onClose, onValider }) {
  const [valeurs, setValeurs] = useState(initial)
  const [erreur, setErreur] = useState('')
  const [envoi, setEnvoi] = useState(false)

  useEffect(() => {
    if (open) { setValeurs(initial); setErreur('') }
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  const valider = async () => {
    const manquant = champs.find((c) => c.required && (valeurs[c.name] === '' || valeurs[c.name] == null))
    if (manquant) return setErreur(`« ${manquant.label} » est obligatoire`)
    const data = { ...valeurs }
    champs.filter((c) => c.type === 'number').forEach((c) => {
      data[c.name] = data[c.name] === '' || data[c.name] == null ? null : Number(data[c.name])
    })
    setEnvoi(true)
    try {
      await onValider(data)
      onClose()
    } catch (err) {
      setErreur(messageErreur(err))
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{titre}</DialogTitle>
      <DialogContent>
        {description && <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{description}</Typography>}
        {erreur && <Alert severity="error" sx={{ mb: 2 }}>{erreur}</Alert>}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2, pt: 1 }}>
          {champs.map((c) => (
            <TextField
              key={c.name}
              label={c.label}
              select={c.type === 'select'}
              type={['select', 'textarea'].includes(c.type) ? undefined : c.type}
              multiline={c.type === 'textarea'}
              minRows={c.type === 'textarea' ? 2 : undefined}
              required={c.required}
              helperText={c.aide}
              value={valeurs[c.name] ?? ''}
              onChange={(e) => setValeurs({ ...valeurs, [c.name]: e.target.value })}
              slotProps={['date', 'time'].includes(c.type) ? { inputLabel: { shrink: true } } : undefined}
              sx={{ gridColumn: c.type === 'textarea' || c.large ? '1 / -1' : undefined }}
              fullWidth
            >
              {c.type === 'select' && c.options.map((o) => <MenuItem key={String(o.value)} value={o.value}>{o.label}</MenuItem>)}
            </TextField>
          ))}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Annuler</Button>
        <Button variant="contained" color={couleur} onClick={valider} disabled={envoi}>{envoi ? '…' : libelleValider}</Button>
      </DialogActions>
    </Dialog>
  )
}
