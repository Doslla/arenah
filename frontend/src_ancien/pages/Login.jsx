import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Box, Button, Paper, TextField, Typography } from '@mui/material'
import { useAuth } from '../auth/AuthContext'
import { messageErreur } from '../api/client'

export default function Login() {
  const [identifiant, setIdentifiant] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [erreur, setErreur] = useState('')
  const [envoi, setEnvoi] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErreur('')
    setEnvoi(true)
    try {
      const profil = await login(identifiant, motDePasse)
      navigate(profil.doit_changer_mdp ? '/changer-mot-de-passe' : '/')
    } catch (err) {
      setErreur(messageErreur(err))
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', bgcolor: 'background.default' }}>
      <Paper sx={{ p: 4, width: 360 }} elevation={3}>
        <Typography variant="h5" fontWeight={700} color="primary">ARENAH</Typography>
        <Typography variant="body2" color="text.secondary" mb={2}>Gestion RH & Budget</Typography>
        {erreur && <Alert severity="error" sx={{ mb: 2 }}>{erreur}</Alert>}
        <form onSubmit={handleSubmit}>
          <TextField label="Identifiant" fullWidth margin="normal" autoFocus autoComplete="username"
            value={identifiant} onChange={(e) => setIdentifiant(e.target.value)} />
          <TextField label="Mot de passe" type="password" fullWidth margin="normal" autoComplete="current-password"
            value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} />
          <Button type="submit" variant="contained" fullWidth sx={{ mt: 2 }} disabled={envoi || !identifiant || !motDePasse}>
            {envoi ? 'Connexion…' : 'Se connecter'}
          </Button>
        </form>
      </Paper>
    </Box>
  )
}
