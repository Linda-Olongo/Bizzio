-- Table pour l'historique des chats Data Analyst
-- Permet à chaque utilisateur admin d'avoir son historique de conversations

CREATE TABLE IF NOT EXISTS data_analyst_chats (
    chat_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES utilisateurs(user_id) ON DELETE CASCADE,
    session_name TEXT DEFAULT 'Nouvelle conversation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Table pour les messages dans chaque chat
CREATE TABLE IF NOT EXISTS data_analyst_messages (
    message_id SERIAL PRIMARY KEY,
    chat_id INT NOT NULL REFERENCES data_analyst_chats(chat_id) ON DELETE CASCADE,
    user_message TEXT,
    bizzio_response TEXT,
    message_type TEXT CHECK (message_type IN ('user', 'bizzio')) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_type TEXT, -- Type d'analyse effectuée (top_articles, prestations_category, etc.)
    model_used TEXT DEFAULT 'gemini-2.0-flash'
);

-- Index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_data_analyst_chats_user ON data_analyst_chats(user_id);
CREATE INDEX IF NOT EXISTS idx_data_analyst_chats_active ON data_analyst_chats(is_active);
CREATE INDEX IF NOT EXISTS idx_data_analyst_messages_chat ON data_analyst_messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_data_analyst_messages_timestamp ON data_analyst_messages(timestamp DESC);

-- Contrainte: seuls les admins peuvent avoir des chats (via TRIGGER, car un CHECK ne peut pas contenir de sous-requête)
DROP TRIGGER IF EXISTS trg_check_admin_chat ON data_analyst_chats;
DROP FUNCTION IF EXISTS fn_check_admin_chat();

CREATE FUNCTION fn_check_admin_chat()
RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM utilisateurs u
        WHERE u.user_id = NEW.user_id AND u.role = 'admin'
    ) THEN
        RAISE EXCEPTION 'Seuls les utilisateurs admin peuvent créer des sessions de chat';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_admin_chat
BEFORE INSERT ON data_analyst_chats
FOR EACH ROW EXECUTE FUNCTION fn_check_admin_chat();

-- Fonction pour créer une nouvelle session de chat
CREATE OR REPLACE FUNCTION create_new_chat_session(p_user_id INT, p_session_name TEXT DEFAULT 'Nouvelle conversation')
RETURNS INT AS $$
DECLARE
    new_chat_id INT;
BEGIN
    -- Vérifier que l'utilisateur est admin
    IF NOT EXISTS (SELECT 1 FROM utilisateurs WHERE user_id = p_user_id AND role = 'admin') THEN
        RAISE EXCEPTION 'Seuls les utilisateurs admin peuvent créer des sessions de chat';
    END IF;
    
    -- Désactiver les autres sessions actives de cet utilisateur
    UPDATE data_analyst_chats 
    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP 
    WHERE user_id = p_user_id AND is_active = TRUE;
    
    -- Créer une nouvelle session
    INSERT INTO data_analyst_chats (user_id, session_name, is_active)
    VALUES (p_user_id, p_session_name, TRUE)
    RETURNING chat_id INTO new_chat_id;
    
    RETURN new_chat_id;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour ajouter un message
-- Règle Postgres: les paramètres avec valeurs par défaut doivent être à la fin
CREATE OR REPLACE FUNCTION add_chat_message(
    p_chat_id INT,
    p_message_type TEXT,
    p_user_message TEXT DEFAULT NULL,
    p_bizzio_response TEXT DEFAULT NULL,
    p_analysis_type TEXT DEFAULT NULL
)
RETURNS INT AS $$
DECLARE
    new_message_id INT;
BEGIN
    INSERT INTO data_analyst_messages (
        chat_id, 
        user_message, 
        bizzio_response, 
        message_type, 
        analysis_type
    )
    VALUES (
        p_chat_id,
        p_user_message,
        p_bizzio_response,
        p_message_type,
        p_analysis_type
    )
    RETURNING message_id INTO new_message_id;
    
    -- Mettre à jour la date de modification du chat
    UPDATE data_analyst_chats 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE chat_id = p_chat_id;
    
    RETURN new_message_id;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour récupérer l'historique d'un chat
CREATE OR REPLACE FUNCTION get_chat_history(p_chat_id INT)
RETURNS TABLE (
    message_id INT,
    user_message TEXT,
    bizzio_response TEXT,
    message_type TEXT,
    message_timestamp TIMESTAMP,
    analysis_type TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dam.message_id,
        dam.user_message,
        dam.bizzio_response,
        dam.message_type,
        dam.timestamp AS message_timestamp,
        dam.analysis_type
    FROM data_analyst_messages dam
    WHERE dam.chat_id = p_chat_id
    ORDER BY dam.timestamp ASC;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour récupérer les sessions d'un utilisateur
CREATE OR REPLACE FUNCTION get_user_chat_sessions(p_user_id INT)
RETURNS TABLE (
    chat_id INT,
    session_name TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    is_active BOOLEAN,
    message_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dac.chat_id,
        dac.session_name,
        dac.created_at,
        dac.updated_at,
        dac.is_active,
        COUNT(dam.message_id) as message_count
    FROM data_analyst_chats dac
    LEFT JOIN data_analyst_messages dam ON dac.chat_id = dam.chat_id
    WHERE dac.user_id = p_user_id
    GROUP BY dac.chat_id, dac.session_name, dac.created_at, dac.updated_at, dac.is_active
    ORDER BY dac.updated_at DESC;
END;
$$ LANGUAGE plpgsql;
