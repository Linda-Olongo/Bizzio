-- Réinitialisation : suppression des tables si elles existent
DROP TABLE IF EXISTS notification_reads CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
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

-- Création des tables
-- 1. Utilisateurs
CREATE TABLE IF NOT EXISTS utilisateurs (
    user_id SERIAL PRIMARY KEY,
    nom_utilisateur TEXT NOT NULL UNIQUE,
    mot_de_passe TEXT NOT NULL,
    email TEXT,
    role TEXT CHECK (role IN ('admin', 'secretaire')) NOT NULL,
    ville TEXT NOT NULL,
    actif BOOLEAN DEFAULT TRUE,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    derniere_connexion TIMESTAMP
);

-- 2. Clients
CREATE TABLE clients (
    client_id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    telephone TEXT,
    telephone_secondaire TEXT,
    adresse TEXT,
    ville TEXT,
    pays TEXT,
    nb_commandes INT DEFAULT 0,
    montant_total_paye INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Historique modifications clients
CREATE TABLE IF NOT EXISTS client_modifications (
    id SERIAL PRIMARY KEY,
    client_id TEXT REFERENCES clients(client_id),
    champ_modifie TEXT,
    ancienne_valeur TEXT,
    nouvelle_valeur TEXT,
    modifie_par INT REFERENCES utilisateurs(user_id),
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Articles (Livres, Fournitures, Services, Formations)
CREATE TABLE IF NOT EXISTS articles (
    article_id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    designation TEXT NOT NULL,
    prix INT NOT NULL DEFAULT 0,
    type_article TEXT CHECK (type_article IN ('livre', 'fourniture', 'service', 'formation')) NOT NULL,
    nature TEXT,
    classe TEXT,
    ville_reference TEXT,
    type_mission TEXT,
    duree TEXT,
    capacite_max INT,
    description TEXT,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Prix des fournitures selon la ville
CREATE TABLE IF NOT EXISTS prix_fournitures_ville (
    id SERIAL PRIMARY KEY,
    article_id INT REFERENCES articles(article_id),
    ville TEXT NOT NULL,
    prix INT NOT NULL
);

-- 6. Proformas (Devis)
CREATE TABLE proformas (
    proforma_id SERIAL PRIMARY KEY,
    client_id TEXT REFERENCES clients(client_id),
    date_creation DATE NOT NULL,
    adresse_livraison TEXT,
    frais INT DEFAULT 0,
    remise INT DEFAULT 0,
    etat TEXT CHECK (etat IN ('en_attente', 'en_cours', 'termine', 'partiel')) NOT NULL,
    commentaire TEXT,
    ville TEXT,
    cree_par INT REFERENCES utilisateurs(user_id),
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    montant_paye DECIMAL(10,2) DEFAULT 0,
    montant_restant DECIMAL(10,2) DEFAULT 0
);

-- 7. Articles dans proformas
CREATE TABLE IF NOT EXISTS proforma_articles (
    id SERIAL PRIMARY KEY,
    proforma_id INT REFERENCES proformas(proforma_id) ON DELETE CASCADE,
    article_id INT REFERENCES articles(article_id),
    quantite INT NOT NULL,
    statut_livraison TEXT CHECK (statut_livraison IN ('livré', 'non_livré')) DEFAULT 'non_livré',
    date_livraison TIMESTAMP
);

-- 8. Versions de proformas
CREATE TABLE IF NOT EXISTS proforma_versions (
    version_id SERIAL PRIMARY KEY,
    proforma_id INT REFERENCES proformas(proforma_id),
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modifie_par INT REFERENCES utilisateurs(user_id),
    donnees_json JSONB,
    commentaire_modif TEXT
);

-- 9. Historique des commandes 
CREATE TABLE commandes_historique (
    historique_id SERIAL PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    date_commande DATE NOT NULL,
    code_commande TEXT NOT NULL UNIQUE,
    montant_total INT NOT NULL DEFAULT 0,
    statut TEXT CHECK (statut IN ('termine', 'partiel')) DEFAULT 'termine',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Articles détaillés par commande
CREATE TABLE commandes_articles_historique (
    id SERIAL PRIMARY KEY,
    historique_id INT NOT NULL REFERENCES commandes_historique(historique_id) ON DELETE CASCADE,
    article_designation TEXT NOT NULL,
    article_code TEXT,
    quantite INT NOT NULL DEFAULT 1,
    prix_unitaire INT NOT NULL DEFAULT 0,
    sous_total INT GENERATED ALWAYS AS (quantite * prix_unitaire) STORED
);

-- 11. Factures
CREATE TABLE IF NOT EXISTS factures (
    facture_id SERIAL PRIMARY KEY,
    code_facture TEXT UNIQUE NOT NULL,
    client_id TEXT REFERENCES clients(client_id),
    date_facture DATE,
    mode_paiement TEXT,
    montant_total INT NOT NULL,
    ville TEXT,
    statut TEXT CHECK (statut IN ('termine', 'partiel')) DEFAULT 'termine'
);

-- 12. Articles dans factures 
CREATE TABLE IF NOT EXISTS facture_articles (
    id SERIAL PRIMARY KEY,
    facture_id INT REFERENCES factures(facture_id) ON DELETE CASCADE,
    article_id INT REFERENCES articles(article_id),
    quantite INT NOT NULL,
    prix_unitaire INT NOT NULL
);

-- 13. Stock
CREATE TABLE IF NOT EXISTS stock (
    stock_id SERIAL PRIMARY KEY,
    article_id INT REFERENCES articles(article_id),
    quantite INT DEFAULT 0,
    emplacement TEXT,
    date_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 14. Logs des actions
CREATE TABLE IF NOT EXISTS logs_actions (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES utilisateurs(user_id),
    action TEXT,
    cible_id TEXT,
    cible_type TEXT,
    ville TEXT,
    payload_avant JSONB,
    payload_apres JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Notifications (internes style Facebook)
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

-- ========================================
-- INDEX POUR OPTIMISER LES PERFORMANCES
-- ========================================

-- Index pour l'historique des commandes
CREATE INDEX idx_commandes_historique_client ON commandes_historique(client_id);
CREATE INDEX idx_commandes_historique_date ON commandes_historique(date_commande DESC);
CREATE INDEX idx_commandes_articles_historique ON commandes_articles_historique(historique_id);

-- Index pour les factures existantes
CREATE INDEX idx_factures_client ON factures(client_id);
CREATE INDEX idx_factures_date ON factures(date_facture DESC);

-- Index pour les clients
CREATE INDEX idx_clients_telephone ON clients(telephone);
CREATE INDEX idx_clients_ville ON clients(ville);

-- Index pour les notifications
CREATE INDEX IF NOT EXISTS idx_notifs_created_at ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifs_scope_ville ON notifications(scope, ville);
CREATE INDEX IF NOT EXISTS idx_notif_reads_user ON notification_reads(user_id);

-- ========================================
-- CONTRAINTES SUPPLÉMENTAIRES
-- ========================================

-- Contraintes pour l'historique
ALTER TABLE commandes_historique ADD CONSTRAINT chk_montant_positif CHECK (montant_total >= 0);
ALTER TABLE commandes_articles_historique ADD CONSTRAINT chk_quantite_positive CHECK (quantite > 0);
ALTER TABLE commandes_articles_historique ADD CONSTRAINT chk_prix_positif CHECK (prix_unitaire >= 0);