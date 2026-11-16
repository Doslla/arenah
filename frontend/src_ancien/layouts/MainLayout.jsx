import { useState } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  AppBar, Avatar, Box, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, ListSubheader, Toolbar, Tooltip, Typography,
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
  { titre: 'Gestion (J3)', items: [
    { label: 'Congés', path: '/conges', icon: <EventBusyIcon /> },
    { label: 'Budgets', path: '/budgets', icon: <AccountBalanceIcon /> },
    { label: 'Dépenses', path: '/depenses', icon: <ReceiptLongIcon /> },
  ] },
  { titre: 'Pilotage', items: [{ label: 'Prévisions IA', path: '/previsions', icon: <InsightsIcon /> }] },
]
const tousItems = sections.flatMap((s) => s.items)

export default function MainLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()

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
