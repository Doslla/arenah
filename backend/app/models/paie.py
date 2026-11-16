"""8-9. Paie (salaire fixe, espèces), avances, évaluations et primes."""
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Horodatage


class PeriodePaie(Horodatage, Base):
    __tablename__ = "periode_paie"
    id: Mapped[int] = mapped_column(primary_key=True)
    mois: Mapped[date] = mapped_column(Date, unique=True)  # 1er jour du mois
    statut: Mapped[str] = mapped_column(String(15), default="brouillon")  # brouillon / soumise PDG / validée / payée / clôturée
    validee_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    date_validation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VariablePaie(Horodatage, Base):
    """Saisies par le RH pour information, SANS montants (décision 2)."""
    __tablename__ = "variable_paie"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    periode_id: Mapped[int] = mapped_column(ForeignKey("periode_paie.id"), index=True)
    jours_presence: Mapped[int] = mapped_column(Integer, default=0)
    absences: Mapped[int] = mapped_column(Integer, default=0)
    retards: Mapped[int] = mapped_column(Integer, default=0)
    heures_sup: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    conges: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    avertissements: Mapped[int] = mapped_column(Integer, default=0)
    jours_preavis_non_effectues: Mapped[int] = mapped_column(Integer, default=0)


class Avance(Horodatage, Base):
    """50 % max, une seule en cours, retenue en une fois (décision 25)."""
    __tablename__ = "avance"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    montant: Mapped[int] = mapped_column(BigInteger)
    date_demande: Mapped[date] = mapped_column(Date)
    motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    statut: Mapped[str] = mapped_column(String(15), default="demandée")  # demandée / accordée / refusée / versée / retenue
    decide_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    periode_retenue_id: Mapped[int | None] = mapped_column(ForeignKey("periode_paie.id"), nullable=True)


class Bulletin(Horodatage, Base):
    __tablename__ = "bulletin"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    periode_id: Mapped[int] = mapped_column(ForeignKey("periode_paie.id"), index=True)
    salaire_fixe: Mapped[int] = mapped_column(BigInteger)
    total_cotisations: Mapped[int] = mapped_column(BigInteger, default=0)
    total_irsa: Mapped[int] = mapped_column(BigInteger, default=0)
    total_avances: Mapped[int] = mapped_column(BigInteger, default=0)
    retenue_demission: Mapped[int] = mapped_column(BigInteger, default=0)
    motif_ajustement: Mapped[str | None] = mapped_column(Text, nullable=True)
    net_a_payer: Mapped[int] = mapped_column(BigInteger)
    fichier_pdf: Mapped[str | None] = mapped_column(String(255), nullable=True)
    statut: Mapped[str] = mapped_column(String(15), default="brouillon")


class LigneBulletin(Horodatage, Base):
    __tablename__ = "ligne_bulletin"
    id: Mapped[int] = mapped_column(primary_key=True)
    bulletin_id: Mapped[int] = mapped_column(ForeignKey("bulletin.id"), index=True)
    libelle: Mapped[str] = mapped_column(String(80))
    type: Mapped[str] = mapped_column(String(15))  # gain / cotisation / irsa / avance / retenue
    base: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    taux: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    montant: Mapped[int] = mapped_column(BigInteger)


class EtatPaiement(Horodatage, Base):
    __tablename__ = "etat_paiement"
    id: Mapped[int] = mapped_column(primary_key=True)
    periode_id: Mapped[int] = mapped_column(ForeignKey("periode_paie.id"))
    fichier_pdf: Mapped[str | None] = mapped_column(String(255), nullable=True)
    genere_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PaiementSalaire(Horodatage, Base):
    __tablename__ = "paiement_salaire"
    id: Mapped[int] = mapped_column(primary_key=True)
    beneficiaire_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    objet: Mapped[str] = mapped_column(String(15))  # bulletin / prime / jour_extra / avance
    objet_id: Mapped[str] = mapped_column(String(40))
    montant: Mapped[int] = mapped_column(BigInteger)
    mode_paiement: Mapped[str] = mapped_column(String(15), default="espèces")
    date: Mapped[date] = mapped_column(Date)
    paye_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    signe_par_employe: Mapped[bool] = mapped_column(Boolean, default=False)
    etat_paiement_id: Mapped[int | None] = mapped_column(ForeignKey("etat_paiement.id"), nullable=True)


class CritereEvaluation(Horodatage, Base):
    __tablename__ = "critere_evaluation"
    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(80), unique=True)
    poids: Mapped[float] = mapped_column(Numeric(4, 2), default=1)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Evaluation(Horodatage, Base):
    __tablename__ = "evaluation"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    evaluateur_id: Mapped[int] = mapped_column(ForeignKey("employe.id"))
    periode: Mapped[date] = mapped_column(Date)
    commentaire: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[date] = mapped_column(Date)


class NoteEvaluation(Horodatage, Base):
    __tablename__ = "note_evaluation"
    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluation.id"), index=True)
    critere_id: Mapped[int] = mapped_column(ForeignKey("critere_evaluation.id"))
    note: Mapped[float] = mapped_column(Numeric(4, 2))


class Prime(Horodatage, Base):
    """Proposée par le responsable, validée par le PDG, payée à part (décision 30)."""
    __tablename__ = "prime"
    id: Mapped[int] = mapped_column(primary_key=True)
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"), index=True)
    periode: Mapped[date] = mapped_column(Date)
    montant: Mapped[int] = mapped_column(BigInteger)
    motif: Mapped[str] = mapped_column(Text)
    proposee_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    validee_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    statut: Mapped[str] = mapped_column(String(15), default="proposée")  # proposée / validée / refusée / payée
