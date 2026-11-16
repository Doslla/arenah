"""1. Organisation : unités (arborescence), rôles, postes, employés, affectations, délégations."""
import uuid
from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Horodatage


class Unite(Horodatage, Base):
    __tablename__ = "unite"
    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(20))  # direction / département / groupe / activité
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("unite.id"), nullable=True, index=True)
    encaisse: Mapped[bool] = mapped_column(Boolean, default=False)
    seuil_depense_pdg: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # vide = paramètre global
    ordre_affichage: Mapped[int] = mapped_column(Integer, default=0)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    parent: Mapped["Unite | None"] = relationship(remote_side="Unite.id", back_populates="enfants")
    enfants: Mapped[list["Unite"]] = relationship(back_populates="parent")
    postes: Mapped[list["Poste"]] = relationship(back_populates="unite")


class Role(Horodatage, Base):
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    libelle: Mapped[str] = mapped_column(String(80))
    portee_globale: Mapped[bool] = mapped_column(Boolean, default=False)  # décision 40


class Poste(Horodatage, Base):
    __tablename__ = "poste"
    id: Mapped[int] = mapped_column(primary_key=True)
    intitule: Mapped[str] = mapped_column(String(80))
    unite_id: Mapped[int] = mapped_column(ForeignKey("unite.id"), index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"))
    est_responsable: Mapped[bool] = mapped_column(Boolean, default=False)
    tarif_extra_defaut: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # décision 19
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    unite: Mapped[Unite] = relationship(back_populates="postes")
    role: Mapped[Role] = relationship()
    affectations: Mapped[list["Affectation"]] = relationship(back_populates="poste")


class Employe(Horodatage, Base):
    __tablename__ = "employe"
    id: Mapped[int] = mapped_column(primary_key=True)
    matricule: Mapped[str] = mapped_column(String(20), unique=True)
    nom: Mapped[str] = mapped_column(String(80))
    prenom: Mapped[str] = mapped_column(String(80), default="")
    civilite: Mapped[str] = mapped_column(String(10), default="")
    cin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_naissance: Mapped[date | None] = mapped_column(Date, nullable=True)
    adresse: Mapped[str | None] = mapped_column(String(200), nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_urgence_nom: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_urgence_tel: Mapped[str | None] = mapped_column(String(30), nullable=True)
    photo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    numero_cnaps: Mapped[str | None] = mapped_column(String(30), nullable=True)
    numero_mvola: Mapped[str | None] = mapped_column(String(30), nullable=True)
    compte_bancaire: Mapped[str | None] = mapped_column(String(60), nullable=True)
    langue_preferee: Mapped[str] = mapped_column(String(2), default="fr")
    date_embauche: Mapped[date] = mapped_column(Date)
    statut: Mapped[str] = mapped_column(String(10), default="actif")  # actif / sorti
    date_sortie: Mapped[date | None] = mapped_column(Date, nullable=True)
    motif_sortie: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: uuid.uuid4().hex)

    affectations: Mapped[list["Affectation"]] = relationship(back_populates="employe")


class Affectation(Horodatage, Base):
    """Cumul de postes (décision 11) : plusieurs affectations en cours possibles."""
    __tablename__ = "affectation"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    poste_id: Mapped[int] = mapped_column(ForeignKey("poste.id"), index=True)
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date, nullable=True)  # vide = en cours
    est_interim: Mapped[bool] = mapped_column(Boolean, default=False)
    motif: Mapped[str | None] = mapped_column(Text, nullable=True)

    employe: Mapped[Employe] = relationship(back_populates="affectations")
    poste: Mapped[Poste] = relationship(back_populates="affectations")


class Delegation(Horodatage, Base):
    __tablename__ = "delegation"
    id: Mapped[int] = mapped_column(primary_key=True)
    delegant_id: Mapped[int] = mapped_column(ForeignKey("employe.id"))
    delegataire_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    poste_id: Mapped[int] = mapped_column(ForeignKey("poste.id"))
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date] = mapped_column(Date)
    motif: Mapped[str | None] = mapped_column(Text, nullable=True)

    delegant: Mapped[Employe] = relationship(foreign_keys=[delegant_id])
    delegataire: Mapped[Employe] = relationship(foreign_keys=[delegataire_id])
    poste: Mapped[Poste] = relationship()
