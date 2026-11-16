"""6-7. Caisses (une par activité), trésorerie, dépenses et budget."""
import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Horodatage


class Caisse(Horodatage, Base):
    __tablename__ = "caisse"
    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(80), unique=True)
    unite_id: Mapped[int] = mapped_column(ForeignKey("unite.id"))
    fonds: Mapped[int] = mapped_column(BigInteger, default=0)  # fonds de caisse fixe (décision 26)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class AffectationCaisse(Horodatage, Base):
    __tablename__ = "affectation_caisse"
    id: Mapped[int] = mapped_column(primary_key=True)
    caisse_id: Mapped[int] = mapped_column(ForeignKey("caisse.id"))
    employe_id: Mapped[int] = mapped_column(ForeignKey("employe.id"))
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    est_remplacement: Mapped[bool] = mapped_column(Boolean, default=False)


class Cloture(Horodatage, Base):
    """Attendu = fonds + report + encaissements − sorties. Après clôture : écriture inverse uniquement (décision 5)."""
    __tablename__ = "cloture"
    __table_args__ = (UniqueConstraint("caisse_id", "date", name="caisse_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    caisse_id: Mapped[int] = mapped_column(ForeignKey("caisse.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    fonds: Mapped[int] = mapped_column(BigInteger)
    report: Mapped[int] = mapped_column(BigInteger, default=0)
    total_encaissements: Mapped[int] = mapped_column(BigInteger, default=0)
    total_sorties: Mapped[int] = mapped_column(BigInteger, default=0)
    montant_theorique: Mapped[int] = mapped_column(BigInteger)
    montant_compte: Mapped[int] = mapped_column(BigInteger)
    ecart: Mapped[int] = mapped_column(BigInteger)
    explication: Mapped[str | None] = mapped_column(Text, nullable=True)
    cloturee_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    statut: Mapped[str] = mapped_column(String(20), default="soumise")  # soumise / contrôlée / écart à traiter
    controlee_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    date_controle: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="saisie")


class MouvementCaisse(Horodatage, Base):
    __tablename__ = "mouvement_caisse"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    caisse_id: Mapped[int] = mapped_column(ForeignKey("caisse.id"), index=True)
    type: Mapped[str] = mapped_column(String(15))  # encaissement / sortie
    categorie_recette_id: Mapped[int | None] = mapped_column(ForeignKey("categorie_recette.id"), nullable=True)
    categorie_depense_id: Mapped[int | None] = mapped_column(ForeignKey("categorie_depense.id"), nullable=True)
    montant: Mapped[int] = mapped_column(BigInteger)
    nb_transactions: Mapped[int] = mapped_column(Integer, default=1)  # > 1 pour un total journalier importé
    mode_paiement: Mapped[str] = mapped_column(String(15), default="espèces")  # espèces ; MVola / virement prévus
    motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    numero_piece: Mapped[str | None] = mapped_column(String(40), nullable=True)
    justificatif: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_heure: Mapped[datetime] = mapped_column(DateTime, index=True)
    caissier_id: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    autorise_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    cloture_id: Mapped[int | None] = mapped_column(ForeignKey("cloture.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="saisie")
    appareil_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synchronise_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RemiseFonds(Horodatage, Base):
    """Remise hebdomadaire au comptable (décision 26)."""
    __tablename__ = "remise_fonds"
    id: Mapped[int] = mapped_column(primary_key=True)
    caisse_id: Mapped[int] = mapped_column(ForeignKey("caisse.id"))
    cloture_id: Mapped[int | None] = mapped_column(ForeignKey("cloture.id"), nullable=True)
    montant: Mapped[int] = mapped_column(BigInteger)
    remis_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    recu_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    date_heure: Mapped[datetime] = mapped_column(DateTime)
    confirmee: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(30), default="saisie")


class CompteTresorerie(Horodatage, Base):
    """Coffre, banque, MVola plus tard (décision 27)."""
    __tablename__ = "compte_tresorerie"
    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(60), unique=True)
    type: Mapped[str] = mapped_column(String(15))  # coffre / banque / mvola
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class MouvementTresorerie(Horodatage, Base):
    __tablename__ = "mouvement_tresorerie"
    id: Mapped[int] = mapped_column(primary_key=True)
    compte_id: Mapped[int] = mapped_column(ForeignKey("compte_tresorerie.id"), index=True)
    sens: Mapped[str] = mapped_column(String(10))  # entrée / sortie
    montant: Mapped[int] = mapped_column(BigInteger)
    objet: Mapped[str] = mapped_column(String(30))  # remise_caisse / depot_banque / salaire / depense / autre
    objet_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    date_heure: Mapped[datetime] = mapped_column(DateTime)
    libelle: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExerciceComptable(Horodatage, Base):
    __tablename__ = "exercice_comptable"
    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(30), unique=True)
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date] = mapped_column(Date)
    statut: Mapped[str] = mapped_column(String(10), default="ouvert")


class Budget(Horodatage, Base):
    __tablename__ = "budget"
    id: Mapped[int] = mapped_column(primary_key=True)
    exercice_id: Mapped[int] = mapped_column(ForeignKey("exercice_comptable.id"), index=True)
    unite_id: Mapped[int] = mapped_column(ForeignKey("unite.id"), index=True)
    categorie_depense_id: Mapped[int] = mapped_column(ForeignKey("categorie_depense.id"))
    mois: Mapped[int] = mapped_column(Integer)
    montant_prevu: Mapped[int] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(Integer, default=1)
    valide_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    date_validation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Depense(Horodatage, Base):
    """Circuit (décision 3) : responsable → Resp. Achats → comptable → PDG au-dessus du seuil."""
    __tablename__ = "depense"
    id: Mapped[int] = mapped_column(primary_key=True)
    unite_id: Mapped[int] = mapped_column(ForeignKey("unite.id"), index=True)
    demandeur_id: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    categorie_depense_id: Mapped[int] = mapped_column(ForeignKey("categorie_depense.id"))
    objet: Mapped[str] = mapped_column(String(200))
    date_paiement: Mapped[date | None] = mapped_column(Date, nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    montant_estime: Mapped[int] = mapped_column(BigInteger)
    montant_reel: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    devis: Mapped[str | None] = mapped_column(String(255), nullable=True)
    facture: Mapped[str | None] = mapped_column(String(255), nullable=True)
    urgence: Mapped[bool] = mapped_column(Boolean, default=False)
    origine: Mapped[str] = mapped_column(String(25), default="demande")  # demande / sortie de caisse / opération administration
    statut: Mapped[str] = mapped_column(String(25), default="brouillon")
    mode_paiement: Mapped[str | None] = mapped_column(String(15), nullable=True)
    payee_par: Mapped[int | None] = mapped_column(ForeignKey("employe.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="saisie")


class ValidationDepense(Horodatage, Base):
    __tablename__ = "validation_depense"
    id: Mapped[int] = mapped_column(primary_key=True)
    depense_id: Mapped[int] = mapped_column(ForeignKey("depense.id"), index=True)
    etape: Mapped[str] = mapped_column(String(15))  # resp_achats / comptable / pdg
    valideur_id: Mapped[int] = mapped_column(ForeignKey("employe.id"))
    decision: Mapped[str] = mapped_column(String(10))  # accepté / refusé / partiel
    montant_accepte: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    remontee: Mapped[bool] = mapped_column(Boolean, default=False)  # décision 11 / 39
