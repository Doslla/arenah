import CrudPage from '../components/CrudPage'
import StatutChip from '../components/StatutChip'
import { depensesService } from '../services'
import { categories, departements } from '../data/mock'
import { formatDate, formatMontant } from '../utils/format'

const nomDep = (id) => departements.find((d) => d.id === id)?.nom ?? '—'

const colonnes = [
  { field: 'date', label: 'Date', render: (r) => formatDate(r.date) },
  { field: 'libelle', label: 'Libellé' },
  { field: 'categorie', label: 'Catégorie' },
  { field: 'departementId', label: 'Unité', render: (r) => nomDep(r.departementId), texte: (r) => nomDep(r.departementId) },
  { field: 'montant', label: 'Montant', align: 'right', render: (r) => formatMontant(r.montant) },
  { field: 'statut', label: 'Statut', render: (r) => <StatutChip statut={r.statut} /> },
]
const champs = [
  { name: 'date', label: 'Date', type: 'date', required: true },
  { name: 'libelle', label: 'Libellé', required: true },
  { name: 'categorie', label: 'Catégorie', type: 'select', required: true, options: categories.map((c) => ({ value: c, label: c })) },
  { name: 'departementId', label: 'Unité', type: 'select', required: true, options: departements.map((d) => ({ value: d.id, label: d.nom })) },
  { name: 'montant', label: 'Montant', type: 'number', required: true },
  { name: 'statut', label: 'Statut', type: 'select', options: [{ value: 'EN_ATTENTE', label: 'En attente' }, { value: 'VALIDEE', label: 'Validée' }, { value: 'REJETEE', label: 'Rejetée' }] },
]
const valeurVide = { date: '', libelle: '', categorie: '', departementId: '', montant: '', statut: 'EN_ATTENTE' }

export default function Depenses() {
  return <CrudPage titre="Dépenses (données fictives, branché au J3)" service={depensesService} colonnes={colonnes} champs={champs} valeurVide={valeurVide} />
}
