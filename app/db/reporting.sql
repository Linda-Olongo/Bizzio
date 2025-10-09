-- ========================================
-- REQUÊTES REPORTING - TOUS LES FILTRES
-- ========================================

-- ========================================
-- 1. REQUÊTES KPIs GLOBALES (SANS FILTRES)
-- ========================================

-- Chiffre d'Affaires Global (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
                (SELECT SUM(pa.quantite * a.prix) 
                FROM proforma_articles pa 
                JOIN articles a ON a.article_id = pa.article_id 
                WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Nombre de Ventes Global (Proformas + Factures)
WITH all_ventes AS (
    SELECT p.proforma_id AS id
FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    
    UNION ALL
    
    SELECT f.facture_id AS id
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
)
SELECT COUNT(DISTINCT id) AS ventes
FROM all_ventes;

-- Nombre d'Articles Vendus Global (Proformas seulement - les factures n'ont pas de détails)
SELECT COALESCE(SUM(pa.quantite), 0) AS articles
FROM proforma_articles pa
JOIN proformas p ON p.proforma_id = pa.proforma_id
WHERE p.etat IN ('termine', 'terminé', 'partiel');

-- Nombre de Nouveaux Clients Global
SELECT COUNT(DISTINCT c.client_id) AS nouveaux_clients
FROM clients c
WHERE c.created_at IS NOT NULL;

-- ========================================
-- 2. REQUÊTES AVEC FILTRE ANNÉE SEULEMENT
-- ========================================

