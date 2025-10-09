DROP TABLE IF EXISTS commandes_articles_historique CASCADE;
DROP TABLE IF EXISTS commandes_historique CASCADE;
DROP TABLE IF EXISTS logs_actions CASCADE;
DROP TABLE IF EXISTS stock CASCADE;
DROP TABLE IF EXISTS facture_articles CASCADE;
DROP TABLE IF EXISTS factures CASCADE;
DROP TABLE IF EXISTS proforma_versions CASCADE;
DROP TABLE IF EXISTS proforma_articles CASCADE;
DROP TABLE IF EXISTS proformas CASCADE;
DROP TABLE IF EXISTS prix_fournitures_ville CASCADE;
DROP TABLE IF EXISTS articles CASCADE;
DROP TABLE IF EXISTS client_modifications CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS utilisateurs CASCADE;
DROP TABLE IF EXISTS classes_manuels CASCADE;
DROP TABLE IF EXISTS fournisseurs CASCADE;

-- 1. Nombre de clients
SELECT COUNT(*) AS total_clients FROM clients;

-- 2. Nombre de livres
SELECT COUNT(*) AS total_livres FROM articles WHERE type_article = 'livre';

-- 3. Nombre de fournitures
SELECT COUNT(*) AS total_fournitures FROM articles WHERE type_article = 'fourniture';

-- 4. Nombre de services
SELECT COUNT(*) AS total_services FROM articles WHERE type_article = 'service';

