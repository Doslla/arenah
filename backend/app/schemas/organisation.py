from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Lecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------- Unités
class UniteEntree(BaseModel):
    nom: str = Field(min_length=2, max_length=120)
    type: str = Field(pattern="^(direction|département|groupe|activité)$")
    parent_id: int | None = None
    encaisse: bool = False
    seuil_depense_pdg: int | None = None
    ordre_affichage: int = 0
    actif: bool = True


class UniteSortie(Lecture):
    id: int
    nom: str
    type: str
    parent_id: int | None
    encaisse: bool
    seuil_depense_pdg: int | None
    ordre_affichage: int
    actif: bool


# ---------------------------------------------------------- Rôles et postes
class RoleSortie(Lecture):
    id: int
    code: str
    libelle: str
    portee_globale: bool


class PosteEntree(BaseModel):
    intitule: str = Field(min_length=2, max_length=80)
    unite_id: int
    role_id: int
    est_responsable: bool = False
    tarif_extra_defaut: int | None = None
    actif: bool = True


class PosteSortie(Lecture):
    id: int
    intitule: str
    unite_id: int
    role_id: int
    est_responsable: bool
    tarif_extra_defaut: int | None
    actif: bool
    unite_nom: str | None = None
    role_code: str | None = None
    titulaires: list[str] = []


# ---------------------------------------------------------- Employés
class EmployeEntree(BaseModel):
    matricule: str = Field(min_length=2, max_length=20)
    nom: str = Field(min_length=1, max_length=80)
    prenom: str = ""
    civilite: str = ""
    cin: str | None = None
    date_naissance: date | None = None
    adresse: str | None = None
    telephone: str | None = None
    email: str | None = None
    contact_urgence_nom: str | None = None
    contact_urgence_tel: str | None = None
    numero_cnaps: str | None = None
    numero_mvola: str | None = None
    langue_preferee: str = "fr"
    date_embauche: date
    statut: str = "actif"


class EmployeSortie(Lecture):
    id: int
    matricule: str
    nom: str
    prenom: str
    civilite: str
    cin: str | None
    date_naissance: date | None
    adresse: str | None
    telephone: str | None
    email: str | None
    contact_urgence_nom: str | None
    contact_urgence_tel: str | None
    numero_cnaps: str | None
    numero_mvola: str | None
    langue_preferee: str
    date_embauche: date
    statut: str
    date_sortie: date | None
    motif_sortie: str | None
    postes: list[str] = []
    unites: list[str] = []
    login: str | None = None


class SortieEmploye(BaseModel):
    date_sortie: date
    motif_sortie: str = Field(min_length=3)


# ---------------------------------------------------------- Affectations et délégations
class AffectationEntree(BaseModel):
    employe_id: int
    poste_id: int
    date_debut: date
    date_fin: date | None = None
    est_interim: bool = False
    motif: str | None = None


class AffectationSortie(Lecture):
    id: int
    employe_id: int
    poste_id: int
    date_debut: date
    date_fin: date | None
    est_interim: bool
    motif: str | None
    employe_nom: str | None = None
    poste_libelle: str | None = None
    en_cours: bool = True


class FinAffectation(BaseModel):
    date_fin: date
    motif: str | None = None


class DelegationEntree(BaseModel):
    delegant_id: int
    delegataire_id: int
    poste_id: int
    date_debut: date
    date_fin: date
    motif: str | None = None


class DelegationSortie(Lecture):
    id: int
    delegant_id: int
    delegataire_id: int
    poste_id: int
    date_debut: date
    date_fin: date
    motif: str | None
    delegant_nom: str | None = None
    delegataire_nom: str | None = None
    poste_libelle: str | None = None
