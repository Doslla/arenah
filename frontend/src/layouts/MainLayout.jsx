import { useEffect, useState } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  AppBar, Avatar, Badge, Box, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, ListSubheader, Menu, MenuItem, Toolbar, Tooltip, Typography,
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import DashboardIcon from '@mui/icons-material/Dashboard'
import PeopleIcon from '@mui/icons-material/People'
import ApartmentIcon from '@mui/icons-material/Apartment'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import EventBusyIcon from '@mui/icons-material/EventBusy'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong'
import InsightsIcon from '@mui/icons-material/Insights'
import KeyIcon from '@mui/icons-material/Key'
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner'
import PointOfSaleIcon from '@mui/icons-material/PointOfSale'
import NotificationsIcon from '@mui/icons-material/Notifications'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import api from '../api/client'
import LogoutIcon from '@mui/icons-material/Logout'
import { useAuth } from '../auth/AuthContext'

const drawerWidth = 250

const sections = [
  { titre: null, items: [{ label: 'Tableau de bord', path: '/', icon: <DashboardIcon /> }] },
  { titre: 'Organisation', items: [
    { label: 'Organigramme', path: '/organigramme', icon: <AccountTreeIcon /> },
    { label: 'Unités', path: '/unites', icon: <ApartmentIcon /> },
    { label: 'Employés', path: '/employes', icon: <PeopleIcon /> },
  ] },
  { titre: 'Ressources humaines', items: [
    { label: 'Présences', path: '/presences', icon: <QrCodeScannerIcon /> },
    { label: 'Congés', path: '/conges', icon: <EventBusyIcon /> },
  ] },
  { titre: 'Finances', items: [
    { label: 'Caisses', path: '/caisses', icon: <PointOfSaleIcon /> },
    { label: 'Dépenses', path: '/depenses', icon: <ReceiptLongIcon /> },
    { label: 'Budgets', path: '/budgets', icon: <AccountBalanceIcon /> },
  ] },
  { titre: 'Pilotage', items: [
    { label: 'Alertes', path: '/alertes', icon: <WarningAmberIcon /> },
    { label: 'Prévisions IA', path: '/previsions', icon: <InsightsIcon /> },
  ] },
]
const tousItems = sections.flatMap((s) => s.items)

export default function MainLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [notifs, setNotifs] = useState({ non_lues: 0, notifications: [] })
  const [ancre, setAncre] = useState(null)

  // Notifications : rafraîchies toutes les 60 secondes et à chaque changement de page
  useEffect(() => {
    const charger = () => api.get('/notifications').then((r) => setNotifs(r.data)).catch(() => {})
    charger()
    const t = setInterval(charger, 60000)
    return () => clearInterval(t)
  }, [pathname])

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" fontWeight={700} color="primary">ARENAH</Typography>
      </Toolbar>
      {sections.map((s) => (
        <List key={s.titre ?? 'accueil'} dense subheader={s.titre && <ListSubheader>{s.titre}</ListSubheader>}>
          {s.items.map((item) => (
            <ListItemButton key={item.path} component={NavLink} to={item.path} selected={pathname === item.path} onClick={() => setMobileOpen(false)}>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      ))}
    </Box>
  )

  const postePrincipal = user?.postes?.[0]
  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" elevation={0} sx={{ width: { md: `calc(100% - ${drawerWidth}px)` }, ml: { md: `${drawerWidth}px` } }}>
        <Toolbar>
          <IconButton color="inherit" edge="start" onClick={() => setMobileOpen(!mobileOpen)} sx={{ mr: 2, display: { md: 'none' } }}>
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>{tousItems.find((m) => m.path === pathname)?.label ?? ''}</Typography>
          <Box sx={{ textAlign: 'right', mr: 1.5, display: { xs: 'none', sm: 'block' } }}>
            <Typography variant="body2" fontWeight={600}>{user?.nom_complet}</Typography>
            <Typography variant="caption" sx={{ opacity: 0.8 }}>
              {postePrincipal ? `${postePrincipal.intitule} – ${postePrincipal.unite}` : (user?.superutilisateur ? 'Administrateur' : '')}
              {user?.postes?.length > 1 ? ` (+${user.postes.length - 1})` : ''}
            </Typography>
          </Box>
          <Avatar sx={{ width: 32, height: 32, mr: 1, bgcolor: 'secondary.main' }}>{user?.nom_complet?.replace(/^(Mr|Mme) /, '')[0]}</Avatar>
          <Tooltip title="Notifications">
            <IconButton color="inherit" onClick={(e) => setAncre(e.currentTarget)}>
              <Badge badgeContent={notifs.non_lues} color="error"><NotificationsIcon /></Badge>
            </IconButton>
          </Tooltip>
          <Menu anchorEl={ancre} open={!!ancre} onClose={() => setAncre(null)} slotProps={{ paper: { sx: { width: 360, maxHeight: 420 } } }}>
            {notifs.notifications.length === 0 && <MenuItem disabled>Aucune notification</MenuItem>}
            {notifs.notifications.slice(0, 12).map((n) => (
              <MenuItem key={n.id} onClick={() => { setAncre(null); if (n.lien) navigate(n.lien) }} sx={{ whiteSpace: 'normal', fontWeight: n.lue ? 400 : 700, fontSize: 14 }}>
                <Box><Box>{n.message}</Box><Typography variant="caption" color="text.secondary">{n.date}</Typography></Box>
              </MenuItem>
            ))}
            {notifs.non_lues > 0 && (
              <MenuItem onClick={async () => { await api.put('/notifications/tout-lire'); setNotifs({ ...notifs, non_lues: 0, notifications: notifs.notifications.map((n) => ({ ...n, lue: true })) }); setAncre(null) }}>
                <Typography color="primary" variant="body2">Tout marquer comme lu</Typography>
              </MenuItem>
            )}
          </Menu>
          <Tooltip title="Changer mon mot de passe">
            <IconButton color="inherit" onClick={() => navigate('/changer-mot-de-passe')}><KeyIcon /></IconButton>
          </Tooltip>
          <Tooltip title="Déconnexion">
            <IconButton color="inherit" onClick={() => { logout(); navigate('/login') }}><LogoutIcon /></IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
        <Drawer variant="temporary" open={mobileOpen} onClose={() => setMobileOpen(false)}
          sx={{ display: { xs: 'block', md: 'none' }, '& .MuiDrawer-paper': { width: drawerWidth } }}>
          {drawer}
        </Drawer>
        <Drawer variant="permanent" open
          sx={{ display: { xs: 'none', md: 'block' }, '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' } }}>
          {drawer}
        </Drawer>
      </Box>

      <Box component="main" sx={{ flexGrow: 1, p: 3, width: { md: `calc(100% - ${drawerWidth}px)` } }}>
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  )
}
