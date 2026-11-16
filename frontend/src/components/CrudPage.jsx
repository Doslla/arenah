import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, CircularProgress, Dialog, DialogActions, DialogContent,
  DialogTitle, IconButton, InputAdornment, MenuItem, Snackbar, Table, TableBody,
  TableCell, TableContainer, TableHead, TablePagination, TableRow, TextField,
  Tooltip, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import SearchIcon from '@mui/icons-material/Search'
import { messageErreur } from '../api/client'

/**
 * colonnes : [{ field, label, align?, render?(row), texte?(row) }]
 * champs : [{ name, label, type?: 'text'|'number'|'date'|'email'|'select', options?, required? }]
 * Options : modifiable (ajout / modification), supprimable, libelleSuppression, confirmationSuppression
 */
export default function CrudPage({
  titre, service, colonnes, champs, valeurVide,
  modifiable = true, supprimable = true, libelleSuppression = 'Supprimer',
  confirmationSuppression = 'Supprimer cet élément ?',
}) {
  const [rows, setRows] = useState([])
  const [chargement, setChargement] = useState(true)
  const [recherche, setRecherche] = useState('')
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [form, setForm] = useState(null)
  const [erreurs, setErreurs] = useState({})
  const [message, setMessage] = useState(null) // { texte, gravite }

  const recharger = useCallback(async () => {
    try {
      setRows(await service.list())
    } catch (err) {
      setMessage({ texte: messageErreur(err), gravite: 'error' })
    } finally {
      setChargement(false)
    }
  }, [service])

  useEffect(() => { recharger() }, [recharger])

  const filtres = useMemo(() => {
    const q = recherche.toLowerCase()
    return rows.filter((r) =>
      colonnes.some((c) => String(c.texte ? c.texte(r) : r[c.field] ?? '').toLowerCase().includes(q))
    )
  }, [rows, recherche, colonnes])

  const visibles = filtres.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)

  const ouvrir = (row) => {
    setErreurs({})
    setForm(row ? { ...row } : { ...valeurVide })
  }

  const valider = () => {
    const e = {}
    champs.forEach((c) => {
      if (c.required && (form[c.name] === '' || form[c.name] == null)) e[c.name] = 'Obligatoire'
    })
    setErreurs(e)
    return Object.keys(e).length === 0
  }

  const enregistrer = async () => {
    if (!valider()) return
    const data = { ...form }
    champs.filter((c) => c.type === 'number').forEach((c) => {
      data[c.name] = data[c.name] === '' || data[c.name] == null ? null : Number(data[c.name])
    })
    try {
      if (form.id) await service.update(form.id, data)
      else await service.create(data)
      setMessage({ texte: form.id ? 'Modification enregistrée' : 'Ajout effectué', gravite: 'success' })
      setForm(null)
      recharger()
    } catch (err) {
      setMessage({ texte: messageErreur(err), gravite: 'error' })
    }
  }

  const supprimer = async (row) => {
    if (!window.confirm(confirmationSuppression)) return
    try {
      await service.remove(row.id)
      setMessage({ texte: 'Opération effectuée', gravite: 'success' })
      recharger()
    } catch (err) {
      setMessage({ texte: messageErreur(err), gravite: 'error' })
    }
  }

  const avecActions = modifiable || supprimable

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>{titre} ({filtres.length})</Typography>
          <TextField
            size="small"
            placeholder="Rechercher…"
            value={recherche}
            onChange={(e) => { setRecherche(e.target.value); setPage(0) }}
            slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> } }}
          />
          {modifiable && <Button variant="contained" startIcon={<AddIcon />} onClick={() => ouvrir(null)}>Ajouter</Button>}
        </Box>

        {chargement ? (
          <Box sx={{ py: 6, display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {colonnes.map((c) => <TableCell key={c.field} align={c.align}>{c.label}</TableCell>)}
                  {avecActions && <TableCell align="right">Actions</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {visibles.map((row) => (
                  <TableRow key={row.id} hover>
                    {colonnes.map((c) => (
                      <TableCell key={c.field} align={c.align}>{c.render ? c.render(row) : row[c.field]}</TableCell>
                    ))}
                    {avecActions && (
                      <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                        {modifiable && (
                          <Tooltip title="Modifier">
                            <IconButton size="small" onClick={() => ouvrir(row)}><EditIcon fontSize="small" /></IconButton>
                          </Tooltip>
                        )}
                        {supprimable && (
                          <Tooltip title={libelleSuppression}>
                            <IconButton size="small" color="error" onClick={() => supprimer(row)}><DeleteIcon fontSize="small" /></IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
                {visibles.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={colonnes.length + 1} align="center">Aucun résultat</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        <TablePagination
          component="div"
          count={filtres.length}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => { setRowsPerPage(+e.target.value); setPage(0) }}
          rowsPerPageOptions={[5, 10, 25, 50]}
          labelRowsPerPage="Lignes par page"
        />
      </CardContent>

      <Dialog open={form !== null} onClose={() => setForm(null)} fullWidth maxWidth="sm">
        <DialogTitle>{form?.id ? 'Modifier' : 'Ajouter'} : {titre}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2, pt: 1 }}>
            {form && champs.map((c) => (
              <TextField
                key={c.name}
                label={c.label}
                select={c.type === 'select'}
                type={c.type === 'select' ? undefined : c.type}
                required={c.required}
                value={form[c.name] ?? ''}
                onChange={(e) => setForm({ ...form, [c.name]: e.target.value })}
                error={!!erreurs[c.name]}
                helperText={erreurs[c.name]}
                slotProps={c.type === 'date' ? { inputLabel: { shrink: true } } : undefined}
                fullWidth
              >
                {c.type === 'select' && c.options.map((o) => (
                  <MenuItem key={String(o.value)} value={o.value}>{o.label}</MenuItem>
                ))}
              </TextField>
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setForm(null)}>Annuler</Button>
          <Button variant="contained" onClick={enregistrer}>Enregistrer</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={!!message} autoHideDuration={4000} onClose={() => setMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        {message ? <Alert severity={message.gravite} variant="filled" onClose={() => setMessage(null)}>{message.texte}</Alert> : <span />}
      </Snackbar>
    </Card>
  )
}
