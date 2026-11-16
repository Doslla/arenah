import { Paper, Typography } from '@mui/material'

export default function EnConstruction({ titre }) {
  return (
    <Paper sx={{ p: 4 }}>
      <Typography variant="h5" gutterBottom>{titre}</Typography>
      <Typography color="text.secondary">Page en cours de construction.</Typography>
    </Paper>
  )
}
