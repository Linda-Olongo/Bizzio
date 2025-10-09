# Flask core
from flask import (
    render_template, redirect, url_for, request,
    session, flash, jsonify, send_file, current_app, make_response
)

# Python standard library
import json
import re
import math
import uuid
import csv
import random
import string
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
import io
import csv

# Database & SQL
import psycopg
from psycopg import sql
from sqlalchemy import func, and_, or_, extract

# External libraries
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
import pandas as pd

from dateutil.relativedelta import relativedelta
import calendar

# PDF LIBRARIES - ESSAYER WEASYPRINT D'ABORD, PUIS PDFKIT EN FALLBACK
try:
    from weasyprint import HTML, CSS
    PDF_ENGINE = "weasyprint"
    print("WeasyPrint loaded successfully")
except ImportError:
    try:
        import pdfkit
        PDF_ENGINE = "pdfkit"
        print("PDFKit loaded as fallback")
    except ImportError:
        PDF_ENGINE = None
        print("❌ No PDF engine available. Install WeasyPrint or PDFKit")

# Local imports
from auth import authenticate_user, get_user_info

# Variables qui seront initialisées par app.py
app = None
db = None
Utilisateur = None
Proforma = None
Client = None
Article = None
ProformaArticle = None
PrixFournituresVille = None
ClassesManuels = None
Facture = None
FactureArticle = None

