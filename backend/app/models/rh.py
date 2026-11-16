"""3-5. Contrats et rémunération, planning, présences, discipline, congés."""
import uuid
from datetime import date, datetime, time

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Horodatage


class Contrat(Horodatage, Base):
    __tablename__ = "contrat"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    type_contrat_id: Mapped[int] = mapped_column(ForeignKey("type_contrat.id"))
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    fin_periode_essai: Mapped[date | None] = mapped_column(Date, nullable=True)
    fichier_signe: Mapped[str | None] = mapped_column(String(255), nullable=True)
    statut: Mapped[str] = mapped_column(String(15), default="actif")  # actif / terminé / rompu


class Remuneration(Horodatage, Base):
    """TABLE PROTÉGÉE : lisible par Comptable, PDG et directeur ; jamais par le RH (décision 2)."""
    __tablename__ = "remuneration"
    id: Mapped[int] = mapped_column(primary_key=True)
    contrat_id: Mapped[int] = mapped_column(ForeignKey("contrat.id"), index=True)
    salaire_fixe: Mapped[int] = mapped_column(BigInteger)
    date_effet: Mapped[date] = mapped_column(Date)


class JourExtra(Horodatage, Base):
    __tablename__ = "jour_extra"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    unite_id: Mapped[int] = mapped_column(ForeignKey("unite.id"))
    date: Mapped[date] = mapped_column(Date)
    tarif_journalier: Mapped[int] = mapped_column(BigInteger)
    declare_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    valide_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    statut: Mapped[str] = mapped_column(String(15), default="déclaré")  # déclaré / validé / refusé / payé


class Creneau(Horodatage, Base):
    __tablename__ = "creneau"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    unite_id: Mapped[int] = mapped_column(ForeignKey("unite.id"))
    date: Mapped[date] = mapped_column(Date, index=True)
    heure_debut: Mapped[time] = mapped_column(Time)
    heure_fin: Mapped[time] = mapped_column(Time)
    publie: Mapped[bool] = mapped_column(Boolean, default=False)


class Presence(Horodatage, Base):
    """Pointage QR scanné par le responsable, saisie manuelle de secours (décision 14)."""
    __tablename__ = "presence"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    unite_id: Mapped[int] = mapped_column(ForeignKey("unite.id"))
    date: Mapped[date] = mapped_column(Date, index=True)
    heure_prevue: Mapped[time | None] = mapped_column(Time, nullable=True)
    heure_arrivee: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    heure_depart: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_saisie: Mapped[str] = mapped_column(String(10), default="QR")  # QR / manuel
    statut: Mapped[str] = mapped_column(String(10))  # présent / retard / absent
    absence_justifiee: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    saisi_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    appareil_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synchronise_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="saisie")  # saisie / import_historique / synthetique


class Avertissement(Horodatage, Base):
    """Sans effet sur la paie (décision 2)."""
    __tablename__ = "avertissement"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    type: Mapped[str] = mapped_column(String(30))  # rappel à l'ordre / avertissement / sanction
    motif: Mapped[str] = mapped_column(Text)
    origine: Mapped[str] = mapped_column(String(30))
    statut: Mapped[str] = mapped_column(String(15), default="proposé")  # proposé (par le système) / émis / annulé
    emis_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date)
    lu_par_employe: Mapped[bool] = mapped_column(Boolean, default=False)


class SoldeConge(Horodatage, Base):
    __tablename__ = "solde_conge"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    annee: Mapped[int] = mapped_column(Integer)
    jours_acquis: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    jours_pris: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    jours_perdus: Mapped[float] = mapped_column(Numeric(5, 2), default=0)


class Conge(Horodatage, Base):
    """Circuit (décision 1) : employé → responsable (avis) → RH (décision)."""
    __tablename__ = "conge"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    type_absence_id: Mapped[int] = mapped_column(ForeignKey("type_absence.id"))
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date] = mapped_column(Date)
    nb_jours: Mapped[float] = mapped_column(Numeric(5, 2))
    motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    piece_justificative: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avis_responsable: Mapped[str | None] = mapped_column(String(15), nullable=True)  # favorable / défavorable
    motif_avis: Mapped[str | None] = mapped_column(Text, nullable=True)
    avis_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    date_avis: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    avis_remonte: Mapped[bool] = mapped_column(Boolean, default=False)  # décision 39
    decision_rh: Mapped[str | None] = mapped_column(String(15), nullable=True)  # accepté / refusé
    motif_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    decide_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    date_decision: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    statut: Mapped[str] = mapped_column(String(20), default="en attente avis")  # en attente avis / en attente RH / accepté / refusé / annulé