-- Chiffre d'Affaires par Année 2022 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
                    (SELECT SUM(pa.quantite * a.prix) 
                    FROM proforma_articles pa 
                    JOIN articles a ON a.article_id = pa.article_id 
                    WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2022
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2022
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Nombre de Ventes par Année 2022 (Proformas + Factures)
WITH all_ventes AS (
    SELECT p.proforma_id AS id
FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2022
    
    UNION ALL
    
    SELECT f.facture_id AS id
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2022
)
SELECT COUNT(DISTINCT id) AS ventes
FROM all_ventes;

-- Articles Vendus par Année 2022 (Proformas seulement)
SELECT COALESCE(SUM(pa.quantite), 0) AS articles
FROM proforma_articles pa
JOIN proformas p ON p.proforma_id = pa.proforma_id
WHERE p.etat IN ('termine', 'terminé', 'partiel')
AND EXTRACT(YEAR FROM p.date_creation) = 2022;

-- Nouveaux Clients par Année 2022
SELECT COUNT(DISTINCT c.client_id) AS nouveaux_clients
FROM clients c
WHERE c.created_at IS NOT NULL
AND EXTRACT(YEAR FROM c.created_at) = 2022;

-- Chiffre d'Affaires par Année 2023 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
                    (SELECT SUM(pa.quantite * a.prix) 
                    FROM proforma_articles pa 
                    JOIN articles a ON a.article_id = pa.article_id 
                    WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2023
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2023
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Nombre de Ventes par Année 2023 (Proformas + Factures)
WITH all_ventes AS (
    SELECT p.proforma_id AS id
FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2023
    
    UNION ALL
    
    SELECT f.facture_id AS id
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2023
)
SELECT COUNT(DISTINCT id) AS ventes
FROM all_ventes;

-- Articles Vendus par Année 2023 (Proformas seulement)
SELECT COALESCE(SUM(pa.quantite), 0) AS articles
FROM proforma_articles pa
JOIN proformas p ON p.proforma_id = pa.proforma_id
WHERE p.etat IN ('termine', 'terminé', 'partiel')
AND EXTRACT(YEAR FROM p.date_creation) = 2023;

-- Nouveaux Clients par Année 2023
SELECT COUNT(DISTINCT c.client_id) AS nouveaux_clients
FROM clients c
WHERE c.created_at IS NOT NULL
AND EXTRACT(YEAR FROM c.created_at) = 2023;

-- Chiffre d'Affaires par Année 2024 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
                    (SELECT SUM(pa.quantite * a.prix) 
                    FROM proforma_articles pa 
                    JOIN articles a ON a.article_id = pa.article_id 
                    WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2024
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2024
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Nombre de Ventes par Année 2024 (Proformas + Factures)
WITH all_ventes AS (
    SELECT p.proforma_id AS id
FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2024
    
    UNION ALL
    
    SELECT f.facture_id AS id
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2024
)
SELECT COUNT(DISTINCT id) AS ventes
FROM all_ventes;

-- Articles Vendus par Année 2024 (Proformas seulement)
SELECT COALESCE(SUM(pa.quantite), 0) AS articles
FROM proforma_articles pa
JOIN proformas p ON p.proforma_id = pa.proforma_id
WHERE p.etat IN ('termine', 'terminé', 'partiel')
AND EXTRACT(YEAR FROM p.date_creation) = 2024;

-- Nouveaux Clients par Année 2024
SELECT COUNT(DISTINCT c.client_id) AS nouveaux_clients
FROM clients c
WHERE c.created_at IS NOT NULL
AND EXTRACT(YEAR FROM c.created_at) = 2024;

-- Chiffre d'Affaires par Année 2025 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Nombre de Ventes par Année 2025 (Proformas + Factures)
WITH all_ventes AS (
    SELECT p.proforma_id AS id
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    
    UNION ALL
    
    SELECT f.facture_id AS id
FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
)
SELECT COUNT(DISTINCT id) AS ventes
FROM all_ventes;

-- Articles Vendus par Année 2025 (Proformas seulement)
SELECT COALESCE(SUM(pa.quantite), 0) AS articles
FROM proforma_articles pa
JOIN proformas p ON p.proforma_id = pa.proforma_id
WHERE p.etat IN ('termine', 'terminé', 'partiel')
AND EXTRACT(YEAR FROM p.date_creation) = 2025;

-- Nouveaux Clients par Année 2025
SELECT COUNT(DISTINCT c.client_id) AS nouveaux_clients
FROM clients c
WHERE c.created_at IS NOT NULL
AND EXTRACT(YEAR FROM c.created_at) = 2025;

-- ========================================
-- 3. REQUÊTES AVEC FILTRE TRIMESTRE
-- ========================================

-- Chiffre d'Affaires par Trimestre Q1 2025 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND EXTRACT(MONTH FROM p.date_creation) IN (1, 2, 3)
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND EXTRACT(MONTH FROM f.date_facture) IN (1, 2, 3)
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Chiffre d'Affaires par Trimestre Q2 2025 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND EXTRACT(MONTH FROM p.date_creation) IN (4, 5, 6)
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND EXTRACT(MONTH FROM f.date_facture) IN (4, 5, 6)
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Chiffre d'Affaires par Trimestre Q3 2025 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND EXTRACT(MONTH FROM p.date_creation) IN (7, 8, 9)
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND EXTRACT(MONTH FROM f.date_facture) IN (7, 8, 9)
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Chiffre d'Affaires par Trimestre Q4 2025 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND EXTRACT(MONTH FROM p.date_creation) IN (10, 11, 12)
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND EXTRACT(MONTH FROM f.date_facture) IN (10, 11, 12)
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- ========================================
-- 4. REQUÊTES AVEC FILTRE MOIS
-- ========================================

-- Chiffre d'Affaires par Mois Janvier 2025 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND EXTRACT(MONTH FROM p.date_creation) = 1
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND EXTRACT(MONTH FROM f.date_facture) = 1
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Chiffre d'Affaires par Mois Février 2025 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND EXTRACT(MONTH FROM p.date_creation) = 2
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND EXTRACT(MONTH FROM f.date_facture) = 2
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Chiffre d'Affaires par Mois Mars 2025 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND EXTRACT(MONTH FROM p.date_creation) = 3
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND EXTRACT(MONTH FROM f.date_facture) = 3
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Chiffre d'Affaires par Mois Octobre 2025 (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND EXTRACT(MONTH FROM p.date_creation) = 10
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND EXTRACT(MONTH FROM f.date_facture) = 10
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- ========================================
-- 5. REQUÊTES AVEC FILTRE VILLE
-- ========================================

-- Chiffre d'Affaires par Ville Yaoundé (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND p.ville = 'Yaoundé'
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND f.ville = 'Yaoundé'
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Chiffre d'Affaires par Ville Douala (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND p.ville = 'Douala'
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND f.ville = 'Douala'
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Chiffre d'Affaires par Ville Bafoussam (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND p.ville = 'Bafoussam'
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND f.ville = 'Bafoussam'
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- ========================================
-- 8. REQUÊTES COMBINAISONS MULTIPLES
-- ========================================

-- Année 2025 + Ville Yaoundé (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND p.ville = 'Yaoundé'
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND f.ville = 'Yaoundé'
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Année 2025 + Trimestre Q4 + Ville Yaoundé (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND EXTRACT(MONTH FROM p.date_creation) IN (10, 11, 12)
    AND p.ville = 'Yaoundé'
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND EXTRACT(MONTH FROM f.date_facture) IN (10, 11, 12)
    AND f.ville = 'Yaoundé'
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- Année 2025 + Trimestre Q4 + Ville Douala (Proformas + Factures)
WITH all_ca AS (
    SELECT COALESCE(
        (SELECT SUM(pa.quantite * a.prix) 
         FROM proforma_articles pa 
         JOIN articles a ON a.article_id = pa.article_id 
         WHERE pa.proforma_id = p.proforma_id), 0
    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    AND EXTRACT(MONTH FROM p.date_creation) IN (10, 11, 12)
    AND p.ville = 'Douala'
    
    UNION ALL
    
    SELECT COALESCE(f.montant_total, 0) AS ca
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
    AND EXTRACT(MONTH FROM f.date_facture) IN (10, 11, 12)
    AND f.ville = 'Douala'
)
SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
FROM all_ca;

-- ========================================
-- 9. REQUÊTES SPARKLINES (ÉVOLUTION TEMPORELLE)
-- ========================================

-- Sparklines par Année (12 derniers mois)
WITH all_data AS (
SELECT  
        TO_CHAR(p.date_creation, 'YYYY-MM') as mois,
                COALESCE(
                    (SELECT SUM(pa.quantite * a.prix) 
                    FROM proforma_articles pa 
                    JOIN articles a ON a.article_id = pa.article_id 
                    WHERE pa.proforma_id = p.proforma_id), 0
        ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca,
        p.proforma_id AS id,
        p.client_id,
        (SELECT SUM(pa.quantite) FROM proforma_articles pa WHERE pa.proforma_id = p.proforma_id) AS articles
    FROM proformas p
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND p.date_creation >= CURRENT_DATE - INTERVAL '12 months'
    
    UNION ALL
    
    SELECT 
        TO_CHAR(f.date_facture, 'YYYY-MM') as mois,
        COALESCE(f.montant_total, 0) AS ca,
        f.facture_id AS id,
        f.client_id,
        0 AS articles
    FROM factures f
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND f.date_facture >= CURRENT_DATE - INTERVAL '12 months'
)
SELECT 
    mois,
    SUM(ca) AS chiffre_affaires,
    COUNT(DISTINCT id) AS ventes,
    COUNT(DISTINCT client_id) AS clients,
    SUM(articles) AS articles
FROM all_data
GROUP BY mois
ORDER BY mois DESC
LIMIT 12;

-- ========================================
-- 10. REQUÊTES DÉTAILS DES VENTES POUR PDF
-- ========================================

-- Détails des Ventes (Proformas)
SELECT 
    p.date_creation,
    c.nom as client_nom,
    c.telephone as client_telephone,
    p.ville,
    u.nom_utilisateur as agent_nom,
    (SELECT SUM(pa.quantite * a.prix) + COALESCE(p.frais,0) - COALESCE(p.remise,0)
     FROM proforma_articles pa
     JOIN articles a ON a.article_id = pa.article_id
     WHERE pa.proforma_id = p.proforma_id) AS montant,
    p.etat as statut,
    'proforma' as type_document,
    p.proforma_id as document_id
FROM proformas p
LEFT JOIN clients c ON c.client_id = p.client_id
LEFT JOIN utilisateurs u ON u.user_id = p.cree_par
WHERE p.etat IN ('termine','terminé','partiel')
ORDER BY p.date_creation DESC;

-- Détails des Ventes (Factures)
SELECT 
    f.date_facture as date_creation,
    c.nom as client_nom,
    c.telephone as client_telephone,
    f.ville,
    u.nom_utilisateur as agent_nom,
    (SELECT SUM(fa.quantite * fa.prix_unitaire)
     FROM facture_articles fa
     WHERE fa.facture_id = f.facture_id) AS montant,
    f.statut,
    'facture' as type_document,
    f.facture_id as document_id
FROM factures f
LEFT JOIN clients c ON c.client_id = f.client_id
LEFT JOIN utilisateurs u ON u.user_id = f.cree_par
WHERE f.statut IN ('termine','terminé','partiel')
ORDER BY f.date_facture DESC;

-- Détails des Articles pour Proforma (ID = 1)
SELECT a.designation, pa.quantite, a.prix, (pa.quantite * a.prix) as total
FROM proforma_articles pa
JOIN articles a ON a.article_id = pa.article_id
WHERE pa.proforma_id = 1
ORDER BY a.designation;

-- Détails des Articles pour Proforma (ID = 7)
SELECT a.designation, pa.quantite, a.prix, (pa.quantite * a.prix) as total
FROM proforma_articles pa
JOIN articles a ON a.article_id = pa.article_id
WHERE pa.proforma_id = 7
ORDER BY a.designation;

-- Détails des Articles pour Facture (ID = 1)
SELECT a.designation, fa.quantite, fa.prix_unitaire, (fa.quantite * fa.prix_unitaire) as total
FROM facture_articles fa
JOIN articles a ON a.article_id = fa.article_id
WHERE fa.facture_id = 1
ORDER BY a.designation;

-- ========================================
-- 11. REQUÊTES OPTIONS DE FILTRAGE
-- ========================================

-- Années disponibles
SELECT DISTINCT EXTRACT(YEAR FROM date_creation) as annee
FROM proformas
WHERE etat IN ('termine','terminé','partiel')
UNION
SELECT DISTINCT EXTRACT(YEAR FROM date_facture) as annee
FROM factures
WHERE statut IN ('termine','terminé','partiel')
ORDER BY annee DESC;

-- Villes disponibles
SELECT DISTINCT ville
FROM proformas
WHERE ville IS NOT NULL AND etat IN ('termine','terminé','partiel')
UNION
SELECT DISTINCT ville
FROM factures
WHERE ville IS NOT NULL AND statut IN ('termine','terminé','partiel')
ORDER BY ville;

-- Types de prestations disponibles
SELECT DISTINCT a.type_article
FROM articles a
JOIN proforma_articles pa ON pa.article_id = a.article_id
JOIN proformas p ON p.proforma_id = pa.proforma_id
WHERE p.etat IN ('termine','terminé','partiel')
ORDER BY a.type_article;

-- Agents disponibles
SELECT DISTINCT u.user_id, u.nom_utilisateur
FROM utilisateurs u
JOIN proformas p ON p.cree_par = u.user_id
WHERE p.etat IN ('termine','terminé','partiel')
ORDER BY u.nom_utilisateur;

-- ========================================
-- 12. REQUÊTES DONNÉES DÉTAILLÉES POUR PDF
-- ========================================

-- Ventes détaillées pour PDF - Année 2025 (Proformas + Factures)
WITH all_ventes AS (
    SELECT 
        p.date_creation,
        c.nom AS client_nom,
        COALESCE(
            (SELECT SUM(pa.quantite * a.prix) 
             FROM proforma_articles pa 
             JOIN articles a ON a.article_id = pa.article_id 
             WHERE pa.proforma_id = p.proforma_id), 0
        ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS total_ttc,
        p.proforma_id AS document_id,
        'proforma' AS type_doc
    FROM proformas p
    JOIN clients c ON c.client_id = p.client_id
    WHERE p.etat IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM p.date_creation) = 2025
    
    UNION ALL
    
    SELECT 
        f.date_facture,
        c.nom AS client_nom,
        COALESCE(f.montant_total, 0) AS total_ttc,
        f.facture_id AS document_id,
        'facture' AS type_doc
    FROM factures f
    JOIN clients c ON c.client_id = f.client_id
    WHERE f.statut IN ('termine', 'terminé', 'partiel')
    AND EXTRACT(YEAR FROM f.date_facture) = 2025
)
SELECT 
    date_creation,
    client_nom,
    total_ttc,
    document_id,
    type_doc
FROM all_ventes
ORDER BY date_creation DESC;

-- Articles détaillés pour une proforma spécifique (ID = 1)
SELECT 
    a.designation,
    pa.quantite,
    a.prix,
    (pa.quantite * a.prix) AS total
FROM proforma_articles pa
JOIN articles a ON a.article_id = pa.article_id
WHERE pa.proforma_id = 1;

-- Articles détaillés pour une facture spécifique (ID = 1)
SELECT 
    a.designation,
    fa.quantite,
    fa.prix_unitaire,
    (fa.quantite * fa.prix_unitaire) AS total
FROM facture_articles fa
JOIN articles a ON a.article_id = fa.article_id
WHERE fa.facture_id = 1;