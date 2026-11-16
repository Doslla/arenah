# ARENAH – J2 : back-end FastAPI + base de données + branchement du front

## Contenu de l'archive
```
backend/                     → remplace entièrement votre dossier backend (votre .env est conservé)
  app/models/                → 57 tables du modèle de données v2 (organisation, RH, caisses, budget, paie, IA, audit)
  app/api/                   → routes : auth, unités, organigramme, postes, employés, affectations, délégations,
                               paramètres, calendrier, référentiels, tableau de bord
  app/services/droits.py     → droits = rôles des postes occupés + délégations, portée de l'unité (décisions 11, 40, 41)
  app/scripts/import_donnees.py → remplit la base (organigramme, paramètres, historique des caisses, dépenses, budget, présences)
  alembic/versions/          → 0001 : création des tables · 0002 : journal d'audit par trigger PostgreSQL (non modifiable)
  Dockerfile, requirements.txt, .env.example
frontend/src/...             → fichiers à ajouter / remplacer dans votre front
frontend/.env                → adresse de l'API pour Vite
docker-compose.yml           → ajoute le service backend (facultatif, profil « complet »)
```

## Installation (Windows, PowerShell)

### 0. Arrêter l'API si elle tourne (Ctrl+C dans son terminal)

### 1. Décompresser l'archive dans `I:\arenah`
Acceptez de remplacer les fichiers. Votre `backend\.env` n'est pas écrasé.
Ajoutez-y une clé plus longue (32 caractères minimum) :
```
SECRET_KEY=mettez-ici-une-longue-phrase-secrete-pour-arenah-2026
```

### 2. Placer les données
Le dossier du jeu de données doit être ici : `I:\arenah\data\dataset_ia_arenah_v1\`
(il contient `parametres\`, `00_referentiel\`, `01_encaissements\`…).

### 3. Démarrer PostgreSQL
```powershell
cd I:\arenah
docker compose up -d
```

### 4. Back-end : dépendances, tables, import
```powershell
cd I:\arenah\backend
.venv\Scripts\activate
python -m pip install -r requirements.txt
alembic upgrade head
python -m app.scripts.import_donnees --data ..\data\dataset_ia_arenah_v1
python -m uvicorn app.main:app --reload
```
Ouvrez http://localhost:8000/docs : toutes les routes sont documentées.
Bouton « Authorize » en haut à droite pour tester avec un compte.

### 5. Front-end
```powershell
cd I:\arenah\frontend
Remove-Item src\pages\Departements.jsx   # remplacée par Unités (facultatif)
npm run dev
```
Relancez `npm run dev` s'il tournait déjà (le fichier `.env` n'est lu qu'au démarrage).

### 6. Se connecter (http://localhost:5173)
| Identifiant | Mot de passe initial | Ce qu'on voit |
|---|---|---|
| `admin` | `Admin@2026` | tout (superutilisateur) |
| `narindra` | `Arenah@2026` | PDG : tout |
| `amboara` | `Arenah@2026` | Directeur + RH + Finance + Informatique : tout, salaires visibles |
| `mireille` | `Arenah@2026` | Directrice d'exploitation + Achats |
| `njaka` | `Arenah@2026` | Chef du Restaurant : uniquement son équipe et sa caisse |
| `nondy`, `nomace`, `faneva`… | `Arenah@2026` | leur unité seulement |

Le mot de passe provisoire doit être changé à la première connexion (décision 34).

### 7. Sauvegarder
```powershell
cd I:\arenah
git add .
git commit -m "J2 : back-end FastAPI, modèle de données, droits, import, front branché"
git push
```

## Problèmes fréquents
| Message | Solution |
|---|---|
| `La base contient déjà des données` | `python -m app.scripts.import_donnees --data ..\data\dataset_ia_arenah_v1 --reset` |
| `relation "..." already exists` pendant `alembic upgrade head` | La base a des tables créées à la main : `docker compose down -v` puis `docker compose up -d` (efface la base) et recommencez l'étape 4 |
| `connection refused` / `could not connect to server` | Docker Desktop n'est pas démarré, ou `docker compose up -d` n'a pas été lancé |
| Page blanche ou « Network Error » dans le front | L'API ne tourne pas sur le port 8000, ou `frontend\.env` manque |
| Erreur d'installation de `pandas` | Python 3.11 minimum : vérifiez `python --version` |

## Règles déjà en place
- Portée des droits : globale pour PDG, RH, comptable, Resp. Achats, informatique ; unité + sous-unités pour les autres.
- Salaires (table `remuneration`) : PDG, comptable, directeur ; jamais le RH (sauf s'il est aussi directeur, cas temporaire de Mr Amboara).
- Journal d'audit : chaque ajout, modification ou suppression est enregistré avec l'utilisateur ; le journal refuse toute modification.
- Jours fériés : ne peuvent pas être supprimés, seulement modifiés (décision 20).
- Paramètres : modifiables par les rôles indiqués dans `modifiable_par`, valeur contrôlée selon son type.
- Unités : désactivées, jamais supprimées (historique conservé).
