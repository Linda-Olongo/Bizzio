from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text

db = None

def init_models(database):
    global db
    db = database

    # Créer l'extension pgcrypto si elle n'existe pas
    with database.engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
        conn.commit()

    database.create_all()
    return database

def create_models():
    global db

    class Utilisateur(db.Model):
        __tablename__ = 'utilisateurs'
        
        user_id = db.Column(db.Integer, primary_key=True)
        nom_utilisateur = db.Column(db.Text, nullable=False, unique=True)
        mot_de_passe = db.Column(db.Text, nullable=False)
        email = db.Column(db.Text, unique=True)
        role = db.Column(db.Text, nullable=False)
        ville = db.Column(db.Text, nullable=False)
        actif = db.Column(db.Boolean, default=True)
        date_creation = db.Column(db.DateTime, default=datetime.utcnow)
        derniere_connexion = db.Column(db.DateTime)
        
        # Relations
        proformas = db.relationship('Proforma', backref='utilisateur', lazy=True)
        
        def __repr__(self):
            return f'<Utilisateur {self.nom_utilisateur}>'

    class Client(db.Model):
        __tablename__ = 'clients'
        
        client_id = db.Column(db.Text, primary_key=True)
        nom = db.Column(db.Text, nullable=False)
        telephone = db.Column(db.Text)
        telephone_secondaire = db.Column(db.Text)
        adresse = db.Column(db.Text)
        ville = db.Column(db.Text)
        historique_commandes = db.Column(db.Text)
        nb_commandes = db.Column(db.Integer, default=0)
        date_creation = db.Column(db.DateTime, default=datetime.utcnow)
        dernier_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # Relations
        proformas = db.relationship('Proforma', backref='client', lazy=True)
        
        def __repr__(self):
            return f'<Client {self.nom}>'

    class Article(db.Model):
        __tablename__ = 'articles'
        
        article_id = db.Column(db.Integer, primary_key=True)
        code = db.Column(db.Text, unique=True, nullable=False)
        designation = db.Column(db.Text, nullable=False)
        prix = db.Column(db.Integer, nullable=False, default=0)
        type_article = db.Column(db.Text, nullable=False)
        nature = db.Column(db.Text)  # Pour livres (Homologué, Académique, Autres)
        classe = db.Column(db.Text)  # Pour livres
        date_creation = db.Column(db.DateTime, default=datetime.utcnow)
        actif = db.Column(db.Boolean, default=True)
        
        # Relations
        prix_villes = db.relationship('PrixFournituresVille', backref='article', lazy=True)
        classes_manuels = db.relationship('ClassesManuels', backref='article', lazy=True)
        
        def __repr__(self):
            return f'<Article {self.designation}>'

    class PrixFournituresVille(db.Model):
        __tablename__ = 'prix_fournitures_ville'
        
        id = db.Column(db.Integer, primary_key=True)
        article_id = db.Column(db.Integer, db.ForeignKey('articles.article_id'), nullable=False)
        ville = db.Column(db.Text, nullable=False)
        prix = db.Column(db.Integer, nullable=False)
        date_creation = db.Column(db.DateTime, default=datetime.utcnow)
        
        def __repr__(self):
            return f'<PrixVille {self.ville}: {self.prix}>'

    class Proforma(db.Model):
        __tablename__ = 'proformas'
        
        proforma_id = db.Column(db.Integer, primary_key=True)
        client_id = db.Column(db.Text, db.ForeignKey('clients.client_id'))
        date_creation = db.Column(db.Date, nullable=False)
        adresse_livraison = db.Column(db.Text)
        frais = db.Column(db.Integer, default=0)
        remise = db.Column(db.Integer, default=0)  # Ajout du champ remise
        etat = db.Column(db.Text, nullable=False, default='en_attente')
        commentaire = db.Column(db.Text)
        ville = db.Column(db.Text)
        cree_par = db.Column(db.Integer, db.ForeignKey('utilisateurs.user_id'))
        date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # Relations
        articles = db.relationship('ProformaArticle', backref='proforma', lazy=True, cascade='all, delete-orphan')
        versions = db.relationship('ProformaVersions', backref='proforma', lazy=True)
        
        @property
        def total_ttc(self):
            """Calculer le total TTC avec TVA 19.25%"""
            try:
                # Sous-total des articles
                sous_total = sum(pa.quantite * pa.article.prix for pa in self.articles if pa.article)
                
                # Appliquer la remise
                montant_remise = (sous_total * (self.remise or 0)) / 100
                sous_total_apres_remise = sous_total - montant_remise
                
                # Ajouter les frais
                sous_total_avec_frais = sous_total_apres_remise + (self.frais or 0)
                
                # Calculer la TVA (19.25%)
                tva = sous_total_avec_frais * 0.1925
                
                # Total TTC
                return int(sous_total_avec_frais + tva)
            except:
                return 0
        
        @property
        def sous_total(self):
            """Sous-total avant remise et frais"""
            try:
                return sum(pa.quantite * pa.article.prix for pa in self.articles if pa.article)
            except:
                return 0
        
        @property
        def montant_remise(self):
            """Montant de la remise"""
            return int((self.sous_total * (self.remise or 0)) / 100)
        
        @property
        def montant_tva(self):
            """Montant de la TVA"""
            base_tva = self.sous_total - self.montant_remise + (self.frais or 0)
            return int(base_tva * 0.1925)
        
        def __repr__(self):
            return f'<Proforma {self.proforma_id}>'

    class ProformaArticle(db.Model):
        __tablename__ = 'proforma_articles'
        
        id = db.Column(db.Integer, primary_key=True)
        proforma_id = db.Column(db.Integer, db.ForeignKey('proformas.proforma_id', ondelete="CASCADE"), nullable=False)
        article_id = db.Column(db.Integer, db.ForeignKey('articles.article_id'), nullable=False)
        quantite = db.Column(db.Integer, nullable=False)
        statut_livraison = db.Column(db.Text, default='non_livré')
        prix_unitaire = db.Column(db.Integer)  # Prix au moment de la commande
        
        # Relations
        article = db.relationship('Article', backref='proforma_articles')
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # Enregistrer le prix au moment de la création
            if self.article and not self.prix_unitaire:
                self.prix_unitaire = self.article.prix
        
        def __repr__(self):
            return f'<ProformaArticle {self.proforma_id}-{self.article_id}>'

    class Facture(db.Model):
        __tablename__ = 'factures'
        
        facture_id = db.Column(db.Integer, primary_key=True)
        code_facture = db.Column(db.Text, unique=True, nullable=False)
        client_id = db.Column(db.Text, db.ForeignKey('clients.client_id'))
        date_facture = db.Column(db.Date)
        mode_paiement = db.Column(db.Text)
        montant_total = db.Column(db.Integer, nullable=False)
        ville = db.Column(db.Text)
        cree_par = db.Column(db.Integer, db.ForeignKey('utilisateurs.user_id'))
        date_creation = db.Column(db.DateTime, default=datetime.utcnow)
        
        # Relations
        articles = db.relationship('FactureArticle', backref='facture', lazy=True, cascade='all, delete-orphan')
        
        def __repr__(self):
            return f'<Facture {self.code_facture}>'

    class FactureArticle(db.Model):
        __tablename__ = 'facture_articles'
        
        id = db.Column(db.Integer, primary_key=True)
        facture_id = db.Column(db.Integer, db.ForeignKey('factures.facture_id', ondelete="CASCADE"), nullable=False)
        article_id = db.Column(db.Integer, db.ForeignKey('articles.article_id'), nullable=False)
        quantite = db.Column(db.Integer, nullable=False)
        prix_unitaire = db.Column(db.Integer, nullable=False)
        
        # Relations
        article = db.relationship('Article', backref='facture_articles')
        
        def __repr__(self):
            return f'<FactureArticle {self.facture_id}-{self.article_id}>'

    class Stock(db.Model):
        __tablename__ = 'stock'
        
        stock_id = db.Column(db.Integer, primary_key=True)
        article_id = db.Column(db.Integer, db.ForeignKey('articles.article_id'), nullable=False)
        quantite = db.Column(db.Integer, default=0)
        emplacement = db.Column(db.Text)
        date_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # Relations
        article = db.relationship('Article', backref='stocks')
        
        def __repr__(self):
            return f'<Stock {self.article_id}: {self.quantite}>'

    class LogsActions(db.Model):
        __tablename__ = 'logs_actions'
        
        log_id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.user_id'))
        action = db.Column(db.Text)
        cible_id = db.Column(db.Text)
        cible_type = db.Column(db.Text)
        timestamp = db.Column(db.DateTime, default=datetime.utcnow)
        details = db.Column(db.JSON)  # Pour stocker des détails supplémentaires
        
        # Relations
        utilisateur = db.relationship('Utilisateur', backref='logs')
        
        def __repr__(self):
            return f'<Log {self.action} par {self.user_id}>'

    class ClientModifications(db.Model):
        __tablename__ = 'client_modifications'
        
        id = db.Column(db.Integer, primary_key=True)
        client_id = db.Column(db.Text, db.ForeignKey('clients.client_id'))
        champ_modifie = db.Column(db.Text)
        ancienne_valeur = db.Column(db.Text)
        nouvelle_valeur = db.Column(db.Text)
        modifie_par = db.Column(db.Integer, db.ForeignKey('utilisateurs.user_id'))
        date_modification = db.Column(db.DateTime, default=datetime.utcnow)
        
        # Relations
        client = db.relationship('Client', backref='modifications')
        utilisateur = db.relationship('Utilisateur', backref='modifications_clients')
        
        def __repr__(self):
            return f'<ClientModif {self.client_id}-{self.champ_modifie}>'

    class ProformaVersions(db.Model):
        __tablename__ = 'proforma_versions'
        
        version_id = db.Column(db.Integer, primary_key=True)
        proforma_id = db.Column(db.Integer, db.ForeignKey('proformas.proforma_id'))
        date_modification = db.Column(db.DateTime, default=datetime.utcnow)
        modifie_par = db.Column(db.Integer, db.ForeignKey('utilisateurs.user_id'))
        donnees_json = db.Column(db.JSON)
        commentaire_modif = db.Column(db.Text)
        
        # Relations
        utilisateur = db.relationship('Utilisateur', backref='versions_proformas')
        
        def __repr__(self):
            return f'<ProformaVersion {self.proforma_id}-{self.version_id}>'

    class ClassesManuels(db.Model):
        __tablename__ = 'classes_manuels'
        
        id = db.Column(db.Integer, primary_key=True)
        article_id = db.Column(db.Integer, db.ForeignKey('articles.article_id'))
        classe = db.Column(db.Text, nullable=False)
        date_creation = db.Column(db.DateTime, default=datetime.utcnow)
        
        def __repr__(self):
            return f'<ClasseManuel {self.classe}>'

    class Fournisseur(db.Model):
        __tablename__ = 'fournisseurs'
        
        fournisseur_id = db.Column(db.Integer, primary_key=True)
        nom = db.Column(db.Text, nullable=False)
        contact = db.Column(db.Text)
        ville = db.Column(db.Text)
        adresse = db.Column(db.Text)
        telephone = db.Column(db.Text)
        email = db.Column(db.Text)
        actif = db.Column(db.Boolean, default=True)
        date_creation = db.Column(db.DateTime, default=datetime.utcnow)
        
        def __repr__(self):
            return f'<Fournisseur {self.nom}>'

    # Retourner tous les modèles
    return {
        "Utilisateur": Utilisateur,
        "Client": Client,
        "Article": Article,
        "PrixFournituresVille": PrixFournituresVille,
        "Proforma": Proforma,
        "ProformaArticle": ProformaArticle,
        "Facture": Facture,
        "FactureArticle": FactureArticle,
        "Stock": Stock,
        "Fournisseur": Fournisseur,
        "LogsActions": LogsActions,
        "ClientModifications": ClientModifications,
        "ProformaVersions": ProformaVersions,
        "ClassesManuels": ClassesManuels
    }
