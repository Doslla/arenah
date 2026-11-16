"""Droits effectifs (décisions 11, 40, 41) :
rôles des postes des affectations EN COURS + délégations actives, avec la portée de l'unité du poste
(et de ses sous-unités). Les rôles transverses ont une portée globale.
"""
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Affectation, Delegation, Poste, Unite, Utilisateur

ROLES_GLOBAUX = {"PDG", "RH", "ASSISTANT_RH", "COMPTABLE", "ASSISTANT_COMPTABLE", "RESP_ACHATS", "ADMIN_INFO"}
ROLES_SALAIRES = {"PDG", "COMPTABLE", "DIRECTEUR"}  # Remuneration lisible (le RH ne voit jamais les salaires)
ROLES_RH = {"RH", "ASSISTANT_RH"}


@dataclass
class Droits:
    utilisateur_id: int
    employe_id: int | None
    superutilisateur: bool = False
    roles: set[str] = field(default_factory=set)           # rôles issus des postes occupés
    roles_delegues: set[str] = field(default_factory=set)  # rôles reçus par délégation
    postes: list[dict] = field(default_factory=list)
    unites_portee: set[int] | None = None                  # None = portée globale
    peut_voir_salaires: bool = False

    @property
    def tous_roles(self) -> set[str]:
        return self.roles | self.roles_delegues

    def a_role(self, *codes: str) -> bool:
        return self.superutilisateur or bool(self.tous_roles & set(codes))

    def voit_unite(self, unite_id: int | None) -> bool:
        return self.unites_portee is None or unite_id in self.unites_portee


def sous_unites(db: Session, racines: set[int]) -> set[int]:
    """Unité + toutes ses sous-unités (parcours de l'arborescence)."""
    parents = {u.id: u.parent_id for u in db.execute(select(Unite.id, Unite.parent_id)).all()}
    enfants: dict[int, list[int]] = {}
    for uid, pid in parents.items():
        enfants.setdefault(pid, []).append(uid)
    resultat, pile = set(), list(racines)
    while pile:
        u = pile.pop()
        if u in resultat:
            continue
        resultat.add(u)
        pile.extend(enfants.get(u, []))
    return resultat


def calculer_droits(db: Session, utilisateur: Utilisateur, jour: date | None = None) -> Droits:
    jour = jour or date.today()
    d = Droits(utilisateur_id=utilisateur.id, employe_id=utilisateur.employe_id, superutilisateur=utilisateur.est_superutilisateur)
    if utilisateur.est_superutilisateur:
        d.roles.add("ADMIN_INFO")
    if utilisateur.employe_id is None:
        d.unites_portee = None
        d.peut_voir_salaires = utilisateur.est_superutilisateur
        return d

    affs = db.scalars(
        select(Affectation).options(joinedload(Affectation.poste).joinedload(Poste.role), joinedload(Affectation.poste).joinedload(Poste.unite))
        .where(Affectation.employe_id == utilisateur.employe_id, Affectation.date_debut <= jour,
               or_(Affectation.date_fin.is_(None), Affectation.date_fin >= jour))
    ).all()
    dels = db.scalars(
        select(Delegation).options(joinedload(Delegation.poste).joinedload(Poste.role), joinedload(Delegation.poste).joinedload(Poste.unite))
        .where(Delegation.delegataire_id == utilisateur.employe_id, Delegation.date_debut <= jour, Delegation.date_fin >= jour)
    ).all()

    racines: set[int] = set()
    for a in affs:
        p = a.poste
        d.roles.add(p.role.code)
        racines.add(p.unite_id)
        d.postes.append({"poste_id": p.id, "intitule": p.intitule, "unite_id": p.unite_id, "unite": p.unite.nom,
                         "role": p.role.code, "est_responsable": p.est_responsable, "interim": a.est_interim, "delegation": False})
    for dl in dels:
        p = dl.poste
        d.roles_delegues.add(p.role.code)
        racines.add(p.unite_id)
        d.postes.append({"poste_id": p.id, "intitule": p.intitule, "unite_id": p.unite_id, "unite": p.unite.nom,
                         "role": p.role.code, "est_responsable": p.est_responsable, "interim": False, "delegation": True})

    d.unites_portee = None if (d.tous_roles & ROLES_GLOBAUX) or d.superutilisateur else sous_unites(db, racines)
    # Décision 41 : la délégation transmet le droit de voir les salaires, sauf si le délégataire occupe un poste RH
    d.peut_voir_salaires = bool(d.roles & ROLES_SALAIRES) or (bool(d.roles_delegues & ROLES_SALAIRES) and not (d.roles & ROLES_RH))
    return d
