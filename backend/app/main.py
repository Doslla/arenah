from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import auth, employes, organisation, parametres, tableau_de_bord
from app.core.config import settings
from app.db.session import get_db

app = FastAPI(title="ARENAH API", version="0.2.0", description="Plateforme de gestion RH, caisses, budget et IA – ARENAH")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
for module in (auth, organisation, employes, parametres, tableau_de_bord):
    api.include_router(module.router)
app.include_router(api)


@app.get("/health", tags=["Système"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}
