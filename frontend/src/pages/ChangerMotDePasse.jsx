import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Box, Button, Paper, TextField, Typography } from '@mui/material'
import api, { messageErreur } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export default function ChangerMotDePasse() {
  const [ancien, setAncien] = useState('')
  const [nouveau, setNouveau] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [erreur, setErreur] = useState('')
  const { user, chargerProfil, logout } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErreur('')
    if (nouveau.length < 8) return setErreur('Le nouveau mot de passe doit contenir au moins 8 caractères')
    if (nouveau !== confirmation) return setErreur('La confirmation ne correspond pas')
    try {
      await api.post('/auth/changer-mot-de-passe', { ancien, nouveau })
      await chargerProfil()
      navigate('/')
    } catch (err) {
      setErreur(messageErreur(err))
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', bgcolor: 'background.default' }}>
      <Paper sx={{ p: 4, width: 400 }} elevation={3}>
        <Typography variant="h6" fontWeight={700}>Changer votre mot de passe</Typography>
        {user?.doit_changer_mdp && (
          <Alert severity="info" sx={{ my: 2 }}>Vous utilisez un mot de passe provisoire : choisissez-en un nouveau pour continuer.</Alert>
        )}
        {erreur && <Alert severity="error" sx={{ mb: 2 }}>{erreur}</Alert>}
        <form onSubmit={handleSubmit}>
          <TextField label="Mot de passe actuel" type="password" fullWidth margin="normal" value={ancien} onChange={(e) => setAncien(e.target.value)} />
          <TextField label="Nouveau mot de passe" type="password" fullWidth margin="normal" value={nouveau} onChange={(e) => setNouveau(e.target.value)}
            helperText="8 caractères minimum" />
          <TextField label="Confirmer le nouveau mot de passe" type="password" fullWidth margin="normal" value={confirmation} onChange={(e) => setConfirmation(e.target.value)} />
          <Button type="submit" variant="contained" fullWidth sx={{ mt: 2 }}>Enregistrer</Button>
          <Button fullWidth sx={{ mt: 1 }} onClick={() => { logout(); navigate('/login') }}>Se déconnecter</Button>
        </form>
      </Paper>
    </Box>
  )
}
