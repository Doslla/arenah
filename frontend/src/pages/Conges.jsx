import CrudPage from '../components/CrudPage'
import StatutChip from '../components/StatutChip'
import { congesService } from '../services'
import { employes } from '../data/mock'
import { formatDate } from '../utils/format'

const nomEmp = (id) => { const e = employes.find((x) => x.id === id); return e ? `${e.nom} ${e.prenom}`.trim() : '—' }
const jours = (r) => Math.round((new Date(r.dateFin) - new Date(r.dateDebut)) / 86400000) + 1
const types = { ANNUEL: 'Congé annuel', MALADIE: 'Maladie', SANS_SOLDE: 'Sans solde', MATERNITE: 'Maternité / Paternité' }

const colonnes = [
  { field: 'employeId', label: 'Employé', render: (r) => nomEmp(r.employeId), texte: (r) => nomEmp(r.employeId) },
  { field: 'type', label: 'Type', render: (r) => types[r.type], texte: (r) => types[r.type] },
  { field: 'dateDebut', label: 'Début', render: (r) => formatDate(r.dateDebut) },
  { field: 'dateFin', label: 'Fin', render: (r) => formatDate(r.dateFin) },
  { field: 'jours', label: 'Jours', align: 'right', render: jours },
  { field: 'statut', label: 'Statut', render: (r) => <StatutChip statut={r.statut} /> },
]
const champs = [
  { name: 'employeId', label: 'Employé', type: 'select', required: true, options: employes.map((e) => ({ value: e.id, label: nomEmp(e.id) })) },
  { name: 'type', label: 'Type', type: 'select', required: true, options: Object.entries(types).map(([value, label]) => ({ value, label })) },
  { name: 'dateDebut', label: 'Date de début', type: 'date', required: true },
  { name: 'dateFin', label: 'Date de fin', type: 'date', required: true },
  { name: 'statut', label: 'Statut', type: 'select', options: [{ value: 'EN_ATTENTE', label: 'En attente' }, { value: 'APPROUVE', label: 'Approuvé' }, { value: 'REFUSE', label: 'Refusé' }] },
]
const valeurVide = { employeId: '', type: 'ANNUEL', dateDebut: '', dateFin: '', statut: 'EN_ATTENTE' }

export default function Conges() {
  return <CrudPage titre="Congés (données fictives, branché au J3)" service={congesService} colonnes={colonnes} champs={champs} valeurVide={valeurVide} />
}
