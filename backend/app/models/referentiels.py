"""2. Référentiels et paramètres configurables (jamais de valeur chiffrée dans le code)."""
from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Horodatage


class TypeContrat(Horodatage, Base):
    __tablename__ = "type_contrat"
    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(60), unique=True)
    a_date_fin: Mapped[bool] = mapped_column(Boolean, default=False)
    preavis_jours: Mapped[int] = mapped_column(Integer, default=0)  # décision 24
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class TypeAbsence(Horodatage, Base):
    __tablename__ = "type_absence"
    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(60), unique=True)
    decompte_solde: Mapped[bool] = mapped_column(Boolean, default=False)
    justificatif_requis: Mapped[bool] = mapped_column(Boolean, default=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class CategorieRecette(Horodatage, Base):
    __tablename__ = "categorie_recette"
    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(80))
    unite_id: Mapped[int | None] = mapped_column(ForeignKey("unite.id"), nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class CategorieDepense(Horodatage, Base):
    __tablename__ = "categorie_depense"
    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(80), unique=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class TauxCotisation(Horodatage, Base):
    """CNaPS, organisme de santé… saisis par le comptable (décision 23)."""
    __tablename__ = "taux_cotisation"
    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(60))
    taux_salarial: Mapped[float] = mapped_column(Numeric(6, 3), default=0)
    taux_patronal: Mapped[float] = mapped_column(Numeric(6, 3), default=0)
    plafond: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    date_effet: Mapped[date] = mapped_column(Date)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class TrancheIrsa(Horodatage, Base):
    """Barème IRSA par tranches, désactivable (décision 23)."""
    __tablename__ = "tranche_irsa"
    id: Mapped[int] = mapped_column(primary_key=True)
    borne_min: Mapped[int] = mapped_column(BigInteger)
    borne_max: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    taux: Mapped[float] = mapped_column(Numeric(6, 3))
    date_effet: Mapped[date] = mapped_column(Date)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class ParametreConge(Horodatage, Base):
    __tablename__ = "parametre_conge"
    id: Mapped[int] = mapped_column(primary_key=True)
    jours_acquis_par_mois: Mapped[float] = mapped_column(Numeric(4, 2), default=2.5)
    anciennete_min_mois: Mapped[int] = mapped_column(Integer, default=12)
    preavis_demande_jours: Mapped[int] = mapped_column(Integer, default=15)
    plafond_par_prise: Mapped[int] = mapped_column(Integer, default=15)
    prises_annuelles_max: Mapped[int] = mapped_column(Integer, default=2)
    annees_report: Mapped[int] = mapped_column(Integer, default=0)  # décision 18
    mode_decompte: Mapped[str] = mapped_column(String(20), default="calendaire")


class EvenementCalendrier(Horodatage, Base):
    """Jours fériés, grandes fêtes, vacances scolaires, fermetures (sert aussi à l'IA)."""
    __tablename__ = "evenement_calendrier"
    id: Mapped[int] = mapped_column(primary_key=True)
    date_debut: Mapped[date] = mapped_column(Date, index=True)
    date_fin: Mapped[date] = mapped_column(Date)
    type: Mapped[str] = mapped_column(String(30))  # ferie / grande_fete / vacances_scolaires / fermeture
    libelle: Mapped[str] = mapped_column(String(120))
    fiabilite: Mapped[str] = mapped_column(String(30), default="officiel")


class Parametre(Horodatage, Base):
    """Clé / valeur : seuils, tolérances, jour de repos, devise, exercice…"""
    __tablename__ = "parametre"
    id: Mapped[int] = mapped_column(primary_key=True)
    cle: Mapped[str] = mapped_column(String(60), unique=True)
    valeur: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(10), default="texte")  # texte / entier / decimal / booleen / date
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    modifiable_par: Mapped[str] = mapped_column(String(120), default="PDG,ADMIN_INFO")
