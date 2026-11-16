# Dataset IA – Restaurant ARENAH (25 mars – 20 octobre 2026) – version 4 (finale)

Sources : rapport de caisse exporté (1 810 tickets) + cahier manuscrit des achats (38 pages, transcrit à la main) + glossaire des libellés fourni par ARENAH.
Chaque ligne indique sa provenance dans `source` : reel_caisse, reel_cahier, reel_cahier_ventile, estime.

| Fichier | Grain | Usage IA |
|---|---|---|
| restaurant_journalier.csv | 1 ligne par jour (210 j) | Prévision journalière du CA |
| restaurant_hebdomadaire.csv | 1 ligne par semaine | Prévision hebdo, ratio achats / CA |
| ventes_tickets.csv | 1 ligne par ticket | Ticket moyen, heures de pointe, anomalies |
| ventes_lignes_articles.csv | 1 ligne par article vendu | Top produits, prévision par plat |
| achats.csv | 1 ligne par achat (lots éclatés) | Anomalies de prix, prévision des achats |
| achats_factures_boissons.csv | 1 ligne par article des 4 factures du fournisseur de boissons (28/04, 12/08, 16/09, 09/10) | Montants réels des boissons |
| achats_stock_reception.csv | 1 ligne par produit reçu (cahier de réception, 01/03 – 29/10) | Quantités réelles, montants estimés |
| prix_reference_stock.csv | 1 ligne par produit du cahier de réception | Prix unitaire utilisé et sa source (modifiable) |
| achats_stock_transcription_brute.csv | transcription du cahier de réception | Traçabilité |
| glossaire_produits.csv | 1 ligne par libellé du cahier | Traduction français / malgache, catégorie, prix de référence |
| achats_transcription_brute.csv | transcription du cahier | Traçabilité (annexe du mémoire) |

## Ce qui a été complété ou estimé (v2)
- Libellés : chaque achat a un nom français, un nom malgache et une catégorie (`certitude_libelle` : utilisateur, deduit, inconnu).
- « Madame » et « Mireille » = retraits d'argent de la caisse par des responsables (catégorie `retrait_caisse`, exclus des achats) : 15 000 Ar (Madame) et 1 150 000 Ar (Mireille).
- Lots à montant unique (5 lots) : éclatés en 20 lignes, montant ventilé au prorata des prix de référence (`montant_ventile_estime`).
- Quantités absentes : estimées pour 124 lignes = montant / prix de référence au kg ou au kapoaka (`quantite_estimee`).
- Prix de référence = médiane des achats où quantité et prix sont écrits ; `ecart_prix_ref` et `prix_anormal` signalent les prix hors norme.
- Lectures corrigées grâce aux totaux notés dans le cahier (`valeur_corrigee`) : gingembre 02/07 (10 000), grenadelle 06/08 (30 000), pomme de terre 06/05 (lu « Vary »), gingembre 26/06 (lu « Anamalao »), totokena 01/09 (lu « Loton-kena »), tranche fine 15/10, penne déplacé au 10/10.
- 2 lignes ajoutées (`ligne_estimee`, source `estime`) : frais 3 000 Ar le 16/05 et le 24/05, pour combler l'écart avec le total noté.
- Semaines sans cahier (avant le 12/04) : achats estimés = CA × ratio médian (0,107), colonne `achats_matiere_estimes_ar` du fichier hebdomadaire.

## Règles de nettoyage
- Jour sans ticket = fermé. Le restaurant ferme le lundi, sauf lundis fériés.
- `jour_atypique` (CA > 98e centile) et `ticket_atypique` (> Q3 + 3×IQR) : événements à traiter à part.
- `hors_restaurant` (gravillon 1 150 000 Ar, retour M. Vola 256 000 Ar) : exclu de tous les totaux.
- `reglement_fournisseur` : paiement groupé d'une semaine ; la date est celle du paiement.

## Limites
- Le cahier ne contient pas tous les achats : le ratio achats / CA (~11 %) n'est pas un vrai coût matière.
- `vacances_scolaires` est à renseigner.

## Ajouts de la version 4
- **Factures fournisseur (4)** : montants réels ; les 4 totaux recalculés tombent juste (1 598 192, 1 470 400, 504 500, 529 296 Ar).
- **Cahier de réception** : 364 lignes, quantités réelles mais aucun prix. Montant estimé = quantité × prix de référence (`prix_reference_stock.csv`).
  - Source du prix : facture fournisseur, cahier d'achats, ou prix de vente × 0,6 (marge observée sur les boissons facturées).
  - Les autres prix sont des `hypothese` (205 lignes) : à corriger dans `prix_reference_stock.csv`, puis relancer le calcul.
- **Anti-doublon** (`doublon_ou_couvert`, montant retenu = 0) :
  - Boissons reçues un jour de facture : comptées dans la facture.
  - Réception du 30/06 (canettes Gold + THB) = « Boissons 849 600 Ar » du cahier d'achats du 01/07 (montant identique).
  - Calmar, charcuterie, Danika bleu, champignon noir et œufs (23/07) déjà payés dans le cahier d'achats.
- **Tables journalière et hebdomadaire** : nouvelles colonnes `achats_factures_boissons_ar`, `achats_stock_matiere_ar`, `achats_stock_autres_ar`, `achats_matiere_total_ar`, `taux_achats_total`.
- Le tabac (cigarettes revendues) et l'entretien ne comptent pas dans `achats_matiere_total_ar`.
- Achats matière totaux ≈ 48 % du CA sur la période (contre 11 % avec le seul cahier d'achats).
- **Limite** : le cahier de réception commence le 01/03, avant les ventes exportées (25/03). Les réceptions sont des entrées en stock, pas des consommations du jour : utiliser le ratio par mois ou par semaine, pas par jour.

## Mise à jour du 03/11 (réponses de l'utilisateur)
- Toutes les ventes sont supposées payées en espèces.
- Cigarettes exclues des ventes (montants retirés des tickets ; tickets 100 % tabac supprimés : 1 804 tickets restants).
- 20/10 = dernier jour des données, mais l'export s'arrête à 12 h 27 : `jour_partiel` = True, `utilisable_entrainement` = False.
- Pauses dues aux travaux de construction : explique les fermetures hors lundi.
- Corrections confirmées : riz 02/05 1 800, viande hachée 14/05 21 000, salade 26/04 5 800, céleri 25/08 1 000, craie = tableau du restaurant.
- Traductions malgaches validées par l'utilisateur (mofo = pain, tongotr'akoho = pattes de poulet).
- Retour M. Vola : dépense complémentaire, hors coût matière.
- Les factures fournisseur sont toutes payées. Le cahier de réception couvre tout Arenah, mais il est enregistré sous le compte du Restaurant.