def init_routes(flask_app, database, models):
    """Initialiser les routes avec les objets Flask et SQLAlchemy"""
    global app, db, Utilisateur, Proforma, Client, Article, ProformaArticle
    global PrixFournituresVille, ClassesManuels, Facture, FactureArticle
    
    app = flask_app
    db = database
    Utilisateur = models.get('Utilisateur')
    Proforma = models.get('Proforma')
    Client = models.get('Client')
    Article = models.get('Article')
    ProformaArticle = models.get('ProformaArticle')
    PrixFournituresVille = models.get('PrixFournituresVille')
    ClassesManuels = models.get('ClassesManuels')
    Facture = models.get('Facture')
    FactureArticle = models.get('FactureArticle')
    
    # Ajouter le filtre tojsonfilter pour Jinja2
    @app.template_filter('tojsonfilter')
    def to_json_filter(obj):
        return json.dumps(obj)

    # === FONCTION UTILITAIRE : CONNEXION BD ===
    def get_db_connection():
        conn = psycopg.connect(current_app.config['SQLALCHEMY_DATABASE_URI'])
        return conn
    
    # === FONCTION UTILITAIRE : DASHBOARD ===
    
    # Créer ou récupérer un client depuis les données du formulaire
    def get_or_create_client_from_data(cur, client_data, clean_phone):
        # Chercher client existant par téléphone
        cur.execute("SELECT client_id FROM clients WHERE telephone = %s", [clean_phone])
        result = cur.fetchone()
        
        if result:
            return result[0]
        
        # Créer nouveau client
        client_id = str(uuid.uuid4())
        
        cur.execute("""
            INSERT INTO clients (client_id, nom, telephone, adresse, ville, pays, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, [
            client_id,
            client_data.get('nom', ''),
            clean_phone,
            client_data.get('adresse', ''),
            client_data.get('ville', ''),
            client_data.get('pays', 'Cameroun')
        ])
        
        return client_id

    # Créer ou récupérer un article depuis les données du formulaire 
    def get_or_create_article_from_form_data(cur, article_data):
        try:            
            # Vérifier les données obligatoires
            if not article_data.get('designation'):
                raise ValueError("Désignation manquante pour l'article")
            
            if not article_data.get('prix'):
                raise ValueError("Prix manquant pour l'article")
            
            # Générer un code unique
            code = generate_article_code_from_form_data(cur, article_data)
            
            # Chercher article existant par designation ET type
            cur.execute("""
                SELECT article_id FROM articles 
                WHERE LOWER(designation) = LOWER(%s) 
                AND type_article = %s
            """, [
                article_data['designation'].strip(),
                article_data.get('type', '').lower()
            ])
            
            result = cur.fetchone()
            
            if result:
                print(f"🔍 DEBUG get_or_create_article - Article existant trouvé: {result[0]}")
                return result[0]
            
            # Créer nouvel article
            cur.execute("""
                INSERT INTO articles (code, designation, prix, type_article, nature, classe)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING article_id
            """, [
                code,
                article_data['designation'].strip(),
                float(article_data.get('prix', 0)),
                article_data.get('type', 'service').lower(),
                article_data.get('nature'),
                article_data.get('classe')
            ])
            
            article_id = cur.fetchone()[0]
            return article_id
            
        except Exception as e:
            print(f"❌ Erreur dans get_or_create_article_from_form_data: {e}")
            raise e

    # Générer un code article unique depuis les données du formulaire
    def generate_article_code_from_form_data(cur, article_data):
        type_prefixes = {
            'livre': 'LIV',
            'fourniture': 'FOU',
            'service': 'SER',
            'formation': 'FOR'
        }
        
        article_type = article_data.get('type', '').lower()
        prefix = type_prefixes.get(article_type, 'ART')
        
        # Compter articles existants du même type
        cur.execute("SELECT COUNT(*) FROM articles WHERE type_article = %s", [article_type])
        count = cur.fetchone()[0]
        
        return f"{prefix}{count + 1:05d}"

    # Calculer les totaux d'une proforma depuis les données du formulaire
    def calculate_proforma_totals_from_data(articles, frais, remise_percent):
        try:
            sous_total = 0
            
            # Valider que articles est une liste
            if not isinstance(articles, list):
                raise ValueError(f"Articles doit être une liste, reçu: {type(articles)}")
            
            for i, article in enumerate(articles):
                # Valider que article est un dictionnaire
                if not isinstance(article, dict):
                    continue
                
                prix = float(article.get('prix', 0))
                quantite = int(article.get('quantite', 1))
                
                article_type = article.get('type', '').strip()
                
                if article_type.lower() == 'service':
                    jours = int(article.get('jours', 1))
                    sous_total += prix * jours
                elif article_type.lower() == 'formation':
                    heures = int(article.get('heures', 1))
                    sous_total += prix * heures
                else:
                    sous_total += prix * quantite
            
            # Convertir frais en float
            if isinstance(frais, list):
                frais_total = sum(float(f.get('amount', 0)) for f in frais if isinstance(f, dict))
            else:
                frais_total = float(frais) if frais else 0
            
            # Convertir remise en float
            remise_percent = float(remise_percent) if remise_percent else 0
            
            # Calculer remise
            montant_remise = (sous_total * remise_percent) / 100
            
            # TVA fixée à 0
            tva = 0
            
            # Total TTC
            total_ttc = sous_total - montant_remise + frais_total + tva
            
            return {
                'sous_total': float(sous_total),
                'remise': float(montant_remise),
                'frais': float(frais_total),
                'tva': float(tva),
                'total_ttc': float(total_ttc)
            }
            
        except Exception as e:
            print(f"❌ Erreur dans calculate_proforma_totals_from_data: {e}")
            raise e

    def get_allowed_documents_by_status(status):
        """Retourne les documents autorisés selon le statut de la proforma"""
        allowed_documents = {
            'en_attente': ['proforma'],
            'en_cours': ['proforma', 'facture', 'bon'],
            'partiel': ['proforma', 'facture', 'bon'],
            'termine': []  # ✅ AUCUN DOCUMENT POUR TERMINÉ
        }
        
        return allowed_documents.get(status, ['proforma'])

    # Retourner un message explicatif pour chaque statut
    def get_status_download_message(etat):
        """Retourner un message explicatif pour chaque statut"""
        messages = {
            'en_attente': "Document de devis disponible",
            'en_cours': "Tous les documents disponibles",
            'partiel': "Facture et bon de livraison partiels disponibles",
            'termine': "Commande terminée - Aucun document à envoyer au client"  
        }
        return messages.get(etat, "Documents disponibles selon le statut")


    # Récupérer toutes les données d'une proforma pour génération PD
    def get_proforma_complete_data(proforma_id, ville, user_id):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Récupérer proforma + client
            cur.execute("""
                SELECT 
                    p.proforma_id, p.date_creation, p.adresse_livraison, 
                    p.frais, p.remise, p.etat, p.commentaire,
                    c.nom, c.telephone, c.adresse, c.ville, c.pays
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                WHERE p.proforma_id = %s AND p.ville = %s AND p.cree_par = %s
            """, [proforma_id, ville, user_id])
            
            proforma_data = cur.fetchone()
            if not proforma_data:
                return None
                
            # Récupérer articles
            cur.execute("""
                SELECT 
                    a.code, a.designation, a.prix, a.type_article,
                    pa.quantite, COALESCE(pa.statut_livraison, 'non_livré') as statut_livraison
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                WHERE pa.proforma_id = %s
                ORDER BY a.type_article, a.designation
            """, [proforma_id])
            
            articles_data = cur.fetchall()
            
            cur.close()
            conn.close()
            
            return {
                'proforma': proforma_data,
                'articles': articles_data
            }
            
        except Exception as e:
            print(f"❌ Erreur get_proforma_complete_data: {e}")
            return None
        
    # Alternative avec pdfkit si WeasyPrint pose problème
    def generate_pdf_with_pdfkit(html_content, filename):
        try:
            import pdfkit
            
            options = {
                'page-size': 'A4',
                'margin-top': '1.5cm',
                'margin-right': '1.5cm',
                'margin-bottom': '1.5cm',
                'margin-left': '1.5cm',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None
            }
            
            pdf_content = pdfkit.from_string(html_content, False, options=options)
            
            response = make_response(pdf_content)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            print(f"❌ Erreur pdfkit: {e}")
            raise e

    # Convertir un nombre en lettres en français - Version complète comme dans le JavaScript
    def convert_number_to_words(num):
        if num == 0 or num is None:
            return "zéro franc CFA"
        
        # Conversion en entier
        try:
            num = int(float(num))
        except (ValueError, TypeError):
            return "montant invalide"
        
        if num == 0:
            return "zéro franc CFA"
        
        ones = ['', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix', 
                'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf']
        tens = ['', '', 'vingt', 'trente', 'quarante', 'cinquante', 'soixante', 'soixante-dix', 'quatre-vingt', 'quatre-vingt-dix']
        
        def convert_chunk(n):
            result = ''
            
            if n >= 100:
                hundreds = n // 100
                if hundreds == 1:
                    result += 'cent '
                else:
                    result += ones[hundreds] + ' cent '
                n %= 100
            
            if n >= 20:
                tens_digit = n // 10
                result += tens[tens_digit]
                n %= 10
                if n > 0:
                    result += '-' + ones[n]
            elif n > 0:
                result += ones[n]
            
            return result.strip()
        
        integer_part = num
        
        if integer_part == 0:
            return "zéro franc CFA"
        
        result = ''
        
        if integer_part >= 1000000:
            millions = integer_part // 1000000
            result += convert_chunk(millions) + ' million' + ('s' if millions > 1 else '') + ' '
        
        remainder = integer_part % 1000000
        if remainder >= 1000:
            thousands = remainder // 1000
            if thousands == 1:
                result += 'mille '
            else:
                result += convert_chunk(thousands) + ' mille '
        
        last_three = remainder % 1000
        if last_three > 0:
            result += convert_chunk(last_three)
        
        return result.strip() + ' franc' + ('s' if integer_part > 1 else '') + ' CFA'
    
    # Générer PDF proforma
    def generate_proforma_pdf(data):
        try:
            html_content = render_template('proforma_template.html', **data)
            pdf = HTML(string=html_content).write_pdf()
            return pdf
        except Exception as e:
            print(f"Erreur generate_proforma_pdf: {e}")
            raise e

    # Générer PDF facture
    def generate_facture_pdf(data):
        try:
            # Utiliser le même template pour l'instant
            html_content = render_template('proforma_template.html', **data)
            pdf = HTML(string=html_content).write_pdf()
            return pdf
        except Exception as e:
            print(f"Erreur generate_facture_pdf: {e}")
            raise e

    # Générer PDF bon de livraison
    def generate_bon_livraison_pdf(data):
        try:
            # Utiliser le même template pour l'instant
            html_content = render_template('proforma_template.html', **data)
            pdf = HTML(string=html_content).write_pdf()
            return pdf
        except Exception as e:
            print(f"Erreur generate_bon_livraison_pdf: {e}")
            raise e
    
    # === FONCTION UTILITAIRE : CATALOGUE ===
    # Calculer les KPIs pour le catalogue
    def get_catalogue_kpi_data():
        try:
            ville = session.get('ville')
            user_id = session.get('user_id')
            
            print(f"DEBUG CA - Session: ville={ville}, user_id={user_id}")
            
            if not ville or not user_id:
                print(f"ERREUR - Session incomplète")
                return {
                    "total_articles": 0,
                    "articles_populaires": "Aucun",
                    "ca_catalogue": 0,
                    "prestations_actives": "Aucune"
                }
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Période mois actuel
            mois_actuel_debut = datetime.now().replace(day=1).date()
            mois_actuel_fin = datetime.now().date()
            
            print(f"DEBUG CA - Période: {mois_actuel_debut} à {mois_actuel_fin}")
            
            # ✅ CORRECTION : Total Articles du CATALOGUE uniquement (pas les articles générés par proformas)
            # Exclure les articles avec codes commençant par "ART" (générés automatiquement)
            cur.execute("""
                SELECT COUNT(*) 
                FROM articles 
                WHERE code NOT LIKE 'ART%' 
                OR code IS NULL
            """)
            total_articles = cur.fetchone()[0] or 0
            print(f"DEBUG CA - Total articles CATALOGUE: {total_articles}")
            
            # 2. Article le plus populaire (mois actuel) - INCHANGÉ
            cur.execute("""
                SELECT a.designation
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                JOIN proformas p ON p.proforma_id = pa.proforma_id
                WHERE p.date_creation >= %s AND p.date_creation <= %s
                AND p.etat = 'termine'
                AND p.ville = %s AND p.cree_par = %s
                GROUP BY pa.article_id, a.designation
                ORDER BY SUM(pa.quantite) DESC
                LIMIT 1
            """, [mois_actuel_debut, mois_actuel_fin, ville, user_id])
            
            result = cur.fetchone()
            articles_populaires = result[0] if result else "Aucun"
            print(f"DEBUG CA - Article populaire: {articles_populaires}")
            
            # 3. CA Catalogue - INCHANGÉ
            print(f"DEBUG CA - Calcul CA pour ville={ville}, user_id={user_id}")
            
            # Étape 1: Compter les proformas éligibles
            cur.execute("""
                SELECT COUNT(*)
                FROM proformas p
                WHERE p.date_creation >= %s AND p.date_creation <= %s
                AND p.etat = 'termine'
                AND p.ville = %s AND p.cree_par = %s
            """, [mois_actuel_debut, mois_actuel_fin, ville, user_id])
            
            nb_proformas = cur.fetchone()[0]
            print(f"DEBUG CA - Proformas terminées trouvées: {nb_proformas}")
            
            # Étape 2: Calculer CA avec détail par proforma
            cur.execute("""
                SELECT 
                    p.proforma_id,
                    p.date_creation,
                    COALESCE(SUM(pa.quantite * a.prix), 0) as sous_total_articles,
                    COALESCE(p.frais, 0) as frais,
                    COALESCE(p.remise, 0) as remise,
                    (COALESCE(SUM(pa.quantite * a.prix), 0) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)) as total_proforma
                FROM proformas p
                LEFT JOIN proforma_articles pa ON pa.proforma_id = p.proforma_id
                LEFT JOIN articles a ON a.article_id = pa.article_id
                WHERE p.date_creation >= %s AND p.date_creation <= %s
                AND p.etat = 'termine'
                AND p.ville = %s AND p.cree_par = %s
                GROUP BY p.proforma_id, p.date_creation, p.frais, p.remise
                ORDER BY p.date_creation DESC
            """, [mois_actuel_debut, mois_actuel_fin, ville, user_id])
            
            proformas_detail = cur.fetchall()
            ca_catalogue = 0
            
            print(f"DEBUG CA - Détail par proforma:")
            for p in proformas_detail:
                proforma_id, date_creation, sous_total, frais, remise, total = p
                ca_catalogue += total
                print(f"  PRO{proforma_id:05d} ({date_creation}): {sous_total} + {frais} - {remise} = {total} FCFA")
            
            print(f"DEBUG CA - CA total calculé: {ca_catalogue} FCFA")
            
            # 4. Prestation la plus active - INCHANGÉ
            cur.execute("""
                SELECT a.type_article
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                JOIN proformas p ON p.proforma_id = pa.proforma_id
                WHERE p.date_creation >= %s AND p.date_creation <= %s
                AND p.etat = 'termine'
                AND p.ville = %s AND p.cree_par = %s
                GROUP BY a.type_article
                ORDER BY SUM(pa.quantite) DESC
                LIMIT 1
            """, [mois_actuel_debut, mois_actuel_fin, ville, user_id])
            
            result = cur.fetchone()
            if result:
                type_article = result[0]
                prestations_actives = type_article.title() + 's' if type_article and not type_article.endswith('s') else (type_article.title() if type_article else "Aucune")
            else:
                prestations_actives = "Aucune"
            
            print(f"DEBUG CA - Prestation active: {prestations_actives}")
            
            cur.close()
            conn.close()
            
            result = {
                "total_articles": total_articles,
                "articles_populaires": articles_populaires,
                "ca_catalogue": ca_catalogue,
                "prestations_actives": prestations_actives
            }
            
            print(f"DEBUG CA - Résultat final: {result}")
            return result
            
        except Exception as e:
            print(f"ERREUR GLOBALE get_catalogue_kpi_data: {e}")
            import traceback
            traceback.print_exc()
            return {
                "total_articles": 0,
                "articles_populaires": "Aucun",
                "ca_catalogue": 0,
                "prestations_actives": "Aucune"
            }

    # Calculer les tendances des KPIs catalogue vs mois précédent
    def calculate_catalogue_kpi_trends():
        try:
            ville = session.get('ville')
            user_id = session.get('user_id')
            
            if not ville or not user_id:
                return {"total_articles": 0, "articles_populaires": 0, "ca_catalogue": 0, "prestations_actives": 0}
            
            # KPIs mois actuel
            current_kpis = get_catalogue_kpi_data()
            
            # Périodes
            mois_actuel_debut = datetime.now().replace(day=1).date()
            mois_actuel_fin = datetime.now().date()
            prev_month_start = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1)
            prev_month_end = datetime.now().replace(day=1) - timedelta(days=1)
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 1. TREND ARTICLE POPULAIRE : Compare la fréquence de l'article actuel
            current_article = current_kpis['articles_populaires']
            current_article_frequency = 0
            prev_article_frequency = 0
            
            if current_article != "Aucun":
                # Fréquence actuelle de cet article
                cur.execute("""
                    SELECT COALESCE(SUM(pa.quantite), 0)
                    FROM proforma_articles pa
                    JOIN articles a ON a.article_id = pa.article_id
                    JOIN proformas p ON p.proforma_id = pa.proforma_id
                    WHERE p.date_creation >= %s AND p.date_creation <= %s
                    AND p.etat = 'termine' AND p.ville = %s AND p.cree_par = %s
                    AND LOWER(a.designation) = LOWER(%s)
                """, [mois_actuel_debut, mois_actuel_fin, ville, user_id, current_article])
                current_article_frequency = cur.fetchone()[0] or 0
                
                # Fréquence du même article le mois précédent
                cur.execute("""
                    SELECT COALESCE(SUM(pa.quantite), 0)
                    FROM proforma_articles pa
                    JOIN articles a ON a.article_id = pa.article_id
                    JOIN proformas p ON p.proforma_id = pa.proforma_id
                    WHERE p.date_creation >= %s AND p.date_creation <= %s
                    AND p.etat = 'termine' AND p.ville = %s AND p.cree_par = %s
                    AND LOWER(a.designation) = LOWER(%s)
                """, [prev_month_start, prev_month_end, ville, user_id, current_article])
                prev_article_frequency = cur.fetchone()[0] or 0
            
            # 2. TREND CATÉGORIE ACTIVE : Compare la fréquence de la catégorie actuelle
            current_categorie = current_kpis['prestations_actives']
            current_categorie_frequency = 0
            prev_categorie_frequency = 0
            
            if current_categorie != "Aucune":
                # Extraire le type depuis la catégorie (enlever le 's' final)
                type_article = current_categorie.lower().rstrip('s')
                
                # Fréquence actuelle de cette catégorie
                cur.execute("""
                    SELECT COALESCE(SUM(pa.quantite), 0)
                    FROM proforma_articles pa
                    JOIN articles a ON a.article_id = pa.article_id
                    JOIN proformas p ON p.proforma_id = pa.proforma_id
                    WHERE p.date_creation >= %s AND p.date_creation <= %s
                    AND p.etat = 'termine' AND p.ville = %s AND p.cree_par = %s
                    AND a.type_article = %s
                """, [mois_actuel_debut, mois_actuel_fin, ville, user_id, type_article])
                current_categorie_frequency = cur.fetchone()[0] or 0
                
                # Fréquence de la même catégorie le mois précédent
                cur.execute("""
                    SELECT COALESCE(SUM(pa.quantite), 0)
                    FROM proforma_articles pa
                    JOIN articles a ON a.article_id = pa.article_id
                    JOIN proformas p ON p.proforma_id = pa.proforma_id
                    WHERE p.date_creation >= %s AND p.date_creation <= %s
                    AND p.etat = 'termine' AND p.ville = %s AND p.cree_par = %s
                    AND a.type_article = %s
                """, [prev_month_start, prev_month_end, ville, user_id, type_article])
                prev_categorie_frequency = cur.fetchone()[0] or 0
            
            # 3. CA CATALOGUE (déjà numérique)
            prev_ca_catalogue = 0
            try:
                cur.execute("""
                    SELECT COALESCE(SUM(
                        (SELECT COALESCE(SUM(pa.quantite * a.prix), 0) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id)
                        + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                    ), 0)
                    FROM proformas p
                    WHERE p.date_creation >= %s AND p.date_creation <= %s
                    AND p.etat = 'termine' AND p.ville = %s AND p.cree_par = %s
                """, [prev_month_start, prev_month_end, ville, user_id])
                prev_ca_catalogue = cur.fetchone()[0] or 0
            except Exception as e:
                print(f"Erreur calcul CA précédent: {e}")
            
            cur.close()
            conn.close()
            
            # Fonction de calcul de trend sécurisée
            def calculate_trend(current, previous):
                if current == 0:
                    return 0
                elif previous == 0 and current > 0:
                    return 100
                else:
                    return round(((current - previous) / previous) * 100, 1)
            
            return {
                "total_articles": 0,  # Pas de trend pour le total
                "articles_populaires": calculate_trend(current_article_frequency, prev_article_frequency),
                "ca_catalogue": calculate_trend(current_kpis['ca_catalogue'], prev_ca_catalogue),
                "prestations_actives": calculate_trend(current_categorie_frequency, prev_categorie_frequency)
            }
            
        except Exception as e:
            print(f"Erreur calculate_catalogue_kpi_trends: {e}")
            import traceback
            traceback.print_exc()
            return {"total_articles": 0, "articles_populaires": 0, "ca_catalogue": 0, "prestations_actives": 0}
    
    def clean_phone_number_for_storage(phone: str) -> str:
        """Nettoyer un numéro de téléphone pour stockage en base (format avec espace pour affichage cohérent)"""
        if not phone:
            return ""
        
        # Convertir en string et supprimer les espaces en trop
        phone_str = str(phone).strip()
        
        # Si le numéro commence déjà par +
        if phone_str.startswith('+'):
            # Extraire seulement les chiffres après le +
            digits = re.sub(r'[^\d]', '', phone_str[1:])
            
            if len(digits) >= 10:
                # UTILISER PHONENUMBERS POUR DÉTECTER LE PAYS ET FORMATER AVEC ESPACE
                try:
                    import phonenumbers
                    full_number = '+' + digits
                    parsed = phonenumbers.parse(full_number, None)
                    if phonenumbers.is_valid_number(parsed):
                        # RETOURNER FORMAT AVEC ESPACE POUR COHÉRENCE D'AFFICHAGE
                        country_code = str(parsed.country_code)
                        national_number = str(parsed.national_number)
                        return f"+{country_code} {national_number}"
                except:
                    pass
                    
                # Fallback manuel si phonenumbers échoue - AVEC ESPACE
                if digits.startswith('237') and len(digits) >= 11:
                    return f"+237 {digits[3:]}"
                elif len(digits) >= 10:
                    # Code pays à 1-3 chiffres avec espace
                    if digits.startswith('1') and len(digits) == 11:
                        return f"+1 {digits[1:]}"
                    elif len(digits) >= 11:
                        return f"+{digits[:3]} {digits[3:]}"
                    else:
                        return f"+{digits[:2]} {digits[2:]}"
            
            return ""  # Format invalide
        
        # Supprimer tout sauf chiffres pour traitement
        cleaned = re.sub(r'\D', '', phone_str)
        
        # Supprimer 00 s'il existe au début
        if cleaned.startswith('00'):
            cleaned = cleaned[2:]
        
        # Logique intelligente basée sur la longueur - AVEC ESPACE
        if 8 <= len(cleaned) <= 9:
            # Numéro local camerounais avec espace
            return f"+237 {cleaned}"
        elif len(cleaned) >= 11 and cleaned.startswith('237'):
            return f"+237 {cleaned[3:]}"
        elif len(cleaned) >= 10:
            # Autres pays - détecter l'indicatif avec espace
            if cleaned.startswith('1') and len(cleaned) == 11:
                return f"+1 {cleaned[1:]}"
            elif len(cleaned) >= 11:
                return f"+{cleaned[:3]} {cleaned[3:]}"
            else:
                return f"+{cleaned[:2]} {cleaned[2:]}"
        
        return ""  # Numéro invalide

    def clean_phone_number_for_display(phone: str) -> str:
        """Nettoyer un numéro de téléphone pour affichage (format avec espaces)"""
        # Utiliser la fonction existante clean_phone_number_simple pour l'affichage
        return clean_phone_number_simple(phone)

    # Récupérer les années disponibles dynamiquement depuis les proformas et factures
    def get_available_years():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Récupérer les années depuis proformas ET factures
            cur.execute("""
                SELECT DISTINCT EXTRACT(YEAR FROM date_creation) as year 
                FROM proformas 
                WHERE date_creation IS NOT NULL
                UNION
                SELECT DISTINCT EXTRACT(YEAR FROM date_facture) as year 
                FROM factures 
                WHERE date_facture IS NOT NULL
                ORDER BY year DESC
            """)
            
            years = [int(row[0]) for row in cur.fetchall()]
            
            # Ajouter l'année actuelle si pas présente
            current_year = datetime.now().year
            if current_year not in years:
                years.insert(0, current_year)
            
            cur.close()
            conn.close()
            return years
            
        except Exception as e:
            print(f"Erreur get_available_years: {e}")
            return [datetime.now().year]

    
    # Calculer les tendances des KPIs vs mois précédent
    def calculate_kpi_trends(ville, user_id):
        try:
            # Mois actuel
            current_kpis = get_kpi_data(ville, user_id)
            
            # Mois précédent
            prev_month_start = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1)
            prev_month_end = datetime.now().replace(day=1) - timedelta(days=1)
            
            prev_kpis = get_kpi_data(ville, user_id, prev_month_start, prev_month_end)
            
            # Calculer les pourcentages
            def calculate_trend(current, previous):
                if current == 0:
                    return 0  # ✅ Si valeur actuelle = 0, toujours afficher 0%
                elif previous == 0 and current > 0:
                    return 100  # Nouvelle apparition
                else:
                    return round(((current - previous) / previous) * 100, 1)
            
            return {
                "chiffre_affaires": calculate_trend(current_kpis['chiffre_affaires'], prev_kpis['chiffre_affaires']),
                "factures": calculate_trend(current_kpis['factures'], prev_kpis['factures']),
                "devis": calculate_trend(current_kpis['devis'], prev_kpis['devis']),
                "a_traiter": calculate_trend(current_kpis['a_traiter'], prev_kpis['a_traiter'])
            }
            
        except Exception as e:
            print(f"Erreur calculate_kpi_trends: {e}")
            return {"chiffre_affaires": 0, "factures": 0, "devis": 0, "a_traiter": 0}
   
    # Fonction de calcul des indicateurs de performance (KPI) par ville et utilisateur sur une période donnée
    def get_kpi_data(ville, user_id, date_debut=None, date_fin=None):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Dates par défaut 
            if not date_debut:
                date_debut = datetime.now().replace(day=1).date()
            if not date_fin:
                date_fin = datetime.now().date()
            
            print(f"🔍 DEBUG KPI - Ville: {ville}, User: {user_id}")
            print(f"🔍 DEBUG KPI - Période: {date_debut} à {date_fin}")
            
            # Chiffre d'affaires (SEULEMENT les proformas terminées)
            cur.execute("""
                SELECT COALESCE(SUM(
                    (SELECT COALESCE(SUM(pa.quantite * a.prix), 0) 
                    FROM proforma_articles pa 
                    JOIN articles a ON a.article_id = pa.article_id 
                    WHERE pa.proforma_id = p.proforma_id)
                    + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                ), 0)
                FROM proformas p
                WHERE p.ville = %s AND p.cree_par = %s 
                AND p.etat = 'termine'
                AND p.date_creation >= %s AND p.date_creation <= %s
            """, [ville, user_id, date_debut, date_fin])
            chiffre_affaires = cur.fetchone()[0] or 0
            
            # Factures (nombre de proformas terminées du mois) 
            cur.execute("""
                SELECT COUNT(*)
                FROM proformas p
                WHERE p.ville = %s AND p.cree_par = %s 
                AND p.etat = 'termine'
                AND p.date_creation >= %s AND p.date_creation <= %s
            """, [ville, user_id, date_debut, date_fin])
            factures = cur.fetchone()[0] or 0
            
            # ✅ CORRECTION: Devis = SEULEMENT les proformas NON terminées (en_attente, en_cours, partiel)
            cur.execute("""
                SELECT COALESCE(SUM(
                    (SELECT COALESCE(SUM(pa.quantite * a.prix), 0) 
                    FROM proforma_articles pa 
                    JOIN articles a ON a.article_id = pa.article_id 
                    WHERE pa.proforma_id = p.proforma_id)
                    + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                ), 0)
                FROM proformas p
                WHERE p.ville = %s AND p.cree_par = %s
                AND p.etat IN ('en_attente', 'en_cours', 'partiel')
                AND p.date_creation >= %s AND p.date_creation <= %s
            """, [ville, user_id, date_debut, date_fin])
            devis = cur.fetchone()[0] or 0
            
            # À traiter (nombre de proformas en_attente + en_cours + partiel du mois)
            cur.execute("""
                SELECT COUNT(*)
                FROM proformas p
                WHERE p.ville = %s AND p.cree_par = %s 
                AND p.etat IN ('en_attente', 'en_cours', 'partiel')
                AND p.date_creation >= %s AND p.date_creation <= %s
            """, [ville, user_id, date_debut, date_fin])
            a_traiter = cur.fetchone()[0] or 0
            
            print(f"🔍 DEBUG KPI - Résultats:")
            print(f"  - CA (terminées): {chiffre_affaires}")
            print(f"  - Factures (nb terminées): {factures}")
            print(f"  - Devis (en cours uniquement): {devis}")
            print(f"  - A traiter: {a_traiter}")
            
            cur.close()
            conn.close()
            
            return {
                "chiffre_affaires": chiffre_affaires,
                "factures": factures,
                "devis": devis,
                "a_traiter": a_traiter
            }
            
        except Exception as e:
            print(f"❌ Erreur get_kpi_data: {e}")
            return {
                "chiffre_affaires": 0,
                "factures": 0,
                "devis": 0,
                "a_traiter": 0
            }

    # Récupérer les proformas formatées pour l'affichage
    def get_proformas_by_user_formatted(ville, user_id):
        """
        Récupère et formate les proformas pour l'affichage, avec validation stricte des statuts.
        Évite les modifications automatiques non désirées et conserve les statuts existants.
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Vérification de la structure de la colonne 'etat' (pour débogage)
            cur.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'proformas' AND column_name = 'etat'
            """)
            column_info = cur.fetchone()
            if column_info:
                print(f"🔍 DEBUG COLONNE - etat: {column_info}")
            
            # Requête pour récupérer les proformas
            cur.execute("""
                SELECT 
                    p.proforma_id,
                    p.date_creation,
                    COALESCE(c.nom, 'Client supprimé') as client_nom,
                    p.etat,
                    COALESCE(u.nom_utilisateur, 'Utilisateur supprimé') as created_by,
                    COALESCE(
                        (SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id), 0
                    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) as total_ttc,
                    COALESCE(p.montant_paye, 0) as montant_paye,
                    COALESCE(p.montant_restant, 0) as montant_restant
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                LEFT JOIN utilisateurs u ON u.user_id = p.cree_par
                WHERE p.ville = %s AND p.cree_par = %s
                ORDER BY p.date_creation DESC, p.proforma_id DESC
                LIMIT 100
            """, [ville, user_id])
            
            proformas = cur.fetchall()
            formatted_proformas = []
            
            print(f"🔍 DEBUG RÉCUPÉRATION - {len(proformas)} proformas trouvées")
            
            valid_statuses = ['en_attente', 'en_cours', 'partiel', 'termine']
            
            for p in proformas:
                proforma_id, date_creation, client_nom, etat_brut, created_by, total_ttc, montant_paye, montant_restant = p
                
                print(f"🔍 DEBUG Proforma {proforma_id}:")
                print(f"   - Statut brut: '{etat_brut}' (type: {type(etat_brut)})")
                print(f"   - Is None?: {etat_brut is None}")
                print(f"   - Is empty?: '{etat_brut}' == ''")
                
                # Validation du statut sans modification automatique en base
                if etat_brut is None or etat_brut == '' or str(etat_brut).strip() == '':
                    print(f"   ⚠️ STATUT NULL/VIDE détecté pour proforma {proforma_id}")
                    etat_final = 'en_attente'  # Valeur par défaut pour l'affichage uniquement
                elif etat_brut.strip() not in valid_statuses:
                    print(f"   ⚠️ STATUT INVALIDE '{etat_brut}' pour proforma {proforma_id}")
                    etat_final = 'en_attente'  # Valeur par défaut pour l'affichage uniquement
                else:
                    etat_final = str(etat_brut).strip()
                
                print(f"   → STATUT FINAL: '{etat_final}'")
                
                formatted_proforma = {
                    'proforma_id': proforma_id,
                    'numero': f"PRO{proforma_id:05d}",
                    'date_creation': date_creation.strftime('%d %b %Y') if date_creation else "Date inconnue",
                    'client_nom': client_nom,
                    'total_ttc': float(total_ttc) if total_ttc else 0.0,
                    'montant_paye': float(montant_paye) if montant_paye else 0.0,
                    'montant_restant': float(montant_restant) if montant_restant else float(total_ttc) - float(montant_paye or 0),
                    'etat': etat_final,  # Utiliser le statut validé
                    'created_by': created_by
                }
                
                formatted_proformas.append(formatted_proforma)
            
            cur.close()
            conn.close()
            
            print(f"✅ RÉCUPÉRATION TERMINÉE - {len(formatted_proformas)} proformas formatées")
            return formatted_proformas
            
        except Exception as e:
            print(f"❌ ERREUR CRITIQUE get_proformas_by_user_formatted: {e}")
            import traceback
            traceback.print_exc()
            return []

    # Calculer le montant payé selon l'état de la proforma
    def calculate_montant_paye_from_etat(etat, total_ttc):
        if etat == 'termine':
            return total_ttc
        elif etat == 'partiel':
            return total_ttc // 2  # 50% par défaut
        else:
            return 0

    # Récupérer les classes disponibles pour les livres
    def get_classes_livres():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT DISTINCT classe 
                FROM articles 
                WHERE type_article = 'livre' 
                AND classe IS NOT NULL 
                ORDER BY classe
            """)
            
            classes = [row[0] for row in cur.fetchall() if row[0]]
            
            cur.close()
            conn.close()
            return classes
            
        except Exception as e:
            print(f"Erreur get_classes_livres: {e}")
            return []

    # Récupérer toutes les formations disponibles
    def get_formations_disponibles():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT article_id, code, designation, prix 
                FROM articles 
                WHERE type_article = 'formation'
                ORDER BY designation
            """)
            
            formations = []
            for row in cur.fetchall():
                formations.append({
                    'article_id': row[0],
                    'code': row[1],
                    'designation': row[2],
                    'prix': row[3]
                })
            
            cur.close()
            conn.close()
            return formations
            
        except Exception as e:
            print(f"Erreur get_formations_disponibles: {e}")
            return []

    # Récupérer les villes disponibles pour les fournitures
    def get_villes_fournitures():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT DISTINCT ville 
                FROM prix_fournitures_ville 
                WHERE ville IS NOT NULL 
                ORDER BY ville
            """)
            villes = [row[0] for row in cur.fetchall() if row[0]]
            
            cur.close()
            conn.close()
            return villes
            
        except Exception as e:
            print(f"Erreur get_villes_fournitures: {e}")
            return []

    # Récupérer les natures disponibles pour les livres
    def get_natures_disponibles():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT DISTINCT nature 
                FROM articles 
                WHERE type_article = 'livre' 
                AND nature IS NOT NULL 
                ORDER BY nature
            """)
            
            natures = [row[0] for row in cur.fetchall() if row[0]]
            
            cur.close()
            conn.close()
            return natures
            
        except Exception as e:
            print(f"Erreur get_natures_disponibles: {e}")
            return []

    # Formater un montant en FCFA
    def format_currency(amount):
        if amount == 0 or amount is None:
            return "0 FCFA"
        # Formatage avec séparateur de milliers (espace)
        formatted = f"{int(float(amount)):,}".replace(',', ' ')
        return formatted + " FCFA"

    def format_number(number):
        if number == 0:
            return "0"
        # Formatage cohérent avec séparateur de milliers (espace)
        return f"{int(number):,}".replace(',', ' ')

    
    # === FONCTION UTILITAIRE : REPERTOIRE ===
    def clean_phone_number_simple(phone: str) -> str:
        """Nettoyer un numéro de téléphone et retourner format international avec + et séparateur"""
        if not phone:
            return ""
        
        # Convertir en string et supprimer les espaces en trop
        phone_str = str(phone).strip()
        
        # Si le numéro commence déjà par +, le nettoyer et formater
        if phone_str.startswith('+'):
            # Extraire seulement les chiffres après le +
            digits = re.sub(r'[^\d]', '', phone_str[1:])
            
            if len(digits) >= 10:
                # Utiliser phonenumbers pour détecter automatiquement le format correct
                try:
                    import phonenumbers
                    # Reconstruire le numéro avec +
                    full_number = '+' + digits
                    parsed = phonenumbers.parse(full_number, None)
                    if phonenumbers.is_valid_number(parsed):
                        # Formater selon les standards internationaux
                        country_code = str(parsed.country_code)
                        national_number = str(parsed.national_number)
                        return f"+{country_code} {national_number}"
                except:
                    pass
                
                # Fallback si phonenumbers échoue : format manuel intelligent
                # Détecter le code pays selon la longueur totale
                if len(digits) == 10:  # Code pays à 1 chiffre
                    return f"+{digits[0]} {digits[1:]}"
                elif len(digits) == 11:  # Code pays à 1 ou 2 chiffres
                    if digits[0] == '1':  # USA/Canada
                        return f"+1 {digits[1:]}"
                    else:  # Code pays à 2 chiffres
                        return f"+{digits[:2]} {digits[2:]}"
                elif len(digits) == 12:  # Code pays à 2 ou 3 chiffres
                    return f"+{digits[:3]} {digits[3:]}"
                else:  # Code pays à 3 chiffres par défaut
                    return f"+{digits[:3]} {digits[3:]}"
            
            return ""  # Format invalide
        
        # Supprimer tout sauf chiffres pour traitement
        cleaned = re.sub(r'\D', '', phone_str)
        
        # Supprimer 00 s'il existe au début
        if cleaned.startswith('00'):
            cleaned = cleaned[2:]
        
        if len(cleaned) >= 10:
            # Utiliser phonenumbers pour détecter automatiquement le pays
            try:
                import phonenumbers
                
                # Essayer de parser comme numéro camerounais d'abord (contexte de l'app)
                if 8 <= len(cleaned) <= 9:
                    full_number = '+237' + cleaned
                    parsed = phonenumbers.parse(full_number, None)
                    if phonenumbers.is_valid_number(parsed):
                        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                
                # Essayer de parser avec le code pays déjà inclus
                if len(cleaned) >= 10:
                    full_number = '+' + cleaned
                    parsed = phonenumbers.parse(full_number, None)
                    if phonenumbers.is_valid_number(parsed):
                        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                        
            except:
                pass
            
            # Fallback manuel si phonenumbers n'est pas disponible
            # Logique intelligente basée sur la longueur
            if 8 <= len(cleaned) <= 9:
                # Numéro local camerounais
                return f"+237 {cleaned}"
            elif len(cleaned) == 10:
                # Pourrait être n'importe quel pays, utiliser le contexte
                return f"+237 {cleaned}"  # Défaut Cameroun pour cette app
            elif len(cleaned) >= 11:
                # Code pays probablement inclus
                if cleaned.startswith('237'):
                    return f"+237 {cleaned[3:]}"
                elif cleaned.startswith('1'):
                    return f"+1 {cleaned[1:]}"
                elif cleaned.startswith('33'):
                    return f"+33 {cleaned[2:]}"
                else:
                    # Code pays à 3 chiffres par défaut
                    return f"+{cleaned[:3]} {cleaned[3:]}"
        
        return ""  # Numéro invalide

    # === FONCTION UTILITAIRE : VENTES ===

        
    # ===== ROUTES CONNEXION =====
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            user_data, error = authenticate_user(Utilisateur, email, password)
            if user_data:
                session['user_id'] = user_data['user_id']
                session['username'] = user_data['nom_utilisateur']
                session['role'] = user_data['role']
                session['ville'] = user_data['ville']
                session['email'] = user_data['email']
                session['actif'] = user_data['actif']
                session.permanent = True
                return redirect(url_for('dashboard'))
            else:
                flash(error or "Identifiants incorrects", "error")
                return redirect(url_for('login'))

        return render_template("login.html")
    
    
    # ===== ROUTES DÉCONNEXION =====
    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))


    # ===== ROUTES DASHBOARD  =====
    @app.route('/dashboard')
    def dashboard():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        username = session['username']
        role = session['role']
        ville = session['ville']

        # SECTION DASHBOARD SECRÉTAIRE CORRIGÉE
        if role == "secretaire":
            
            # Récupérer les années disponibles dynamiquement
            available_years = get_available_years()
            selected_year = request.args.get('year', datetime.now().year, type=int)
            
            # Calculer les KPIs filtrés par ville de l'utilisateur
            kpi_data = get_kpi_data(ville, user_id)
            print(f"📊 KPI data: {kpi_data}")
            
            # Calculer les tendances vs mois précédent
            kpi_trends = calculate_kpi_trends(ville, user_id)
            
            # CORRECTION CRITIQUE: Récupérer les proformas avec debug
            print(f"🔍 Fetching proformas for user {user_id} in ville {ville}")
            proformas = get_proformas_by_user_formatted(ville, user_id)
            print(f"📋 Dashboard will show {len(proformas)} proformas")
            
            # Calculer le montant total des proformas
            total_amount = sum(p['total_ttc'] for p in proformas)
            print(f"💰 Total amount: {total_amount}")
            
            # Récupérer les données pour les formulaires
            classes_disponibles = get_classes_livres()
            formations_disponibles = get_formations_disponibles()
            villes_fournitures = get_villes_fournitures()
            natures_disponibles = get_natures_disponibles()
            
            # AJOUT DEBUG: Vérifier les données avant le template
            print(f"DEBUG AVANT TEMPLATE:")
            print(f"  - Nombre de proformas: {len(proformas)}")
            print(f"  - Total amount: {total_amount}")
            print(f"  - KPI CA: {kpi_data['chiffre_affaires']}")
            
            return render_template("dashboard_secretaire.html",
                # KPIs avec formatage correct
                kpi_ca=format_currency(kpi_data['chiffre_affaires']),
                kpi_ca_trend=kpi_trends['chiffre_affaires'],
                kpi_factures=format_number(kpi_data['factures']),
                kpi_factures_trend=kpi_trends['factures'],  
                kpi_devis=format_currency(kpi_data['devis']),
                kpi_devis_trend=kpi_trends['devis'],
                kpi_a_traiter=format_number(kpi_data['a_traiter']),
                kpi_a_traiter_trend=kpi_trends['a_traiter'],
                    
                    # Données principales
                    proformas=proformas,
                    total_amount=format_currency(total_amount),
                    proformas_count=len(proformas),
                    
                    # Données pour filtrages
                    available_years=available_years,
                    selected_year=selected_year,
                    
                    # Données pour formulaire
                    classes_livres=classes_disponibles,
                    formations=formations_disponibles,
                    villes_fournitures=villes_fournitures,
                    natures_disponibles=natures_disponibles,
                    current_date=datetime.now().strftime('%Y-%m-%d'))
        elif role == "admin":
            return render_template("dashboard_admin.html")
        else:
            flash("Rôle utilisateur inconnu", "error")
            return redirect(url_for('login'))
    
    @app.route('/api/dashboard/ca-factures-evolution')
    def api_dashboard_ca_factures_evolution():
        """Récupérer l'évolution mensuelle du CA et nombre de factures pour les 12 prochains mois"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Calculer du mois actuel jusqu'à 11 mois dans le futur
            now = datetime.now()
            start_date = now.replace(day=1)  # Premier jour du mois actuel
            end_date = (now.replace(day=1) + relativedelta(months=11) + relativedelta(day=31))  # Dernier jour dans 11 mois

            print(f"🔍 DEBUG CA EVOLUTION - Période FUTURE: {start_date} à {end_date}")

            cur.execute("""
                WITH monthly_stats AS (
                    SELECT 
                        EXTRACT(YEAR FROM p.date_creation) as year,
                        EXTRACT(MONTH FROM p.date_creation) as month,
                        COUNT(CASE WHEN p.etat = 'termine' THEN 1 END) as nb_factures,
                        SUM(
                            CASE WHEN p.etat = 'termine' THEN
                                (SELECT COALESCE(SUM(pa.quantite * a.prix), 0) 
                                FROM proforma_articles pa 
                                JOIN articles a ON a.article_id = pa.article_id 
                                WHERE pa.proforma_id = p.proforma_id)
                                + COALESCE(p.frais, 0)
                                - COALESCE(p.remise, 0)
                            ELSE 0 END
                        ) as ca_total
                    FROM proformas p
                    WHERE p.date_creation >= %s
                    AND p.date_creation <= %s
                    AND p.ville = %s
                    AND p.cree_par = %s
                    GROUP BY EXTRACT(YEAR FROM p.date_creation), EXTRACT(MONTH FROM p.date_creation)
                    ORDER BY year, month
                )
                SELECT year, month, nb_factures, ca_total FROM monthly_stats
            """, [start_date, end_date, ville, user_id])

            results = cur.fetchall()
            has_data = len(results) > 0

            # Mapping mois texte français
            month_names = {
                1: 'Jan', 2: 'Fév', 3: 'Mar', 4: 'Avr', 5: 'Mai', 6: 'Juin',
                7: 'Juil', 8: 'Aoû', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Déc'
            }

            # Indexation des données SQL par (année, mois)
            monthly_data = {(int(r[0]), int(r[1])): (int(r[2]), float(r[3])) for r in results}

            labels = []
            
            nb_factures = []
            ca_montants = []

            # Générer TOUJOURS 12 mois, même sans données
            current_date = now.replace(day=1)  # Commencer par le mois actuel
            for i in range(12):
                year = current_date.year
                month = current_date.month

                labels.append(f"{month_names[month]} {year}")
                
                # Valeurs par défaut si pas de données
                nb, ca = monthly_data.get((year, month), (0, 0))
                nb_factures.append(int(nb))
                ca_montants.append(float(ca))

                current_date += relativedelta(months=1)  # Aller vers le futur

            cur.close()
            conn.close()

            return jsonify({
                "success": True,
                "labels": labels,
                "nb_factures": nb_factures,
                "ca_montants": ca_montants,
                "has_data": has_data  # Mettre à True si vous voulez toujours afficher le graphique
            })

        except Exception as e:
            print(f"❌ Erreur api_dashboard_ca_factures_evolution: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

        
    @app.route('/api/check-client', methods=['POST'])
    def api_check_client():
        """Vérifier si un client existe par numéro de téléphone et auto-compléter"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            data = request.get_json()
            phone = data.get('phone')
            
            if not phone:
                return jsonify({"exists": False})
            
            # ✅ CORRECTION: Utiliser le format de stockage compact pour la recherche
            clean_phone_storage = clean_phone_number_for_storage(phone)
            
            if not clean_phone_storage:
                return jsonify({
                    "exists": False,
                    "error": "Numéro de téléphone invalide"
                })
            
            # ✅ DEBUG: Afficher les formats pour vérification
            print(f"🔍 DEBUG check-client:")
            print(f"   Numéro original: {phone}")
            print(f"   Format recherche: {clean_phone_storage}")
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # ✅ CORRECTION: Chercher avec le format compact qui est stocké en base
            cur.execute("""
                SELECT client_id, nom, adresse, ville, pays, telephone
                FROM clients 
                WHERE telephone = %s OR telephone_secondaire = %s
            """, [clean_phone_storage, clean_phone_storage])
            
            client = cur.fetchone()
            
            if client:
                print(f"✅ Client trouvé avec téléphone: {client[5]}")
            else:
                print(f"❌ Aucun client trouvé pour: {clean_phone_storage}")
            
            cur.close()
            conn.close()
            
            if client:
                return jsonify({
                    "exists": True,
                    "client": {
                        "client_id": client[0],
                        "nom": client[1] or "",
                        "adresse": client[2] or "",
                        "ville": client[3] or "",
                        "pays": client[4] or "Cameroun"
                    }
                })
            else:
                return jsonify({
                    "exists": False,
                    "new_client": True,
                    "message": "Nouveau client détecté"
                })
                    
        except Exception as e:
            print(f"❌ Erreur api_check_client: {e}")
            return jsonify({
                "exists": False,
                "error": str(e)
            })

    # 2. ROUTE CORRIGÉE : Classes par nature
    @app.route('/api/classes-by-nature')
    def api_get_classes_by_nature():
        """Récupérer les classes filtrées par nature - CORRIGÉ"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            nature = request.args.get('nature')
            if not nature:
                return jsonify({"success": False, "message": "Nature manquante"}), 400

            print(f"🔍 DEBUG: Getting classes for nature '{nature}'")

            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête optimisée pour les classes
            cur.execute("""
                SELECT DISTINCT classe 
                FROM articles 
                WHERE type_article = 'livre' 
                AND LOWER(TRIM(COALESCE(nature, ''))) = LOWER(TRIM(%s))
                AND classe IS NOT NULL 
                AND classe != ''
                ORDER BY classe
            """, [nature])
            
            classes = [row[0] for row in cur.fetchall() if row[0]]
            print(f"🔍 DEBUG: Found {len(classes)} classes for nature '{nature}': {classes}")
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "classes": classes
            })
            
        except Exception as e:
            print(f"❌ Erreur api_get_classes_by_nature: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    @app.route('/api/livres-by-nature-classe')
    def api_get_livres_by_nature_classe():
        """Récupérer les livres filtrés par nature ET classe - NOUVELLE ROUTE"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            nature = request.args.get('nature')
            classe = request.args.get('classe')
            
            print(f"🔍 DEBUG API: nature='{nature}', classe='{classe}'")
            
            if not nature or not classe:
                return jsonify({
                    "success": False, 
                    "message": "Nature et classe obligatoires"
                }), 400

            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête pour récupérer les livres par nature + classe
            cur.execute("""
                SELECT article_id, code, designation, prix, nature, classe
                FROM articles 
                WHERE type_article = 'livre' 
                AND LOWER(TRIM(COALESCE(nature, ''))) = LOWER(TRIM(%s))
                AND LOWER(TRIM(COALESCE(classe, ''))) = LOWER(TRIM(%s))
                AND designation IS NOT NULL
                AND designation != ''
                ORDER BY designation
            """, [nature, classe])
            
            livres = []
            rows = cur.fetchall()
            print(f"🔍 DEBUG: Found {len(rows)} books")
            
            for row in rows:
                article_id, code, designation, prix, nature_db, classe_db = row
                
                livres.append({
                    'article_id': article_id,
                    'code': code or f"LIV{article_id:05d}",
                    'designation': designation,
                    'prix': int(prix) if prix else 0,
                    'nature': nature_db,
                    'classe': classe_db
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "livres": livres
            })
            
        except Exception as e:
            print(f"❌ Erreur api_get_livres_by_nature_classe: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur serveur: {str(e)}"
            }), 500

    # Récupérer les fournitures par ville
    @app.route('/api/fournitures-by-ville/<ville>')
    def api_get_fournitures_by_ville(ville):
        """Récupérer les fournitures par ville de référence"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT a.article_id, a.code, a.designation, pv.prix
                FROM prix_fournitures_ville pv
                JOIN articles a ON a.article_id = pv.article_id
                WHERE pv.ville = %s 
                AND a.type_article = 'fourniture'
                ORDER BY a.designation
            """, [ville])
            
            fournitures = []
            for row in cur.fetchall():
                fournitures.append({
                    'article_id': row[0],
                    'code': row[1],
                    'designation': row[2],
                    'prix': row[3]
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "fournitures": fournitures
            })
            
        except Exception as e:
            print(f"Erreur api_get_fournitures_by_ville: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    # Récupérer toutes les formations
    @app.route('/api/formations')
    def api_get_formations():
        """Récupérer toutes les formations"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            formations = get_formations_disponibles()
            
            return jsonify({
                "success": True,
                "formations": formations
            })
            
        except Exception as e:
            print(f"Erreur api_get_formations: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    # Créer une nouvelle proforma
    @app.route('/api/proforma', methods=['POST'])
    def api_create_proforma():
        conn = None
        cursor = None
        
        try:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"success": False, "message": "Utilisateur non connecté"}), 401

            data = request.get_json()

            client_data = data.get("client", {})
            client_name = client_data.get("nom")
            raw_phone = client_data.get("telephone")
            date_creation = data.get("date")
            articles = data.get("articles", [])
            frais = data.get("frais", [])

            if not client_name or not raw_phone or not date_creation:
                return jsonify({"success": False, "message": "Champs obligatoires manquants"}), 400

            if not articles:
                return jsonify({"success": False, "message": "Au moins un article est requis"}), 400

            conn = get_db_connection()
            cursor = conn.cursor()

            clean_phone_storage = clean_phone_number_for_storage(raw_phone)
            if not clean_phone_storage:
                return jsonify({"success": False, "message": "Format du numéro de téléphone invalide"}), 400

            cursor.execute("SELECT client_id FROM clients WHERE telephone = %s", (clean_phone_storage,))
            client = cursor.fetchone()
            client_created = False

            if not client:
                client_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO clients (client_id, nom, telephone, adresse, ville, pays, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    client_id, 
                    client_name, 
                    clean_phone_storage,
                    client_data.get("adresse", ""), 
                    client_data.get("ville", ""), 
                    client_data.get("pays", "Cameroun")
                ))
                client_created = True
            else:
                client_id = client[0]

            totals = calculate_proforma_totals_from_data(articles, frais, data.get("remise", 0))

            cursor.execute("""
                INSERT INTO proformas (client_id, date_creation, adresse_livraison, frais, remise, etat, ville, cree_par)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING proforma_id
            """, (
                client_id, 
                date_creation, 
                client_data.get("adresse", ""), 
                totals['frais'],
                data.get("remise", 0), 
                'en_attente', 
                session.get('ville', 'Yaoundé'),
                user_id
            ))

            proforma_id = cursor.fetchone()[0]

            for i, article in enumerate(articles):
                article_type = article.get("type", "service").lower()
                designation = article.get("designation", "")
                prix = float(article.get("prix", 0))
                
                if not designation or not prix:
                    continue

                article_id_from_form = article.get('article_id')
                article_id = None

                if article_id_from_form and str(article_id_from_form).strip() not in ['', 'null', 'undefined']:
                    cursor.execute("SELECT article_id FROM articles WHERE article_id = %s", [article_id_from_form])
                    existing_article = cursor.fetchone()
                    if existing_article:
                        article_id = int(article_id_from_form)

                if not article_id:
                    cursor.execute("""
                        SELECT article_id FROM articles 
                        WHERE LOWER(TRIM(designation)) = LOWER(TRIM(%s)) 
                        AND type_article = %s
                        AND TRIM(COALESCE(nature, '')) = TRIM(COALESCE(%s, ''))
                        AND TRIM(COALESCE(classe, '')) = TRIM(COALESCE(%s, ''))
                        LIMIT 1
                    """, (
                        designation,
                        article_type,
                        article.get('nature'),
                        article.get('classe')
                    ))

                    existing_article = cursor.fetchone()
                    if existing_article:
                        article_id = existing_article[0]
                    else:
                        if article_type in ['service']:
                            cursor.execute("""
                                INSERT INTO articles (designation, prix, type_article, nature, classe)
                                VALUES (%s, %s, %s, %s, %s)
                                RETURNING article_id
                            """, (
                                designation, prix, article_type,
                                article.get('nature'),
                                article.get('classe')
                            ))
                            article_id = cursor.fetchone()[0]
                        else:
                            raise Exception(f"Impossible de créer un article de type {article_type} sans ID préexistant")

                if article_type == 'service':
                    quantite = int(article.get('jours', 1))
                elif article_type == 'formation':
                    quantite = int(article.get('heures', 1))
                else:
                    quantite = int(article.get('quantite', 1))

                cursor.execute("""
                    INSERT INTO proforma_articles (proforma_id, article_id, quantite)
                    VALUES (%s, %s, %s)
                """, (proforma_id, article_id, quantite))

            frais_total = 0
            for fee in frais:
                fee_amount = float(fee.get('amount', 0))
                if fee_amount > 0:
                    frais_total += fee_amount

            if frais_total != totals['frais']:
                cursor.execute("UPDATE proformas SET frais = %s WHERE proforma_id = %s", (frais_total, proforma_id))

            conn.commit()

            cursor.execute("SELECT COUNT(*) FROM proforma_articles WHERE proforma_id = %s", [proforma_id])
            nb_articles_associes = cursor.fetchone()[0]

            if nb_articles_associes == 0:
                conn.rollback()
                return jsonify({"success": False, "message": "Erreur: Aucun article n'a pu être associé à la proforma"}), 500

            return jsonify({
                "success": True,
                "client_created": client_created,
                "proforma": {
                    "proforma_id": proforma_id,
                    "numero": f"PRO{proforma_id:05d}",
                    "date_creation": date_creation,
                    "client_nom": client_name,
                    "total_ttc": totals['total_ttc'],
                    "etat": "en_attente",
                    "created_by": user_id,
                    "nb_articles": nb_articles_associes
                }
            })

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Erreur api_create_proforma: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "message": str(e)}), 500

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        
    # Actions sur les proformas
    @app.route('/api/proforma/<int:proforma_id>', methods=['GET'])
    def api_get_proforma(proforma_id):
        """Récupérer les détails d'une proforma avec la bonne structure"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Récupérer la proforma avec client
            cur.execute("""
                SELECT 
                    p.proforma_id, p.date_creation, p.frais, p.remise, p.commentaire,
                    c.nom, c.telephone, c.adresse, c.ville, c.pays
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                WHERE p.proforma_id = %s AND p.ville = %s AND p.cree_par = %s
            """, [proforma_id, ville, user_id])
            
            proforma_row = cur.fetchone()
            if not proforma_row:
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Proforma non trouvée"}), 404
            
            # Récupérer les articles
            cur.execute("""
                SELECT 
                    a.article_id, a.designation, a.prix, a.type_article,
                    a.nature, a.classe, pa.quantite
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                WHERE pa.proforma_id = %s
            """, [proforma_id])
            articles_rows = cur.fetchall()
            
            # STRUCTURE CORRIGÉE POUR LE FRONTEND
            proforma_data = {
                "proforma_id": proforma_row[0],
                "date_creation": proforma_row[1].strftime('%Y-%m-%d') if proforma_row[1] else "",
                "remise": proforma_row[3] or 0,
                "commentaire": proforma_row[4],
                # DONNÉES CLIENT AVEC LES BONS NOMS
                "client_nom": proforma_row[5] or "",
                "client_telephone": proforma_row[6] or "",
                "client_adresse": proforma_row[7] or "",
                "client_ville": proforma_row[8] or "",
                "client_pays": proforma_row[9] or "Cameroun",
                "articles": [],
                "frais": []
            }
            
            # ARTICLES AVEC LA BONNE STRUCTURE
            for article in articles_rows:
                article_type = article[3] or "service"
                
                article_data = {
                    "article_id": article[0],
                    "designation": article[1],
                    "prix": float(article[2]) if article[2] else 0,
                    "type": article_type,
                    "nature": article[4],
                    "classe": article[5],
                    "quantite": int(article[6]) if article[6] else 1
                }
                
                # AJOUTER CHAMPS SPÉCIFIQUES SELON LE TYPE
                if article_type == "livre":
                    article_data["ville_reference"] = None
                    article_data["jours"] = None
                    article_data["heures"] = None
                elif article_type == "fourniture":
                    article_data["ville_reference"] = article[4]  # nature utilisée pour ville
                    article_data["jours"] = None
                    article_data["heures"] = None
                elif article_type == "service":
                    article_data["ville_reference"] = None
                    article_data["jours"] = article[6] if article[6] else 1  # quantité = jours
                    article_data["heures"] = None
                elif article_type == "formation":
                    article_data["ville_reference"] = None
                    article_data["jours"] = None
                    article_data["heures"] = article[6] if article[6] else 1  # quantité = heures
                
                proforma_data["articles"].append(article_data)
            
            # FRAIS 
            frais_total = proforma_row[2] or 0
            if frais_total > 0:
                proforma_data["frais"].append({
                    "type": "Livraison",
                    "montant": frais_total,
                    "commentaire": ""
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "proforma": proforma_data
            })
            
        except Exception as e:
            print(f"❌ Erreur api_get_proforma: {e}")
            return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500
            
    @app.route('/api/proforma/<int:proforma_id>', methods=['PUT'])
    def api_update_proforma(proforma_id):
        """Modifier une proforma existante - VERSION COMPLÈTE CORRIGÉE"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            data = request.get_json()
            ville = session['ville']
            user_id = session['user_id']
            
            print(f"🔧 Updating proforma {proforma_id} with data: {data}")
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Vérifier que la proforma existe et appartient à l'utilisateur
            cur.execute("""
                SELECT client_id FROM proformas 
                WHERE proforma_id = %s AND ville = %s AND cree_par = %s
            """, [proforma_id, ville, user_id])
            
            result = cur.fetchone()
            if not result:
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Proforma non trouvée"}), 404
            
            existing_client_id = result[0]
            
            # METTRE À JOUR LE CLIENT D'ABORD
            client_data = data.get("client", {})
            if client_data:
                cur.execute("""
                    UPDATE clients 
                    SET nom = %s, adresse = %s, ville = %s, pays = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE client_id = %s
                """, [
                    client_data.get('nom', ''),
                    client_data.get('adresse', ''),
                    client_data.get('ville', ''),
                    client_data.get('pays', 'Cameroun'),
                    existing_client_id
                ])
            
            # TRAITEMENT DES ARTICLES AVEC DÉTAILS SELON TYPE
            articles = data.get('articles', [])
            frais = data.get('frais', [])
            remise = float(data.get('remise', 0))
            
            # Calcul du sous-total
            sous_total = 0
            for article in articles:
                prix = float(article.get('prix', 0))
                article_type = article.get('type', '').lower()
                
                if article_type == 'service':
                    jours = int(article.get('jours', 1))
                    sous_total += prix * jours
                elif article_type == 'formation':
                    heures = int(article.get('heures', 1))
                    sous_total += prix * heures
                else:  # livre, fourniture
                    quantite = int(article.get('quantite', 1))
                    sous_total += prix * quantite
            
            # Calcul frais supplémentaires
            total_frais = 0
            for fee in frais:
                total_frais += float(fee.get('amount', 0))
            
            # Calcul remise et total
            montant_remise = (sous_total * remise) / 100
            total_ttc = sous_total - montant_remise + total_frais
            
            # METTRE À JOUR LA PROFORMA
            cur.execute("""
                UPDATE proformas 
                SET frais = %s, remise = %s, commentaire = %s, 
                    date_modification = CURRENT_TIMESTAMP
                WHERE proforma_id = %s
            """, [
                total_frais,
                remise,
                data.get('commentaire', ''),
                proforma_id
            ])
            
            # SUPPRIMER ANCIENS ARTICLES
            cur.execute("DELETE FROM proforma_articles WHERE proforma_id = %s", [proforma_id])
            
            for i, article_data in enumerate(articles):
                article_type = article_data.get('type', 'service').lower()
                article_id = article_data.get('article_id')

                try:
                    article_id = int(article_id)
                except (ValueError, TypeError):
                    article_id = None

                designation = article_data.get('designation', 'Article')
                prix = float(article_data.get('prix', 0))
                nature = article_data.get('nature')
                classe = article_data.get('classe')
                quantite = int(article_data.get('quantite', 1))

                if article_type == 'service' and article_data.get('jours'):
                    quantite = int(article_data.get('jours', 1))
                elif article_type == 'formation' and article_data.get('heures'):
                    quantite = int(article_data.get('heures', 1))

                if article_id:
                    print(f"✅ Article existant utilisé : {designation} (ID: {article_id})")
                else:
                    # Seuls les services personnalisés SANS ID peuvent créer un nouvel article
                    if article_type in ['service']:
                        cur.execute("""
                            INSERT INTO articles (designation, prix, type_article, nature, classe)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING article_id
                        """, [designation, prix, article_type, nature, classe])
                        article_id = cur.fetchone()[0]
                        print(f"🆕 Article personnalisé créé : {designation} (ID: {article_id})")
                    else:
                        # ❌ Si on est ici sans article_id et ce n’est pas un service → ERREUR !
                        raise Exception(f"Article manquant ou invalide pour {designation} (type {article_type})")

                # Association à la proforma
                cur.execute("""
                    INSERT INTO proforma_articles (proforma_id, article_id, quantite)
                    VALUES (%s, %s, %s)
                """, [proforma_id, article_id, quantite])

            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✅ Proforma {proforma_id} mise à jour avec succès")
            
            return jsonify({
                "success": True,
                "message": "Proforma mise à jour avec succès",
                "proforma_id": proforma_id,
                "total_ttc": total_ttc
            })
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                if 'cur' in locals():
                    cur.close()
                conn.close()
            
            print(f"❌ Erreur api_update_proforma: {e}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                "success": False,
                "message": f"Erreur lors de la mise à jour: {str(e)}"
            }), 500

    @app.route('/api/proforma/<int:proforma_id>', methods=['DELETE'])
    def api_delete_proforma(proforma_id):
        """Supprimer une proforma"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Vérifier que la proforma existe et peut être supprimée
            cur.execute("""
                SELECT etat FROM proformas 
                WHERE proforma_id = %s AND ville = %s AND cree_par = %s
            """, [proforma_id, ville, user_id])
            
            result = cur.fetchone()
            if not result:
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Proforma non trouvée"}), 404
            
            etat = result[0]
            if etat in ['termine', 'partiel']:
                cur.close()
                conn.close()
                return jsonify({
                    "success": False, 
                    "message": "Impossible de supprimer une proforma terminée ou partiellement payée"
                }), 400
            
            # Supprimer la proforma
            cur.execute("DELETE FROM proformas WHERE proforma_id = %s", [proforma_id])
            
            if cur.rowcount == 0:
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Aucune proforma supprimée"}), 404
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "message": "Proforma supprimée avec succès"
            })
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cur.close()
                conn.close()
            print(f"Erreur api_delete_proforma: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur lors de la suppression: {str(e)}"
            }), 500

    
    @app.route('/api/proforma/<int:proforma_id>/status', methods=['PUT'])
    def api_update_proforma_status(proforma_id):
        """Mettre à jour le statut d'une proforma - VERSION CORRIGÉE"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            data = request.get_json()
            ville = session['ville']
            user_id = session['user_id']
            
            nouveau_statut = data.get('statut')
            commentaire = data.get('commentaire', '')
            
            print(f"🔄 UPDATE STATUS REQUEST: Proforma {proforma_id} -> {nouveau_statut}")
            
            # Validation des statuts autorisés
            statuts_autorises = ['en_attente', 'en_cours', 'partiel', 'termine']
            if nouveau_statut not in statuts_autorises:
                return jsonify({
                    "success": False,
                    "message": f"Statut invalide. Autorisés: {', '.join(statuts_autorises)}"
                }), 400
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # ✅ CORRECTION: Requête UPDATE simplifiée sans WHERE restrictif
            try:
                # Démarrer une transaction explicite
                cur.execute("BEGIN")
                
                # ✅ UPDATE SIMPLE ET DIRECT
                update_query = """
                    UPDATE proformas 
                    SET etat = %s, 
                        date_modification = CURRENT_TIMESTAMP,
                        commentaire = %s
                    WHERE proforma_id = %s 
                    AND ville = %s 
                    AND cree_par = %s
                """
                
                cur.execute(update_query, [nouveau_statut, commentaire, proforma_id, ville, user_id])
                rows_affected = cur.rowcount
                
                print(f"🔍 ROWS UPDATED: {rows_affected}")
                
                if rows_affected == 0:
                    cur.execute("ROLLBACK")
                    cur.close()
                    conn.close()
                    print(f"❌ Aucune ligne mise à jour - Proforma introuvable ou non autorisée")
                    return jsonify({
                        "success": False, 
                        "message": "Proforma introuvable ou modification non autorisée"
                    }), 404
                
                # ✅ MISE À JOUR DES ARTICLES SI STATUT = TERMINÉ
                if nouveau_statut == 'termine':
                    cur.execute("""
                        UPDATE proforma_articles 
                        SET statut_livraison = 'livré',
                            date_livraison = CURRENT_TIMESTAMP
                        WHERE proforma_id = %s
                    """, [proforma_id])
                    print(f"🔄 Articles mis à jour en 'livré' pour proforma {proforma_id}")
                
                # ✅ VÉRIFICATION AVANT COMMIT
                cur.execute("SELECT etat FROM proformas WHERE proforma_id = %s", [proforma_id])
                verification = cur.fetchone()
                
                if not verification:
                    cur.execute("ROLLBACK")
                    cur.close()
                    conn.close()
                    return jsonify({"success": False, "message": "Proforma disparue après mise à jour"}), 500
                
                statut_verifie = verification[0]
                print(f"🔍 STATUT APRÈS UPDATE: '{statut_verifie}'")
                
                if statut_verifie != nouveau_statut:
                    cur.execute("ROLLBACK")
                    cur.close()
                    conn.close()
                    print(f"❌ ÉCHEC PERSISTANCE - Attendu: '{nouveau_statut}', Trouvé: '{statut_verifie}'")
                    return jsonify({
                        "success": False,
                        "message": f"Échec de la mise à jour du statut"
                    }), 500
                
                # ✅ COMMIT SEULEMENT SI TOUT EST OK
                cur.execute("COMMIT")
                print(f"✅ STATUT PERSISTÉ AVEC SUCCÈS: {proforma_id} -> {nouveau_statut}")
                
                # ✅ CALCUL DES MONTANTS SELON LE NOUVEAU STATUT
                montant_paye = 0
                montant_restant = 0
                
                # Récupérer le total TTC
                cur.execute("""
                    SELECT COALESCE(
                        (SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = %s)
                        + COALESCE(p.frais, 0) - COALESCE(p.remise, 0), 0
                    ) as total_ttc
                    FROM proformas p
                    WHERE p.proforma_id = %s
                """, [proforma_id, proforma_id])
                
                total_result = cur.fetchone()
                total_ttc = total_result[0] if total_result else 0
                
                if nouveau_statut == 'termine':
                    montant_paye = total_ttc
                    montant_restant = 0
                elif nouveau_statut == 'partiel':
                    montant_paye = total_ttc / 2  # Exemple : 50% payé
                    montant_restant = total_ttc - montant_paye
                elif nouveau_statut == 'en_cours':
                    montant_paye = 0
                    montant_restant = total_ttc
                else:  # en_attente
                    montant_paye = 0
                    montant_restant = 0
                
                # ✅ METTRE À JOUR LES MONTANTS
                cur.execute("""
                    UPDATE proformas 
                    SET montant_paye = %s, montant_restant = %s
                    WHERE proforma_id = %s
                """, [montant_paye, montant_restant, proforma_id])
                
                cur.close()
                conn.close()
                
                return jsonify({
                    "success": True,
                    "message": "Statut mis à jour avec succès",
                    "proforma": {
                        "proforma_id": proforma_id,
                        "etat": nouveau_statut,
                        "montant_paye": float(montant_paye),
                        "montant_restant": float(montant_restant)
                    }
                })
                
            except Exception as e:
                print(f"❌ ERROR IN TRANSACTION: {e}")
                if 'cur' in locals():
                    cur.execute("ROLLBACK")
                raise e
                
        except Exception as e:
            if 'conn' in locals():
                try:
                    if 'cur' in locals():
                        cur.execute("ROLLBACK")
                        cur.close()
                    conn.close()
                except:
                    pass
            
            print(f"❌ ERREUR GLOBALE api_update_proforma_status: {e}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                "success": False,
                "message": f"Erreur serveur: {str(e)}"
            }), 500      

    @app.route('/api/proforma/<int:proforma_id>/status-check', methods=['GET'])
    def api_check_proforma_status_debug(proforma_id):
        """Route de diagnostic pour vérifier le statut réel en base de données"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401
        
        try:
            ville = session['ville']
            user_id = session['user_id']
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Récupération complète des informations de la proforma
            cur.execute("""
                SELECT proforma_id, etat, date_creation, date_modification, 
                    cree_par, ville, commentaire, montant_paye, montant_restant
                FROM proformas 
                WHERE proforma_id = %s
            """, [proforma_id])
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if result:
                return jsonify({
                    "success": True,
                    "proforma_id": result[0],
                    "etat": result[1],
                    "date_creation": result[2].isoformat() if result[2] else None,
                    "date_modification": result[3].isoformat() if result[3] else None,
                    "cree_par": result[4],
                    "ville": result[5],
                    "commentaire": result[6],
                    "montant_paye": float(result[7]) if result[7] else 0,
                    "montant_restant": float(result[8]) if result[8] else 0,
                    "user_matches": result[4] == user_id,
                    "ville_matches": result[5] == ville,
                    "can_modify": result[4] == user_id and result[5] == ville
                })
            else:
                return jsonify({"success": False, "message": "Proforma non trouvée"})
                
        except Exception as e:
            print(f"❌ Erreur check status: {e}")
            return jsonify({"success": False, "message": str(e)})
    
    @app.route('/api/proforma/<int:proforma_id>/details')
    def api_get_proforma_details(proforma_id):
        """Récupérer les détails complets d'une proforma pour modal de statut"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Récupérer proforma avec client
            cur.execute("""
                SELECT 
                    p.proforma_id, p.date_creation, p.frais, p.remise, p.commentaire, p.etat,
                    c.nom, c.telephone, c.adresse, c.ville, c.pays,
                    COALESCE((
                        SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id
                    ), 0) as sous_total,

                    COALESCE((
                        SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id
                    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0), 0) as total_ttc
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                WHERE p.proforma_id = %s AND p.ville = %s AND p.cree_par = %s
            """, [proforma_id, ville, user_id])
            
            proforma_row = cur.fetchone()
            if not proforma_row:
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Proforma non trouvée"}), 404
            
            # Récupérer les articles
            cur.execute("""
                SELECT 
                    a.article_id, a.designation, a.prix, a.type_article,
                    pa.quantite, COALESCE(pa.statut_livraison, 'non_livré') as statut_livraison
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                WHERE pa.proforma_id = %s
                ORDER BY a.designation
            """, [proforma_id])
            articles_rows = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Construire la réponse
            proforma_data = {
                "proforma_id": proforma_row[0],
                "date_creation": proforma_row[1].strftime('%Y-%m-%d') if proforma_row[1] else "",
                "frais": proforma_row[2] or 0,
                "remise": proforma_row[3] or 0,
                "commentaire": proforma_row[4] or "",
                "etat": proforma_row[5] or "en_attente",
                "sous_total": float(proforma_row[11]) if proforma_row[11] else 0,
                "total_ttc": float(proforma_row[12]) if proforma_row[12] else 0,
                "remise_montant": float(proforma_row[3]) if proforma_row[3] else 0,
                "frais_total": float(proforma_row[2]) if proforma_row[2] else 0,
                "client": {
                    "nom": proforma_row[6] or "",
                    "telephone": proforma_row[7] or "",
                    "adresse": proforma_row[8] or "",
                    "ville": proforma_row[9] or "",
                    "pays": proforma_row[10] or "Cameroun"
                },
                "articles": []
            }

            
            # Ajouter les articles
            for article in articles_rows:
                article_data = {
                    "article_id": article[0],
                    "designation": article[1],
                    "prix": float(article[2]) if article[2] else 0,
                    "type_article": article[3] or "service",
                    "quantite": int(article[4]) if article[4] else 1,
                    "statut_livraison": article[5] or "non_livré"
                }
                proforma_data["articles"].append(article_data)
            
            return jsonify({
                "success": True,
                "proforma": proforma_data
            })
            
        except Exception as e:
            print(f"❌ Erreur api_get_proforma_details: {e}")
            return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500
        
    
    @app.route('/api/proforma/<int:proforma_id>/download/<document_type>')
    def api_download_document(proforma_id, document_type):
        """
        Télécharger un document (proforma/facture/bon de livraison) en PDF
        AVEC VALIDATION COMPLÈTE DU STATUT
        """
        # Vérification de l'authentification
        if 'user_id' not in session:
            print(f"❌ Accès non autorisé pour le téléchargement de {document_type}")
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        # Validation du type de document
        valid_document_types = ['proforma', 'facture', 'bon']
        if document_type not in valid_document_types:
            print(f"❌ Type de document invalide: {document_type}")
            return jsonify({
                "success": False, 
                "message": f"Type de document invalide: {document_type}. Types autorisés: {', '.join(valid_document_types)}"
            }), 400

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            print(f"🔍 DEBUG: Téléchargement {document_type} pour proforma {proforma_id}")
            print(f"🔍 DEBUG: User {user_id}, Ville {ville}")
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # RÉCUPÉRATION DE LA PROFORMA AVEC TOUTES LES DONNÉES
            cur.execute("""
                SELECT 
                    p.proforma_id, p.date_creation, p.adresse_livraison, 
                    p.frais, p.remise, p.etat, p.commentaire,
                    c.nom, c.telephone, c.adresse, c.ville, c.pays
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                WHERE p.proforma_id = %s AND p.ville = %s AND p.cree_par = %s
            """, [proforma_id, ville, user_id])
            
            proforma_row = cur.fetchone()
            if not proforma_row:
                cur.close()
                conn.close()
                print(f"❌ Proforma {proforma_id} non trouvée pour user {user_id} ville {ville}")
                return jsonify({"success": False, "message": "Proforma non trouvée"}), 404
            
            print(f"✅ Proforma {proforma_id} trouvée avec statut: {proforma_row[5]}")
            
            # ✅ VALIDATION CRITIQUE DU STATUT ET DU TYPE DE DOCUMENT
            etat = proforma_row[5] or 'en_attente'  # Statut par défaut si NULL
            allowed_docs = get_allowed_documents_by_status(etat)

            print(f"🔍 DEBUG: Proforma {proforma_id} - Statut: '{etat}', Document demandé: '{document_type}'")
            print(f"🔍 DEBUG: Documents autorisés pour ce statut: {allowed_docs}")

            # ✅ VALIDATION AVEC MESSAGES D'ERREUR DÉTAILLÉS
            if document_type not in allowed_docs:
                error_messages = {
                    'en_attente': "Seule la proforma est disponible pour une commande en attente",
                    'en_cours': "Erreur: Document non autorisé malgré le statut en cours",
                    'partiel': "Erreur: Document non autorisé malgré le statut partiel", 
                    'termine': "Aucun document n'est disponible - la commande est terminée"
                }
                
                error_msg = error_messages.get(etat, f"Document {document_type} non autorisé pour le statut {etat}")
                
                print(f"❌ VALIDATION FAILED: {error_msg}")
                cur.close()
                conn.close()
                return jsonify({
                    "success": False, 
                    "message": error_msg,
                    "status": etat,
                    "allowed_documents": allowed_docs,
                    "requested_document": document_type
                }), 400

            # ✅ PROTECTION SPÉCIALE POUR LE STATUT "TERMINÉ"
            if etat == 'termine':
                print(f"❌ TÉLÉCHARGEMENT BLOQUÉ: Commande terminée, aucun document disponible")
                cur.close()
                conn.close()
                return jsonify({
                    "success": False,
                    "message": "La commande est terminée. Aucun document n'est disponible pour téléchargement.",
                    "status": "termine",
                    "allowed_documents": [],
                    "requested_document": document_type
                }), 400

            print(f"✅ Document {document_type} autorisé pour le statut {etat}")
                    
            # RÉCUPÉRER LES ARTICLES AVEC DÉTAILS
            cur.execute("""
                SELECT 
                    a.code, a.designation, a.prix, a.type_article,
                    pa.quantite, COALESCE(pa.statut_livraison, 'non_livré') as statut_livraison
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                WHERE pa.proforma_id = %s
                ORDER BY a.type_article, a.designation
            """, [proforma_id])
            
            articles_rows = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # CONSTRUIRE LES DONNÉES POUR LE TEMPLATE
            pdf_data = {
                'proforma_id': proforma_row[0],
                'date_creation': proforma_row[1],
                'adresse_livraison': proforma_row[2],
                'frais': proforma_row[3] or 0,
                'remise': proforma_row[4] or 0,
                'etat': proforma_row[5],
                'commentaire': proforma_row[6],
                'client': {
                    'nom': proforma_row[7] or "Client inconnu",
                    'telephone': proforma_row[8] or "Non renseigné",
                    'adresse': proforma_row[9] or "Non renseignée",
                    'ville': proforma_row[10] or "Non renseignée",
                    'pays': proforma_row[11] or "Cameroun"
                },
                'articles': [],
                'document_type': document_type
            }
            
            # TRAITER LES ARTICLES SELON LE TYPE DE DOCUMENT
            sous_total = 0
            articles_filtered = []

            print(f"🔍 DEBUG: Filtrage des articles pour {document_type} avec statut {etat}")

            for i, article in enumerate(articles_rows):
                code, designation, prix_unitaire, type_article, quantite, statut_livraison = article
                
                # ✅ LOGIQUE DE FILTRAGE SELON LE TYPE DE DOCUMENT ET LE STATUT
                include_article = True
                
                if document_type == 'bon':
                    if etat == 'partiel':
                        # Pour bon de livraison partiel, ne prendre que les articles livrés
                        if statut_livraison != 'livré':
                            include_article = False
                            print(f"🔍 DEBUG: Article {i+1} '{designation}' exclu (statut: {statut_livraison})")
                        else:
                            print(f"🔍 DEBUG: Article {i+1} '{designation}' inclus (livré)")
                    elif etat in ['en_cours']:
                        # Pour bon de livraison complet, prendre tous les articles
                        print(f"🔍 DEBUG: Article {i+1} '{designation}' inclus (bon complet)")
                else:
                    # Pour proforma et facture, toujours inclure tous les articles
                    print(f"🔍 DEBUG: Article {i+1} '{designation}' inclus ({document_type})")
                
                if include_article:
                    # Calculer le total pour cet article
                    total_article = prix_unitaire * quantite
                    sous_total += total_article
                    
                    articles_filtered.append({
                        'code': code or f"ART{len(articles_filtered)+1:03d}",
                        'designation': designation,
                        'prix_unitaire': float(prix_unitaire) if prix_unitaire else 0,
                        'type_article': type_article.title() if type_article else "Service",
                        'quantite': int(quantite) if quantite else 1,
                        'statut_livraison': statut_livraison,
                        'total': float(total_article)
                    })

            print(f"🔍 DEBUG: {len(articles_filtered)} articles retenus sur {len(articles_rows)} total")
            print(f"🔍 DEBUG: Sous-total calculé: {sous_total}")
            
            # Injecter les articles filtrés dans le template
            pdf_data['articles'] = articles_filtered
            
            # Vérification qu'il y a des articles à afficher
            if not articles_filtered:
                print(f"⚠️ WARNING: Aucun article à afficher pour {document_type} avec statut {etat}")
                if document_type == 'bon' and etat == 'partiel':
                    return jsonify({
                        "success": False,
                        "message": "Aucun article n'a été marqué comme livré pour ce bon de livraison partiel"
                    }), 400
            
            # CALCULS FINANCIERS
            remise_percent = pdf_data['remise']
            remise_montant = (sous_total * remise_percent) / 100 if remise_percent > 0 else 0
            total_ttc = sous_total - remise_montant + pdf_data['frais']
            
            pdf_data.update({
                'sous_total': float(sous_total),
                'remise_montant': float(remise_montant),
                'total_ttc': float(total_ttc),
                'montant_lettre': convert_number_to_words(total_ttc)
            })
            
            # ✅ DÉFINITION DU TITRE SELON LE TYPE DE DOCUMENT
            if document_type == 'facture':
                if etat == 'partiel':
                    pdf_data['document_title'] = 'FACTURE PARTIELLE'
                else:
                    pdf_data['document_title'] = 'FACTURE'
            elif document_type == 'bon':
                if etat == 'partiel':
                    pdf_data['document_title'] = 'BON DE LIVRAISON PARTIEL'
                else:
                    pdf_data['document_title'] = 'BON DE LIVRAISON'
            else:
                pdf_data['document_title'] = 'PROFORMA'

            pdf_data['document_type'] = document_type

            print(f"📄 Generating {document_type} with title: {pdf_data['document_title']}")

            # Génération du HTML avec le template unifié
            try:
                html_content = render_template('proforma_template.html', **pdf_data)
                print(f"✅ Template rendered successfully for {document_type}")
            except Exception as e:
                print(f"❌ Template rendering failed for {document_type}: {e}")
                raise e
            
            # GÉNÉRER LE PDF SELON L'ENGINE DISPONIBLE
            try:
                filename_prefixes = {
                    'proforma': 'PROFORMA',
                    'facture': 'FACTURE', 
                    'bon': 'BON_LIVRAISON'
                }
                filename = f"{filename_prefixes.get(document_type, 'DOCUMENT')}_{proforma_id:05d}.pdf"
                
                if PDF_ENGINE == "weasyprint":
                    base_url = request.url_root
                    pdf_file = HTML(string=html_content, base_url=base_url).write_pdf()
                    
                    response = make_response(pdf_file)
                    response.headers['Content-Type'] = 'application/pdf'
                    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    print(f"✅ PDF généré avec WeasyPrint: {filename}")
                    return response
                    
                elif PDF_ENGINE == "pdfkit":
                    options = {
                        'page-size': 'A4',
                        'margin-top': '1.5cm',
                        'margin-right': '1.5cm',
                        'margin-bottom': '1.5cm',
                        'margin-left': '1.5cm',
                        'encoding': "UTF-8",
                        'no-outline': None
                    }
                    
                    pdf_file = pdfkit.from_string(html_content, False, options=options)
                    
                    response = make_response(pdf_file)
                    response.headers['Content-Type'] = 'application/pdf'
                    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    print(f"✅ PDF généré avec PDFKit: {filename}")
                    return response
                    
                else:
                    return jsonify({
                        "success": False,
                        "message": "Aucun moteur PDF installé. Installez WeasyPrint: pip install weasyprint"
                    }), 500
                
            except Exception as e:
                print(f"❌ Erreur génération PDF: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback: retourner le HTML directement
                response = make_response(html_content)
                response.headers['Content-Type'] = 'text/html'
                return response
                
        except Exception as e:
            print(f"❌ Erreur api_download_document: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "message": f"Erreur serveur: {str(e)}"
            }), 500
            
    @app.route('/api/proforma/<int:proforma_id>/partial-amounts')
    def api_get_partial_amounts(proforma_id):
        """Récupérer les montants payé et restant pour une proforma partielle"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Récupérer les montants de la proforma
            cur.execute("""
                SELECT 
                    COALESCE(p.montant_paye, 0) as montant_paye,
                    COALESCE(p.montant_restant, 0) as montant_restant,
                    COALESCE(
                        (SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id)
                        + COALESCE(p.frais, 0) - COALESCE(p.remise, 0), 0
                    ) as total_ttc
                FROM proformas p
                WHERE p.proforma_id = %s AND p.ville = %s AND p.cree_par = %s
            """, [proforma_id, ville, user_id])
            
            result = cur.fetchone()
            if not result:
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Proforma non trouvée"}), 404
            
            montant_paye, montant_restant, total_ttc = result
            
            # Si montant_restant n'est pas défini, le calculer
            if montant_restant == 0 and montant_paye > 0:
                montant_restant = max(0, total_ttc - montant_paye)
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "montant_paye": float(montant_paye),
                "montant_restant": float(montant_restant),
                "total_ttc": float(total_ttc)
            })
            
        except Exception as e:
            print(f"❌ Erreur api_get_partial_amounts: {e}")
            return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500

    @app.route('/api/kpi-by-year/<int:year>')
    def api_kpi_by_year(year):
        """Récupérer les KPI pour une année donnée"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            current_year = datetime.now().year
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Dates pour l'année sélectionnée
            if year == current_year:
                date_debut = datetime(year, 1, 1).date()
                date_fin = datetime.now().date()
            else:
                date_debut = datetime(year, 1, 1).date()
                date_fin = datetime(year, 12, 31).date()
            
            # KPIs pour l'année
            kpi_data = get_kpi_data(ville, user_id, date_debut, date_fin)
            
            # Pour les années passées, "à traiter" = 0
            if year != current_year:
                kpi_data['a_traiter'] = 0
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "kpi": kpi_data,
                "year": year
            })
            
        except Exception as e:
            print(f"❌ Erreur api_kpi_by_year: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    @app.route('/api/proformas/filter')
    def api_filter_proformas():
        """Filtrer les proformas selon différents critères"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            # Paramètres de filtrage
            status = request.args.get('status', '')
            year = request.args.get('year', datetime.now().year, type=int)
            page = request.args.get('page', 1, type=int)
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Construction de la requête de base
            base_query = """
                SELECT 
                    p.proforma_id,
                    p.date_creation,
                    c.nom as client_nom,
                    p.etat,
                    u.nom_utilisateur,
                    COALESCE(
                        (SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id)
                        + COALESCE(p.frais, 0) - COALESCE(p.remise, 0), 0
                    ) as total_ttc
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                LEFT JOIN utilisateurs u ON u.user_id = p.cree_par
                WHERE p.ville = %s AND p.cree_par = %s
            """
            params = [ville, user_id]
            
            # Ajouter les filtres
            if status:
                base_query += " AND p.etat = %s"
                params.append(status)
                
            if year:
                base_query += " AND EXTRACT(YEAR FROM p.date_creation) = %s"
                params.append(year)
            
            # Pagination
            rows_per_page = 20
            offset = (page - 1) * rows_per_page
            
            # Compter le total
            count_query = f"SELECT COUNT(*) FROM ({base_query}) AS sub"
            cur.execute(count_query, params)
            total_count = cur.fetchone()[0]
            
            # Récupérer les données paginées
            paginated_query = f"{base_query} ORDER BY p.date_creation DESC LIMIT %s OFFSET %s"
            params.extend([rows_per_page, offset])
            cur.execute(paginated_query, params)
            
            proformas = cur.fetchall()
            
            # Formater les données
            formatted_proformas = []
            for p in proformas:
                proforma_id, date_creation, client_nom, etat, created_by, total_ttc = p
                
                montant_paye = calculate_montant_paye_from_etat(etat, total_ttc)
                
                formatted_proformas.append({
                    'proforma_id': proforma_id,
                    'numero': f"PRO{proforma_id:05d}",
                    'date_creation': date_creation.strftime('%d %b %Y'),
                    'client_nom': client_nom or "Client supprimé",
                    'total_ttc': total_ttc,
                    'montant_paye': montant_paye if montant_paye > 0 else None,
                    'montant_restant': total_ttc - montant_paye if montant_paye > 0 else None,
                    'etat': etat,
                    'created_by': created_by or "N/A"
                })
            
            cur.close()
            conn.close()
            
            # Calculer pagination
            total_pages = max(1, math.ceil(total_count / rows_per_page))
            
            return jsonify({
                "success": True,
                "proformas": formatted_proformas,
                "pagination": {
                    "page": page,
                    "pages": total_pages,
                    "total": total_count
                }
            })
            
        except Exception as e:
            print(f"Erreur api_filter_proformas: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    @app.route('/api/proforma/<int:proforma_id>/articles')
    def api_get_proforma_articles(proforma_id):
        """Récupérer les articles d'une proforma pour livraison partielle"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Vérifier que la proforma appartient à l'utilisateur
            cur.execute("""
                SELECT proforma_id FROM proformas 
                WHERE proforma_id = %s AND ville = %s AND cree_par = %s
            """, [proforma_id, ville, user_id])
            
            if not cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Proforma non trouvée"}), 404
            
            # Récupérer les articles
            cur.execute("""
                SELECT 
                    pa.id,
                    a.designation,
                    a.type_article,
                    pa.quantite,
                    pa.statut_livraison
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                WHERE pa.proforma_id = %s
            """, [proforma_id])
            
            articles_rows = cur.fetchall()
            
            articles = []
            for row in articles_rows:
                articles.append({
                    'id': row[0],
                    'designation': row[1],
                    'type': row[2],
                    'quantite': row[3],
                    'statut_livraison': row[4] or 'non_livré'
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "articles": articles
            })
            
        except Exception as e:
            print(f"Erreur api_get_proforma_articles: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
    
    

    @app.route('/api/export/proformas')
    def api_export_proformas():
        """Exporter les proformas en CSV"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            # Paramètres de filtrage
            status = request.args.get('status', '')
            year = request.args.get('year', '', type=str)
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Construction de la requête
            query = """
                SELECT 
                    p.proforma_id,
                    p.date_creation,
                    c.nom as client_nom,
                    c.telephone,
                    p.etat,
                    COALESCE(
                        (SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id)
                        + COALESCE(p.frais, 0) - COALESCE(p.remise, 0), 0
                    ) as total_ttc
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                WHERE p.ville = %s AND p.cree_par = %s
            """
            params = [ville, user_id]
            
            if status:
                query += " AND p.etat = %s"
                params.append(status)
                
            if year:
                query += " AND EXTRACT(YEAR FROM p.date_creation) = %s"
                params.append(int(year))
            
            query += " ORDER BY p.date_creation DESC"
            
            cur.execute(query, params)
            proformas = cur.fetchall()
            
            # Créer le CSV
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # En-têtes
            writer.writerow([
                'Numéro Proforma', 'Date', 'Client', 'Téléphone', 
                'Statut', 'Montant Total (FCFA)'
            ])
            
            # Données
            for p in proformas:
                writer.writerow([
                    f"PRO{p[0]:05d}",
                    p[1].strftime('%d/%m/%Y'),
                    p[2] or "Client supprimé",
                    p[3] or "-",
                    p[4],
                    f"{int(p[5]):,}".replace(',', ' ')
                ])
            
            cur.close()
            conn.close()
            
            # Préparer la réponse
            output.seek(0)
            
            from flask import make_response
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=proformas_export_{datetime.now().strftime("%Y%m%d")}.csv'
            
            return response
            
        except Exception as e:
            print(f"Erreur api_export_proformas: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

        @app.route("/download/<string:doc_type>/<int:proforma_id>")
        def download_document(doc_type, proforma_id):
            # 1. Récupération des données proforma depuis la BDD
            proforma = get_proforma_by_id(proforma_id)  # À implémenter selon ton ORM
            client = get_client_by_id(proforma.client_id)
            articles = get_articles_by_proforma(proforma_id)

            # 2. Préparer les données pour le template
            context = {
                "document_type": doc_type,
                "proforma_id": proforma.id,
                "date_creation": proforma.date_creation,
                "client": client,
                "articles": articles,
                "sous_total": proforma.sous_total,
                "remise": proforma.remise,
                "remise_montant": proforma.remise_montant,
                "frais": proforma.frais,
                "total_ttc": proforma.total_ttc,
                "montant_lettre": proforma.montant_lettre,
                "commentaire": proforma.commentaire
            }

            # 3. Générer HTML à partir du template
            html = render_template("proforma_template.html", **context)

            # 4. Conversion en PDF
            pdf = pdfkit.from_string(html, False, options={"page-size": "A4", "encoding": "UTF-8"})

            # 5. Retourner le PDF
            response = make_response(pdf)
            response.headers["Content-Type"] = "application/pdf"
            response.headers["Content-Disposition"] = f"attachment; filename={doc_type.upper()}_{proforma_id}.pdf"
            return response
        
        



    
        
    # ============================
    # ROUTE PRINCIPALE /repertoire
    # ============================
    @app.route('/repertoire')
    def repertoire():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        ville_filter = request.args.get('ville', '')
        rows_per_page = 50  # 50 clients par page
        offset = (page - 1) * rows_per_page

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # 1. Récupération des clients avec nb_commandes dynamique
            base_query = """
                SELECT c.client_id, c.nom, c.telephone, c.telephone_secondaire,
                    c.adresse, c.ville, c.pays,
                    COALESCE(COUNT(f.facture_id), 0) AS nb_commandes,
                    COALESCE(SUM(f.montant_total), 0) AS montant_total_paye
                FROM clients c
                LEFT JOIN factures f ON f.client_id = c.client_id
                WHERE 1=1
            """
            params = []

            if search:
                base_query += " AND (LOWER(c.nom) LIKE LOWER(%s) OR c.telephone LIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])

            if ville_filter:
                base_query += " AND c.ville = %s"
                params.append(ville_filter)

            base_query += " GROUP BY c.client_id"

            # Comptage total pour pagination
            count_query = f"SELECT COUNT(*) FROM ({base_query}) AS sub"
            cur.execute(count_query, params)
            total_clients = cur.fetchone()[0]
            total_pages = math.ceil(total_clients / rows_per_page) if total_clients > 0 else 1

            # Requête paginée
            paginated_query = f"{base_query} ORDER BY c.nom LIMIT %s OFFSET %s"
            params.extend([rows_per_page, offset])
            cur.execute(paginated_query, params)
            clients = cur.fetchall()

            # 2. Liste des villes distinctes
            cur.execute("SELECT DISTINCT ville FROM clients WHERE ville IS NOT NULL AND ville != '' AND LOWER(ville) != 'nan' ORDER BY ville")
            villes = [row[0] for row in cur.fetchall()]

            # SECTION KPI 
            mois_actuel_debut = datetime.now().replace(day=1).date()
            mois_actuel_fin = datetime.now().date()
            mois_precedent_fin = (datetime.now().replace(day=1) - timedelta(days=1)).date()
            mois_precedent_debut = mois_precedent_fin.replace(day=1)

            # 1. Total Clients (TOUS)
            cur.execute("SELECT COUNT(*) FROM clients")
            kpi_total_clients = cur.fetchone()[0] or 0

            # 2. KPI Chiffre d'affaires MOIS ACTUEL
            cur.execute("""
                SELECT COALESCE(SUM(
                    (SELECT COALESCE(SUM(pa.quantite * a.prix), 0) 
                    FROM proforma_articles pa 
                    JOIN articles a ON a.article_id = pa.article_id 
                    WHERE pa.proforma_id = p.proforma_id)
                    + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                ), 0)
                FROM proformas p
                WHERE p.date_creation >= %s AND p.date_creation <= %s
                AND p.etat = 'termine'
            """, [mois_actuel_debut, mois_actuel_fin])
            kpi_ca_mois = cur.fetchone()[0] or 0

            # Et aussi pour le CA mois précédent
            cur.execute("""
                SELECT COALESCE(SUM(
                    (SELECT COALESCE(SUM(pa.quantite * a.prix), 0) 
                    FROM proforma_articles pa 
                    JOIN articles a ON a.article_id = pa.article_id 
                    WHERE pa.proforma_id = p.proforma_id)
                    + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                ), 0)
                FROM proformas p
                WHERE p.date_creation >= %s AND p.date_creation <= %s
                AND p.etat = 'termine'
            """, [mois_precedent_debut, mois_precedent_fin])
            ca_mois_precedent = cur.fetchone()[0] or 0

            # Calcul tendance CA
            kpi_ca_trend = 0
            if ca_mois_precedent > 0:
                kpi_ca_trend = round(((kpi_ca_mois - ca_mois_precedent) / ca_mois_precedent) * 100, 1)
            elif kpi_ca_mois > 0:
                kpi_ca_trend = 100
            
            # 3. Nouveaux Clients MOIS ACTUEL
            cur.execute("""
                SELECT COUNT(*) FROM clients
                WHERE created_at >= %s AND created_at <= %s
            """, [mois_actuel_debut, mois_actuel_fin])
            kpi_new_clients = cur.fetchone()[0] or 0

            # Nouveaux clients mois précédent
            cur.execute("""
                SELECT COUNT(*) FROM clients
                WHERE created_at >= %s AND created_at <= %s
            """, [mois_precedent_debut, mois_precedent_fin])
            prev_new_clients = cur.fetchone()[0] or 0

            # Calcul progression nouveaux clients
            kpi_new_clients_trend = 0
            if kpi_new_clients == 0:
                kpi_new_clients_trend = 0  # ✅ Si 0 nouveaux clients, afficher 0%
            elif prev_new_clients > 0:
                kpi_new_clients_trend = round(((kpi_new_clients - prev_new_clients) / prev_new_clients) * 100, 1)
            elif kpi_new_clients > 0:
                kpi_new_clients_trend = 100

            # 4. Ville la plus active
            cur.execute("""
                SELECT ville, COUNT(*) AS total
                FROM clients
                WHERE ville IS NOT NULL AND ville != '' 
                AND TRIM(LOWER(ville)) NOT IN ('non renseigné', 'nan', '')
                GROUP BY ville
                ORDER BY total DESC
                LIMIT 1
            """)
            kpi_top = cur.fetchone()
            kpi_top_city = kpi_top[0] if kpi_top else "N/A"
            kpi_top_city_count = kpi_top[1] if kpi_top else 0

            # Formatage clients
            clients_data = []
            print("🔍 DEBUG: Formatage des clients...")
            for i, c in enumerate(clients):
                client_data = {
                    'client_id': c[0] or f"unknown_{i}",
                    'nom': c[1] or 'Nom inconnu',
                    'telephone': c[2] or '-',
                    'telephone_secondaire': c[3] or '-',
                    'adresse': c[4] or '-',
                    'ville': c[5] or '-',
                    'pays': c[6] or 'Non renseigné',
                    'nb_commandes': c[7] or 0,
                    'montant_total_paye': format_number(c[8] or 0)  # UTILISE format_number (sans FCFA)
                }
                clients_data.append(client_data)

            today = datetime.now()
            first_day_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Nouveaux clients du mois
            cur.execute("SELECT COUNT(*) FROM clients WHERE created_at >= %s", [first_day_month])
            kpi_new_clients = cur.fetchone()[0]

            return render_template('clients.html',
                clients=clients_data,
                villes=villes,
                kpi_ca=format_currency(kpi_ca_mois),  # UTILISE format_currency
                kpi_ca_trend=kpi_ca_trend,
                kpi_total_clients=format_number(kpi_total_clients),  # AJOUT FORMATAGE
                kpi_clients_trend=kpi_new_clients_trend,
                kpi_top_city=kpi_top_city,
                kpi_top_city_count=kpi_top_city_count,
                kpi_top_city_trend=0,
                kpi_new_clients=format_number(kpi_new_clients),  # AJOUT FORMATAGE
                kpi_new_clients_trend=kpi_new_clients_trend,
                total_pages=total_pages,
                current_page=page,
                search=search,
                ville_filter=ville_filter,
                periode_info=f"Période: {mois_actuel_debut.strftime('%B %Y')}"
            )

        except Exception as e:
            flash(f"Erreur lors de la récupération des données: {str(e)}", "error")
            return redirect(url_for('dashboard'))
        finally:
            cur.close()
            conn.close()

    # AJOUT D'UN CLIENT
    @app.route('/api/clients', methods=['POST'])
    def api_add_client():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "message": "Données manquantes"}), 400

            # ✅ Validation des champs obligatoires avec messages spécifiques
            required_fields = ['nom', 'telephone', 'ville', 'pays', 'adresse']
            missing_fields = []
            
            for field in required_fields:
                if not data.get(field) or not str(data[field]).strip():
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    "success": False, 
                    "message": f"Champs manquants ou vides: {', '.join(missing_fields)}"
                }), 400

            # Validation téléphone principal (obligatoire)
            raw_phone = str(data['telephone']).strip()
            if len(raw_phone) < 8:
                return jsonify({
                    "success": False, 
                    "message": "Le numéro de téléphone principal doit contenir au moins 8 chiffres"
                }), 400

            # Normalisation téléphone principal
            clean_phone = clean_phone_number_simple(data['telephone'])
            if not clean_phone:
                return jsonify({
                    "success": False, 
                    "message": "Format du numéro de téléphone principal invalide"
                }), 400

            # Validation SEULEMENT si fourni
            clean_phone_secondary = ""
            secondary_phone_raw = data.get('telephone_secondaire', '').strip()
            
            if secondary_phone_raw:  # Seulement si réellement fourni
                # Vérifier qu'il y a plus que juste l'indicatif
                digits_only = re.sub(r'\D', '', secondary_phone_raw)
                if len(digits_only) >= 8:  # Au moins 8 chiffres
                    clean_phone_secondary = clean_phone_number_simple(secondary_phone_raw)
                    if not clean_phone_secondary:
                        return jsonify({
                            "success": False, 
                            "message": "Format du numéro de téléphone secondaire invalide"
                        }), 400

            conn = get_db_connection()
            cur = conn.cursor()

            # Vérifier doublon téléphone principal ou secondaire
            cur.execute("""
                SELECT client_id, nom FROM clients
                WHERE telephone = %s OR telephone_secondaire = %s
            """, (clean_phone, clean_phone))
            duplicate = cur.fetchone()
            if duplicate:
                cur.close()
                conn.close()
                return jsonify({
                    "status": 409, 
                    "message": f"Un client avec ce numéro existe déjà: {duplicate[1]}",
                    "client_id": duplicate[0]
                }), 409

            # Vérifier doublon téléphone secondaire (SEULEMENT si fourni)
            if clean_phone_secondary:
                cur.execute("""
                    SELECT client_id, nom FROM clients
                    WHERE telephone = %s OR telephone_secondaire = %s
                """, (clean_phone_secondary, clean_phone_secondary))
                duplicate = cur.fetchone()
                if duplicate:
                    cur.close()
                    conn.close()
                    return jsonify({
                        "status": 409, 
                        "message": f"Le numéro secondaire est déjà utilisé par: {duplicate[1]}",
                        "client_id": duplicate[0]
                    }), 409

            # Générer un ID unique pour le nouveau client
            client_id = str(uuid.uuid4())

            #  Insérer le client avec timestamp
            cur.execute("""
                INSERT INTO clients (client_id, nom, telephone, telephone_secondaire, adresse, ville, pays, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                client_id,
                data['nom'].strip(),
                clean_phone,
                clean_phone_secondary if clean_phone_secondary else None,  # NULL si vide
                data['adresse'].strip(),
                data['ville'].strip(),
                data['pays'].strip()
            ))

            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True, 
                "message": "Client ajouté avec succès", 
                "client_id": client_id
            })

        except psycopg2.Error as e:
            if 'conn' in locals():
                conn.rollback()
                cur.close()
                conn.close()
            print(f"❌ Erreur base de données dans api_add_client: {e}")
            return jsonify({"success": False, "message": "Erreur de base de données"}), 500
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cur.close()
                conn.close()
            print(f"❌ Erreur générale dans api_add_client: {e}")
            return jsonify({"success": False, "message": f"Erreur serveur: {str(e)}"}), 500
           
    # RÉCUPÉRER CLIENT
    @app.route('/api/clients/<string:client_id>', methods=['GET'])
    def api_get_client(client_id):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        # Validation de base de l'ID
        if not client_id or client_id.strip() == '' or client_id in ['undefined', 'null']:
            return jsonify({"success": False, "message": "ID client invalide"}), 400

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête avec gestion des valeurs NULL
            cur.execute("""
                SELECT client_id, nom, telephone, telephone_secondaire, adresse, ville, pays
                FROM clients 
                WHERE client_id = %s
            """, (client_id.strip(),))
            
            row = cur.fetchone()
            cur.close()
            conn.close()

            if not row:
                return jsonify({"success": False, "message": "Client non trouvé"}), 404

            # Construction de l'objet client avec gestion des valeurs NULL
            client = {
                "client_id": row[0],
                "nom": row[1] or "",
                "telephone": row[2] or "",
                "telephone_secondaire": row[3] or "",
                "adresse": row[4] or "",
                "ville": row[5] or "",
                "pays": row[6] or "Cameroun"
            }

            return jsonify({"success": True, "client": client})
            
        except psycopg2.Error as e:
            print(f"❌ Erreur base de données dans api_get_client: {e}")
            return jsonify({"success": False, "message": "Erreur de base de données"}), 500
        except Exception as e:
            print(f"❌ Erreur générale dans api_get_client: {e}")
            return jsonify({"success": False, "message": f"Erreur serveur: {str(e)}"}), 500

    # MODIFIER CLIENT
    @app.route('/api/clients/<client_id>', methods=['PUT'])
    def api_update_client(client_id):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        # Validation de l'ID client
        if not client_id or client_id.strip() == '' or client_id in ['undefined', 'null']:
            return jsonify({"success": False, "message": "ID client invalide"}), 400

        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "message": "Données manquantes"}), 400

            # Validation des champs obligatoires
            required_fields = ['nom', 'telephone', 'ville', 'pays', 'adresse']
            missing_fields = []
            
            for field in required_fields:
                if not data.get(field) or not str(data[field]).strip():
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    "success": False, 
                    "message": f"Champs manquants ou vides: {', '.join(missing_fields)}"
                }), 400

            # Validation téléphone principal (obligatoire)
            raw_phone = str(data['telephone']).strip()
            if len(raw_phone) < 8:
                return jsonify({
                    "success": False, 
                    "message": "Le numéro de téléphone principal doit contenir au moins 8 chiffres"
                }), 400

            # Normalisation téléphone principal
            clean_phone = clean_phone_number_simple(data['telephone'])
            if not clean_phone:
                return jsonify({
                    "success": False, 
                    "message": "Format du numéro de téléphone principal invalide"
                }), 400

            # CORRECTION TÉLÉPHONE SECONDAIRE : Validation SEULEMENT si fourni et significatif
            clean_phone_secondary = ""
            secondary_phone_raw = data.get('telephone_secondaire', '').strip()
            
            if secondary_phone_raw:  # Seulement si réellement fourni
                # Vérifier qu'il y a plus que juste l'indicatif
                digits_only = re.sub(r'\D', '', secondary_phone_raw)
                if len(digits_only) >= 8:  # Au moins 8 chiffres
                    clean_phone_secondary = clean_phone_number_simple(secondary_phone_raw)
                    if not clean_phone_secondary:
                        return jsonify({
                            "success": False, 
                            "message": "Format du numéro de téléphone secondaire invalide"
                        }), 400

            conn = get_db_connection()
            cur = conn.cursor()

            # Vérifier si le client existe
            cur.execute("SELECT client_id FROM clients WHERE client_id = %s", [client_id.strip()])
            if not cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Client non trouvé"}), 404

            # Vérifier doublon téléphone principal (exclure le client courant)
            cur.execute("""
                SELECT client_id, nom FROM clients
                WHERE (telephone = %s OR telephone_secondaire = %s) AND client_id != %s
            """, (clean_phone, clean_phone, client_id.strip()))
            duplicate = cur.fetchone()
            if duplicate:
                cur.close()
                conn.close()
                return jsonify({
                    "success": False, 
                    "message": f"Le numéro {clean_phone} est déjà utilisé par un autre client: {duplicate[1]}"
                }), 409

            # Vérifier doublon téléphone secondaire (SEULEMENT si fourni)
            if clean_phone_secondary:
                cur.execute("""
                    SELECT client_id, nom FROM clients
                    WHERE (telephone = %s OR telephone_secondaire = %s) AND client_id != %s
                """, (clean_phone_secondary, clean_phone_secondary, client_id.strip()))
                duplicate = cur.fetchone()
                if duplicate:
                    cur.close()
                    conn.close()
                    return jsonify({
                        "success": False, 
                        "message": f"Le numéro secondaire {clean_phone_secondary} est déjà utilisé par un autre client: {duplicate[1]}"
                    }), 409

            # Mettre à jour le client
            cur.execute("""
                UPDATE clients
                SET nom = %s, telephone = %s, telephone_secondaire = %s,
                    adresse = %s, ville = %s, pays = %s, updated_at = CURRENT_TIMESTAMP
                WHERE client_id = %s
            """, (
                data['nom'].strip(),
                clean_phone,
                clean_phone_secondary if clean_phone_secondary else None,  # NULL si vide
                data['adresse'].strip(),
                data['ville'].strip(),
                data['pays'].strip(),
                client_id.strip()
            ))

            if cur.rowcount == 0:
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Aucune modification effectuée"}), 400

            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({"success": True, "message": "Client mis à jour avec succès"})

        except psycopg2.Error as e:
            if 'conn' in locals():
                conn.rollback()
                cur.close()
                conn.close()
            print(f"❌ Erreur base de données dans api_update_client: {e}")
            return jsonify({"success": False, "message": "Erreur de base de données"}), 500
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cur.close() 
                conn.close()
            print(f"❌ Erreur générale dans api_update_client: {e}")
            return jsonify({"success": False, "message": f"Erreur serveur: {str(e)}"}), 500
    
    # SUPPRIMER CLIENT
    @app.route('/api/clients/<client_id>', methods=['DELETE'])
    def api_delete_client(client_id):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("SELECT client_id FROM clients WHERE client_id = %s", [client_id])
            if not cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Client non trouvé"}), 404

            cur.execute("SELECT COUNT(*) FROM factures WHERE client_id = %s", [client_id])
            nb_factures = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM proformas WHERE client_id = %s", [client_id])
            nb_proformas = cur.fetchone()[0]

            if nb_factures > 0 or nb_proformas > 0:
                cur.close()
                conn.close()
                return jsonify({
                    "success": False, 
                    "message": f"Impossible de supprimer: le client a {nb_factures} facture(s) et {nb_proformas} proforma(s) associée(s)"
                }), 400

            cur.execute("DELETE FROM clients WHERE client_id = %s", [client_id])
            rows_affected = cur.rowcount
            
            if rows_affected == 0:
                cur.close()
                conn.close()
                return jsonify({"success": False, "message": "Aucun client supprimé"}), 404
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({"success": True, "message": "Client supprimé avec succès"})

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cur.close()
                conn.close()
            return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500

    # HISTORIQUE COMMANDES
    @app.route('/api/clients/<client_id>/history')
    def api_client_history(client_id):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Vérifier si le client existe
            cur.execute("SELECT nom FROM clients WHERE client_id = %s", [client_id])
            client_row = cur.fetchone()
            if not client_row:
                return jsonify({"success": False, "message": "Client non trouvé"}), 404

            cur.execute("""
                SELECT ch.historique_id, ch.code_commande, ch.date_commande, 
                    ch.montant_total, ch.statut
                FROM commandes_historique ch
                WHERE ch.client_id = %s
                ORDER BY ch.date_commande DESC NULLS LAST
            """, [client_id])

            commandes = cur.fetchall()
            history = []

            for c in commandes:
                historique_id, code_commande, date_commande, montant_total, statut = c

                # Formatage date
                date_str = date_commande.strftime('%d/%m/%Y') if date_commande else "Non renseignée"

                # RÉCUPÉRER LES VRAIS ARTICLES PARSÉS
                cur.execute("""
                    SELECT cah.article_designation, cah.quantite, cah.prix_unitaire
                    FROM commandes_articles_historique cah
                    WHERE cah.historique_id = %s
                """, [historique_id])

                articles_rows = cur.fetchall()
                articles = []

                for row in articles_rows:
                    designation, quantite, prix_unitaire = row
                    articles.append({
                        "nom": designation,  # Juste la désignation : "Class 2", "Form 2", etc.
                        "quantite": quantite,
                        "prix": ""  # Vide = pas d'affichage du prix
                    })

                # Si aucun article (ne devrait plus arriver)
                if not articles:
                    articles.append({
                        "nom": "Commande sans détail",
                        "quantite": 1,
                        "prix": f"{montant_total:,} FCFA".replace(',', ' ')
                    })

                history.append({
                    "date": date_str,
                    "code": code_commande,
                    "montant": f"{montant_total:,} FCFA".replace(',', ' '),
                    "status": statut or "termine",
                    "ville": "Cameroun",
                    "articles": articles
                })

            return jsonify({
                "success": True, 
                "client_nom": client_row[0], 
                "history": history
            })

        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            cur.close()
            conn.close()
        
    # EXPORT DE LA LISTE DES CLIENTS
    @app.route('/api/export/clients')
    def api_export_clients():
        """Exporter les clients en CSV"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            # Paramètres de filtrage
            search = request.args.get('search', '')
            ville_filter = request.args.get('ville', '')
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Construction de la requête
            query = """
                SELECT c.nom, c.telephone, c.telephone_secondaire,
                    c.adresse, c.ville, c.pays,
                    COALESCE(COUNT(f.facture_id), 0) AS nb_commandes,
                    COALESCE(SUM(f.montant_total), 0) AS montant_total_paye
                FROM clients c
                LEFT JOIN factures f ON f.client_id = c.client_id
                WHERE 1=1
            """
            params = []
            
            if search:
                query += " AND (LOWER(c.nom) LIKE LOWER(%s) OR c.telephone LIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])
                
            if ville_filter:
                query += " AND c.ville = %s"
                params.append(ville_filter)
            
            query += " GROUP BY c.client_id ORDER BY c.nom"
            
            cur.execute(query, params)
            clients = cur.fetchall()
            
            # Créer le CSV
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # En-têtes
            writer.writerow([
                'Nom', 'Téléphone Principal', 'Téléphone Secondaire', 
                'Adresse', 'Ville', 'Pays', 'Nb Commandes', 'Total Versements (FCFA)'
            ])
            
            # Données
            for c in clients:
                writer.writerow([
                    c[0] or "Non renseigné",
                    c[1] or "-",
                    c[2] or "-",
                    c[3] or "-", 
                    c[4] or "-",
                    c[5] or "-",
                    c[6],
                    f"{int(c[7]):,}".replace(',', ' ') if c[7] else "0"
                ])
            
            cur.close()
            conn.close()
            
            # Préparer la réponse
            output.seek(0)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=clients_export_{datetime.now().strftime("%Y%m%d")}.csv'
            
            return response
            
        except Exception as e:
            print(f"Erreur api_export_clients: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500


    @app.route('/ventes')
    def ventes():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return render_template('ventes.html')

    @app.route('/rapports')
    def rapports():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return render_template('rapports.html')

    @app.route('/bug')
    def bug():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return render_template('bug.html')

    @app.route('/aide')
    def aide():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return render_template('aide.html')

    # ROUTE POUR CATALOGUE
    @app.route('/catalogue')
    def catalogue():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        try:
            # Calculer les KPIs pour le catalogue
            kpi_data = get_catalogue_kpi_data()
            
            # Calculer les tendances vs mois précédent
            kpi_trends = calculate_catalogue_kpi_trends()
            
            return render_template('catalogue.html',
                # KPIs avec formatage
                kpi_total_articles=format_number(kpi_data['total_articles']),
                kpi_total_articles_trend=kpi_trends['total_articles'],
                kpi_articles_populaires=kpi_data['articles_populaires'],
                kpi_articles_populaires_trend=kpi_trends['articles_populaires'],
                kpi_ca_catalogue=format_currency(kpi_data['ca_catalogue']),
                kpi_ca_catalogue_trend=kpi_trends['ca_catalogue'],
                kpi_prestations_actives=kpi_data['prestations_actives'],
                kpi_prestations_actives_trend=kpi_trends['prestations_actives']
            )
            
        except Exception as e:
            print(f"❌ Erreur catalogue: {e}")
            flash(f"Erreur lors de la récupération des données: {str(e)}", "error")
            return redirect(url_for('dashboard'))
    
    @app.route('/api/catalogue/monthly-evolution')
    def api_catalogue_monthly_evolution():
        """Récupérer l'évolution mensuelle des articles vendus et CA généré"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Date actuelle - mois en cours
            now = datetime.now()
            
            # Période étendue pour capturer toutes les données existantes et futures
            start_date = now.replace(day=1).date()
            end_date = (now + relativedelta(months=12)).date()
            
            print(f"🔍 DEBUG MONTHLY EVOLUTION - Période future: {start_date} à {end_date}")
            
            cur.execute("""
                WITH monthly_stats AS (
                    SELECT 
                        EXTRACT(YEAR FROM p.date_creation) as year,
                        EXTRACT(MONTH FROM p.date_creation) as month,
                        SUM(pa.quantite) as total_quantity,
                        SUM(pa.quantite * a.prix) as total_revenue
                    FROM proformas p
                    JOIN proforma_articles pa ON pa.proforma_id = p.proforma_id
                    JOIN articles a ON a.article_id = pa.article_id
                    
                    WHERE p.date_creation >= %s 
                    AND p.date_creation <= %s
                    AND p.etat = 'termine'
                    AND p.ville = %s
                    AND p.cree_par = %s
                    GROUP BY EXTRACT(YEAR FROM p.date_creation), EXTRACT(MONTH FROM p.date_creation)
                    ORDER BY year, month
                )
                SELECT year, month, total_quantity, total_revenue FROM monthly_stats
            """, [start_date, end_date, ville, user_id])

            results = cur.fetchall()
            print(f"🔍 DEBUG API - Résultats trouvés: {len(results)} mois avec données")
            print(f"🔍 DEBUG API - Raw results: {results}")
            
            # NOUVELLE LOGIQUE : Générer 12 mois à partir du mois actuel
            labels = []
            quantities = []
            revenues = []
            
            # Créer le dictionnaire des données par (année, mois)
            monthly_data = {(int(row[0]), int(row[1])): (row[2], row[3]) for row in results}
            
            # COMMENCER DU MOIS ACTUEL ET S'INCRÉMENTER
            current_date = now.replace(day=1)  # Premier jour du mois actuel
            
            for i in range(12):
                year = current_date.year
                month = current_date.month
                
                # LABELS AVEC ANNÉE
                month_names = {
                    1: 'Janv', 2: 'Févr', 3: 'Mars', 4: 'Avr', 5: 'Mai', 6: 'Juin',
                    7: 'Juil', 8: 'Août', 9: 'Sept', 10: 'Oct', 11: 'Nov', 12: 'Déc'
                }
                
                labels.append(f"{month_names[month]} {year}")
                
                # Récupérer les données pour ce mois ou 0 par défaut
                data = monthly_data.get((year, month), (0, 0))
                quantities.append(int(data[0]) if data[0] else 0)
                revenues.append(int(data[1]) if data[1] else 0)
                
                # ✅ PASSER AU MOIS SUIVANT
                current_date = current_date + relativedelta(months=1)
            
            cur.close()
            conn.close()
            
            print(f"🔍 DEBUG MONTHLY - Final Labels: {labels}")
            print(f"🔍 DEBUG MONTHLY - Final Quantities: {quantities}")
            print(f"🔍 DEBUG MONTHLY - Final Revenues: {revenues}")
            
            return jsonify({
                "success": True,
                "labels": labels,
                "quantities": quantities,
                "revenues": revenues,
                "has_data": sum(quantities) > 0
            })
            
        except Exception as e:
            print(f"❌ Erreur api_catalogue_monthly_evolution: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
        
    @app.route('/api/catalogue/top-prestations')
    def api_catalogue_top_prestations():
        """Récupérer la répartition par catégorie"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            ville = session['ville']
            user_id = session['user_id']
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            mois_actuel_debut = datetime.now().replace(day=1).date()
            mois_actuel_fin = datetime.now().date()
            
            cur.execute("""
                SELECT 
                    a.type_article,
                    SUM(pa.quantite) as total_quantity,
                    SUM(pa.quantite * a.prix) as total_revenue
                FROM proformas p
                JOIN proforma_articles pa ON pa.proforma_id = p.proforma_id
                JOIN articles a ON a.article_id = pa.article_id
                WHERE p.date_creation >= %s 
                AND p.date_creation <= %s
                AND p.etat = 'termine'
                AND p.ville = %s
                AND p.cree_par = %s
                GROUP BY a.type_article
                ORDER BY total_quantity DESC
            """, [mois_actuel_debut, mois_actuel_fin, ville, user_id])
            
            results = cur.fetchall()
            
            if not results:
                cur.close()
                conn.close()
                return jsonify({
                    "success": True,
                    "prestations": [],
                    "total_ca": 0,
                    "has_data": False
                })
            
            total_quantity = sum(row[1] for row in results)
            total_ca = sum(row[2] for row in results)
            
            prestations = []
            for row in results:
                type_article, quantity, revenue = row
                percentage = round((quantity / total_quantity) * 100, 1) if total_quantity > 0 else 0
                
                # Conversion directe BD → Français
                if type_article.endswith('s'):
                    nom_francais = type_article.title()
                else:
                    nom_francais = type_article.title() + 's'
                
                prestations.append({
                    "designation": nom_francais,
                    "quantity": int(quantity),
                    "revenue": int(revenue),
                    "percentage": percentage
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "prestations": prestations,
                "total_ca": int(total_ca),
                "has_data": len(prestations) > 0
            })
            
        except Exception as e:
            print(f"❌ Erreur api_catalogue_top_prestations: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
    
    @app.route('/api/articles')
    def api_articles():
        """Récupérer la liste des articles avec filtres"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            page = request.args.get('page', 1, type=int)
            per_page = 10
            search = request.args.get('search', '').strip()
            article_type = request.args.get('type', '').strip()
            ville = request.args.get('ville', '').strip()

            conn = get_db_connection()
            cur = conn.cursor()

            # Requête de base avec jointures pour les statistiques
            query = """
                SELECT 
                    a.article_id,
                    a.code,
                    a.designation,
                    a.prix,
                    a.type_article,
                    a.nature,
                    a.classe,
                    COALESCE(pv.ville, '') as ville,
                    COUNT(DISTINCT pa.proforma_id) as nb_commandes,
                    SUM(pa.quantite * a.prix) as montant_total
                FROM articles a
                LEFT JOIN proforma_articles pa ON pa.article_id = a.article_id
                LEFT JOIN proformas p ON p.proforma_id = pa.proforma_id AND p.etat = 'termine'
                LEFT JOIN prix_fournitures_ville pv ON pv.article_id = a.article_id
                WHERE 1=1
            """

            params = []

            # Filtre de recherche
            if search:
                query += " AND a.designation ILIKE %s"
                params.append(f"%{search}%")

            # Filtre de nature 
            if article_type == 'livre' and request.args.get('nature'):
                query += " AND a.nature = %s"
                params.append(request.args.get('nature'))
    
            # Filtre par type
            if article_type:
                # Modification pour les services
                if article_type == 'service':
                    query += " AND a.type_article = 'service'"
                else:
                    query += " AND a.type_article = %s"
                    params.append(article_type)

            # Filtre par ville (uniquement pour les fournitures)
            if article_type == 'fourniture' and ville:
                # Modification pour le filtrage par ville
                query += " AND (pv.ville = %s OR pv.ville IS NULL)"
                params.append(ville)

            # Group by et pagination
            query += """
                GROUP BY a.article_id, a.code, a.designation, a.prix, a.type_article, a.nature, a.classe, pv.ville
                ORDER BY a.designation
                LIMIT %s OFFSET %s
            """
            params.extend([per_page, (page - 1) * per_page])

            cur.execute(query, params)
            articles = cur.fetchall()

            # Compter le total pour la pagination
            count_query = """
                SELECT COUNT(DISTINCT a.article_id)
                FROM articles a
                LEFT JOIN prix_fournitures_ville pv ON pv.article_id = a.article_id
                WHERE 1=1
            """
            count_params = []

            if search:
                count_query += " AND a.designation ILIKE %s"
                count_params.append(f"%{search}%")

            if article_type:
                # Même logique que pour la requête principale
                if article_type == 'service':
                    count_query += " AND a.type_article = 'service'"
                else:
                    count_query += " AND a.type_article = %s"
                    count_params.append(article_type)

            if article_type == 'fourniture' and ville:
                count_query += " AND (pv.ville = %s OR pv.ville IS NULL)"
                count_params.append(ville)

            cur.execute(count_query, count_params)
            total_count = cur.fetchone()[0]
            total_pages = (total_count + per_page - 1) // per_page

            cur.close()
            conn.close()

            # Formater les résultats
            articles_list = []
            for article in articles:
                articles_list.append({
                    "article_id": article[0],
                    "code": article[1],
                    "designation": article[2],
                    "prix": article[3],
                    "type_article": article[4],
                    "nature": article[5],
                    "classe": article[6],
                    "ville": article[7],
                    "nb_commandes": article[8],
                    "montant_total": article[9] or 0
                })

            return jsonify({
                "success": True,
                "articles": articles_list,
                "total_pages": total_pages,
                "current_page": page
            })

        except Exception as e:
            print(f"Erreur api_articles: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route('/api/articles/<int:article_id>', methods=['PUT'])
    def update_article(article_id):
        """Mettre à jour un article"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            data = request.get_json()
            required_fields = ['designation', 'code', 'prix', 'type_article']
            
            # Validation des champs obligatoires
            for field in required_fields:
                if not data.get(field):
                    return jsonify({"success": False, "message": f"Le champ {field} est obligatoire"}), 400

            conn = get_db_connection()
            cur = conn.cursor()

            # Mise à jour de l'article
            update_query = """
                UPDATE articles 
                SET designation = %s,
                    code = %s,
                    prix = %s,
                    type_article = %s,
                    nature = %s,
                    classe = %s
                WHERE article_id = %s
                RETURNING *
            """
            update_params = [
                data['designation'],
                data['code'],
                data['prix'],
                data['type_article'],
                data.get('nature'),
                data.get('classe'),
                article_id
            ]

            cur.execute(update_query, update_params)
            updated_article = cur.fetchone()

            # Pour les fournitures, mettre à jour le prix par ville
            if data['type_article'] == 'fourniture' and data.get('ville'):
                # Supprimer d'abord les anciennes entrées
                cur.execute("DELETE FROM prix_fournitures_ville WHERE article_id = %s", [article_id])
                
                # Ajouter le nouveau prix pour la ville
                insert_query = """
                    INSERT INTO prix_fournitures_ville (article_id, ville, prix)
                    VALUES (%s, %s, %s)
                """
                cur.execute(insert_query, [article_id, data['ville'], data['prix']])

            conn.commit()
            cur.close()
            conn.close()

            if not updated_article:
                return jsonify({"success": False, "message": "Article non trouvé"}), 404

            return jsonify({
                "success": True,
                "message": "Article mis à jour avec succès"
            })

        except Exception as e:
            print(f"Erreur update_article: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route('/api/articles/<int:article_id>', methods=['DELETE'])
    def delete_article(article_id):
        """Supprimer un article"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Vérifier si l'article est utilisé dans des commandes
            cur.execute("""
                SELECT COUNT(*) FROM proforma_articles 
                WHERE article_id = %s
            """, [article_id])
            count = cur.fetchone()[0]

            if count > 0:
                return jsonify({
                    "success": False,
                    "message": "Impossible de supprimer cet article car il est associé à des commandes"
                }), 400

            # Supprimer les prix par ville d'abord
            cur.execute("DELETE FROM prix_fournitures_ville WHERE article_id = %s", [article_id])

            # Puis supprimer l'article
            cur.execute("DELETE FROM articles WHERE article_id = %s RETURNING article_id", [article_id])
            deleted = cur.fetchone()

            conn.commit()
            cur.close()
            conn.close()

            if not deleted:
                return jsonify({"success": False, "message": "Article non trouvé"}), 404

            return jsonify({
                "success": True,
                "message": "Article supprimé avec succès"
            })

        except Exception as e:
            print(f"Erreur delete_article: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route('/api/export/articles')
    def export_articles():
        """Exporter les articles en CSV"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            search = request.args.get('search', '').strip()
            article_type = request.args.get('type', '').strip()
            ville = request.args.get('ville', '').strip()

            conn = get_db_connection()
            cur = conn.cursor()

            # Requête similaire à api_articles mais sans pagination
            query = """
                SELECT 
                    a.article_id,
                    a.code,
                    a.designation,
                    a.prix,
                    a.type_article,
                    a.nature,
                    a.classe,
                    COALESCE(pv.ville, '') as ville,
                    COUNT(DISTINCT pa.proforma_id) as nb_commandes,
                    SUM(pa.quantite * a.prix) as montant_total
                FROM articles a
                LEFT JOIN proforma_articles pa ON pa.article_id = a.article_id
                LEFT JOIN proformas p ON p.proforma_id = pa.proforma_id AND p.etat = 'termine'
                LEFT JOIN prix_fournitures_ville pv ON pv.article_id = a.article_id
                WHERE 1=1
            """

            params = []

            if search:
                query += " AND a.designation ILIKE %s"
                params.append(f"%{search}%")

            if article_type:
                query += " AND a.type_article = %s"
                params.append(article_type)

            if article_type == 'fourniture' and ville:
                query += " AND pv.ville = %s"
                params.append(ville)

            query += """
                GROUP BY a.article_id, a.code, a.designation, a.prix, a.type_article, a.nature, a.classe, pv.ville
                ORDER BY a.designation
            """

            cur.execute(query, params)
            articles = cur.fetchall()

            cur.close()
            conn.close()

            # Créer le CSV en mémoire
            output = io.StringIO()
            writer = csv.writer(output)
            
            # En-têtes en fonction du type
            if not article_type or article_type == 'livre':
                headers = ["ID", "Code", "Désignation", "Prix (FCFA)", "Type", "Classe", "Commandes", "Montant total"]
            elif article_type == 'fourniture':
                headers = ["ID", "Code", "Désignation", "Prix (FCFA)", "Ville", "Commandes", "Montant total"]
            elif article_type == 'formation':
                headers = ["ID", "Code", "Désignation", "Souscrits", "Montant total"]
            elif article_type == 'service':
                headers = ["ID", "Code", "Désignation", "Souscrits", "Commandes", "Montant total"]
            
            writer.writerow(headers)

            # Écrire les données
            for article in articles:
                if not article_type or article_type == 'livre':
                    row = [
                        article[0], article[1], article[2], article[3],
                        article[4], article[6] or '', article[8], article[9] or 0
                    ]
                elif article_type == 'fourniture':
                    row = [
                        article[0], article[1], article[2], article[3],
                        article[7] or '', article[8], article[9] or 0
                    ]
                elif article_type == 'formation':
                    row = [
                        article[0], article[1], article[2], 
                        article[8], article[9] or 0
                    ]
                elif article_type == 'service':
                    row = [
                        article[0], article[1], article[2], 
                        article[8], article[8], article[9] or 0
                    ]
                
                writer.writerow(row)

            # Créer la réponse avec le CSV
            response = make_response(output.getvalue())
            response.headers['Content-Disposition'] = 'attachment; filename=articles.csv'
            response.headers['Content-type'] = 'text/csv'
            return response

        except Exception as e:
            print(f"Erreur export_articles: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
