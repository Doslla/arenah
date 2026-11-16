import secrets
import string
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHME = "HS256"
_hash = PasswordHash.recommended()  # argon2


def hacher(mot_de_passe: str) -> str:
    return _hash.hash(mot_de_passe)


def verifier(mot_de_passe: str, mot_de_passe_hash: str) -> bool:
    try:
        return _hash.verify(mot_de_passe, mot_de_passe_hash)
    except Exception:
        return False


def creer_jeton(utilisateur_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(utilisateur_id), "exp": exp}, settings.secret_key, algorithm=ALGORITHME)


def lire_jeton(jeton: str) -> int | None:
    try:
        return int(jwt.decode(jeton, settings.secret_key, algorithms=[ALGORITHME])["sub"])
    except Exception:
        return None


def mot_de_passe_provisoire(longueur: int = 10) -> str:
    """Mot de passe provisoire (décision 34) : l'employé devra le changer à la connexion."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(longueur - 2)) + secrets.choice("@#$%") + secrets.choice(string.digits)
