# Jeu de données IA – ARENAH (v1.2, 17 novembre 2026)

Construit à partir du dataset réel du Restaurant (v5 : caisse du 25/03 au 20/10/2026, cahier d'achats, factures boissons, cahier de réception) et de l'organigramme nominatif (photos du 09/10/2026).

**Règle de provenance (décision 31)** : chaque ligne porte une colonne `source`.
- `reel_caisse`, `reel_cahier`, `reel_facture`, `reel_quantite_prix_estime`… : données réelles, reprises **sans modification**.
- `synthetique` : données générées par `generer_donnees_ia.py`.
- `synthetique_sur_ca_reel` : clôtures du Restaurant calculées sur le chiffre d'affaires réel (les clôtures réelles n'existent pas).

## Paramètres modifiables (dossier `parametres/`)

Tous les réglages sont dans des fichiers CSV, ouvrables dans Excel. Modifiez-les puis relancez le script. Dans la plateforme, ils deviendront les tables `Parametre` et `JourFerie` (réglables dans l'administration, sans toucher au code).

| Fichier | Contenu |
|---|---|
| `parametres_generaux.csv` | Période, **jour de repos du personnel (lundi)**, ouverture du lundi s'il est férié, unités qui travaillent le lundi (Sécurité et entretien), jour de remise des caisses, seuil PDG, fonds du Restaurant, taux d'anomalies, graine |
| `calendrier.csv` | **Jours fériés** (14), **grandes fêtes** (fin d'année, Saint-Valentin, Pâques, Pentecôte, fête des mères, fête des pères, festivités du 26 juin, Assomption), **vacances scolaires**, fermetures générales. Colonne `fiabilite` : officiel / à confirmer / approximatif |
| `activites.csv` | Par activité : fonds de caisse, coefficient de chaque jour de la semaine, coefficients férié / grande fête / vacances, profil de saison, tendance annuelle |
| `categories_recettes.csv` | Montant moyen d'un jour normal par catégorie de recette |
| `saisons.csv` | Coefficient de chaque mois par profil (loisir, piscine, scolaire, fêtes, plate) |
| `depenses_recurrentes.csv` | Dépenses habituelles de chaque unité (montant mensuel, nombre d'achats par mois) |

Les coefficients se multiplient : un samedi de vacances pendant une grande fête cumule les trois effets (plafonné à ×4).

## Contenu

| Dossier / fichier | Contenu | Période | Provenance |
|---|---|---|---|
| `00_referentiel/unites.csv` | Arborescence direction → département / groupe → activité (27 unités), `encaisse` = caisse ouverte | – | Organigramme |
| `00_referentiel/postes.csv` | 51 postes avec rôle, responsable, vacant (« à définir ») | – | Organigramme |
| `00_referentiel/employes.csv` | 17 personnes nommées dans l'organigramme | – | Organigramme (dates d'embauche fictives) |
| `00_referentiel/affectations.csv` | 29 affectations, cumuls compris (Amboara 5, Mireille 4, Nomace 3, Nondy, Dada Jean, Faustin 2) | – | Organigramme |
| `00_referentiel/caisses.csv` | 6 caisses (décision 28) et fonds de caisse | – | Paramètres |
| `00_referentiel/calendrier.csv` | Copie du calendrier utilisé (fériés, grandes fêtes, vacances) | – | Paramètres |
| `01_encaissements/encaissements_journaliers.csv` | Montant par jour, activité et catégorie de recette ; colonnes `ferie`, `grande_fete`, `vacances_scolaires` | 01/11/2025 → 15/11/2026 | Restaurant réel (25/03 → 20/10) + synthétique |
| `02_caisses/sorties_caisse.csv` | Sorties de caisse (retraits réels du cahier + petites sorties) | idem | Réel + synthétique |
| `02_caisses/clotures.csv` | Clôture quotidienne : fonds + report + encaissements − sorties, montant compté, écart | idem | Synthétique |
| `02_caisses/remises_fonds.csv` | Remise hebdomadaire au comptable (dimanche) | idem | Synthétique |
| `03_depenses_budget/depenses.csv` | Dépenses par unité et catégorie, statut du circuit | 01/03 → 15/11/2026 (Restaurant), 01/11/2025 → 15/11/2026 (autres) | Restaurant réel + synthétique |
| `03_depenses_budget/budget_2026.csv` | Budget mensuel 2026 par unité et catégorie (`sous_dimensionne` = alertes attendues) | 2026 | Synthétique |
| `04_presences/presences.csv` | Pointage QR / manuel, retards, absences ; personne ne pointe le lundi sauf Sécurité et entretien et lundis fériés | 01/09 → 15/11/2026 | Synthétique |
| `anomalies_injectees.csv` | **Vérité terrain** : les anomalies générées (manques en caisse, encaissements sous-déclarés ou anormalement hauts, sorties sans justificatif, prix anormaux) | – | Synthétique |
| `generer_donnees_ia.py` | Script de génération (graine fixe = résultats reproductibles) | – | – |

## Règles appliquées
- **Lundi = repos du personnel** : toutes les activités sont fermées le lundi, sauf les lundis fériés (lundi de Pâques, lundi de Pentecôte), comme observé au Restaurant. Sécurité et entretien reste en poste.
- **Week-end plus fréquenté** : un jour de week-end rapporte en moyenne ×4 (Piscine), ×3 (Accueil, Restaurant réel), ×2,3 (Coiffure), ×1,5 (Cyber, Ménage et cuisine) par rapport à un jour de semaine.
- **Grandes fêtes** : environ ×3 pour la Piscine et le Restaurant, ×2,6 pour l'Accueil, ×2 pour la Coiffure ; baisse pour le Cyber.
- Fermeture générale le 1er mai ; 1,5 % de fermetures imprévues.
- Niveaux d'encaissement par activité : **hypothèses** à faire valider par les responsables.
- Restaurant après le 20/10 : médiane des 8 dernières semaines par jour de la semaine ; achats ≈ 48 % du CA (ratio observé en v4).
- Clôtures : 80 % sans écart, 18 % de petits écarts (±500 à 6 000 Ar), 2 % de manques importants (anomalies).

## Utilisation pour l'IA
1. **Prévision des encaissements** : entraîner et évaluer le Restaurant **sur les données réelles uniquement** (`utilisable_entrainement = True`, `source` commençant par `reel`). Variables : jour de la semaine, lundi de repos, férié, grande fête, vacances, mois. Les jours fermés ne sont pas des ventes nulles à prévoir : les exclure ou les traiter à part.
2. **Détection d'anomalies (Isolation Forest)** : comparer les alertes à `anomalies_injectees.csv` (précision, rappel). Ne pas utiliser `anomalie_injectee` comme variable d'entrée. Un gros montant un dimanche ou pendant une fête est normal : donner au modèle le jour de la semaine et les indicateurs de calendrier.
3. **Dépassement de budget** : projeter les dépenses cumulées du mois et comparer à `budget_2026.csv`.
4. **Indicateurs RH** (extension) : `presences.csv`.

## Limites à écrire dans le mémoire
- Seul le Restaurant a des données réelles (7 mois, sans cycle annuel complet).
- Les autres activités sont simulées : leurs résultats démontrent la méthode, pas la performance réelle.
- Les grandes fêtes et vacances scolaires sont à confirmer (colonne `fiabilite`).

## Régénérer
```
python generer_donnees_ia.py <dossier_dataset_restaurant_v5> <dossier_sortie>
```
Le dossier `parametres/` doit être à côté du script (ou indiqué par la variable d'environnement `ARENAH_PARAMS`).
