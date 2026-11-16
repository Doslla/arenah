"""Importe tous les modèles pour qu'Alembic et SQLAlchemy les connaissent."""
from app.models.organisation import Affectation, Delegation, Employe, Poste, Role, Unite  # noqa: F401
from app.models.referentiels import (  # noqa: F401
    CategorieDepense, CategorieRecette, EvenementCalendrier, Parametre, ParametreConge,
    TauxCotisation, TrancheIrsa, TypeAbsence, TypeContrat,
)
from app.models.rh import Avertissement, Conge, Contrat, Creneau, JourExtra, Presence, Remuneration, SoldeConge  # noqa: F401
from app.models.finances import (  # noqa: F401
    AffectationCaisse, Budget, Caisse, Cloture, CompteTresorerie, Depense, ExerciceComptable,
    MouvementCaisse, MouvementTresorerie, RemiseFonds, ValidationDepense,
)
from app.models.paie import (  # noqa: F401
    Avance, Bulletin, CritereEvaluation, EtatPaiement, Evaluation, LigneBulletin, NoteEvaluation,
    PaiementSalaire, PeriodePaie, Prime, VariablePaie,
)
from app.models.systeme import (  # noqa: F401
    Alerte, AnomalieDetectee, Appareil, Correction, JournalAudit, LecturePublication, ModeleIA,
    Notification, ParametreAlerte, Prevision, Publication, Utilisateur,
)
