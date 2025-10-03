import psycopg2
from flask import current_app
from werkzeug.security import check_password_hash
import re

def authenticate_user(Utilisateur, email, password):
    """
    Authentifie un utilisateur en vérifiant son email et mot de passe.
    Retourne (user_data, error_message)
    """
    try:
        # Validation des entrées
        if not email or not password:
            return None, "Email et mot de passe requis"
        
        # Normaliser l'email
        email = email.lower().strip()
        
        user = Utilisateur.query.filter_by(email=email, actif=True).first()

        if user:
            # Vérification avec werkzeug uniquement si mot de passe commence par "pbkdf2:sha256"
            if user.mot_de_passe.startswith("pbkdf2:sha256"):
                if check_password_hash(user.mot_de_passe, password):
                    return create_user_session_data(user), None

            # Vérification avec PostgreSQL crypt()
            try:
                conn = psycopg2.connect(current_app.config['SQLALCHEMY_DATABASE_URI'])
                cursor = conn.cursor()
                cursor.execute("SELECT crypt(%s, %s) = %s", (password, user.mot_de_passe, user.mot_de_passe))
                result = cursor.fetchone()
                
                if result and result[0]:
                    return create_user_session_data(user), None
                    
            except Exception as e:
                print(f"Erreur lors de la vérification du mot de passe avec crypt: {e}")
                return None, "Erreur lors de la vérification du mot de passe"
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()

            return None, "Email ou mot de passe incorrect"
        else:
            return None, "Email ou mot de passe incorrect"

    except Exception as e:
        print(f"Erreur lors de l'authentification: {e}")
        return None, f"Erreur lors de l'authentification: {str(e)}"

def create_user_session_data(user):
    """Créer les données de session pour un utilisateur"""
    return {
        'user_id': user.user_id,
        'nom_utilisateur': user.nom_utilisateur,
        'email': user.email,
        'role': user.role,
        'ville': user.ville,
        'actif': user.actif
    }

def get_user_info(user_id):
    """
    Récupère les informations d'un utilisateur par son ID.
    Retourne (user_data, error_message)
    """
    try:
        from app import Utilisateur

        user = Utilisateur.query.filter_by(user_id=user_id, actif=True).first()

        if user:
            return create_user_session_data(user), None
        else:
            return None, "Utilisateur non trouvé"

    except Exception as e:
        print(f"Erreur lors de la récupération des informations utilisateur: {e}")
        return None, f"Erreur DB: {str(e)}"

def validate_user_session(session_data):
    """Valider les données de session utilisateur"""
    required_fields = ['user_id', 'nom_utilisateur', 'role', 'ville']
    
    for field in required_fields:
        if field not in session_data:
            return False
    
    return True

def is_user_authorized(user_role, required_roles):
    """Vérifier si l'utilisateur a les permissions nécessaires"""
    if not isinstance(required_roles, list):
        required_roles = [required_roles]
    
    return user_role in required_roles

def clean_phone_number(phone):
    """
    Nettoyer et normaliser un numéro de téléphone internationalement
    Supporte le format international avec intl-tel-input
    """
    if not phone:
        return ""
    
    # Supprimer tous les espaces, tirets, points, parenthèses
    cleaned = re.sub(r'[\s\-\.\(\)]', '', phone)
    
    # Garder seulement les chiffres et le signe +
    cleaned = re.sub(r'[^\d+]', '', cleaned)
    
    # Si le numéro commence déjà par +, le retourner tel quel
    if cleaned.startswith('+'):
        return cleaned
    
    # Cas spécifique Cameroun (pour compatibilité)
    if cleaned.startswith('237'):
        return '+' + cleaned
    elif cleaned.startswith('6') and len(cleaned) == 9:
        return '+237' + cleaned
    
    # Pour autres pays, retourner tel quel si format correct
    return cleaned if len(cleaned) >= 7 else ""

def normalize_email(email):
    """Normaliser une adresse email"""
    if not email:
        return ""
    
    return email.lower().strip()

def validate_email(email):
    """Valider le format d'une adresse email"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None