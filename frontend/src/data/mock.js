// Données fictives des pages encore non branchées (Congés, Budgets, Dépenses) : remplacées par l'API au J3
export const categories = ['Salaires', 'Fonctionnement', 'Formation', 'Informatique', 'Déplacement']

export const departements = [
  { id: 1, code: 'DRH', nom: 'Ressources humaines', responsable: 'Mr Amboara' },
  { id: 2, code: 'DAF', nom: 'Finance et comptabilité', responsable: 'Mr Amboara' },
  { id: 3, code: 'RES', nom: 'Restaurant', responsable: 'Njaka' },
  { id: 4, code: 'PIS', nom: 'Piscine', responsable: 'Mampionona' },
]

export const employes = [
  { id: 1, nom: 'Njaka', prenom: '' },
  { id: 2, nom: 'Nirina', prenom: '' },
  { id: 3, nom: 'Faneva', prenom: '' },
  { id: 4, nom: 'Mi', prenom: '' },
]

export const conges = [
  { id: 1, employeId: 2, type: 'ANNUEL', dateDebut: '2026-11-18', dateFin: '2026-11-22', statut: 'EN_ATTENTE' },
  { id: 2, employeId: 3, type: 'MALADIE', dateDebut: '2026-11-10', dateFin: '2026-11-12', statut: 'APPROUVE' },
  { id: 3, employeId: 1, type: 'ANNUEL', dateDebut: '2026-12-22', dateFin: '2027-01-02', statut: 'EN_ATTENTE' },
]

export const budgets = [
  { id: 1, annee: 2026, departementId: 1, categorie: 'Formation', montantAlloue: 60000000, montantConsomme: 41000000 },
  { id: 2, annee: 2026, departementId: 2, categorie: 'Fonctionnement', montantAlloue: 120000000, montantConsomme: 98000000 },
  { id: 3, annee: 2026, departementId: 3, categorie: 'Fonctionnement', montantAlloue: 80000000, montantConsomme: 72000000 },
]

export const depenses = [
  { id: 1, date: '2026-11-12', libelle: 'Fournitures de bureau', categorie: 'Fonctionnement', departementId: 2, montant: 1250000, statut: 'VALIDEE' },
  { id: 2, date: '2026-11-10', libelle: 'Formation Excel', categorie: 'Formation', departementId: 1, montant: 3400000, statut: 'EN_ATTENTE' },
  { id: 3, date: '2026-11-05', libelle: 'Mission terrain', categorie: 'Déplacement', departementId: 4, montant: 2100000, statut: 'REJETEE' },
]
