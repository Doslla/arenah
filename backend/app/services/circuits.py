"""Résolution des valideurs et remontée (décisions 9, 11, 39, 40 et arbitrages du 20 octobre).

- Le valideur est déterminé AU MOMENT de la décision (délégations et nominations prises en compte).
- Titulaire et délégataire peuvent tous deux décider ; le journal indique qui.
- Si le valideur résolu est le demandeur, l'étape remonte :
  * étape d'AVIS : le supérieur prend la place de l'étape ;
  * étape de DÉCISION : le supérieur valide en dernier, une seule fois.
- Supérieur d'un rôle transverse : le PDG. Supérieur d'un rôle d'unité : le responsable de la
  première unité parente qui a un responsable en poste (groupes sautés, demandeur exclu).
"""
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Affectation, Delegation, Employe, Notification, Parametre, Poste, Role, Unite, Utilisateur


def _affs_en_cours(jour: date):
    return (Affectation.date_debut <= jour, or_(Affectation.date_fin.is_(None), Affectation.date_fin >= jour))


def titulaires_postes(db: Session, poste_ids: list[int], jour: date | None = None) -> set[int]:
    """Employés qui occupent ces postes (affectation en cours) ou les détiennent par délégation active."""
    if not poste_ids:
        return set()
    jour = jour or date.today()
    ids = set(db.scalars(select(Affectation.employe_id).where(Affectation.poste_id.in_(poste_ids), *_affs_en_cours(jour))))
    ids |= set(db.scalars(select(Delegation.delegataire_id).where(Delegation.poste_id.in_(poste_ids),
                                                                  Delegation.date_debut <= jour, Delegation.date_fin >= jour)))
    return ids


def titulaires_role(db: Session, code: str, jour: date | None = None) -> set[int]:
    postes = list(db.scalars(select(Poste.id).join(Role).where(Role.code == code, Poste.actif)))
    return titulaires_postes(db, postes, jour)


def unite_principale(db: Session, employe_id: int, jour: date | None = None) -> int | None:
    """Unité du premier poste occupé (les responsables d'activité passent avant les rôles transverses)."""
    jour = jour or date.today()
    rows = db.execute(select(Poste.unite_id, Poste.est_responsable, Unite.type).join(Affectation, Affectation.poste_id == Poste.id)
                      .join(Unite, Unite.id == Poste.unite_id)
                      .where(Affectation.employe_id == employe_id, *_affs_en_cours(jour)).order_by(Affectation.id)).all()
    if not rows:
        return None
    activites = [r for r in rows if r.type == "activité"]
    return (activites or rows)[0].unite_id


def responsable_unite(db: Session, unite_id: int, exclure: set[int], jour: date | None = None) -> tuple[set[int], int | None]:
    """Responsables de l'unité ; si aucun (ou seulement des exclus), on remonte aux unités parentes."""
    jour = jour or date.today()
    u = db.get(Unite, unite_id)
    while u is not None:
        postes = list(db.scalars(select(Poste.id).where(Poste.unite_id == u.id, Poste.est_responsable, Poste.actif)))
        resp = titulaires_postes(db, postes, jour) - exclure
        if resp:
            return resp, u.id
        u = db.get(Unite, u.parent_id) if u.parent_id else None
    return titulaires_role(db, "PDG", jour) - exclure, None


def noms(db: Session, ids: set[int]) -> list[str]:
    if not ids:
        return []
    return [f"{e.civilite} {e.nom} {e.prenom}".strip() for e in db.scalars(select(Employe).where(Employe.id.in_(ids)).order_by(Employe.nom))]


def parametre(db: Session, cle: str, defaut: str) -> str:
    v = db.scalar(select(Parametre.valeur).where(Parametre.cle == cle))
    return v if v is not None else defaut


def notifier(db: Session, employe_ids: set[int], message: str, lien: str | None = None):
    """Notification dans l'application (décision 33). E-mail et push : plus tard."""
    if not employe_ids:
        return
    for uid in db.scalars(select(Utilisateur.id).where(Utilisateur.employe_id.in_(employe_ids), Utilisateur.actif)):
        db.add(Notification(utilisateur_id=uid, message=message, lien=lien))


def notifier_role(db: Session, codes: list[str], message: str, lien: str | None = None, exclure: set[int] | None = None):
    ids: set[int] = set()
    for c in codes:
        ids |= titulaires_role(db, c)
    notifier(db, ids - (exclure or set()), message, lien)
