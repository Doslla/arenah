# ARENAH – J3 : présences QR, congés, caisses, dépenses, budget, alertes

## Nouveautés
| Module | Règles appliquées |
|---|---|
| **Présences** (badge QR) | Le responsable scanne avec la caméra (1er passage = arrivée, 2e = départ) ; retard au-delà de la tolérance (10 min) ; saisie manuelle de secours ; badges imprimables ; absence non justifiée sous 48 h → rappel à l'ordre ou avertissement **proposé** au RH, qui décide (décisions 14, 15, 16) |
| **Congés** | Employé → avis du responsable → décision du RH ; solde (2,5 j/mois), préavis 15 j, 15 j max par prise, 2 congés annuels par an, ancienneté 12 mois ; **remontée** : le congé de Njaka va à Mireille, celui de Mr Amboara à Mme Narindra (décisions 1, 17, 39) |
| **Caisses** | Encaissements, sorties (motif + autorisation du responsable), clôture du jour avec écart calculé, remise au comptable, confirmation → coffre ; journée clôturée = plus de modification, **écriture inverse** tracée (décisions 5, 10, 26, 27) |
| **Dépenses** | Resp. Achats → comptable → PDG au-dessus de 1 000 000 Ar ; accepté / partiel / refusé avec motif ; **contrôle budgétaire avant validation** ; remontée en cas de cumul (dépense de Mireille → comptable puis PDG) ; paiement (décisions 3, 11, 22, 39) |
| **Budgets** | Synthèse par unité et catégorie (prévu, consommé, % à date, % du mois) ; saisie mois par mois par le comptable ou le PDG (décision 29) |
| **Alertes et notifications** | Budget ≥ 80 %, écart de caisse, fin de contrat / d'essai, absences ; cloche de notifications dans la barre du haut (décisions 8, 33) |

Toutes les heures sont à l'heure de Madagascar (paramètre `FUSEAU_HORAIRE`, par défaut `Indian/Antananarivo`).

## Installation (10 minutes)

### 1. Arrêter l'API et le front (Ctrl+C dans leurs terminaux)

### 2. Remplacer les dossiers
```powershell
cd I:\arenah
Rename-Item backend\app backend\app_j2        # sauvegarde
Rename-Item frontend\src frontend\src_j2      # sauvegarde
```
Décompressez l'archive dans `I:\arenah` et acceptez de remplacer les fichiers.
Vos fichiers `backend\.env` et `frontend\node_modules` sont conservés.

### 3. Back-end : migration (ajoute un paramètre, ne touche pas aux données)
```powershell
cd I:\arenah\backend
..\.venv\Scripts\activate          # ou .venv\Scripts\activate selon l'emplacement de votre venv
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

### 4. Front-end : 2 nouvelles bibliothèques (scan et badges QR)
```powershell
cd I:\arenah\frontend
npm install html5-qrcode qrcode.react
npm run dev
```

### 5. Tester (http://localhost:5173)
| Compte | À essayer |
|---|---|
| `njaka` | Caisses : encaissement, sortie, clôture (mettez un montant compté différent pour voir l'écart) · Dépenses : nouvelle demande · Présences : scanner un badge (ou coller le code d'un badge) · Congés : faire une demande et voir qu'elle part chez Mireille |
| `nirina` | Congés : demande (Maladie ou Permission) → part chez Njaka |
| `mireille` | Dépenses → « À traiter par moi » → accepter (étude Resp. Achats) · avis sur le congé de Njaka |
| `amboara` | Dépenses : validation comptable puis paiement · Congés : décision RH · Caisses : contrôler une clôture, confirmer une remise · Alertes : « Recalculer maintenant » · Présences : avertissements proposés |
| `narindra` | Validation PDG des dépenses de plus de 1 000 000 Ar et des dépenses de Mireille |

### 6. Sauvegarder
```powershell
cd I:\arenah
git add .
git commit -m "J3 : présences QR, congés, caisses, dépenses, budget, alertes"
git push
```
Une fois que tout fonctionne, supprimez `backend\app_j2` et `frontend\src_j2`.

## Bon à savoir
- **Caméra sur téléphone** : le navigateur n'autorise la caméra qu'en HTTPS (ou sur `localhost`). Sur PC, ça fonctionne directement ; pour les téléphones, ce sera réglé avec le déploiement HTTPS (J5).
- Les dépenses **importées** (historique) ne passent pas dans les circuits : seules les nouvelles demandes sont « à traiter ».
- Les 11 avertissements proposés viennent des absences de l'historique généré : le RH peut les émettre ou les annuler.
- **Point ouvert du registre** : si le PDG est lui-même demandeur d'une dépense qui exige sa validation, la plateforme refuse (règle à définir).