-- 5. Nombre de formations
-- Créer la table pour les types de formations
CREATE TABLE IF NOT EXISTS types_formations (
    type_formation_id SERIAL PRIMARY KEY,
    nom_formation VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insérer les formations disponibles
INSERT INTO types_formations (nom_formation) VALUES 
('Secrétariat Bureautique'),
('Secrétariat Comptable'), 
('Marketing Digital'),
('Infographie'),
('Montage et Gestion des Projets'),
('Maintenance des Réseaux et Systèmes Informatique'),
('Maintenance Informatique')
ON CONFLICT (nom_formation) DO NOTHING;

-- Vérifier les insertions
SELECT * FROM types_formations ORDER BY nom_formation;

-- Supprimer complètement les formations de la table articles
-- (elles seront créées dynamiquement comme les services)
DELETE FROM articles WHERE type_article = 'formation';

-- Vérification
SELECT COUNT(*) as formations_restantes FROM articles WHERE type_article = 'formation';
-- Devrait retourner 0



-- 6. Nombre de prix des fournitures par ville
SELECT COUNT(*) AS total_prix_ville FROM prix_fournitures_ville;

-- 7. Nombre de villes distinctes avec des prix de fournitures
SELECT COUNT(DISTINCT ville) AS nb_villes_fournitures FROM prix_fournitures_ville;

-- 8. Répartition des villes avec nombre d’articles associés
SELECT ville, COUNT(*) AS nb_articles
FROM prix_fournitures_ville
GROUP BY ville
ORDER BY nb_articles DESC;

-- 9. Nombre total de factures
SELECT COUNT(*) AS total_factures FROM factures;

-- 10. Articles liés à des factures
SELECT COUNT(*) AS total_articles_factures FROM facture_articles;

-- 11. Aperçu des 20 premiers clients
SELECT client_id, nom, telephone, ville, adresse
FROM clients
ORDER BY nom
LIMIT 20;

-- 12. Aperçu des livres
SELECT article_id, code, designation, prix, nature, classe
FROM articles
WHERE type_article = 'livre'
ORDER BY designation
LIMIT 20;

-- 13. Aperçu des fournitures
SELECT article_id, code, designation, prix
FROM articles
WHERE type_article = 'fourniture'
ORDER BY designation
LIMIT 20;

-- 14. Prix des fournitures par ville
SELECT pfv.ville, a.designation, pfv.prix
FROM prix_fournitures_ville pfv
JOIN articles a ON a.article_id = pfv.article_id
ORDER BY ville, a.designation
LIMIT 30;

-- 15. Factures récentes avec clients (groupées par année)
SELECT 
    EXTRACT(YEAR FROM f.date_facture) AS annee,
    COUNT(*) AS nombre_factures,
    SUM(f.montant_total) AS total_ventes
FROM factures f
JOIN clients c ON c.client_id = f.client_id
GROUP BY EXTRACT(YEAR FROM f.date_facture)
ORDER BY annee DESC;

-- Factures avec clients (sans tri par date précise)
SELECT 
    f.facture_id, 
    f.code_facture, 
    f.client_id, 
    c.nom AS client_nom, 
    EXTRACT(YEAR FROM f.date_facture) AS annee_facture,
    f.montant_total
FROM factures f
JOIN clients c ON c.client_id = f.client_id
ORDER BY annee_facture DESC, f.code_facture
LIMIT 20;

-- 16. Ajouter des utilisateurs
CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO utilisateurs (nom_utilisateur, mot_de_passe, email, role, ville, actif)
VALUES ('Linda', crypt('linda', gen_salt('bf')), 'olongolinda@gmail.com', 'admin', 'Yaoundé', TRUE);

INSERT INTO utilisateurs (nom_utilisateur, mot_de_passe, email, role, ville, actif)
VALUES ('Yvana', crypt('bbsyaounde@2025', gen_salt('bf')), 'annynke519@gmail.com', 'secretaire', 'Yaoundé', TRUE);

INSERT INTO utilisateurs (nom_utilisateur, mot_de_passe, email, role, ville, actif)
VALUES ('Nelly', crypt('nelly', gen_salt('bf')), 'nelly@gmail.com', 'secretaire', 'Yaoundé', TRUE);

-- Vérification des utilisateurs
SELECT * FROM utilisateurs;

-- Suppression des utilisateurs (exemple)
DELETE FROM utilisateurs WHERE nom_utilisateur IN ('Linda');

-- 17. Ajouter le pays (Pays = Cameroun) à tous les utilisateurs ayant Yaoundé ou Douala comme ville 
UPDATE clients
SET pays = 'Cameroun'
WHERE ville IN ('Yaoundé', 'Douala', 'Nanga', 'Tonga');


-- 18. Voir les clients qui ont un pays défini
SELECT client_id, nom, ville, pays
FROM clients
WHERE pays IS NOT NULL AND pays <> '';

-- Pour avoir aussi le nombre total 
SELECT COUNT(*) AS clients_avec_pays
FROM clients
WHERE pays IS NOT NULL AND pays <> '';

-- 19. Requête SQL pour remplacer les valeurs NaN, NULL et vides par des valeurs par défaut (Page client)
UPDATE clients
SET 
    nom = CASE 
            WHEN nom IS NULL OR nom = '' OR nom = 'NaN' OR nom = '(None)' THEN '(none)' 
            ELSE nom 
          END,
    telephone = CASE 
                  WHEN telephone IS NULL OR telephone = '' OR telephone = 'NaN' OR telephone = '(None)' THEN '-' 
                  ELSE telephone 
                END,
    telephone_secondaire = CASE 
                              WHEN telephone_secondaire IS NULL OR telephone_secondaire = '' OR telephone_secondaire = 'NaN' OR telephone_secondaire = '(None)' THEN '-' 
                              ELSE telephone_secondaire 
                            END,
    adresse = CASE 
                WHEN adresse IS NULL OR adresse = '' OR adresse = 'NaN' OR adresse = '(None)' THEN 'Non renseigné' 
                ELSE adresse 
              END,
    ville = CASE 
              WHEN ville IS NULL OR ville = '' OR ville = 'NaN' OR ville = '(None)' THEN 'Non renseigné' 
              ELSE ville 
            END;

-- visualiser le nombre de champs adresse avec "(none)" comme paramètre"
SELECT COUNT(*) AS nb FROM clients WHERE adresse = '(None)';

-- changer es champs (none) en none "Non renseigné"
UPDATE clients
SET adresse = 'Non renseigné'
WHERE TRIM(LOWER(adresse)) IN ('(none)', 'none');

-- 20. -- Mise à jour pour améliorer l'historique des clients

-- 20.1. Mettre à jour les données existantes pour normaliser les téléphones
UPDATE clients 
SET telephone = REGEXP_REPLACE(REGEXP_REPLACE(telephone, '[^0-9]', '', 'g'), '^00', '', 'g')
WHERE telephone IS NOT NULL;

-- 20.2. Nettoyer les doublons potentiels de téléphone
WITH doublons AS (
    SELECT telephone, MIN(client_id) as keep_id
    FROM clients 
    WHERE telephone IS NOT NULL AND telephone != ''
    GROUP BY telephone 
    HAVING COUNT(*) > 1
)
DELETE FROM clients 
WHERE client_id NOT IN (SELECT keep_id FROM doublons)
  AND telephone IN (SELECT telephone FROM doublons);

-- 20.3 supprimer un utilisateur x
SELECT client_id, nom 
FROM clients 
WHERE LOWER(nom) = '(none)' 
ORDER BY created_at ASC 
LIMIT 2;

DELETE FROM clients 
WHERE client_id = 'CLTLGOSS';

-- 20.4 Trouver un client avec des commandes
SELECT 
    c.client_id, 
    c.nom, 
    COUNT(ch.historique_id) as nb_commandes
FROM clients c
JOIN commandes_historique ch ON ch.client_id = c.client_id
GROUP BY c.client_id, c.nom
ORDER BY nb_commandes DESC
LIMIT 5;

-- 20.5 Remplacez 'CLTYBW9T' par un vrai client_id
SELECT 
    ch.code_commande,
    ch.date_commande,
    ch.montant_total,
    ch.statut,
    cah.article_designation,
    cah.quantite,
    cah.prix_unitaire,
    cah.sous_total
FROM commandes_historique ch
LEFT JOIN commandes_articles_historique cah ON cah.historique_id = ch.historique_id
WHERE ch.client_id = 'CLTYBW9T'
ORDER BY ch.date_commande DESC, cah.article_designation;


-- 21. Mettre à jour les articles des historiques qui valent (none) en 'Non renseigné'
UPDATE commandes_articles_historique
SET article_designation = 'Non renseigné'
WHERE TRIM(LOWER(article_designation)) IN ('(none)', 'none');

-- Vérifier après mise à jour
SELECT COUNT(*) AS nb_articles_none_restants
FROM commandes_articles_historique
WHERE TRIM(LOWER(article_designation)) IN ('(none)', 'none');

-- 22.Supprimer les proformas
DELETE FROM proformas;

--23. Vérifier les proformas existantes
SELECT 
    p.proforma_id,
    p.date_creation,
    p.etat,
    p.remise,
    c.nom AS client_nom,
    c.telephone,
    c.ville,
    c.pays
FROM proformas p
JOIN clients c ON p.client_id = c.client_id
ORDER BY p.proforma_id DESC;

--- Vérifier les articles liés à une proforma spécifique (ex = 25)
SELECT 
    pa.id,
    pa.proforma_id,
    a.designation,
    a.code,
    pa.quantite,
    pa.statut_livraison
FROM proforma_articles pa
JOIN articles a ON pa.article_id = a.article_id
WHERE pa.proforma_id = 25;

--24. REQUÊTE SQL POUR AJOUTER LE "+" AUX NUMÉROS EXISTANTS
-- 24.1. FORMATER LES TÉLÉPHONES PRINCIPAUX CAMEROUNAIS
UPDATE clients 
SET telephone = '+237 ' || SUBSTRING(REGEXP_REPLACE(telephone, '\D', '', 'g'), 4)
WHERE telephone IS NOT NULL 
AND telephone != '' 
AND REGEXP_REPLACE(telephone, '\D', '', 'g') LIKE '237%'
AND LENGTH(REGEXP_REPLACE(telephone, '\D', '', 'g')) >= 11
AND telephone NOT LIKE '+237 %';  -- Éviter de reformater si déjà bon

-- 24.2. FORMATER LES TÉLÉPHONES PRINCIPAUX LOCAUX CAMEROUNAIS (8-9 chiffres)
UPDATE clients 
SET telephone = '+237 ' || REGEXP_REPLACE(telephone, '\D', '', 'g')
WHERE telephone IS NOT NULL 
AND telephone != '' 
AND LENGTH(REGEXP_REPLACE(telephone, '\D', '', 'g')) BETWEEN 8 AND 9
AND telephone NOT LIKE '+%';

-- 24.3. FORMATER LES TÉLÉPHONES SECONDAIRES CAMEROUNAIS
UPDATE clients 
SET telephone_secondaire = '+237 ' || SUBSTRING(REGEXP_REPLACE(telephone_secondaire, '\D', '', 'g'), 4)
WHERE telephone_secondaire IS NOT NULL 
AND telephone_secondaire != '' 
AND REGEXP_REPLACE(telephone_secondaire, '\D', '', 'g') LIKE '237%'
AND LENGTH(REGEXP_REPLACE(telephone_secondaire, '\D', '', 'g')) >= 11
AND telephone_secondaire NOT LIKE '+237 %';

-- 24.4. FORMATER LES TÉLÉPHONES SECONDAIRES LOCAUX CAMEROUNAIS
UPDATE clients 
SET telephone_secondaire = '+237 ' || REGEXP_REPLACE(telephone_secondaire, '\D', '', 'g')
WHERE telephone_secondaire IS NOT NULL 
AND telephone_secondaire != '' 
AND LENGTH(REGEXP_REPLACE(telephone_secondaire, '\D', '', 'g')) BETWEEN 8 AND 9
AND telephone_secondaire NOT LIKE '+%';

-- 24.5. GÉRER LES AUTRES INDICATIFS INTERNATIONAUX (non-camerounais)
UPDATE clients 
SET telephone = '+' || SUBSTRING(REGEXP_REPLACE(telephone, '\D', '', 'g'), 1, 
    CASE 
        WHEN REGEXP_REPLACE(telephone, '\D', '', 'g') LIKE '1%' THEN 1
        WHEN LENGTH(REGEXP_REPLACE(telephone, '\D', '', 'g')) = 11 THEN 2
        ELSE 3
    END) || ' ' || 
    SUBSTRING(REGEXP_REPLACE(telephone, '\D', '', 'g'), 
    CASE 
        WHEN REGEXP_REPLACE(telephone, '\D', '', 'g') LIKE '1%' THEN 2
        WHEN LENGTH(REGEXP_REPLACE(telephone, '\D', '', 'g')) = 11 THEN 3
        ELSE 4
    END)
WHERE telephone IS NOT NULL 
AND telephone != '' 
AND LENGTH(REGEXP_REPLACE(telephone, '\D', '', 'g')) >= 10
AND REGEXP_REPLACE(telephone, '\D', '', 'g') NOT LIKE '237%'
AND telephone NOT LIKE '+% %';

-- 24.6. Vérification après mise à jour
SELECT 
    COUNT(*) as total_clients,
    COUNT(CASE WHEN telephone LIKE '+%' THEN 1 END) as tel_principal_avec_plus,
    COUNT(CASE WHEN telephone_secondaire LIKE '+%' THEN 1 END) as tel_secondaire_avec_plus
FROM clients 
WHERE telephone IS NOT NULL AND telephone != '';

-- 24.7. Affichage de quelques exemples pour vérification
SELECT nom, telephone, telephone_secondaire 
FROM clients 
WHERE telephone IS NOT NULL 
LIMIT 10;


-- 25. Ajouter les colonnes manquantes à la table proforma et proforma_articles
-- Ajouter les colonnes pour la gestion des montants partiels
ALTER TABLE proformas ADD COLUMN IF NOT EXISTS montant_paye DECIMAL(10,2) DEFAULT 0;
ALTER TABLE proformas ADD COLUMN IF NOT EXISTS montant_restant DECIMAL(10,2) DEFAULT 0;

-- Ajouter une colonne pour la date de livraison partielle
ALTER TABLE proforma_articles ADD COLUMN IF NOT EXISTS date_livraison TIMESTAMP;

-- Vérifier que les colonnes ont été ajoutées
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'proformas' 
ORDER BY ordinal_position;



-- 27. Correction - Catalogue

-- 27.1 Ajout de la table pour les types de missions (tu peux insérer ça)
CREATE TABLE IF NOT EXISTS types_missions (
    id SERIAL PRIMARY KEY,
    nom_type VARCHAR(100) NOT NULL UNIQUE
);

-- 27.2 Ajout des colonnes manquantes à la table articles existante
ALTER TABLE articles ADD COLUMN IF NOT EXISTS ville_reference VARCHAR(50);
ALTER TABLE articles ADD COLUMN IF NOT EXISTS type_mission VARCHAR(100);
ALTER TABLE articles ADD COLUMN IF NOT EXISTS duree VARCHAR(50);
ALTER TABLE articles ADD COLUMN IF NOT EXISTS capacite_max INTEGER;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS description TEXT;

-- 27.3 Insertion des types de missions
INSERT INTO types_missions (nom_type) VALUES 
('Mission d''Études'), ('Mission d''Analyses'), ('Mission de Conseils'), ('Autres')
ON CONFLICT (nom_type) DO NOTHING;





-- 1. VOIR D'ABORD les articles en double
SELECT 
    designation, 
    type_article, 
    COUNT(*) as nb_occurrences,
    STRING_AGG(code, ', ') as codes
FROM articles 
WHERE designation = 'Allemand: Deutsch In Africa (ABID)'
GROUP BY designation, type_article
HAVING COUNT(*) > 1;

-- 2. SUPPRIMER les doublons (garder seulement le premier)
DELETE FROM articles 
WHERE article_id IN (
    SELECT article_id 
    FROM (
        SELECT article_id,
               ROW_NUMBER() OVER (
                   PARTITION BY designation, type_article 
                   ORDER BY article_id
               ) as rn
        FROM articles
        WHERE designation = 'Allemand: Deutsch In Africa (ABID)'
    ) t 
    WHERE t.rn > 1
);

SELECT * FROM articles
ORDER BY article_id DESC
LIMIT 10;

DELETE FROM articles
WHERE code LIKE 'ART%';

SELECT * FROM proforma_articles WHERE proforma_id = 6;

SELECT pa.*, a.prix
FROM proforma_articles pa
JOIN articles a ON a.article_id = pa.article_id
WHERE pa.proforma_id = 6;

SELECT * FROM articles WHERE article_id = 904;

SELECT * 
FROM proformas 
WHERE etat = 'termine';


-- Mise à Jour Base de Données - Livraison partielle
-- Ajouter la colonne quantite_livree qui manque
ALTER TABLE proforma_articles 
ADD COLUMN IF NOT EXISTS quantite_livree INTEGER DEFAULT 0;

-- Corriger les valeurs du statut_livraison (votre schéma a un caractère bizarre)
ALTER TABLE proforma_articles 
ALTER COLUMN statut_livraison TYPE TEXT,
ALTER COLUMN statut_livraison SET DEFAULT 'non_livré';

-- Mettre à jour les valeurs existantes si nécessaire
UPDATE proforma_articles 
SET statut_livraison = 'non_livré' 
WHERE statut_livraison IS NULL OR statut_livraison = '';

-- Recréer la contrainte avec les bonnes valeurs
ALTER TABLE proforma_articles 
DROP CONSTRAINT IF EXISTS proforma_articles_statut_livraison_check;

ALTER TABLE proforma_articles 
ADD CONSTRAINT proforma_articles_statut_livraison_check 
CHECK (statut_livraison IN ('livré', 'non_livré', 'partiel'));

-- Index pour les performances
CREATE INDEX IF NOT EXISTS idx_proforma_articles_livraison 
ON proforma_articles(proforma_id, statut_livraison);



-- Notifications (scope = 'city' ou 'global')
CREATE TABLE IF NOT EXISTS notifications (
    notif_id SERIAL PRIMARY KEY,
    scope TEXT CHECK (scope IN ('global','city')) NOT NULL,
    ville TEXT,
    actor_user_id INT NOT NULL REFERENCES utilisateurs(user_id),
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 16. Lectures de notifications (qui a lu quoi)
CREATE TABLE IF NOT EXISTS notification_reads (
    notif_id INT NOT NULL REFERENCES notifications(notif_id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES utilisateurs(user_id) ON DELETE CASCADE,
    read_at TIMESTAMP,
    PRIMARY KEY (notif_id, user_id)
);


ALTER TABLE logs_actions ADD COLUMN ville TEXT; ALTER TABLE logs_actions ADD COLUMN payload_avant JSONB; ALTER TABLE logs_actions ADD COLUMN payload_apres JSONB;



-- Mise à jour
CREATE INDEX IF NOT EXISTS idx_utilisateurs_derniere_connexion ON utilisateurs (derniere_connexion DESC);

-- Pour gérer “Fonction”, “Téléphone”, “Adresse”, “Pays” côté staff (manquants):
ALTER TABLE utilisateurs
  ADD COLUMN IF NOT EXISTS telephone TEXT,
  ADD COLUMN IF NOT EXISTS adresse   TEXT,
  ADD COLUMN IF NOT EXISTS pays      TEXT,
  ADD COLUMN IF NOT EXISTS fonction  TEXT;

-- Index éventuels (recherche rapide par nom/email/téléphone)
CREATE INDEX IF NOT EXISTS idx_utilisateurs_nom ON utilisateurs (LOWER(nom_utilisateur));
CREATE INDEX IF NOT EXISTS idx_utilisateurs_email ON utilisateurs (LOWER(email));
CREATE INDEX IF NOT EXISTS idx_utilisateurs_telephone ON utilisateurs (telephone);


-- Ajout des champs de date dans la table utilisateurs
ALTER TABLE utilisateurs 
ADD COLUMN date_entree DATE,
ADD COLUMN date_sortie DATE;

ALTER TABLE utilisateurs ALTER COLUMN mot_de_passe DROP NOT NULL;
ALTER TABLE utilisateurs ALTER COLUMN role DROP NOT NULL;


-- Ajouter la colonne agent à la table factures
ALTER TABLE factures ADD COLUMN agent TEXT;

-- MISE A JOURS DE LA COLONNE "AGENT" POUR LES ANCIENNES FACTURES
UPDATE factures SET agent = CASE WHEN ville = 'Douala' THEN 'Etienne' WHEN ville = 'Yaoundé' THEN 'Yvana' ELSE 'N/A' END WHERE ville IN ('Douala', 'Yaoundé');


-- Mettre à jour les valeurs NULL et N/A dans la table clients
UPDATE clients 
SET nom = 'Non Renseigné' 
WHERE nom IS NULL OR nom = 'N/A' OR nom = '';

UPDATE clients 
SET telephone = 'Non Renseigné' 
WHERE telephone IS NULL OR telephone = 'N/A' OR telephone = '';

UPDATE clients 
SET adresse = 'Non Renseigné' 
WHERE adresse IS NULL OR adresse = 'N/A' OR adresse = '';

-- Mettre à jour les valeurs NULL et N/A dans la table factures
UPDATE factures 
SET agent = 'Non Renseigné' 
WHERE agent IS NULL OR agent = 'N/A' OR agent = '';


ALTER TABLE proforma_articles 
ADD COLUMN prix_unitaire DECIMAL(10,2) DEFAULT 0;

-- Mettre à jour les prix existants avec les prix actuels des articles
UPDATE proforma_articles 
SET prix_unitaire = a.prix 
FROM articles a 
WHERE proforma_articles.article_id = a.article_id 
AND proforma_articles.prix_unitaire = 0;

-- MISE A JOUR PARTIEL
-- Ajouter la colonne quantite_livree à la table proforma_articles
ALTER TABLE proforma_articles 
ADD COLUMN IF NOT EXISTS quantite_livree INTEGER DEFAULT 0;

-- Ajouter la colonne date_livraison à la table proforma_articles
ALTER TABLE proforma_articles 
ADD COLUMN IF NOT EXISTS date_livraison TIMESTAMP;

-- Ajouter les colonnes nécessaires à la table facture_articles
ALTER TABLE facture_articles 
ADD COLUMN IF NOT EXISTS date_livraison TIMESTAMP;

ALTER TABLE facture_articles 
ADD COLUMN IF NOT EXISTS agent_livraison INTEGER REFERENCES utilisateurs(user_id);

-- Ajouter la colonne cree_par à la table factures si elle n'existe pas
ALTER TABLE factures 
ADD COLUMN IF NOT EXISTS cree_par INTEGER REFERENCES utilisateurs(user_id);

-- Ajouter la colonne date_modification à la table factures si elle n'existe pas
ALTER TABLE factures 
ADD COLUMN IF NOT EXISTS date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP;


-- MISE A JOUR 
ALTER TABLE proforma_articles 
DROP CONSTRAINT IF EXISTS proforma_articles_statut_livraison_check;

ALTER TABLE proforma_articles 
ADD CONSTRAINT proforma_articles_statut_livraison_check 
CHECK (statut_livraison IN ('livré', 'non_livré', 'partiellement_livré'));

-- Ajouter date_creation à la table clients
ALTER TABLE clients ADD COLUMN date_creation DATE DEFAULT CURRENT_DATE;
-- Ajouter date_creation à la table factures
ALTER TABLE factures ADD COLUMN date_creation DATE DEFAULT CURRENT_DATE;
-- Ajouter cree_par à la table factures :
ALTER TABLE factures ADD COLUMN cree_par INT REFERENCES utilisateurs(user_id);
-- Ajouter date_creation à la table factures (si vous voulez synchroniser avec date_facture) 
UPDATE factures SET date_creation = date_facture WHERE date_facture IS NOT NULL;