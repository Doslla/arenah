"""10-13. Communication, utilisateurs et sécurité, pilotage et IA, traçabilité."""
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Horodatage


# ---------------------------------------------------------- Communication
class Publication(Horodatage, Base):
    __tablename__ = "publication"
    id: Mapped[int] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(150))
    contenu: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(15), default="annonce")  # annonce / réunion / planning
    cible: Mapped[str] = mapped_column(String(10), default="tous")  # tous / unité / rôle
    cible_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_evenement: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auteur_id: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    date_publication: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LecturePublication(Horodatage, Base):
    __tablename__ = "lecture_publication"
    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey("publication.id"), index=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"))
    lu_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Horodatage, Base):
    __tablename__ = "notification"
    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateur.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    lien: Mapped[str | None] = mapped_column(String(255), nullable=True)
    canal: Mapped[str] = mapped_column(String(15), default="application")  # application / e-mail / push
    lue: Mapped[bool] = mapped_column(Boolean, default=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------- Sécurité
class Utilisateur(Horodatage, Base):
    __tablename__ = "utilisateur"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), unique=True, nullable=True)  # vide = admin technique
    login: Mapped[str] = mapped_column(String(60), unique=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    doit_changer_mdp: Mapped[bool] = mapped_column(Boolean, default=True)  # décision 34
    est_superutilisateur: Mapped[bool] = mapped_column(Boolean, default=False)
    langue: Mapped[str] = mapped_column(String(2), default="fr")
    derniere_connexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Appareil(Horodatage, Base):
    __tablename__ = "appareil"
    id: Mapped[int] = mapped_column(primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateur.id"))
    nom: Mapped[str] = mapped_column(String(80))
    plateforme: Mapped[str] = mapped_column(String(10), default="web")
    derniere_synchro: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------- Pilotage et IA
class ParametreAlerte(Horodatage, Base):
    __tablename__ = "parametre_alerte"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(30))
    seuil: Mapped[float] = mapped_column(Numeric(12, 2))
    unite_id: Mapped[int | None] = mapped_column(ForeignKey("unite.id"), nullable=True)
    roles_destinataires: Mapped[str] = mapped_column(String(200))  # codes séparés par des virgules
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Alerte(Horodatage, Base):
    __tablename__ = "alerte"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(30))  # budget / dépassement prévu / écart caisse / anomalie / absences / fin de contrat / fin d'essai
    niveau: Mapped[str] = mapped_column(String(10), default="info")  # info / attention / critique
    message: Mapped[str] = mapped_column(Text)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)  # « basé sur les 8 derniers samedis »
    entite: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entite_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unite_id: Mapped[int | None] = mapped_column(ForeignKey("unite.id"), nullable=True)
    role_destinataire: Mapped[str | None] = mapped_column(String(30), nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    traitee_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    statut: Mapped[str] = mapped_column(String(15), default="nouvelle")  # nouvelle / vue / traitée


class ModeleIA(Horodatage, Base):
    __tablename__ = "modele_ia"
    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(60))  # prévision encaissements / anomalies caisse / budget
    unite_id: Mapped[int | None] = mapped_column(ForeignKey("unite.id"), nullable=True)
    algorithme: Mapped[str] = mapped_column(String(40))
    version: Mapped[int] = mapped_column(Integer, default=1)
    metriques: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fichier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_entrainement: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Prevision(Horodatage, Base):
    __tablename__ = "prevision"
    id: Mapped[int] = mapped_column(primary_key=True)
    modele_id: Mapped[int] = mapped_column(ForeignKey("modele_ia.id"), index=True)
    type: Mapped[str] = mapped_column(String(15))  # encaissements / dépenses
    unite_id: Mapped[int | None] = mapped_column(ForeignKey("unite.id"), nullable=True)
    date_cible: Mapped[date] = mapped_column(Date, index=True)
    valeur_prevue: Mapped[int] = mapped_column(BigInteger)
    borne_basse: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    borne_haute: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_calcul: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnomalieDetectee(Horodatage, Base):
    __tablename__ = "anomalie_detectee"
    id: Mapped[int] = mapped_column(primary_key=True)
    modele_id: Mapped[int] = mapped_column(ForeignKey("modele_ia.id"))
    entite: Mapped[str] = mapped_column(String(30))  # mouvement / clôture / dépense
    entite_id: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Numeric(8, 4))
    explication: Mapped[str] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(String(15), default="à revoir")  # à revoir / confirmée / fausse alerte
    revue_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    date_revue: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------- Traçabilité
class Correction(Horodatage, Base):
    __tablename__ = "correction"
    id: Mapped[int] = mapped_column(primary_key=True)
    entite: Mapped[str] = mapped_column(String(40))
    entite_id: Mapped[str] = mapped_column(String(40))
    type: Mapped[str] = mapped_column(String(30))  # modification avant clôture / écriture inverse après
    motif: Mapped[str] = mapped_column(Text)
    auteur_id: Mapped[int] = mapped_column(ForeignKey("employe.id"))
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JournalAudit(Base):
    """Ajout seul : rempli par trigger PostgreSQL, jamais modifié ni supprimé (migration 0002)."""
    __tablename__ = "journal_audit"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    utilisateur_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(10))  # INSERT / UPDATE / DELETE
    table_nom: Mapped[str] = mapped_column(String(60), index=True)
    entite_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    valeurs_avant: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    valeurs_apres: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    adresse_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    appareil_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
