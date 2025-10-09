from flask import Flask, session, redirect, url_for, request, render_template
from config import config
import os
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_mail import Mail, Message
from jinja2 import ChoiceLoader, FileSystemLoader


# Initialisation de l'application Flask
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
print(f"Template folder: {app.template_folder}")

#  le dossier app/templates_admin à la recherche Jinja
app.jinja_loader = ChoiceLoader([
    app.jinja_loader,  # garde app/templates
    FileSystemLoader(os.path.join(app.root_path, 'app', 'templates_admin')), 
])

# Configuration basée sur l'environnement
env = os.getenv('ENV', 'production')
app.config.from_object(config[env])

# Configuration Flask-Mail (APRÈS la création de l'app)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Initialiser Flask-Mail
mail = Mail(app)

# Initialiser les dossiers nécessaires pour la production
config[env].init_app(app)

# Initialisation de SQLAlchemy
try:
    db = SQLAlchemy(app)

    with app.app_context():
        from models import init_models, create_models
        init_models(db)
        models = create_models()
        
        for model_name, model_class in models.items():
            globals()[model_name] = model_class
        
        # Création des tables seulement si nécessaire
        db.create_all()
        print("✅ Base de données initialisée avec succès")

except Exception as e:
    print(f"❌ Erreur lors de l'initialisation de SQLAlchemy : {e}")
    raise

# Initialisation de Flask-Session avec un dossier temporaire pour Render
app.config['SESSION_TYPE'] = 'filesystem'
session_dir = os.path.join(os.getcwd(), 'flask_session')
os.makedirs(session_dir, exist_ok=True)
app.config['SESSION_FILE_DIR'] = session_dir
Session(app)

# Route pour la page de chargement
@app.route('/')
def index():
    return render_template('loading.html')

# IMPORTATION DES ROUTES
import routes
routes.init_routes(app, db, models, mail)

import routes_admin
routes_admin.init_admin_routes(app, db, models, mail)

# Vérification de la connexion utilisateur
@app.before_request
def check_session():
    if request.endpoint is None:
        return
    if request.endpoint.startswith('static') or request.endpoint in ['login', 'index']:
        return
    if request.endpoint.startswith('api_'):
        return
    # Exclure les routes API admin
    if request.path.startswith('/admin/api/'):
        return
    if 'user_id' not in session:
        return redirect(url_for('login'))

# Injection de variables globales dans les templates
@app.context_processor
def inject_user():
    if 'user_id' in session:
        return {
            'current_user': {
                'user_id': session['user_id'],
                'nom_utilisateur': session['username'],
                'role': session['role'],
                'ville': session['ville'],
                'email': session.get('email'),
                'initiales': session['username'][:2].upper()
            }
        }
    return {}

# Gestionnaire d'erreurs
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html') if os.path.exists('app/templates/404.html') else "<h1>Page non trouvée</h1>", 404

@app.errorhandler(500)
def internal_error(error):
    if 'db' in globals():
        db.session.rollback()
    print(f"Erreur 500: {error}")
    return render_template('500.html') if os.path.exists('app/templates/500.html') else "<h1>Erreur serveur</h1>", 500

# Health check pour Render
@app.route('/health')
def health_check():
    try:
        # Test de connexion à la base de données
        db.session.execute('SELECT 1')
        return {'status': 'healthy', 'database': 'connected'}, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500

if __name__ == '__main__':
    # Configuration pour le développement local
    port = int(os.getenv('PORT', 5001))
    debug_mode = True  # Force le hot reload
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
else:
    # Configuration pour Render (production)
    print("🚀 Application démarrée en mode production")