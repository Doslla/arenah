from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Lecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------- Authentification
class Jeton(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doit_changer_mdp: bool


class ChangementMotDePasse(BaseModel):
    ancien: str
    nouveau: str = Field(min_length=8, max_length=128)


class MotDePasseProvisoire(BaseModel):
    login: str
    mot_de_passe_provisoire: str


class Moi(BaseModel):
    utilisateur_id: int
    login: str
    employe_id: int | None
    nom_complet: str
    superutilisateur: bool
    doit_changer_mdp: bool
    langue: str
    roles: list[str]
    roles_delegues: list[str]
    postes: list[dict]
    portee_globale: bool
    unites_portee: list[int] | None
    peut_voir_salaires: bool


# ---------------------------------------------------------- Paramètres et calendrier
class ParametreSortie(Lecture):
    id: int
    cle: str
    valeur: str
    type: str
    description: str | None


class ParametreMaj(BaseModel):
    valeur: str = Field(min_length=1, max_length=255)


class EvenementEntree(BaseModel):
    date_debut: date
    date_fin: date
    type: str = Field(pattern="^(ferie|grande_fete|vacances_scolaires|fermeture)$")
    libelle: str = Field(min_length=2, max_length=120)
    fiabilite: str = "officiel"


class EvenementSortie(Lecture):
    id: int
    date_debut: date
    date_fin: date
    type: str
    libelle: str
    fiabilite: str


class Referentiel(Lecture):
    id: int
    libelle: str
    actif: bool = True
