 # Flask core
from flask import (
    render_template, redirect, url_for, request,
    session, flash, jsonify, send_file, current_app, make_response, g, abort
)

# Python standard library
import json
import re, hashlib
import math
import time
import uuid
import time
import csv
import random
import string
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
import io
import csv
from typing import Optional
from datetime import timezone

# Database & SQL
import psycopg2
from psycopg2 import sql
from sqlalchemy import func, and_, or_, extract

# External libraries
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
import pandas as pd

from dateutil.relativedelta import relativedelta
import calendar

from flask_mail import Mail, Message
import os

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

# === Helper functions c===
def format_currency(amount):
    if amount == 0 or amount is None:
        return "0 FCFA"
    formatted = f"{int(float(amount)):,}".replace(',', ' ')
    return formatted + " FCFA"

def format_number(number):
    if number == 0:
        return "0"
    return f"{int(number):,}".replace(',', ' ')

# log_action
def log_action(action, cible_type, cible_id, payload_avant=None, payload_apres=None):
    # TODO: implement proper logging
    print(f"[LOG] {action} {cible_type} {cible_id}")

def init_admin_routes(flask_app, database, models, mail_instance):
    """Initialiser les routes avec les objets Flask et SQLAlchemy"""
    global app, db, Utilisateur, Proforma, Client, Article, ProformaArticle
    global PrixFournituresVille, ClassesManuels, Facture, FactureArticle, mail
    
    app = flask_app
    db = database
    mail = mail_instance 
    Utilisateur = models.get('Utilisateur')
    Proforma = models.get('Proforma')
    Client = models.get('Client')
    Article = models.get('Article')
    ProformaArticle = models.get('ProformaArticle')
    PrixFournituresVille = models.get('PrixFournituresVille')
    ClassesManuels = models.get('ClassesManuels')
    Facture = models.get('Facture')
    FactureArticle = models.get('FactureArticle')
    
    # === FONCTION UTILITAIRE : CONNEXION BD ===
    def get_db_connection():
        conn = psycopg2.connect(current_app.config['SQLALCHEMY_DATABASE_URI'])
        return conn

    # --- helper simple ---
    def _require_admin():
        if "user_id" not in session:
            return None, redirect(url_for("login"))
        role = (session.get("role") or "").strip().lower()
        if role not in ("admin", "superadmin"):
            return None, abort(403)
        user = Utilisateur.query.get(session["user_id"])
        if not user:
            return None, abort(404)
        return user, None
    
    
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

    @app.route("/admin/dashboard", methods=["GET"])
    def my_admin_dashboard():
        user, resp = _require_admin()
        if resp: return resp
        
        # Éviter les erreurs SQLAlchemy en utilisant des requêtes SQL directes
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Compter les clients directement avec SQL
            cur.execute("SELECT COUNT(*) FROM clients")
            nb_clients = cur.fetchone()[0] or 0
            
            # Compter les proformas
            cur.execute("SELECT COUNT(*) FROM proformas")
            nb_proformas = cur.fetchone()[0] or 0
            
            # Compter les articles
            cur.execute("SELECT COUNT(*) FROM articles")
            nb_articles = cur.fetchone()[0] or 0
            
            conn.close()
            
            kpis = {
                "nb_clients": nb_clients,
                "nb_proformas": nb_proformas,
                "nb_articles": nb_articles,
            }
        except Exception as e:
            print(f"Erreur lors du calcul des KPIs basiques: {e}")
            # Valeurs par défaut en cas d'erreur
            kpis = {
                "nb_clients": 0,
                "nb_proformas": 0,
                "nb_articles": 0,
            }
        
        # on passe explicitement 'admin' pour le template
        return render_template("dashboard_admin.html", admin=user, kpis=kpis)

    @app.route('/admin/api/dashboard/kpis', methods=['GET'])
    def admin_api_dashboard_kpis():
        """API pour récupérer les KPIs du dashboard avec tendances"""
        user, resp = _require_admin()
        if resp: return resp
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Calculer les KPIs pour le mois actuel (sans filtres = global)
            current_month = datetime.now().month
            current_year = datetime.now().year
            previous_month = current_month - 1 if current_month > 1 else 12
            previous_year = current_year if current_month > 1 else current_year - 1
            
            # KPIs du mois actuel (global)
            kpis_current = calculate_reporting_kpis(cur, {})
            
            # KPIs du mois précédent (global)
            kpis_previous = calculate_reporting_kpis(cur, {
                'annee': str(previous_year),
                'mois': str(previous_month)
            })
            
            conn.close()
            
            return jsonify({
                'success': True,
                'kpis': {
                    'ca': kpis_current['ca'],
                    'ca_last_month': kpis_previous['ca'],
                    'ventes': kpis_current['ventes'],
                    'ventes_last_month': kpis_previous['ventes'],
                    'articles': kpis_current['articles'],
                    'articles_last_month': kpis_previous['articles'],
                    'clients': kpis_current['nouveaux_clients'],
                    'clients_last_month': kpis_previous['nouveaux_clients']
                }
            })
            
        except Exception as e:
            print(f"Erreur lors du calcul des KPIs dashboard: {e}")
            return jsonify({
                'success': False,
                'message': 'Erreur lors du calcul des KPIs',
                'error': str(e)
            }), 500

    # ========== FONCTIONS UTILITAIRES POUR CATALOGUE/PRESTATION ==========
    
    def get_admin_catalogue_kpi_data():
        """Calculer les KPIs globaux pour le catalogue/prestation (vue admin)"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 1. Total Articles du CATALOGUE uniquement (vue globale)
            cur.execute("""
                SELECT COUNT(*) 
                FROM articles 
                WHERE code NOT LIKE 'ART%' 
                OR code IS NULL
            """)
            total_articles = cur.fetchone()[0] or 0
            print(f"DEBUG ADMIN CA - Total articles CATALOGUE: {total_articles}")
            
            # 2. Article le plus populaire (vue globale - toutes les villes, toutes les périodes)
            cur.execute("""
                SELECT a.designation
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                JOIN proformas p ON p.proforma_id = pa.proforma_id
                WHERE p.etat = 'termine'
                GROUP BY pa.article_id, a.designation
                ORDER BY SUM(pa.quantite) DESC
                LIMIT 1
            """)
            
            result = cur.fetchone()
            articles_populaires = result[0] if result else "Aucun"
            print(f"DEBUG ADMIN CA - Article populaire: {articles_populaires}")
            
            # 3. CA Catalogue GLOBAL (toutes les villes, toutes les périodes) - comme dans repertoire_admin.py
            cur.execute("""
                WITH proformas_ca AS (
                    SELECT 
                        COALESCE((SELECT SUM(pa.quantite * a.prix)
                                  FROM proforma_articles pa
                                  JOIN articles a ON a.article_id = pa.article_id
                                  WHERE pa.proforma_id = p.proforma_id), 0)
                        + COALESCE(p.frais,0) - COALESCE(p.remise,0) AS total
                    FROM proformas p
                    WHERE p.etat IN ('termine','terminé','partiel')
                ), factures_ca AS (
                    SELECT COALESCE(f.montant_total,0) AS total
                    FROM factures f
                    WHERE f.statut IN ('termine','terminé','partiel')
                )
                SELECT SUM(total) FROM (
                    SELECT total FROM proformas_ca
                    UNION ALL
                    SELECT total FROM factures_ca
                ) AS union_ca
            """)
            
            ca_catalogue = cur.fetchone()[0] or 0
            print(f"DEBUG ADMIN CA - CA total global: {ca_catalogue} FCFA")
            
            # 4. Prestation la plus active (vue globale, toutes les périodes)
            cur.execute("""
                SELECT a.type_article
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                JOIN proformas p ON p.proforma_id = pa.proforma_id
                WHERE p.etat = 'termine'
                GROUP BY a.type_article
                ORDER BY SUM(pa.quantite) DESC
                LIMIT 1
            """)
            
            result = cur.fetchone()
            if result:
                type_article = result[0]
                prestations_actives = type_article.title() + 's' if type_article and not type_article.endswith('s') else (type_article.title() if type_article else "Aucune")
            else:
                prestations_actives = "Aucune"
            
            print(f"DEBUG ADMIN CA - Prestation active: {prestations_actives}")
            
            cur.close()
            conn.close()
            
            result = {
                "total_articles": total_articles,
                "articles_populaires": articles_populaires,
                "ca_catalogue": ca_catalogue,
                "prestations_actives": prestations_actives
            }
            
            print(f"DEBUG ADMIN CA - Résultat final: {result}")
            return result
            
        except Exception as e:
            print(f"ERREUR GLOBALE get_admin_catalogue_kpi_data: {e}")
            import traceback
            traceback.print_exc()
            return {
                "total_articles": 0,
                "articles_populaires": "Aucun",
                "ca_catalogue": 0,
                "prestations_actives": "Aucune"
            }


    # Onglet: Prestation
    @app.route("/admin/catalogue", methods=["GET"])
    def admin_catalogue():
        user, resp = _require_admin()
        if resp: return resp
        
        try:
            # Calculer les KPIs globaux pour le catalogue/prestation
            kpi_data = get_admin_catalogue_kpi_data()
            
            return render_template("prestation.html",
                # KPIs avec formatage (sans tendances)
                kpi_total_articles=format_number(kpi_data['total_articles']),
                kpi_articles_populaires=kpi_data['articles_populaires'],
                kpi_ca_catalogue=format_currency(kpi_data['ca_catalogue']),
                kpi_prestations_actives=kpi_data['prestations_actives']
            )
            
        except Exception as e:
            print(f"❌ Erreur admin_catalogue: {e}")
            flash(f"Erreur lors de la récupération des données: {str(e)}", "error")
            return redirect(url_for('my_admin_dashboard'))

    # ========== API CHARTS: CATALOGUE/PRESTATION ==========
    
    @app.route('/admin/api/catalogue/monthly-evolution', methods=['GET'])
    def admin_api_catalogue_monthly_evolution():
        """Récupérer l'évolution mensuelle des articles vendus et CA généré (vue globale admin)"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Période glissante 12 mois à partir du mois précédent (comme dashboard_secretaire.html)
            now = datetime.now()
            start_date = now.replace(day=1) - relativedelta(months=1)
            end_date = start_date + relativedelta(months=11) + relativedelta(day=31)
            
            print(f"🔍 DEBUG ADMIN MONTHLY EVOLUTION - Période glissante: {start_date.date()} à {end_date.date()}")
            
            # Requête globale (toutes les villes) avec détails par agence - INCLUANT FRAIS ET REMISES
            cur.execute("""
                WITH proforma_totals AS (
                    SELECT 
                        p.proforma_id,
                        EXTRACT(YEAR FROM p.date_creation) as year,
                        EXTRACT(MONTH FROM p.date_creation) as month,
                        p.ville,
                        SUM(pa.quantite) as total_quantity,
                        SUM(pa.quantite * a.prix) as articles_total,
                        COALESCE(p.frais, 0) as frais,
                        COALESCE(p.remise, 0) as remise
                    FROM proformas p
                    JOIN proforma_articles pa ON pa.proforma_id = p.proforma_id
                    JOIN articles a ON a.article_id = pa.article_id
                    WHERE p.date_creation >= %s 
                    AND p.date_creation <= %s
                    AND p.etat = 'termine'
                    GROUP BY p.proforma_id, EXTRACT(YEAR FROM p.date_creation), EXTRACT(MONTH FROM p.date_creation), p.ville, p.frais, p.remise
                ),
                monthly_stats AS (
                    SELECT 
                        year,
                        month,
                        ville,
                        SUM(total_quantity) as total_quantity,
                        SUM(articles_total + frais - remise) as total_revenue
                    FROM proforma_totals
                    GROUP BY year, month, ville
                    ORDER BY year, month, ville
                )
                SELECT year, month, ville, total_quantity, total_revenue FROM monthly_stats
            """, [start_date, end_date])

            results = cur.fetchall()
            print(f"🔍 DEBUG ADMIN API - Résultats trouvés: {len(results)} mois avec données")
            
            # Créer le dictionnaire des données par (année, mois, ville)
            monthly_data = {}
            for row in results:
                year, month, ville, quantity, revenue = row
                key = (int(year), int(month))
                if key not in monthly_data:
                    monthly_data[key] = {}
                monthly_data[key][ville] = (quantity, revenue)
            
            # Générer les labels et données pour la période glissante 12 mois
            labels = []
            quantities = []
            revenues = []
            agence_details = []  # Pour les tooltips
            
            current_date = start_date  # Utiliser la date de début calculée
            
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
                month_data = monthly_data.get((year, month), {})
                total_quantity = sum(data[0] for data in month_data.values())
                total_revenue = sum(data[1] for data in month_data.values())
                
                quantities.append(int(total_quantity) if total_quantity else 0)
                revenues.append(int(total_revenue) if total_revenue else 0)
                
                # Détails par agence pour le tooltip
                agence_details.append({
                    ville: {
                        "articles_vendus": int(data[0]) if data[0] else 0,
                        "chiffre_affaire": int(data[1]) if data[1] else 0
                    }
                    for ville, data in month_data.items()
                })
                
                # Passer au mois suivant
                current_date = current_date + relativedelta(months=1)
            
            cur.close()
            conn.close()
            
            print(f"🔍 DEBUG ADMIN MONTHLY - Final Labels: {labels}")
            print(f"🔍 DEBUG ADMIN MONTHLY - Final Quantities: {quantities}")
            print(f"🔍 DEBUG ADMIN MONTHLY - Final Revenues: {revenues}")
            
            return jsonify({
                "success": True,
                "labels": labels,
                "quantities": quantities,
                "revenues": revenues,
                "agence_details": agence_details,
                "has_data": sum(quantities) > 0
            })
            
        except Exception as e:
            print(f"❌ Erreur admin_api_catalogue_monthly_evolution: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    @app.route('/admin/api/catalogue/top-prestations', methods=['GET'])
    def admin_api_catalogue_top_prestations():
        """Récupérer la répartition par catégorie (vue globale admin)"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Vue globale - toutes les données depuis le début (pas de filtre de date) - INCLUANT FRAIS ET REMISES
            cur.execute("""
                WITH proforma_totals AS (
                SELECT 
                        p.proforma_id,
                    a.type_article,
                    SUM(pa.quantite) as total_quantity,
                        SUM(pa.quantite * a.prix) as articles_total,
                        COALESCE(p.frais, 0) as frais,
                        COALESCE(p.remise, 0) as remise
                FROM proformas p
                JOIN proforma_articles pa ON pa.proforma_id = p.proforma_id
                JOIN articles a ON a.article_id = pa.article_id
                    WHERE p.etat = 'termine'
                    GROUP BY p.proforma_id, a.type_article, p.frais, p.remise
                )
                SELECT 
                    type_article,
                    SUM(total_quantity) as total_quantity,
                    SUM(articles_total + frais - remise) as total_revenue
                FROM proforma_totals
                GROUP BY type_article
                ORDER BY total_quantity DESC
            """)
            
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
            print(f"❌ Erreur admin_api_catalogue_top_prestations: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500


    # AJOUT D'UN CLIENT
    @app.route('/admin/api/clients', methods=['POST'], endpoint='admin_api_add_client')
    def admin_api_add_client():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "message": "Données manquantes"}), 400

            # Validation des champs obligatoires avec messages spécifiques
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
            
            # Log global → création client
            try:
                log_action(action='create', cible_type='client', cible_id=client_id,
                           payload_avant=None, payload_apres={"nom": data.get('nom')})
            except Exception as _e:
                print(f"[NOTIF CREATE CLIENT WARN] {_e}")
            
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
    @app.route('/admin/api/clients/<string:client_id>', methods=['GET'], endpoint='admin_api_get_client')
    def admin_api_get_client(client_id):
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
    @app.route('/admin/api/clients/<client_id>', methods=['PUT'], endpoint='admin_api_update_client')
    def admin_api_update_client(client_id):
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
    @app.route('/admin/api/clients/<client_id>', methods=['DELETE'], endpoint='admin_api_delete_client')
    def admin_api_delete_client(client_id):
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
            
            # Log global → suppression client
            try:
                log_action(action='delete', cible_type='client', cible_id=client_id,
                           payload_avant=None, payload_apres=None)
            except Exception as _e:
                print(f"[NOTIF DELETE CLIENT WARN] {_e}")

            return jsonify({"success": True, "message": "Client supprimé avec succès"})

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cur.close()
                conn.close()
            return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500
    
    # HISTORIQUE COMMANDES
    @app.route('/admin/api/clients/<client_id>/history', methods=['GET'], endpoint='admin_api_client_history')
    def admin_api_client_history(client_id):
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

            # Récupérer les proformas ET les factures du client
            cur.execute("""
                SELECT 
                    'proforma' as type,
                    p.proforma_id as id,
                    p.date_creation as date,
                    p.etat as statut,
                    COALESCE(
                        (SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id), 0
                    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) as total_ttc
                FROM proformas p
                WHERE p.client_id = %s
                
                UNION ALL
                
                SELECT 
                    'facture' as type,
                    f.facture_id as id,
                    f.date_facture as date,
                    f.statut,
                    f.montant_total as total_ttc
                FROM factures f
                WHERE f.client_id = %s
                
                ORDER BY date DESC, id DESC
                LIMIT 50
            """, [client_id, client_id])

            proformas = cur.fetchall()
            history = []

            valid_statuses = ['en_attente', 'en_cours', 'partiel', 'termine', 'terminé']

            for p in proformas:
                type_commande, id_commande, date_commande, statut_brut, total_ttc = p

                # Normalisation des statuts
                if statut_brut is None or statut_brut == '' or str(statut_brut).strip() == '':
                    status_final = 'termine'
                elif statut_brut.strip().lower() in ['termine', 'terminé', 'terminee', 'terminée']:
                    status_final = 'terminé'
                elif statut_brut.strip() in valid_statuses:
                    status_final = statut_brut.strip()
                else:
                    status_final = 'termine'

                # Formatage date
                date_str = date_commande.strftime('%d/%m/%Y') if date_commande else "Date inconnue"

                # Récupérer les articles selon le type de commande
                articles = []
                if type_commande == 'proforma':
                    # Récupérer les articles de la proforma
                    cur.execute("""
                        SELECT a.designation, pa.quantite, a.prix
                        FROM proforma_articles pa
                        JOIN articles a ON a.article_id = pa.article_id
                        WHERE pa.proforma_id = %s
                        ORDER BY a.designation
                    """, [id_commande])

                    articles_rows = cur.fetchall()
                    for row in articles_rows:
                        designation, quantite, prix = row
                        articles.append({
                            "nom": designation,
                            "quantite": quantite,
                            "prix": prix
                        })
                else:
                    # Récupérer les articles de la facture
                    cur.execute("""
                        SELECT a.designation, fa.quantite, fa.prix_unitaire
                        FROM facture_articles fa
                        JOIN articles a ON a.article_id = fa.article_id
                        WHERE fa.facture_id = %s
                        ORDER BY a.designation
                    """, [id_commande])

                    articles_rows = cur.fetchall()
                    for row in articles_rows:
                        designation, quantite, prix = row
                        articles.append({
                            "nom": designation,
                            "quantite": quantite,
                            "prix": prix
                        })

                # Si aucun article trouvé, afficher "Commande sans détail"
                if not articles:
                    articles.append({
                        "nom": "Commande sans détail",
                        "quantite": 1,
                        "prix": 0
                    })

                # Calcul du montant avec fallback
                montant = total_ttc if total_ttc and total_ttc > 0 else 0

                # Générer le code selon le type
                if type_commande == 'proforma':
                    code = f"PRO{id_commande:05d}"
                else:
                    code = f"FAC{id_commande:05d}"

                history.append({
                    "date": date_str,
                    "code": code,
                    "montant": f"{montant:,} FCFA".replace(',', ' ') if montant > 0 else "0 FCFA",
                    "status": status_final,
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
    @app.route('/admin/api/export/clients', methods=['GET'], endpoint='admin_api_export_clients')
    def admin_api_export_clients():
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

    @app.route("/admin/repertoire", methods=["GET"])
    def admin_repertoire():
        user, resp = _require_admin()
        if resp:
            return resp

        # Paramètres
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        ville_filter = request.args.get('ville', '')
        rows_per_page = 50
        offset = (page - 1) * rows_per_page

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Base query Clients + nb_commandes + montant_total_paye
            base_query = """
                SELECT c.client_id, c.nom, c.telephone, c.telephone_secondaire,
                    c.adresse, c.ville, c.pays,
                    COALESCE(
                        COUNT(CASE WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN p.proforma_id END) +
                        COUNT(CASE WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.facture_id END), 0
                    ) AS nb_commandes,
                    COALESCE(
                        SUM(CASE WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN
                            COALESCE(
                                (SELECT SUM(pa.quantite * a.prix) 
                                    FROM proforma_articles pa 
                                    JOIN articles a ON a.article_id = pa.article_id 
                                    WHERE pa.proforma_id = p.proforma_id), 0
                            ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                        ELSE 0 END) +
                        SUM(CASE WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.montant_total ELSE 0 END), 0
                    ) AS montant_total_paye
                FROM clients c
                LEFT JOIN proformas p ON p.client_id = c.client_id
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

            # Pagination
            cur.execute(f"SELECT COUNT(*) FROM ({base_query}) AS sub", params)
            total_clients = cur.fetchone()[0] or 0
            total_pages = math.ceil(total_clients / rows_per_page) if total_clients > 0 else 1

            cur.execute(f"{base_query} ORDER BY c.nom LIMIT %s OFFSET %s", params + [rows_per_page, offset])
            clients_rows = cur.fetchall()

            # Villes
            cur.execute("""
                SELECT DISTINCT ville FROM clients 
                WHERE ville IS NOT NULL AND ville != '' AND LOWER(ville) != 'nan' 
                ORDER BY ville
            """)
            villes = [row[0] for row in cur.fetchall()]

            # KPIs
            mois_actuel_debut = datetime.now().replace(day=1).date()
            mois_actuel_fin = datetime.now().date()
            mois_precedent_fin = (datetime.now().replace(day=1) - timedelta(days=1)).date()
            mois_precedent_debut = mois_precedent_fin.replace(day=1)

            # Total clients (GLOBAL - sans progression)
            cur.execute("SELECT COUNT(*) FROM clients")
            kpi_total_clients_raw = cur.fetchone()[0] or 0

            # CA GLOBAL (proformas terminées + factures terminées) - TOUS LES UTILISATEURS SECRÉTAIRES
            cur.execute("""
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN
                            COALESCE(
                                (SELECT SUM(pa.quantite * a.prix) 
                                FROM proforma_articles pa 
                                JOIN articles a ON a.article_id = pa.article_id 
                                WHERE pa.proforma_id = p.proforma_id), 0
                            ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                        ELSE 0
                    END
                ), 0) +
                COALESCE(SUM(
                    CASE 
                        WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.montant_total 
                        ELSE 0 
                    END
                ), 0)
                FROM proformas p
                FULL OUTER JOIN factures f ON f.client_id = p.client_id
                WHERE (p.etat IN ('termine', 'terminé', 'partiel') OR f.statut IN ('termine', 'terminé', 'partiel'))
            """)
            kpi_ca_total = int(cur.fetchone()[0] or 0)

            # Nouveaux clients (mois actuel) + progression
            cur.execute("SELECT COUNT(*) FROM clients WHERE created_at >= %s AND created_at <= %s",
                        [mois_actuel_debut, mois_actuel_fin])
            kpi_new_clients_raw = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM clients WHERE created_at >= %s AND created_at <= %s",
                        [mois_precedent_debut, mois_precedent_fin])
            prev_new_clients = cur.fetchone()[0] or 0
            if kpi_new_clients_raw == 0:
                kpi_new_clients_trend = 0
            elif prev_new_clients > 0:
                kpi_new_clients_trend = round(((kpi_new_clients_raw - prev_new_clients) / prev_new_clients) * 100, 1)
            else:
                kpi_new_clients_trend = 100

            # Ville la plus active
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

            # Format clients
            clients = []
            for i, c in enumerate(clients_rows):
                clients.append({
                    'client_id': c[0] or f"unknown_{i}",
                    'nom': c[1] or 'Nom inconnu',
                    'telephone': c[2] or '-',
                    'telephone_secondaire': c[3] or '-',
                    'adresse': c[4] or '-',
                    'ville': c[5] or '-',
                    'pays': c[6] or 'Non renseigné',
                    'nb_commandes': c[7] or 0,
                    # Sans suffixe FCFA, le template l’ajoute
                    'montant_total_paye': format_number(c[8] or 0)
                })

            ctx = {
                'clients': clients,
                'villes': villes,
                'kpi_ca': format_currency(kpi_ca_total),
                'kpi_total_clients': format_number(kpi_total_clients_raw),
                'kpi_top_city': kpi_top_city,
                'kpi_top_city_count': kpi_top_city_count,
                'kpi_new_clients': format_number(kpi_new_clients_raw),
                'kpi_new_clients_trend': kpi_new_clients_trend,
                'total_pages': total_pages,
                'current_page': page,
                'search': search,
                'ville_filter': ville_filter,
            }
            return render_template("repertoire_admin.html", admin=user, **ctx)

        except Exception as e:
            flash(f"Erreur lors de la récupération des données: {str(e)}", "error")
            return redirect(url_for('my_admin_dashboard'))
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass
    
    # ========== API CHARTS: RÉPERTOIRE ==========
    @app.route('/admin/api/repertoire/monthly-evolution', methods=['GET'])
    def admin_api_repertoire_monthly_evolution():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        months_forward = int(request.args.get('months', 12))
        # Période glissante 12 mois à partir du mois précédent (comme dashboard_secretaire.html)
        start_date = datetime.now().replace(day=1) - relativedelta(months=1)
        end_date = start_date + relativedelta(months=months_forward-1) + relativedelta(day=31)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # 1) Clients ayant passé commande par mois (distincts)
            cur.execute("""
                WITH clients_commandes AS (
                    SELECT to_char(date_trunc('month', p.date_creation), 'YYYY-MM') AS ym,
                           p.client_id
                    FROM proformas p
                    WHERE p.date_creation >= %s AND p.date_creation < %s + interval '1 month'
                      AND p.etat IN ('termine','terminé','partiel')
                    UNION
                    SELECT to_char(date_trunc('month', f.date_facture), 'YYYY-MM') AS ym,
                           f.client_id
                    FROM factures f
                    WHERE f.date_facture >= %s AND f.date_facture < %s + interval '1 month'
                      AND f.statut IN ('termine','terminé','partiel')
                )
                SELECT ym, COUNT(DISTINCT client_id) AS clients_commandes
                FROM clients_commandes
                GROUP BY 1
                ORDER BY 1
            """, [start_date.date(), end_date.date(), start_date.date(), end_date.date()])
            rows_clients_commandes = {r[0]: int(r[1]) for r in cur.fetchall()}

            # 2) CA total et clients uniques par mois (proformas terminées + factures terminées)
            cur.execute("""
                WITH proformas_m AS (
                    SELECT to_char(date_trunc('month', p.date_creation), 'YYYY-MM') AS ym,
                           p.client_id,
                           COALESCE((SELECT SUM(pa.quantite * a.prix)
                                     FROM proforma_articles pa
                                     JOIN articles a ON a.article_id = pa.article_id
                                     WHERE pa.proforma_id = p.proforma_id), 0)
                           + COALESCE(p.frais,0) - COALESCE(p.remise,0) AS total
                    FROM proformas p
                    WHERE p.date_creation >= %s AND p.date_creation < %s + interval '1 month'
                      AND p.etat IN ('termine','terminé','partiel')
                ), factures_m AS (
                    SELECT to_char(date_trunc('month', f.date_facture), 'YYYY-MM') AS ym,
                           f.client_id,
                           COALESCE(f.montant_total,0) AS total
                    FROM factures f
                    WHERE f.date_facture >= %s AND f.date_facture < %s + interval '1 month'
                      AND f.statut IN ('termine','terminé','partiel')
                ), union_m AS (
                    SELECT * FROM proformas_m
                    UNION ALL
                    SELECT * FROM factures_m
                )
                SELECT ym,
                       SUM(total) AS ca_total,
                       COUNT(DISTINCT client_id) AS clients_uniques
                FROM union_m
                GROUP BY ym
                ORDER BY ym
            """, [start_date.date(), end_date.date(),
                   start_date.date(), end_date.date()])
            ca_rows = {r[0]: (float(r[1] or 0), int(r[2] or 0)) for r in cur.fetchall()}

            # 3) Top 10 clients par mois (pour tooltip)
            cur.execute("""
                WITH union_m AS (
                    SELECT to_char(date_trunc('month', p.date_creation), 'YYYY-MM') AS ym,
                           p.client_id,
                           COALESCE((SELECT SUM(pa.quantite * a.prix)
                                     FROM proforma_articles pa
                                     JOIN articles a ON a.article_id = pa.article_id
                                     WHERE pa.proforma_id = p.proforma_id), 0)
                           + COALESCE(p.frais,0) - COALESCE(p.remise,0) AS total
                    FROM proformas p
                    WHERE p.date_creation >= %s AND p.date_creation < %s + interval '1 month'
                      AND p.etat IN ('termine','terminé','partiel')
                    UNION ALL
                    SELECT to_char(date_trunc('month', f.date_facture), 'YYYY-MM') AS ym,
                           f.client_id,
                           COALESCE(f.montant_total,0) AS total
                    FROM factures f
                    WHERE f.date_facture >= %s AND f.date_facture < %s + interval '1 month'
                      AND f.statut IN ('termine','terminé','partiel')
                )
                SELECT u.ym, c.nom, SUM(u.total) AS montant
                FROM union_m u
                JOIN clients c ON c.client_id = u.client_id
                GROUP BY u.ym, c.nom
                ORDER BY u.ym ASC, montant DESC
            """, [start_date.date(), end_date.date(),
                   start_date.date(), end_date.date()])
            top_raw = cur.fetchall()

            # Build month labels
            # Build month keys and display labels (French abbreviated month)
            def fr_month_label(dt: datetime) -> str:
                months_fr = ['janv', 'févr', 'mars', 'avr', 'mai', 'juin', 'juil', 'août', 'sept', 'oct', 'nov', 'déc']
                return f"{months_fr[dt.month-1]} {dt.year}"

            keys = []
            labels = []
            cursor = start_date
            for _ in range(months_forward):
                keys.append(cursor.strftime('%Y-%m'))
                labels.append(fr_month_label(cursor))
                cursor = cursor + relativedelta(months=1)

            clients_commandes = [rows_clients_commandes.get(m, 0) for m in keys]
            avg_ca_per_client = []
            for m in keys:
                ca, uniq = ca_rows.get(m, (0.0, 0))
                avg = (ca / uniq) if uniq > 0 else 0
                avg_ca_per_client.append(int(avg))

            # Top clients map
            top_map = {}
            for ym, nom, montant in top_raw:
                top_map.setdefault(ym, [])
                if len(top_map[ym]) < 10:
                    top_map[ym].append({"nom": nom, "montant": float(montant or 0)})

            has_data = any(v > 0 for v in clients_commandes) or any(v > 0 for v in avg_ca_per_client)
            return jsonify({
                "success": True,
                "has_data": has_data,
                "labels": labels,
                "keys": keys,
                "clients_commandes": clients_commandes,
                "avg_ca_per_client": avg_ca_per_client,
                "top_clients_by_month": top_map
            })
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            try:
                cur.close(); conn.close()
            except Exception:
                pass

    @app.route('/admin/api/repertoire/active-inactive', methods=['GET'])
    def admin_api_repertoire_active_inactive():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        months = int(request.args.get('months', 3))
        cutoff = datetime.now() - relativedelta(months=months)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # MODE B: Ratio parmi les clients ayant déjà commandé au moins une fois
            cur.execute("""
                WITH last_orders AS (
                    SELECT c.client_id,
                           GREATEST(
                               COALESCE((SELECT MAX(p.date_creation) FROM proformas p WHERE p.client_id=c.client_id AND p.etat IN ('termine','terminé','partiel')), '1900-01-01'),
                               COALESCE((SELECT MAX(f.date_facture)  FROM factures  f WHERE f.client_id=c.client_id AND f.statut IN ('termine','terminé','partiel')), '1900-01-01')
                           ) AS last_order
                    FROM clients c
                ), buyers_only AS (
                    SELECT * FROM last_orders WHERE last_order > '1900-01-01'
                )
                SELECT
                    COUNT(CASE WHEN last_order >= %s THEN 1 END) AS actifs,
                    COUNT(CASE WHEN last_order < %s THEN 1 END)  AS inactifs
                FROM buyers_only
            """, [cutoff, cutoff])
            row = cur.fetchone()
            actifs = int(row[0] or 0)
            inactifs = int(row[1] or 0)
            total = actifs + inactifs
            if total == 0:
                return jsonify({
                    "success": True,
                    "labels": ["Actifs","Inactifs"],
                    "counts": [0,0],
                    "percentages": [0.0,0.0],
                    "window_months": months
                })
            pct_actifs = round(actifs * 100.0 / total, 1)
            pct_inactifs = round(100.0 - pct_actifs, 1)
            return jsonify({
                "success": True,
                "labels": ["Actifs","Inactifs"],
                "counts": [actifs, inactifs],
                "percentages": [pct_actifs, pct_inactifs],
                "window_months": months
            })
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            try:
                cur.close(); conn.close()
            except Exception:
                pass

    # Onglet: Ventes / Proformas
    @app.route("/admin/ventes", methods=["GET"])
    def admin_ventes():
        user, resp = _require_admin()
        if resp: return resp
        return render_template("ventes_admin.html", admin=user)

    # ================== API VENTES (KPIs GLOBAUX) ==================
    @app.route('/admin/api/ventes/kpis', methods=['GET'])
    def admin_api_ventes_kpis():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # 1) Chiffre d'Affaires GLOBAL (proformas terminées + factures terminées) - TOUS LES UTILISATEURS SECRÉTAIRES
            cur.execute(
                """
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN
                            COALESCE(
                                (SELECT SUM(pa.quantite * a.prix) 
                                FROM proforma_articles pa 
                                JOIN articles a ON a.article_id = pa.article_id 
                                WHERE pa.proforma_id = p.proforma_id), 0
                            ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                        ELSE 0
                    END
                ), 0) +
                COALESCE(SUM(
                    CASE 
                        WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.montant_total 
                        ELSE 0 
                    END
                ), 0)
                FROM proformas p
                FULL OUTER JOIN factures f ON f.client_id = p.client_id
                WHERE (p.etat IN ('termine', 'terminé', 'partiel') OR f.statut IN ('termine', 'terminé', 'partiel'))
                """
            )
            kpi_ca_global = int(cur.fetchone()[0] or 0)

            # 2) Total Ventes GLOBAL (nombre de factures terminées)
            cur.execute(
                """
                SELECT COUNT(*)
                FROM factures f
                WHERE f.statut IN ('termine','terminé','partiel')
                """
            )
            kpi_total_ventes_global = cur.fetchone()[0] or 0

            # 3) Nombre de Clients GLOBAL (clients ayant passé des commandes)
            cur.execute(
                """
                SELECT COUNT(DISTINCT f.client_id)
                FROM factures f
                WHERE f.statut IN ('termine','terminé','partiel')
                """
            )
            kpi_nombre_clients_global = cur.fetchone()[0] or 0

            # 4) Articles Vendus GLOBAL (quantité totale d'articles vendus)
            cur.execute(
                """
                SELECT COALESCE(SUM(pa.quantite), 0)
                FROM proforma_articles pa
                JOIN proformas p ON p.proforma_id = pa.proforma_id
                WHERE p.etat IN ('termine','terminé','partiel')
                """
            )
            kpi_articles_vendus_global = int(cur.fetchone()[0] or 0)

            return jsonify({
                "success": True,
                "ca_global": format_currency(kpi_ca_global),
                "total_ventes_global": format_number(kpi_total_ventes_global),
                "nombre_clients_global": format_number(kpi_nombre_clients_global),
                "articles_vendus_global": format_number(kpi_articles_vendus_global)
            })

        except Exception as e:
            print(f"Erreur lors du calcul des KPI ventes: {e}")
            return jsonify({"success": False, "message": "Erreur lors du calcul des KPI"}), 500
        finally:
            conn.close()

    # ================== API VENTES GRAPHIQUES ==================
    @app.route('/admin/api/ventes/evolution', methods=['GET'])
    def admin_api_ventes_evolution():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            print("🔍 Début calcul évolution ventes...")
            start_time = time.time()
            
            # Vérifier si une année spécifique est demandée
            year_filter = request.args.get('year', '')
            
            if year_filter:
                # Si une année est spécifiée, prendre toute l'année
                start_date = datetime(int(year_filter), 1, 1)
                end_date = datetime(int(year_filter), 12, 31)
                print(f"🔍 DEBUG ADMIN VENTES EVOLUTION - Année spécifique: {year_filter}")
            else:
                # Période glissante 12 mois à partir du mois précédent (comme dashboard_secretaire.html)
                now = datetime.now()
                start_date = now.replace(day=1) - relativedelta(months=1)
                end_date = start_date + relativedelta(months=11) + relativedelta(day=31)
                print(f"🔍 DEBUG ADMIN VENTES EVOLUTION - Période glissante: {start_date.date()} à {end_date.date()}")
            
            # Requête globale (toutes les villes) avec détails par agence - INCLUANT FRAIS ET REMISES
            cur.execute("""
                WITH proforma_totals AS (
                SELECT 
                    p.proforma_id,
                        EXTRACT(YEAR FROM p.date_creation) as year,
                        EXTRACT(MONTH FROM p.date_creation) as month,
                    p.ville,
                        SUM(pa.quantite) as total_quantity,
                        SUM(pa.quantite * a.prix) as articles_total,
                        COALESCE(p.frais, 0) as frais,
                        COALESCE(p.remise, 0) as remise
                FROM proformas p
                    JOIN proforma_articles pa ON pa.proforma_id = p.proforma_id
                    JOIN articles a ON a.article_id = pa.article_id
                    WHERE p.date_creation >= %s 
                    AND p.date_creation <= %s
                    AND p.etat = 'termine'
                    GROUP BY p.proforma_id, EXTRACT(YEAR FROM p.date_creation), EXTRACT(MONTH FROM p.date_creation), p.ville, p.frais, p.remise
                ),
                monthly_stats AS (
                SELECT 
                        year,
                        month,
                        ville,
                        COUNT(DISTINCT proforma_id) as nb_ventes,
                        SUM(total_quantity) as total_quantity,
                        SUM(articles_total + frais - remise) as total_revenue
                    FROM proforma_totals
                    GROUP BY year, month, ville
                    ORDER BY year, month, ville
                )
                SELECT year, month, ville, nb_ventes, total_quantity, total_revenue FROM monthly_stats
            """, [start_date, end_date])
            results = cur.fetchall()
            print(f"🔍 Évolution data récupérée: {len(results)} mois en {time.time() - start_time:.2f}s")
            
            # Créer le dictionnaire des données par (année, mois, ville)
            monthly_data = {}
            for row in results:
                year, month, ville, nb_ventes, quantity, revenue = row
                key = (int(year), int(month))
                if key not in monthly_data:
                    monthly_data[key] = {}
                monthly_data[key][ville] = (nb_ventes, quantity, revenue)
            
            # Générer les labels et données
            labels = []
            nb_ventes_data = []
            ca_montants_data = []
            agence_details = []  # Pour les tooltips
            
            if year_filter:
                # Pour une année spécifique, générer les 12 mois de l'année
                for month in range(1, 13):
                    year = int(year_filter)
                    
                    # LABELS SANS ANNÉE (car c'est la même année)
                    month_names = {
                        1: 'Janv', 2: 'Févr', 3: 'Mars', 4: 'Avr', 5: 'Mai', 6: 'Juin',
                        7: 'Juil', 8: 'Août', 9: 'Sept', 10: 'Oct', 11: 'Nov', 12: 'Déc'
                    }
                    
                    labels.append(month_names[month])
                    
                    # Récupérer les données pour ce mois ou 0 par défaut
                    month_data = monthly_data.get((year, month), {})
                    total_nb_ventes = sum(data[0] for data in month_data.values())
                    total_quantity = sum(data[1] for data in month_data.values())
                    total_revenue = sum(data[2] for data in month_data.values())
                    
                    nb_ventes_data.append(int(total_nb_ventes) if total_nb_ventes else 0)
                    ca_montants_data.append(int(total_revenue) if total_revenue else 0)
                    
                    # Détails par agence pour le tooltip
                    agence_details.append({
                        ville: {
                            "nb_ventes": int(data[0]) if data[0] else 0,
                            "articles_vendus": int(data[1]) if data[1] else 0,
                            "chiffre_affaire": int(data[2]) if data[2] else 0
                        }
                        for ville, data in month_data.items()
                    })
            else:
                # Période glissante 12 mois à partir du mois précédent
                current_date = start_date
            
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
                month_data = monthly_data.get((year, month), {})
                total_nb_ventes = sum(data[0] for data in month_data.values())
                total_quantity = sum(data[1] for data in month_data.values())
                total_revenue = sum(data[2] for data in month_data.values())
                
                nb_ventes_data.append(int(total_nb_ventes) if total_nb_ventes else 0)
                ca_montants_data.append(int(total_revenue) if total_revenue else 0)
                
                # Détails par agence pour le tooltip
                agence_details.append({
                    ville: {
                        "nb_ventes": int(data[0]) if data[0] else 0,
                        "articles_vendus": int(data[1]) if data[1] else 0,
                        "chiffre_affaire": int(data[2]) if data[2] else 0
                    }
                    for ville, data in month_data.items()
                })
                
                # Passer au mois suivant
                current_date = current_date + relativedelta(months=1)
            
            cur.close()
            conn.close()
            
            print(f"🔍 DEBUG ADMIN VENTES - Final Labels: {labels}")
            print(f"🔍 DEBUG ADMIN VENTES - Final Nb Ventes: {nb_ventes_data}")
            print(f"🔍 DEBUG ADMIN VENTES - Final CA: {ca_montants_data}")

            return jsonify({
                "success": True,
                "labels": labels,
                "nb_ventes": nb_ventes_data,
                "ca_montants": ca_montants_data,
                "agence_details": agence_details,
                "has_data": sum(nb_ventes_data) > 0
            })

        except Exception as e:
            print(f"Erreur lors du calcul de l'évolution ventes: {e}")
            return jsonify({"success": False, "message": "Erreur lors du calcul de l'évolution"}), 500
        finally:
            conn.close()

    @app.route('/admin/api/ventes/years', methods=['GET'])
    def admin_api_ventes_years():
        """Récupérer les années disponibles pour le filtre"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Récupérer toutes les années disponibles dans les proformas (tous états)
            cur.execute("""
                SELECT DISTINCT EXTRACT(YEAR FROM date_creation) as year
                FROM proformas 
                ORDER BY year DESC
            """)
            
            years = [int(row[0]) for row in cur.fetchall()]
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "years": years
            })
            
        except Exception as e:
            print(f"Erreur lors de la récupération des années: {e}")
            return jsonify({"success": False, "message": "Erreur lors de la récupération des années"}), 500
        finally:
            conn.close()

    @app.route('/admin/api/ventes/segmentation-villes', methods=['GET'])
    def admin_api_ventes_segmentation_villes():
        """Récupérer la segmentation par ville/agence (vue globale admin)"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Vue globale - toutes les données depuis le début (pas de filtre de date) - INCLUANT FRAIS ET REMISES
            cur.execute("""
                WITH proforma_totals AS (
                SELECT 
                        p.proforma_id,
                        p.ville,
                        SUM(pa.quantite) as total_quantity,
                        SUM(pa.quantite * a.prix) as articles_total,
                        COALESCE(p.frais, 0) as frais,
                        COALESCE(p.remise, 0) as remise
                    FROM proformas p
                    JOIN proforma_articles pa ON pa.proforma_id = p.proforma_id
                    JOIN articles a ON a.article_id = pa.article_id
                    WHERE p.etat = 'termine'
                    GROUP BY p.proforma_id, p.ville, p.frais, p.remise
                )
                SELECT 
                    ville,
                    COUNT(DISTINCT proforma_id) as nb_ventes,
                    SUM(total_quantity) as total_quantity,
                    SUM(articles_total + frais - remise) as total_revenue
                FROM proforma_totals
                GROUP BY ville
                ORDER BY total_revenue DESC
            """)
            
            results = cur.fetchall()
            
            if not results:
                cur.close()
                conn.close()
                return jsonify({
                    "success": True,
                    "villes": [],
                    "total_ca": 0,
                    "has_data": False
                })
            
            total_ca = sum(row[3] for row in results)
            
            villes = []
            for row in results:
                ville, nb_ventes, quantity, revenue = row
                percentage = round((revenue / total_ca) * 100, 1) if total_ca > 0 else 0
                
                villes.append({
                    "ville": ville or "Non renseigné",
                    "nb_ventes": int(nb_ventes),
                    "quantity": int(quantity),
                    "revenue": int(revenue),
                    "percentage": float(percentage)
                })
            
            cur.close()
            conn.close()

            result = {
                "success": True,
                "villes": villes,
                "total_ca": int(total_ca),
                "has_data": len(villes) > 0
            }
            
            print(f"🔍 DEBUG SEGMENTATION VILLES - Résultat: {result}")
            
            return jsonify(result)

        except Exception as e:
            print(f"❌ Erreur admin_api_ventes_segmentation_villes: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass

    # ================== API LISTE GLOBALE DEVIS & FACTURES ==================
    @app.route('/admin/api/ventes/commandes-globales', methods=['GET'])
    def admin_api_ventes_commandes_globales():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '', type=str)
        statut = request.args.get('statut', '', type=str)
        per_page = 50
        offset = (page - 1) * per_page

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Construire la requête avec filtres
            where_conditions_proforma = []
            where_conditions_facture = []
            params = []
            
            if search:
                where_conditions_proforma.append("(c.nom ILIKE %s OR c.telephone ILIKE %s)")
                where_conditions_facture.append("(c.nom ILIKE %s OR c.telephone ILIKE %s)")
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param, search_param])
            
            if statut:
                where_conditions_proforma.append("p.etat = %s")
                where_conditions_facture.append("f.statut = %s")
                params.extend([statut, statut])
            
            where_clause_proforma = "WHERE " + " AND ".join(where_conditions_proforma) if where_conditions_proforma else ""
            where_clause_facture = "WHERE " + " AND ".join(where_conditions_facture) if where_conditions_facture else ""
            
            # Compter le total (proformas + factures)
            count_query = f"""
                SELECT 
                    (SELECT COUNT(*) FROM proformas p LEFT JOIN clients c ON c.client_id = p.client_id {where_clause_proforma}) +
                    (SELECT COUNT(*) FROM factures f LEFT JOIN clients c ON c.client_id = f.client_id {where_clause_facture})
            """
            cur.execute(count_query, params)
            total_count = cur.fetchone()[0]

            # Récupérer les proformas ET factures avec pagination
            # Union des proformas et factures
            query = f"""
                SELECT 
                    p.proforma_id as id,
                    'proforma' as type,
                    p.date_creation,
                    c.nom as client_nom,
                    c.telephone as client_telephone,
                    p.ville,
                    p.etat,
                    COALESCE(u.nom_utilisateur, 'N/A') as agent_nom,
                    COALESCE((
                        SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id
                    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0), 0) as total_ttc
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                LEFT JOIN utilisateurs u ON u.user_id = p.cree_par
                {where_clause_proforma}
                
                UNION ALL
                
                SELECT 
                    f.facture_id as id,
                    'facture' as type,
                    f.date_facture as date_creation,
                    c.nom as client_nom,
                    c.telephone as client_telephone,
                    f.ville,
                    f.statut as etat,
                    COALESCE(f.agent, 'N/A') as agent_nom,
                    f.montant_total as total_ttc
                FROM factures f
                LEFT JOIN clients c ON c.client_id = f.client_id
                {where_clause_facture}
                
                ORDER BY date_creation DESC
                LIMIT %s OFFSET %s
            """
            
            cur.execute(query, params + [per_page, offset])
            commandes_data = cur.fetchall()
            
            total_pages = (total_count + per_page - 1) // per_page

            # Calculer les totaux pour le résumé (toutes les données, pas seulement la page courante)
            # Proformas = statuts 'en_attente' et 'en_cours'
            # Factures = statuts 'termine' et 'partiel'
            cur.execute(f"""
                SELECT 
                    'proforma' as type,
                    COUNT(*) as count,
                    COALESCE(SUM((
                        SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id
                    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)), 0) as total
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                WHERE p.etat IN ('en_attente', 'en_cours')
                {('AND ' + ' AND '.join(where_conditions_proforma)) if where_conditions_proforma else ''}
                
                UNION ALL
                
                SELECT 
                    'facture' as type,
                    COUNT(*) as count,
                    COALESCE(SUM(f.montant_total), 0) as total
                FROM factures f
                LEFT JOIN clients c ON c.client_id = f.client_id
                WHERE f.statut IN ('termine', 'partiel')
                {('AND ' + ' AND '.join(where_conditions_facture)) if where_conditions_facture else ''}
            """, params)
            
            summary_data = cur.fetchall()
            total_proformas = 0
            total_factures = 0
            montant_proformas = 0
            montant_factures = 0
            
            for row in summary_data:
                if row[0] == 'proforma':
                    total_proformas = row[1]
                    montant_proformas = float(row[2])
                else:
                    total_factures = row[1]
                    montant_factures = float(row[2])

            return jsonify({
                "success": True,
                "commandes": [{
                    "id": row[0],
                    "type": row[1],
                    "numero": f"PRO{row[0]:05d}" if row[1] == 'proforma' else f"FAC{row[0]:05d}",
                    "date_creation": row[2].isoformat() if row[2] else None,
                    "client_nom": row[3] or "N/A",
                    "client_telephone": row[4] or "N/A",
                    "ville": row[5] or "N/A",
                    "etat": row[6] or "en_cours",
                    "created_by": row[7] or "N/A",
                    "total_ttc": float(row[8])
                } for row in commandes_data],
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "summary": {
                    "proformas": {
                        "count": total_proformas,
                        "total_amount": montant_proformas
                    },
                    "factures": {
                        "count": total_factures,
                        "total_amount": montant_factures
                    }
                }
            })

        except Exception as e:
            print(f"Erreur lors de la récupération des commandes globales: {e}")
            return jsonify({"success": False, "message": "Erreur lors de la récupération des commandes"}), 500
        finally:
            conn.close()

    # ================== API DÉTAILS PROFORMA ==================
    @app.route('/admin/api/ventes/proforma-details/<int:proforma_id>', methods=['GET'])
    def admin_api_ventes_proforma_details(proforma_id):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Récupérer les détails de la proforma
            cur.execute("""
                SELECT 
                    p.proforma_id,
                    p.date_creation,
                    p.etat,
                    p.ville,
                    p.cree_par,
                    p.frais,
                    p.remise,
                    c.nom as client_nom,
                    c.telephone as client_telephone,
                    c.adresse as client_adresse,
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
                WHERE p.proforma_id = %s
            """, [proforma_id])
            
            proforma_data = cur.fetchone()
            if not proforma_data:
                return jsonify({"success": False, "message": "Proforma non trouvée"}), 404

            # Récupérer les articles de la proforma
            cur.execute("""
                SELECT 
                    a.designation,
                    a.type_article,
                    pa.quantite,
                    a.prix,
                    pa.quantite * a.prix as total
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                WHERE pa.proforma_id = %s
                ORDER BY a.designation
            """, [proforma_id])
            
            articles_data = cur.fetchall()

            return jsonify({
                "success": True,
                "proforma": {
                    "proforma_id": proforma_data[0],
                    "numero": f"PRO{proforma_data[0]:05d}",
                    "date_creation": proforma_data[1].isoformat() if proforma_data[1] else None,
                    "etat": proforma_data[2],
                    "ville": proforma_data[3],
                    "created_by": proforma_data[4],  # cree_par
                    "frais": float(proforma_data[5]) if proforma_data[5] else 0,
                    "remise": float(proforma_data[6]) if proforma_data[6] else 0,
                    "remise_percent": 0,  # Pas de colonne remise_percent dans la table
                    "client_nom": proforma_data[7],
                    "client_telephone": proforma_data[8],
                    "client_email": None,  # Pas de colonne email dans la table clients
                    "client_adresse": proforma_data[9],
                    "sous_total": float(proforma_data[10]),
                    "total_ttc": float(proforma_data[11])
                },
                "articles": [{
                    "designation": row[0],
                    "type_article": row[1],
                    "quantite": int(row[2]),
                    "prix": float(row[3]),
                    "total": float(row[4])
                } for row in articles_data]
            })

        except Exception as e:
            print(f"Erreur lors de la récupération des détails proforma: {e}")
            return jsonify({"success": False, "message": "Erreur lors de la récupération des détails"}), 500
        finally:
            conn.close()

    # ================== API DÉTAILS FACTURE ==================
    @app.route('/admin/api/ventes/facture-details/<int:facture_id>', methods=['GET'])
    def admin_api_ventes_facture_details(facture_id):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Récupérer les détails de la facture
            cur.execute("""
                SELECT 
                    f.facture_id,
                    f.date_facture,
                    f.statut,
                    f.ville,
                    f.agent,
                    f.montant_total,
                    c.nom as client_nom,
                    c.telephone as client_telephone,
                    c.adresse as client_adresse
                FROM factures f
                LEFT JOIN clients c ON c.client_id = f.client_id
                WHERE f.facture_id = %s
            """, [facture_id])
            
            facture_data = cur.fetchone()
            if not facture_data:
                return jsonify({"success": False, "message": "Facture non trouvée"}), 404

            # Récupérer les articles de la facture
            cur.execute("""
                SELECT 
                    a.designation,
                    a.type_article,
                    fa.quantite,
                    a.prix,
                    fa.quantite * a.prix as total
                FROM facture_articles fa
                JOIN articles a ON a.article_id = fa.article_id
                WHERE fa.facture_id = %s
                ORDER BY a.designation
            """, [facture_id])
            
            articles_data = cur.fetchall()

            # Calculer le sous-total à partir des articles
            sous_total = sum(row[4] for row in articles_data)  # total de chaque article
            montant_total = float(facture_data[5])
            frais = max(0, montant_total - sous_total)  # Différence = frais
            remise = 0  # Pas de remise pour les anciennes factures
            
            return jsonify({
                "success": True,
                "proforma": {
                    "proforma_id": facture_data[0],
                    "numero": f"FAC{facture_data[0]:05d}",
                    "date_creation": facture_data[1].isoformat() if facture_data[1] else None,
                    "etat": facture_data[2],
                    "ville": facture_data[3],
                    "created_by": facture_data[4],  # agent
                    "frais": frais,
                    "remise": remise,
                    "remise_percent": 0,
                    "client_nom": facture_data[6],
                    "client_telephone": facture_data[7],
                    "client_email": None,
                    "client_adresse": facture_data[8],
                    "sous_total": sous_total,
                    "total_ttc": montant_total
                },
                "articles": [{
                    "designation": row[0],
                    "type_article": row[1],
                    "quantite": int(row[2]),
                    "prix": float(row[3]),
                    "total": float(row[4])
                } for row in articles_data]
            })

        except Exception as e:
            print(f"Erreur lors de la récupération des détails facture: {e}")
            return jsonify({"success": False, "message": "Erreur lors de la récupération des détails"}), 500
        finally:
            conn.close()

    # ================== API SUPPRESSION PROFORMA ==================
    @app.route('/admin/api/ventes/proforma/<int:proforma_id>', methods=['DELETE'])
    def admin_api_ventes_delete_proforma(proforma_id):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Vérifier que la proforma existe (la table n'a pas de colonne 'numero')
            # On récupère simplement l'ID pour construire une référence affichable
            cur.execute("SELECT proforma_id FROM proformas WHERE proforma_id = %s", [proforma_id])
            proforma = cur.fetchone()
            if not proforma:
                return jsonify({"success": False, "message": "Proforma non trouvée"}), 404

            # Supprimer les articles de la proforma
            cur.execute("DELETE FROM proforma_articles WHERE proforma_id = %s", [proforma_id])
            
            # Supprimer la proforma
            cur.execute("DELETE FROM proformas WHERE proforma_id = %s", [proforma_id])
            
            conn.commit()
            
            # Log de l'action
            log_action("delete", "proforma", str(proforma_id), 
                      payload_avant={"proforma_id": proforma_id})

            # Construire une référence lisible type PRO00006
            ref = f"PRO{proforma_id:05d}"
            return jsonify({
                "success": True,
                "message": f"Proforma {ref} supprimée avec succès",
                "reference": ref
            })

        except Exception as e:
            print(f"Erreur lors de la suppression de la proforma: {e}")
            conn.rollback()
            return jsonify({"success": False, "message": "Erreur lors de la suppression"}), 500
        finally:
            conn.close()

    # ================== API SUPPRESSION FACTURE ==================
    @app.route('/admin/api/ventes/facture/<int:facture_id>', methods=['DELETE'])
    def admin_api_ventes_delete_facture(facture_id):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Vérifier que la facture existe
            cur.execute("SELECT code_facture FROM factures WHERE facture_id = %s", [facture_id])
            facture = cur.fetchone()
            if not facture:
                return jsonify({"success": False, "message": "Facture non trouvée"}), 404

            # Supprimer les articles de la facture
            cur.execute("DELETE FROM facture_articles WHERE facture_id = %s", [facture_id])
            
            # Supprimer la facture
            cur.execute("DELETE FROM factures WHERE facture_id = %s", [facture_id])
            
            conn.commit()
            
            # Log de l'action
            log_action("delete", "facture", str(facture_id), 
                      payload_avant={"code_facture": facture[0]})

            return jsonify({
                "success": True,
                "message": f"Facture {facture[0]} supprimée avec succès"
            })

        except Exception as e:
            print(f"Erreur lors de la suppression de la facture: {e}")
            conn.rollback()
            return jsonify({"success": False, "message": "Erreur lors de la suppression"}), 500
        finally:
            cur.close()
            conn.close()

    # Onglet: Équipe
    @app.route("/admin/equipe", methods=["GET"])
    def admin_equipe():
        user, resp = _require_admin()
        if resp: return resp
        return render_template("team.html", admin=user)

    # ================== API ÉQUIPE (KPIs & COMPARATIF) ==================
    @app.route('/admin/api/team/kpis', methods=['GET'])
    def admin_api_team_kpis():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        # Calculs pour progressions (mois actuel vs mois précédent)
        now = datetime.now().date()
        mois_actuel_debut = now.replace(day=1)
        mois_precedent_fin = (mois_actuel_debut - timedelta(days=1))
        mois_precedent_debut = mois_precedent_fin.replace(day=1)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # 1) Chiffre d'Affaires GLOBAL (proformas terminées + factures terminées) - TOUS LES UTILISATEURS SECRÉTAIRES
            cur.execute(
                """
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN
                            COALESCE(
                                (SELECT SUM(pa.quantite * a.prix) 
                                FROM proforma_articles pa 
                                JOIN articles a ON a.article_id = pa.article_id 
                                WHERE pa.proforma_id = p.proforma_id), 0
                            ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                        ELSE 0
                    END
                ), 0) +
                COALESCE(SUM(
                    CASE 
                        WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.montant_total 
                        ELSE 0 
                    END
                ), 0)
                FROM proformas p
                FULL OUTER JOIN factures f ON f.client_id = p.client_id
                WHERE (p.etat IN ('termine', 'terminé', 'partiel') OR f.statut IN ('termine', 'terminé', 'partiel'))
                """
            )
            kpi_ca_total = int(cur.fetchone()[0] or 0)

            # 2) Meilleur agent (même logique que le tableau comparatif)
            cur.execute(
                """
                WITH p_all AS (
                    SELECT p.proforma_id, p.cree_par,
                           COALESCE((SELECT SUM(pa.quantite * a.prix)
                                    FROM proforma_articles pa
                                    JOIN articles a ON a.article_id = pa.article_id
                                    WHERE pa.proforma_id = p.proforma_id), 0)
                           + COALESCE(p.frais,0) - COALESCE(p.remise,0) AS total,
                           p.etat
                    FROM proformas p
                )
                SELECT u.nom_utilisateur,
                       COALESCE(SUM(CASE WHEN p_all.etat IN ('termine','terminé','partiel') THEN p_all.total ELSE 0 END),0) AS revenu
                FROM utilisateurs u
                LEFT JOIN p_all ON p_all.cree_par = u.user_id
                WHERE LOWER(u.role) = 'secretaire' AND u.actif = TRUE
                GROUP BY u.user_id, u.nom_utilisateur
                HAVING SUM(CASE WHEN p_all.etat IN ('termine','terminé','partiel') THEN p_all.total ELSE 0 END) > 0
                ORDER BY revenu DESC
                LIMIT 1
                """
            )
            top_user_data = cur.fetchone()
            
            if top_user_data and top_user_data[1] > 0:
                kpi_users_actifs = top_user_data[0]  # Juste le nom
            else:
                kpi_users_actifs = "Aucun"

            # 3) Devis GLOBAL (proformas)
            cur.execute("SELECT COUNT(*) FROM proformas")
            kpi_devis_total = int(cur.fetchone()[0] or 0)

            # 4) Factures GLOBAL
            cur.execute("SELECT COUNT(*) FROM factures WHERE statut IN ('termine','terminé','partiel')")
            kpi_factures_total = int(cur.fetchone()[0] or 0)

            return jsonify({
                "success": True,
                "kpi_ca": kpi_ca_total,
                "kpi_users_actifs": kpi_users_actifs,
                "kpi_devis": kpi_devis_total,
                "kpi_factures": kpi_factures_total
            })
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            try:
                cur.close(); conn.close()
            except Exception:
                pass

    @app.route('/admin/api/team/comparatif', methods=['GET'])
    def admin_api_team_comparatif():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        now = datetime.now().date()
        start_30 = now - timedelta(days=30)
        # Pagination params
        page = request.args.get('page', 1, type=int)
        rows_per_page = request.args.get('rows', 5, type=int)

        conn = get_db_connection(); cur = conn.cursor()
        try:
            # Agrégations par utilisateur secrétaire (fenêtre 30 jours)
            cur.execute(
                """
                WITH p30 AS (
                    SELECT p.proforma_id, p.cree_par,
                           COALESCE((SELECT SUM(pa.quantite * a.prix)
                                    FROM proforma_articles pa
                                    JOIN articles a ON a.article_id = pa.article_id
                                    WHERE pa.proforma_id = p.proforma_id), 0)
                           + COALESCE(p.frais,0) - COALESCE(p.remise,0) AS total,
                           p.etat
                    FROM proformas p
                    WHERE p.date_creation >= %s AND p.date_creation <= %s
                )
                SELECT u.user_id,
                       COALESCE(u.nom_utilisateur,'Utilisateur') AS nom,
                       COALESCE(SUM(CASE WHEN p30.etat IN ('termine','terminé','partiel') THEN p30.total ELSE 0 END),0) AS revenu,
                       COUNT(p30.proforma_id) AS nb_devis,
                       COALESCE(SUM(CASE WHEN p30.etat IN ('termine','terminé','partiel') THEN 1 ELSE 0 END),0) AS nb_facturees
                FROM utilisateurs u
                LEFT JOIN p30 ON p30.cree_par = u.user_id
                WHERE LOWER(u.role) = 'secretaire'
                GROUP BY u.user_id, u.nom_utilisateur
                ORDER BY revenu DESC
                """,
                [start_30, now]
            )
            rows = cur.fetchall()

            items = []
            for user_id, nom, revenu, nb_devis, nb_facturees in rows:
                revenu = float(revenu or 0)
                nb_devis = int(nb_devis or 0)
                nb_facturees = int(nb_facturees or 0)
                atp = (revenu / nb_facturees) if nb_facturees > 0 else 0.0
                taux = round((nb_facturees * 100.0 / nb_devis), 1) if nb_devis > 0 else 0.0
                items.append({
                    "user_id": user_id,
                    "nom": nom,
                    "revenu": int(revenu),
                    "nb_devis": nb_devis,
                    "atp": int(atp),
                    "taux": taux
                })
            total = len(items)
            start = max(0, (page - 1) * rows_per_page)
            end = start + rows_per_page
            items_page = items[start:end]

            return jsonify({
                "success": True,
                "items": items_page,
                "total": total,
                "page": page,
                "rows_per_page": rows_per_page
            })
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            try:
                cur.close(); conn.close()
            except Exception:
                pass

    # ================== API STAFF (LISTE + CRUD SIMPLE) ==================
    @app.route('/admin/api/staff', methods=['GET'])
    def admin_api_staff_list():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        ville_filter = request.args.get('ville', '')
        rows_per_page = 5
        offset = (page - 1) * rows_per_page

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Ajout des champs date_entree et date_sortie dans la requête
            base = """
                SELECT 
                    user_id, 
                    nom_utilisateur, 
                    email, 
                    ville, 
                    actif, 
                    role, 
                    COALESCE(telephone,'') AS telephone, 
                    COALESCE(adresse,'') AS adresse, 
                    COALESCE(pays,'') AS pays, 
                    COALESCE(fonction,'') AS fonction,
                    date_entree,
                    date_sortie
                FROM utilisateurs 
                WHERE 1=1
            """
            params = []
            if search:
                base += " AND (LOWER(nom_utilisateur) LIKE LOWER(%s) OR LOWER(email) LIKE LOWER(%s))"
                params.extend([f"%{search}%", f"%{search}%"])
            if ville_filter:
                base += " AND ville = %s"
                params.append(ville_filter)

            cur.execute(f"SELECT COUNT(*) FROM ({base}) t", params)
            total = cur.fetchone()[0] or 0

            cur.execute(f"{base} ORDER BY nom_utilisateur LIMIT %s OFFSET %s", params + [rows_per_page, offset])
            rows = cur.fetchall()

            items = []
            for u in rows:
                items.append({
                    "user_id": u[0],
                    "nom": u[1] or "-",
                    "telephone": (u[6] or "-").strip() or "-",
                    "adresse": (u[7] or "-").strip() or "-",
                    "ville": u[3] or "-",
                    "pays": (u[8] or "-").strip() or "-",
                    "fonction": (u[9] or "Non Renseigné").strip() or "Non Renseigné",
                    "role": u[5] or "-",
                    "actif": bool(u[4]),
                    "email": (u[2] or '').strip(),
                    "date_entree": u[10].strftime('%Y-%m-%d') if u[10] else None,
                    "date_sortie": u[11].strftime('%Y-%m-%d') if u[11] else None
                })

            # Villes distinctes
            cur.execute("SELECT DISTINCT ville FROM utilisateurs WHERE ville IS NOT NULL AND TRIM(ville) <> '' ORDER BY ville")
            villes = [r[0] for r in cur.fetchall()]

            return jsonify({
                "success": True,
                "items": items,
                "total": total,
                "page": page,
                "rows_per_page": rows_per_page,
                "villes": villes
            })
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass

    @app.route('/admin/api/staff', methods=['POST'])
    def admin_api_staff_create():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401
        
        data = request.get_json()
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Validation des champs obligatoires
            required_fields = ['nom', 'telephone', 'adresse', 'ville', 'pays', 'fonction', 'date_entree']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        "success": False,
                        "message": f"Le champ {field} est obligatoire"
                    }), 400
            
            # Construction de la requête avec NOT NULL pour mot_de_passe uniquement si rôle sélectionné
            fields = ['nom_utilisateur', 'telephone', 'adresse', 'ville', 'pays', 'fonction', 'date_entree', 'date_sortie', 'actif']
            values = [
                data['nom'],
                data['telephone'],
                data['adresse'],
                data['ville'],
                data['pays'],
                data['fonction'],
                data['date_entree'],
                data.get('date_sortie'),
                True
            ]
            
            # Ajout des champs d'authentification seulement si rôle sélectionné
            if data.get('role'):
                fields.extend(['role', 'email'])
                values.extend([data['role'], data.get('email')])
                
                if data.get('mot_de_passe'):
                    fields.append('mot_de_passe')
                    cur.execute("SELECT crypt(%s, gen_salt('bf'))", [data['mot_de_passe']])
                    hashed = cur.fetchone()[0]
                    values.append(hashed)
            
            query = f"""
                INSERT INTO utilisateurs ({', '.join(fields)})
                VALUES ({', '.join(['%s'] * len(fields))})
                RETURNING user_id
            """
            
            cur.execute(query, values)
            new_id = cur.fetchone()[0]
            conn.commit()
            
            return jsonify({"success": True, "user_id": new_id})
            
        except Exception as e:
            conn.rollback()
            print(f"Erreur création staff: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/admin/api/export/staff', methods=['GET'])
    def admin_api_export_staff():
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401
        ville = request.args.get('ville','')
        search = request.args.get('search','')
        conn = get_db_connection(); cur = conn.cursor()
        try:
            base = "SELECT nom_utilisateur, email, ville, role, actif FROM utilisateurs WHERE 1=1"
            params=[]
            if search:
                base += " AND (LOWER(nom_utilisateur) LIKE LOWER(%s) OR LOWER(email) LIKE LOWER(%s))"; params.extend([f"%{search}%", f"%{search}%"])
            if ville:
                base += " AND ville = %s"; params.append(ville)
            cur.execute(base + " ORDER BY nom_utilisateur", params)
            rows = cur.fetchall()
            output = StringIO(); writer = csv.writer(output)
            writer.writerow(['Nom','Email','Ville','Rôle','Actif'])
            for r in rows:
                writer.writerow([r[0] or '-', r[1] or '-', r[2] or '-', r[3] or '-', 'Oui' if r[4] else 'Non'])
            output.seek(0)
            resp = make_response(output.getvalue())
            resp.headers['Content-Type'] = 'text/csv'
            resp.headers['Content-Disposition'] = f'attachment; filename=staff_{datetime.now().strftime("%Y%m%d")}.csv'
            return resp
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            try: cur.close(); conn.close()
            except Exception: pass

    @app.route('/admin/api/staff/<int:user_id>', methods=['PUT'])
    def admin_api_staff_update(user_id):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401
            
        data = request.get_json()
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            updates = []
            values = []
            
            # Mapping des champs
            fields_mapping = {
                'nom': 'nom_utilisateur',
                'telephone': 'telephone',
                'adresse': 'adresse',
                'ville': 'ville',
                'pays': 'pays',
                'fonction': 'fonction',
                'date_entree': 'date_entree',
                'date_sortie': 'date_sortie',
                'email': 'email',
                'role': 'role'
            }
            
            for key, db_field in fields_mapping.items():
                if key in data:
                    updates.append(f"{db_field} = %s")
                    values.append(data[key])
            
            # Gestion du mot de passe si fourni
            if data.get('mot_de_passe'):
                cur.execute("SELECT crypt(%s, gen_salt('bf'))", [data['mot_de_passe']])
                hashed = cur.fetchone()[0]
                updates.append("mot_de_passe = %s")
                values.append(hashed)
            
            if not updates:
                return jsonify({"success": False, "message": "Aucune donnée à mettre à jour"}), 400
                
            values.append(user_id)
            query = f"UPDATE utilisateurs SET {', '.join(updates)} WHERE user_id = %s"
            
            cur.execute(query, values)
            if cur.rowcount == 0:
                return jsonify({"success": False, "message": "Utilisateur non trouvé"}), 404
                
            conn.commit()
            return jsonify({"success": True})
            
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/admin/api/staff/<int:user_id>', methods=['DELETE'])
    def admin_api_staff_delete(user_id):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401
        try:
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute("DELETE FROM utilisateurs WHERE user_id=%s", [user_id])
            if cur.rowcount == 0:
                conn.rollback(); cur.close(); conn.close()
                return jsonify({"success": False, "message": "Utilisateur introuvable"}), 404
            conn.commit(); cur.close(); conn.close()
            return jsonify({"success": True})
        except Exception as e:
            if 'conn' in locals():
                conn.rollback(); cur.close(); conn.close()
            return jsonify({"success": False, "message": str(e)}), 500

    # Onglet: Data Analyst
    @app.route("/admin/data-analyst", methods=["GET"])
    def admin_data_analyst():
        user, resp = _require_admin()
        if resp: return resp
        return render_template("data_analyst.html", admin=user)
    
    # ======== DATA ANALYST: Sessions & Messages ========
    @app.route('/admin/api/data-analyst/sessions', methods=['GET'])
    def admin_api_da_sessions_list():
        user, resp = _require_admin();
        if resp: return resp
        try:
            conn = get_db_connection(); cur = conn.cursor()
            # utiliser la fonction SQL
            # Filtrer les sessions vides (sans messages)
            cur.execute("""
                SELECT dac.chat_id, dac.session_name, dac.created_at, dac.updated_at, dac.is_active, COUNT(dam.message_id) as message_count
                FROM data_analyst_chats dac
                LEFT JOIN data_analyst_messages dam ON dac.chat_id = dam.chat_id
                WHERE dac.user_id = %s
                GROUP BY dac.chat_id, dac.session_name, dac.created_at, dac.updated_at, dac.is_active
                HAVING COUNT(dam.message_id) > 0
                ORDER BY dac.updated_at DESC
            """, [user.user_id])
            rows = cur.fetchall()
            sessions = []
            cols = [d[0] for d in cur.description]
            for r in rows:
                item = {cols[i]: r[i] for i in range(len(cols))}
                sessions.append(item)
            cur.close(); conn.close()
            return jsonify({"success": True, "sessions": sessions})
        except Exception as e:
            if 'conn' in locals(): cur.close(); conn.close()
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route('/admin/api/data-analyst/sessions', methods=['POST'])
    def admin_api_da_sessions_create():
        user, resp = _require_admin();
        if resp: return resp
        name = (request.json or {}).get('session_name', 'Nouvelle conversation')
        try:
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute("SELECT create_new_chat_session(%s, %s)", [user.user_id, name])
            chat_id = cur.fetchone()[0]
            conn.commit(); cur.close(); conn.close()
            return jsonify({"success": True, "chat_id": chat_id, "session_name": name})
        except Exception as e:
            if 'conn' in locals(): conn.rollback(); cur.close(); conn.close()
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route('/admin/api/data-analyst/sessions/<int:chat_id>', methods=['PATCH'])
    def admin_api_da_sessions_rename(chat_id):
        user, resp = _require_admin();
        if resp: return resp
        data = request.get_json() or {}
        new_name = data.get('session_name', '').strip()
        if not new_name:
            return jsonify({"success": False, "message": "Nom requis"}), 400
        try:
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute("""
                UPDATE data_analyst_chats
                   SET session_name = %s, updated_at = CURRENT_TIMESTAMP
                 WHERE chat_id = %s AND user_id = %s
            """, [new_name, chat_id, user.user_id])
            if cur.rowcount == 0:
                conn.rollback(); cur.close(); conn.close()
                return jsonify({"success": False, "message": "Chat introuvable"}), 404
            conn.commit(); cur.close(); conn.close()
            return jsonify({"success": True})
        except Exception as e:
            if 'conn' in locals(): conn.rollback(); cur.close(); conn.close()
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route('/admin/api/data-analyst/sessions/<int:chat_id>', methods=['DELETE'])
    def admin_api_da_sessions_delete(chat_id):
        user, resp = _require_admin();
        if resp: return resp
        try:
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute("DELETE FROM data_analyst_chats WHERE chat_id=%s AND user_id=%s", [chat_id, user.user_id])
            if cur.rowcount == 0:
                conn.rollback(); cur.close(); conn.close()
                return jsonify({"success": False, "message": "Chat introuvable"}), 404
            conn.commit(); cur.close(); conn.close()
            return jsonify({"success": True})
        except Exception as e:
            if 'conn' in locals(): conn.rollback(); cur.close(); conn.close()
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route('/admin/api/data-analyst/chats/<int:chat_id>/messages', methods=['GET'])
    def admin_api_da_messages_get(chat_id):
        user, resp = _require_admin();
        if resp: return resp
        limit = int(request.args.get('limit', 50))
        before_id = request.args.get('before_id')
        try:
            conn = get_db_connection(); cur = conn.cursor()
            # sécurité: s'assurer que le chat appartient à l'utilisateur
            cur.execute("SELECT 1 FROM data_analyst_chats WHERE chat_id=%s AND user_id=%s", [chat_id, user.user_id])
            if not cur.fetchone():
                cur.close(); conn.close()
                return jsonify({"success": False, "message": "Accès refusé"}), 403
            if before_id:
                cur.execute("""
                    SELECT message_id, user_message, bizzio_response, message_type, timestamp, analysis_type
                      FROM data_analyst_messages
                     WHERE chat_id=%s AND message_id < %s
                  ORDER BY message_id DESC
                     LIMIT %s
                """, [chat_id, before_id, limit])
            else:
                cur.execute("""
                    SELECT message_id, user_message, bizzio_response, message_type, timestamp, analysis_type
                      FROM data_analyst_messages
                     WHERE chat_id=%s
                  ORDER BY message_id DESC
                     LIMIT %s
                """, [chat_id, limit])
            rows = cur.fetchall()
            # renvoyer dans l'ordre chronologique ascendant
            rows = rows[::-1]
            messages = [{
                'message_id': r[0], 'user_message': r[1], 'bizzio_response': r[2],
                'message_type': r[3], 'timestamp': r[4].isoformat() if r[4] else None,
                'analysis_type': r[5]
            } for r in rows]
            has_more = len(rows) == limit
            last_id = rows[0][0] if rows else None
            cur.close(); conn.close()
            return jsonify({"success": True, "messages": messages, "has_more": has_more, "last_id": last_id})
        except Exception as e:
            if 'conn' in locals(): cur.close(); conn.close()
            return jsonify({"success": False, "message": str(e)}), 500

    # API d'envoi d'un message (sauvegarde + appel Gemini)
    @app.route("/admin/api/data-analyst/chat", methods=["POST"])
    def admin_api_data_analyst_chat():
        user, resp = _require_admin()
        if resp: return resp
        
        try:
            data = request.get_json()
            if not data or 'message' not in data:
                return jsonify({"success": False, "error": "Message requis"}), 400
            
            user_message = data['message'].strip()
            if not user_message:
                return jsonify({"success": False, "error": "Message vide"}), 400
            chat_id = data.get('chat_id')
            session_name = data.get('session_name', 'Nouvelle conversation')
            conn = get_db_connection(); cur = conn.cursor()
            # Créer une session si nécessaire
            if not chat_id:
                cur.execute("SELECT create_new_chat_session(%s, %s)", [user.user_id, session_name])
                chat_id = cur.fetchone()[0]
            # Sauvegarder le message utilisateur
            cur.execute("SELECT add_chat_message(%s, %s, %s, %s, %s)", [chat_id, 'user', user_message, None, None])
            _ = cur.fetchone()[0]
            
            # Import du module Gemini
            from GeminiHandler.gemini import BizzioGemini
            
            # Initialisation de Bizzio
            bizzio = BizzioGemini()
            
            # Envoi du message à Bizzio
            result = bizzio.chat_with_bizzio(user_message)
            
            if result['success']:
                # Sauvegarder la réponse de Bizzio
                cur.execute("SELECT add_chat_message(%s, %s, %s, %s, %s)", [chat_id, 'bizzio', None, result['response'], None])
                _ = cur.fetchone()[0]
                
                # Si c'est le premier message, générer un titre accrocheur via Gemini
                session_name = None
                cur.execute("SELECT session_name FROM data_analyst_chats WHERE chat_id = %s", [chat_id])
                current_name = cur.fetchone()[0]
                if current_name == 'Nouvelle conversation':
                    try:
                        # Générer un titre professionnel et accrocheur via Gemini
                        title_prompt = f"""Analyse cette question et génère un titre professionnel en une phrase courte (max 35 caractères) qui résume l'intention business:

Question: "{user_message}"

Règles:
- Titre en français uniquement
- Pas de deux-points (:)
- Pas de ponctuation finale
- Style professionnel et informatif
- Éviter les interjections courtes (yo, salut, etc.)

Réponds uniquement par le titre, sans guillemets ni explications."""
                        
                        title_response = bizzio.model.generate_content(title_prompt)
                        session_name = title_response.text.strip()
                        
                        # Nettoyer le titre
                        session_name = session_name.replace('"', '').replace("'", '').strip()
                        if session_name.endswith(':'):
                            session_name = session_name[:-1].strip()
                        if session_name.endswith('.') or session_name.endswith('!'):
                            session_name = session_name[:-1].strip()
                        
                        # Fallback si titre trop court ou vide
                        if not session_name or len(session_name) < 4:
                            # Extraire les mots clés principaux
                            words = user_message.lower().split()
                            key_words = [w for w in words if len(w) > 3 and w not in ['quels', 'sont', 'nos', 'les', 'plus', 'pour', 'avec', 'dans', 'sur', 'par']]
                            if key_words:
                                session_name = ' '.join(key_words[:3]).title()
                            else:
                                session_name = user_message[:35]
                    except Exception as e:
                        print(f"Erreur génération titre: {e}")
                        session_name = user_message[:35]
                    
                    cur.execute("""
                        UPDATE data_analyst_chats 
                           SET session_name = %s, updated_at = CURRENT_TIMESTAMP
                         WHERE chat_id = %s AND user_id = %s
                    """, [session_name, chat_id, user.user_id])
                
                conn.commit(); cur.close(); conn.close()
                return jsonify({
                    "success": True,
                    "response": result['response'],
                    "timestamp": result['timestamp'],
                    "model_used": result['model_used'],
                    "conversation_id": result['conversation_id'],
                    "chat_id": chat_id,
                    "session_name": session_name or current_name
                })
            else:
                conn.rollback(); cur.close(); conn.close()
                return jsonify({
                    "success": False,
                    "error": "Erreur lors du traitement du message"
                }), 500
                
        except Exception as e:
            print(f"Erreur dans admin_api_data_analyst_chat: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Erreur interne du serveur"
            }), 500

    # Onglet: Reporting
    @app.route("/admin/reporting", methods=["GET"])
    def admin_reporting():
        user, resp = _require_admin()
        if resp: return resp
        return render_template("reporting.html", admin=user)

    # ================== API REPORTING ANALYTIQUE ==================
    
    @app.route('/admin/api/reporting/filter-options', methods=['GET'])
    def admin_api_reporting_filter_options():
        """Récupérer les options disponibles pour les filtres"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Années distinctes - utiliser COALESCE pour proformas ET factures
            cur.execute("""
                SELECT DISTINCT EXTRACT(YEAR FROM COALESCE(p.date_creation, f.date_facture)) as annee
                FROM proformas p
                FULL OUTER JOIN factures f ON f.client_id = p.client_id
                WHERE COALESCE(p.date_creation, f.date_facture) IS NOT NULL
                AND (p.etat IN ('termine', 'terminé', 'partiel') OR f.statut IN ('termine', 'terminé', 'partiel'))
                ORDER BY annee DESC
            """)
            annees = [int(row[0]) for row in cur.fetchall()]
            
            # Villes distinctes - utiliser COALESCE
            cur.execute("""
                SELECT DISTINCT COALESCE(p.ville, f.ville) as ville
                FROM proformas p
                FULL OUTER JOIN factures f ON f.client_id = p.client_id
                WHERE COALESCE(p.ville, f.ville) IS NOT NULL 
                AND COALESCE(p.ville, f.ville) != ''
                AND (p.etat IN ('termine', 'terminé', 'partiel') OR f.statut IN ('termine', 'terminé', 'partiel'))
                ORDER BY ville
            """)
            villes = [row[0] for row in cur.fetchall()]
            
            # Types de prestations distincts
            cur.execute("""
                SELECT DISTINCT type_article
                FROM articles
                WHERE type_article IS NOT NULL AND type_article != ''
                ORDER BY type_article
            """)
            types = [row[0] for row in cur.fetchall()]
            
            # Agents distincts - inclure agents des proformas ET factures
            cur.execute("""
                SELECT DISTINCT u.user_id, u.nom_utilisateur
                FROM utilisateurs u
                WHERE u.role = 'secretaire' AND u.actif = TRUE
                AND (
                    EXISTS (SELECT 1 FROM proformas p WHERE p.cree_par = u.user_id)
                    OR EXISTS (SELECT 1 FROM factures f WHERE f.cree_par = u.user_id)
                )
                ORDER BY u.nom_utilisateur
            """)
            agents = [{"id": row[0], "nom": row[1]} for row in cur.fetchall()]
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "options": {
                    "annees": annees,
                    "villes": villes,
                    "types": types,
                    "agents": agents
                }
            })
            
        except Exception as e:
            print(f"❌ Erreur filter-options: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    @app.route('/admin/api/reporting/kpis', methods=['GET'])
    def admin_api_reporting_kpis():
        """Récupérer les KPIs de reporting avec filtres"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            # Récupérer les paramètres de filtrage
            filters = {
                'annee': request.args.get('annee', ''),
                'trimestre': request.args.get('trimestre', ''),
                'mois': request.args.get('mois', ''),
                'ville': request.args.get('ville', ''),
                'type_prestation': request.args.get('type', ''),
                'agent': request.args.get('agent', '')
            }
            
            # Supprimer les filtres vides
            filters = {k: v for k, v in filters.items() if v}
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Calculer les KPIs avec la nouvelle logique
            kpis = calculate_reporting_kpis(cur, filters)
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "kpis": kpis
            })
            
        except Exception as e:
            print(f"❌ Erreur reporting KPIs: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    @app.route('/admin/api/reporting/sparklines', methods=['GET'])
    def admin_api_reporting_sparklines():
        """Récupérer les données pour les sparklines des tendances temporelles"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            # Récupérer les paramètres de filtrage
            filters = {
                'annee': request.args.get('annee', ''),
                'trimestre': request.args.get('trimestre', ''),
                'mois': request.args.get('mois', ''),
                'ville': request.args.get('ville', ''),
                'type_prestation': request.args.get('type', ''),
                'agent': request.args.get('agent', '')
            }
            
            # Supprimer les filtres vides
            filters = {k: v for k, v in filters.items() if v}
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Construire les conditions WHERE et paramètres séparément pour chaque table
            proforma_conditions = []
            facture_conditions = []
            proforma_params = []
            facture_params = []
            
            # Filtre par année
            if filters.get('annee'):
                proforma_conditions.append("EXTRACT(YEAR FROM p.date_creation) = %s")
                facture_conditions.append("EXTRACT(YEAR FROM f.date_facture) = %s")
                proforma_params.append(filters['annee'])
                facture_params.append(filters['annee'])
            
            # Filtre par trimestre
            if filters.get('trimestre'):
                quarter_map = {'Q1': [1,2,3], 'Q2': [4,5,6], 'Q3': [7,8,9], 'Q4': [10,11,12]}
                months = quarter_map.get(filters['trimestre'], [])
                if months:
                    placeholders = ','.join(['%s'] * len(months))
                    proforma_conditions.append(f"EXTRACT(MONTH FROM p.date_creation) IN ({placeholders})")
                    facture_conditions.append(f"EXTRACT(MONTH FROM f.date_facture) IN ({placeholders})")
                    proforma_params.extend(months)
                    facture_params.extend(months)
            
            # Filtre par mois
            if filters.get('mois'):
                proforma_conditions.append("EXTRACT(MONTH FROM p.date_creation) = %s")
                facture_conditions.append("EXTRACT(MONTH FROM f.date_facture) = %s")
                proforma_params.append(filters['mois'])
                facture_params.append(filters['mois'])
            
            # Filtre par ville
            if filters.get('ville'):
                proforma_conditions.append("p.ville = %s")
                # Pour les factures, filtrer strictement par ville
                facture_conditions.append("f.ville = %s")
                proforma_params.append(filters['ville'])
                facture_params.append(filters['ville'])
            
            # Filtre par type de prestation (articles)
            if filters.get('type_prestation'):
                proforma_conditions.append("EXISTS (SELECT 1 FROM proforma_articles pa JOIN articles a ON a.article_id = pa.article_id WHERE pa.proforma_id = p.proforma_id AND a.type_article = %s)")
                facture_conditions.append("EXISTS (SELECT 1 FROM facture_articles fa JOIN articles a ON a.article_id = fa.article_id WHERE fa.facture_id = f.facture_id AND a.type_article = %s)")
                proforma_params.append(filters['type_prestation'])
                facture_params.append(filters['type_prestation'])
            
            # Filtre par agent
            if filters.get('agent'):
                proforma_conditions.append("p.cree_par = %s")
                # Pour les factures, inclure celles sans agent pour les anciennes factures
                facture_conditions.append("(f.cree_par = %s OR f.cree_par IS NULL)")
                proforma_params.append(filters['agent'])
                facture_params.append(filters['agent'])
            
            # Requête pour les données mensuelles - utiliser la même logique que les KPIs
            sparklines_query = f"""
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
                    WHERE p.etat IN ('termine', 'partiel')
            """
                    
            if proforma_conditions:
                sparklines_query += " AND " + " AND ".join(proforma_conditions)
                    
            sparklines_query += """
                    UNION ALL
                    SELECT 
                        TO_CHAR(f.date_facture, 'YYYY-MM') as mois,
                        COALESCE(f.montant_total, 0) AS ca,
                        f.facture_id AS id,
                        f.client_id,
                        0 AS articles
                    FROM factures f
                    WHERE f.statut IN ('termine', 'partiel')
            """
            
            if facture_conditions:
                sparklines_query += " AND " + " AND ".join(facture_conditions)
            
            sparklines_query += """
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
                LIMIT 12
            """
            
            # Combiner tous les paramètres
            all_params = proforma_params + facture_params
            
            try:
                cur.execute(sparklines_query, all_params)
                results = cur.fetchall()
                print(f"✅ Sparklines query executed successfully, {len(results)} results")
            except Exception as e:
                print(f"❌ Erreur sparklines: {e}")
                print(f"Query: {sparklines_query}")
                print(f"Params: {all_params}")
                results = []
            
            # Organiser les données pour les sparklines
            sparklines_data = {
                "labels": [],
                "chiffre_affaires": [],
                "ventes": [],
                "clients": [],
                "articles": []
            }

            for row in results:
                try:
                    sparklines_data["labels"].append(row[0] if len(row) > 0 else "")
                    sparklines_data["chiffre_affaires"].append(int(row[1] or 0) if len(row) > 1 else 0)
                    sparklines_data["ventes"].append(int(row[2] or 0) if len(row) > 2 else 0)
                    sparklines_data["clients"].append(int(row[3] or 0) if len(row) > 3 else 0)
                    sparklines_data["articles"].append(int(row[4] or 0) if len(row) > 4 else 0)
                except Exception as e:
                    print(f"❌ Erreur traitement ligne sparklines: {e}, row: {row}")
                    continue
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "sparklines": sparklines_data
            })
            
        except Exception as e:
            print(f"❌ Erreur sparklines: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
    @app.route('/admin/api/reporting/export', methods=['GET'])
    def admin_api_reporting_export():
        """Générer le rapport PDF avec WeasyPrint"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            # Récupérer les paramètres
            annee = request.args.get('annee', '')
            ville = request.args.get('ville', '')
            agent = request.args.get('agent', '')
            format_type = request.args.get('format', 'PDF')
            
            # Construire les filtres pour les KPIs
            filters = {}
            if annee:
                filters['annee'] = annee
            if ville:
                filters['ville'] = ville
            if agent:
                filters['agent'] = agent
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Calculer les KPIs avec filtres
            print(f"🔍 DEBUG EXPORT - Filtres reçus: {filters}")
            kpis = calculate_reporting_kpis(cur, filters)
            print(f"🔍 DEBUG EXPORT - KPIs calculés: {kpis}")
            
            # Récupérer les ventes détaillées avec filtres - LOGIQUE SIMPLE
            ventes_avec_details = []
            
            # Construire les conditions WHERE pour proformas
            proforma_conditions = []
            proforma_params = []
            
            if annee:
                proforma_conditions.append("EXTRACT(YEAR FROM p.date_creation) = %s")
                proforma_params.append(annee)
            
            if ville:
                proforma_conditions.append("p.ville = %s")
                proforma_params.append(ville)
            
            if agent:
                proforma_conditions.append("p.cree_par = %s")
                proforma_params.append(agent)
            
            # Toujours filtrer par statut terminé/partiel
            proforma_conditions.append("p.etat IN ('termine', 'terminé', 'partiel')")
            
            proforma_where = "WHERE " + " AND ".join(proforma_conditions) if proforma_conditions else ""
            
            # Requête pour les proformas
            cur.execute(f"""
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
                    p.etat,
                    p.proforma_id,
                    'proforma' as type_doc
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                LEFT JOIN utilisateurs u ON u.user_id = p.cree_par
                {proforma_where}
                ORDER BY p.date_creation DESC
            """, proforma_params)
            
            proformas = cur.fetchall()
            
            # Construire les conditions WHERE pour factures
            facture_conditions = []
            facture_params = []
            
            if annee:
                facture_conditions.append("EXTRACT(YEAR FROM f.date_facture) = %s")
                facture_params.append(annee)
            
            if ville:
                # Pour les factures, filtrer par ville OU inclure celles sans ville (anciennes factures)
                facture_conditions.append("(f.ville = %s OR f.ville IS NULL OR f.ville = '')")
                facture_params.append(ville)
            
            if agent:
                # Pour les factures, filtrer par cree_par ou inclure celles sans agent
                facture_conditions.append("(f.cree_par = %s OR f.cree_par IS NULL)")
                facture_params.append(agent)
            
            # Toujours filtrer par statut terminé/partiel
            facture_conditions.append("f.statut IN ('termine', 'terminé', 'partiel')")
            
            facture_where = "WHERE " + " AND ".join(facture_conditions) if facture_conditions else ""
            
            # Requête pour les factures
            cur.execute(f"""
                SELECT 
                    f.date_facture,
                    c.nom as client_nom,
                    c.telephone as client_telephone,
                    f.ville,
                    u.nom_utilisateur as agent_nom,
                    COALESCE(f.montant_total, 0) AS montant,
                    f.statut,
                    f.facture_id,
                    'facture' as type_doc
                FROM factures f
                LEFT JOIN clients c ON c.client_id = f.client_id
                LEFT JOIN utilisateurs u ON u.user_id = f.cree_par
                {facture_where}
                ORDER BY f.date_facture DESC
            """, facture_params)
            
            factures = cur.fetchall()
            
            # Combiner les résultats
            all_ventes = []
            for vente in proformas:
                all_ventes.append(vente)
            for vente in factures:
                all_ventes.append(vente)
            
            # Trier par date
            all_ventes.sort(key=lambda x: x[0], reverse=True)
            
            # Récupérer les détails des articles pour chaque vente
            for vente in all_ventes:
                document_id = vente[7]  # proforma_id ou facture_id
                type_doc = vente[8]     # 'proforma' ou 'facture'
                
                articles_list = []
                
                if type_doc == 'proforma':
                    # Récupérer les articles de la proforma
                    cur.execute("""
                        SELECT a.designation, pa.quantite, a.prix, pa.quantite * a.prix as total
                        FROM proforma_articles pa
                        JOIN articles a ON a.article_id = pa.article_id
                        WHERE pa.proforma_id = %s
                    """, (document_id,))
                    articles = cur.fetchall()
                    
                    for article in articles:
                        articles_list.append({
                            'designation': article[0],
                            'quantite': article[1],
                            'prix': article[2],
                            'total': article[3]
                        })
                
                elif type_doc == 'facture':
                    # Récupérer les articles de la facture
                    cur.execute("""
                        SELECT a.designation, fa.quantite, fa.prix_unitaire, fa.quantite * fa.prix_unitaire as total
                        FROM facture_articles fa
                        JOIN articles a ON a.article_id = fa.article_id
                        WHERE fa.facture_id = %s
                    """, (document_id,))
                    articles = cur.fetchall()
                    
                    if articles:
                        # Facture avec détails d'articles
                        for article in articles:
                            articles_list.append({
                                'designation': article[0],
                                'quantite': article[1],
                                'prix': article[2],
                                'total': article[3]
                            })
                    else:
                        # Facture sans détails (ancien système)
                        articles_list.append({
                            'designation': 'Non Renseigné',
                            'quantite': 1,
                            'prix': 0,
                            'total': 0
                        })
                
                ventes_avec_details.append({
                    'date_creation': vente[0],
                    'date': vente[0],
                    'client_nom': vente[1],
                    'nom_client': vente[1],
                    'total_ttc': vente[5],
                    'articles': articles_list
                })
            
            # Construire les conditions spécifiques pour factures
            facture_conditions = []
            facture_params = []
            
            if annee:
                facture_conditions.append("EXTRACT(YEAR FROM f.date_facture) = %s")
                facture_params.append(annee)
            
            if ville:
                # Pour les factures, filtrer par ville ou inclure celles sans ville si "Toutes"
                if ville.lower() == 'toutes':
                    # Ne pas filtrer par ville pour les factures anciennes
                    pass
                else:
                    facture_conditions.append("(f.ville = %s OR f.ville IS NULL)")
                    facture_params.append(ville)
            
            if agent:
                # Pour les factures, filtrer par cree_par ou inclure celles sans agent
                facture_conditions.append("(f.cree_par = %s OR f.cree_par IS NULL)")
                facture_params.append(agent)
            
            facture_where = "WHERE f.statut IN ('termine', 'terminé', 'partiel')" + (" AND " + " AND ".join(facture_conditions) if facture_conditions else "")
            
            # Requête pour les factures
            cur.execute(f"""
                SELECT 
                    f.date_facture,
                    c.nom as client_nom,
                    c.telephone as client_telephone,
                    f.ville,
                    u.nom_utilisateur as agent_nom,
                    f.montant_total AS montant,
                    f.statut,
                    f.facture_id,
                    'facture' as type_doc
                FROM factures f
                LEFT JOIN clients c ON c.client_id = f.client_id
                LEFT JOIN utilisateurs u ON u.user_id = f.cree_par
                {facture_where}
                ORDER BY f.date_facture DESC
            """, facture_params)
            
            factures = cur.fetchall()
            
            # Combiner les résultats
            all_ventes = []
            for vente in proformas:
                all_ventes.append(vente)
            for vente in factures:
                all_ventes.append(vente)
            
            # Trier par date
            all_ventes.sort(key=lambda x: x[0], reverse=True)
            
            # Récupérer les détails des articles pour chaque vente
            for vente in all_ventes:
                document_id = vente[7]  # proforma_id ou facture_id
                type_doc = vente[8]     # 'proforma' ou 'facture'
                
                if not document_id or not isinstance(document_id, int):
                    # Créer une entrée avec message d'ancien système
                    ventes_avec_details.append({
                    'date_creation': vente[0],
                    'date': vente[0],
                    'client_nom': vente[1],
                    'nom_client': vente[1],
                    'total_ttc': vente[5],
                    'statut': vente[6],  # Ajouter le statut
                    'etat': vente[6],    # Alias pour compatibilité
                    'articles': [{
                        'designation': 'Non Renseigné',
                        'nom': 'Non Renseigné',
                        'quantite': 1,
                        'prix': vente[5] or 0,
                        'total': vente[5] or 0
                    }]
                })
                continue
                
                # Récupérer les articles selon le type de document
                if type_doc == 'proforma':
                    cur.execute("""
                        SELECT a.designation, pa.quantite, a.prix, (pa.quantite * a.prix) as total
                        FROM proforma_articles pa
                        JOIN articles a ON a.article_id = pa.article_id
                        WHERE pa.proforma_id = %s
                        ORDER BY a.designation
                    """, (document_id,))
                else:  # facture
                    cur.execute("""
                        SELECT a.designation, fa.quantite, fa.prix_unitaire, (fa.quantite * fa.prix_unitaire) as total
                        FROM facture_articles fa
                        JOIN articles a ON a.article_id = fa.article_id
                        WHERE fa.facture_id = %s
                        ORDER BY a.designation
                    """, (document_id,))
                
                articles = cur.fetchall()
                
                # Construire la structure des articles
                articles_list = []
                for article in articles:
                    articles_list.append({
                        'designation': article[0],
                        'nom': article[0],
                        'quantite': article[1],
                        'prix': article[2],
                        'total': article[3]
                    })
                
                ventes_avec_details.append({
                    'date_creation': vente[0],
                    'date': vente[0],
                    'client_nom': vente[1],
                    'nom_client': vente[1],
                    'total_ttc': vente[5],
                    'articles': articles_list
                })
            
            # Récupérer le nom de l'agent si un agent est sélectionné
            agent_nom = None
            if agent:
                cur.execute("SELECT nom_utilisateur FROM utilisateurs WHERE user_id = %s", (agent,))
                result = cur.fetchone()
                if result:
                    agent_nom = result[0]
            
            cur.close()
            conn.close()
            
            # Générer le PDF avec WeasyPrint
            html_content = render_template('reporting_template.html',
                ventes=ventes_avec_details,
                annee=annee or datetime.now().year,
                ville=ville or 'Toutes',
                pays='Cameroun',
                date_generation=datetime.now().strftime('%d/%m/%Y'),
                chiffre_affaires=kpis['ca'],
                nombre_ventes=kpis['ventes'],
                nombre_clients=kpis['nouveaux_clients'],
                clients_uniques=kpis['nouveaux_clients'],
                agent_selectionne=agent_nom  # Passer le nom de l'agent pour affichage conditionnel
            )
            
            # Générer le PDF
            pdf_content = HTML(string=html_content).write_pdf()
            
            # Créer la réponse
            response = make_response(pdf_content)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=rapport_{annee or datetime.now().year}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
            
            return response
            
        except Exception as e:
            print(f"❌ Erreur génération PDF: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
    def admin_api_reporting_monthly_detail():
        """Récupérer le détail mensuel pour les sparklines"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            # Récupérer les paramètres de filtrage
            annee = request.args.get('annee', '')
            trimestre = request.args.get('trimestre', '')
            mois = request.args.get('mois', '')
            ville = request.args.get('ville', '')
            type_prestation = request.args.get('type', '')
            agent = request.args.get('agent', '')
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Construire les conditions WHERE D'ABORD
            where_conditions = []
            params = []
            
            # Filtre temporel
            if annee:
                where_conditions.append("EXTRACT(YEAR FROM COALESCE(p.date_creation, f.date_facture)) = %s")
                params.append(annee)
            
            if trimestre:
                quarter_map = {'Q1': [1,2,3], 'Q2': [4,5,6], 'Q3': [7,8,9], 'Q4': [10,11,12]}
                months = quarter_map.get(trimestre, [])
                if months:
                    placeholders = ','.join(['%s'] * len(months))
                    where_conditions.append(f"EXTRACT(MONTH FROM COALESCE(p.date_creation, f.date_facture)) IN ({placeholders})")
                    params.extend(months)
            
            if mois:
                where_conditions.append("EXTRACT(MONTH FROM COALESCE(p.date_creation, f.date_facture)) = %s")
                params.append(mois)
            
            # Filtres métier
            if ville:
                where_conditions.append("COALESCE(p.ville, f.ville) = %s")
                params.append(ville)
            
            if type_prestation:
                where_conditions.append("(p.proforma_id IS NULL OR EXISTS (SELECT 1 FROM proforma_articles pa JOIN articles a ON a.article_id = pa.article_id WHERE pa.proforma_id = p.proforma_id AND a.type_article = %s))")
                params.append(type_prestation)
            
            if agent:
                where_conditions.append("(p.cree_par = %s OR f.agent = (SELECT nom_utilisateur FROM utilisateurs WHERE user_id = %s))")
                params.extend([agent, agent])
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Utiliser la même logique que les sparklines mais avec plus de détails
            monthly_query = f"""
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
                    WHERE p.etat IN ('termine', 'partiel')
                    {where_clause.replace('COALESCE(p.date_creation, f.date_facture)', 'p.date_creation').replace('COALESCE(p.ville, f.ville)', 'p.ville').replace('(p.cree_par = %s OR f.agent = (SELECT nom_utilisateur FROM utilisateurs WHERE user_id = %s))', 'p.cree_par = %s')}
                    
                    UNION ALL
                    
                    SELECT 
                        TO_CHAR(f.date_facture, 'YYYY-MM') as mois,
                        f.montant_total AS ca,
                        f.facture_id AS id,
                        f.client_id,
                        0 AS articles
                    FROM factures f
                    WHERE f.statut IN ('termine', 'partiel')
                    {where_clause.replace('COALESCE(p.date_creation, f.date_facture)', 'f.date_facture').replace('COALESCE(p.ville, f.ville)', 'f.ville').replace('(p.cree_par = %s OR f.agent = (SELECT nom_utilisateur FROM utilisateurs WHERE user_id = %s))', 'f.agent = (SELECT nom_utilisateur FROM utilisateurs WHERE user_id = %s)')}
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
                LIMIT 12
            """
            
            # Appliquer les filtres à la requête monthly_query
            if not any([annee, trimestre, mois]):
                monthly_query = monthly_query.replace('{where_clause}', 'AND p.date_creation >= CURRENT_DATE - INTERVAL \'12 months\'')
                monthly_query = monthly_query.replace('{where_clause}', 'AND f.date_facture >= CURRENT_DATE - INTERVAL \'12 months\'')
            else:
                # Remplacer les placeholders par les vraies conditions
                proformas_conditions = where_clause.replace('COALESCE(p.date_creation, f.date_facture)', 'p.date_creation').replace('COALESCE(p.ville, f.ville)', 'p.ville').replace('(p.cree_par = %s OR f.agent = (SELECT nom_utilisateur FROM utilisateurs WHERE user_id = %s))', 'p.cree_par = %s').replace('WHERE ', 'AND ')
                factures_conditions = where_clause.replace('COALESCE(p.date_creation, f.date_facture)', 'f.date_facture').replace('COALESCE(p.ville, f.ville)', 'f.ville').replace('(p.cree_par = %s OR f.agent = (SELECT nom_utilisateur FROM utilisateurs WHERE user_id = %s))', 'f.agent = (SELECT nom_utilisateur FROM utilisateurs WHERE user_id = %s)').replace('WHERE ', 'AND ')
                monthly_query = monthly_query.replace('{where_clause}', proformas_conditions)
                monthly_query = monthly_query.replace('{where_clause}', factures_conditions)
            
            try:
                cur.execute(monthly_query, params)
                results = cur.fetchall()
            except Exception as e:
                print(f"❌ Erreur monthly detail: {e}")
                results = []
            
            # Organiser les données pour le détail
            monthly_detail = []
            for row in results:
                try:
                    # Convertir le format "2025-10" en "October 2025"
                    mois_raw = row[0] if len(row) > 0 else ""
                    mois_nom = ""
                    if mois_raw:
                        try:
                            year, month = mois_raw.split('-')
                            month_names = {
                                '01': 'January', '02': 'February', '03': 'March', '04': 'April',
                                '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                                '09': 'September', '10': 'October', '11': 'November', '12': 'December'
                            }
                            mois_nom = f"{month_names.get(month, month)} {year}"
                        except:
                            mois_nom = mois_raw
                    
                    monthly_detail.append({
                        "mois": mois_raw,
                        "mois_nom": mois_nom,
                        "chiffre_affaires": int(row[1] or 0) if len(row) > 1 else 0,
                        "ventes_factures": int(row[2] or 0) if len(row) > 2 else 0,
                        "ventes_proformas": 0,  # Pas utilisé dans la requête simple
                        "clients_factures": int(row[3] or 0) if len(row) > 3 else 0,
                        "clients_proformas": 0,  # Pas utilisé dans la requête simple
                        "articles": int(row[4] or 0) if len(row) > 4 else 0
                    })
                except Exception as e:
                    print(f"❌ Erreur traitement ligne monthly detail: {e}, row: {row}")
                    continue
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "monthly_detail": monthly_detail
            })
            
        except Exception as e:
            print(f"❌ Erreur monthly detail: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    @app.route('/admin/api/reporting/prestation-performance', methods=['GET'])
    def admin_api_reporting_prestation_performance():
        """Récupérer les performances par prestation et ville"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête pour les performances par prestation - SEULEMENT TERMINÉ/PARTIEL
            prestation_query = """
                WITH all_prestations AS (
                    SELECT DISTINCT a.type_article as prestation
                    FROM articles a
                ),
                prestation_data AS (
                    SELECT 
                        ap.prestation,
                        COALESCE(SUM(
                            CASE 
                                WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN pa.quantite * a.prix
                                ELSE 0
                            END
                        ), 0) as ca_total,
                        COALESCE(COUNT(DISTINCT 
                            CASE 
                                WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN p.proforma_id
                                ELSE NULL
                            END
                        ), 0) as nb_commandes,
                        COALESCE(COUNT(DISTINCT 
                            CASE 
                                WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN p.client_id
                                ELSE NULL
                            END
                        ), 0) as nb_clients
                    FROM all_prestations ap
                    LEFT JOIN articles a ON a.type_article = ap.prestation
                    LEFT JOIN proforma_articles pa ON pa.article_id = a.article_id
                    LEFT JOIN proformas p ON p.proforma_id = pa.proforma_id
                    GROUP BY ap.prestation
                )
                SELECT 
                    prestation,
                    ca_total,
                    nb_commandes,
                    nb_clients,
                    CASE 
                        WHEN SUM(ca_total) OVER() > 0 THEN ROUND((ca_total * 100.0 / SUM(ca_total) OVER()), 1)
                        ELSE 0
                    END as pourcentage
                FROM prestation_data
                ORDER BY ca_total DESC
            """
            
            cur.execute(prestation_query)
            prestations = cur.fetchall()
            
            # Requête pour les performances par ville - UTILISER LA REQUÊTE QUI FONCTIONNE
            ville_query = """
                SELECT 
                    COALESCE(p.ville, f.ville) AS ville,
                    COALESCE(SUM(
                        CASE 
                            WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN
                                COALESCE(
                                    (SELECT SUM(pa.quantite * a.prix) 
                                    FROM proforma_articles pa 
                                    JOIN articles a ON a.article_id = pa.article_id 
                                    WHERE pa.proforma_id = p.proforma_id), 0
                                ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                            ELSE 0
                        END
                    ), 0) +
                    COALESCE(SUM(
                        CASE 
                            WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.montant_total 
                            ELSE 0 
                        END
                    ), 0) AS ca_total,
                    COUNT(DISTINCT 
                        CASE 
                            WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN p.proforma_id
                            ELSE NULL
                        END
                    ) + 
                    COUNT(DISTINCT 
                        CASE 
                            WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.facture_id
                            ELSE NULL
                        END
                    ) as nb_commandes,
                    COUNT(DISTINCT 
                        CASE 
                            WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN p.client_id
                            ELSE NULL
                        END
                    ) + 
                    COUNT(DISTINCT 
                        CASE 
                            WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.client_id
                            ELSE NULL
                        END
                    ) as nb_clients
                FROM proformas p
                FULL OUTER JOIN factures f ON f.client_id = p.client_id
                WHERE (p.etat IN ('termine', 'terminé', 'partiel') OR f.statut IN ('termine', 'terminé', 'partiel'))
                AND COALESCE(p.ville, f.ville) IS NOT NULL
                GROUP BY COALESCE(p.ville, f.ville)
                ORDER BY ca_total DESC
            """
            
            cur.execute(ville_query)
            villes = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Formater les données des prestations
            prestation_data = []
            for row in prestations:
                prestation_data.append({
                    "prestation": row[0],
                    "ca_total": int(row[1] or 0),
                    "nb_commandes": int(row[2] or 0),
                    "nb_clients": int(row[3] or 0),
                    "pourcentage": float(row[4] or 0)
                })
            
            # Calculer le pourcentage pour chaque ville
            total_ca_villes = sum(int(row[1] or 0) for row in villes)
            
            ville_data = []
            for row in villes:
                ca_ville = int(row[1] or 0)
                pourcentage = round((ca_ville * 100.0 / total_ca_villes), 1) if total_ca_villes > 0 else 0
                
                ville_data.append({
                    "ville": row[0],
                    "ca_total": ca_ville,
                    "nb_commandes": int(row[2] or 0),
                    "nb_clients": int(row[3] or 0),
                    "pourcentage": pourcentage
                })
            
            return jsonify({
                "success": True,
                "prestations": prestation_data,
                "villes": ville_data
            })
            
        except Exception as e:
            print(f"❌ Erreur prestation performance: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500



    @app.route('/admin/api/reporting/ventes-region', methods=['GET'])
    def admin_api_reporting_ventes_region():
        """API pour récupérer les ventes par région (villes)"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête pour les ventes par ville (factures seulement)
            query = """
                SELECT 
                    ville,
                    COUNT(*) as nb_commandes,
                    SUM(montant_total) as ca_total
                FROM factures 
                WHERE statut != 'annule'
                GROUP BY ville
                ORDER BY nb_commandes DESC
                LIMIT 10
            """
            
            cur.execute(query)
            results = cur.fetchall()
            
            # Calculer le total pour les pourcentages
            total_commandes = sum(row[1] for row in results)
            
            regions = []
            for row in results:
                ville, nb_commandes, ca_total = row
                pourcentage = (nb_commandes / total_commandes * 100) if total_commandes > 0 else 0
                
                regions.append({
                    'ville': ville,
                    'nb_commandes': nb_commandes,
                    'ca_total': float(ca_total or 0),
                    'pourcentage': round(pourcentage, 1)
                })
            
            return jsonify({
                "success": True,
                "regions": regions
            })
            
        except Exception as e:
            print(f"Erreur ventes région: {e}")
            return jsonify({
                "success": False,
                "message": str(e)
            })
        finally:
            if 'conn' in locals():
                conn.close()

    @app.route('/admin/api/reporting/top-articles', methods=['GET'])
    def admin_api_reporting_top_articles():
        """API pour récupérer les articles les plus vendus"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête pour les articles les plus vendus (factures + proformas)
            query = """
                WITH article_stats AS (
                    SELECT 
                        a.designation as nom,
                        a.prix,
                        SUM(fa.quantite) as total_quantite,
                        SUM(fa.quantite * a.prix) as ca_total,
                        COUNT(DISTINCT f.facture_id) as nb_commandes
                    FROM articles a
                    JOIN facture_articles fa ON fa.article_id = a.article_id
                    JOIN factures f ON f.facture_id = fa.facture_id
                    WHERE f.statut != 'annule'
                    GROUP BY a.article_id, a.designation, a.prix
                    
                    UNION ALL
                    
                    SELECT 
                        a.designation as nom,
                        a.prix,
                        SUM(pa.quantite) as total_quantite,
                        SUM(pa.quantite * a.prix) as ca_total,
                        COUNT(DISTINCT p.proforma_id) as nb_commandes
                    FROM articles a
                    JOIN proforma_articles pa ON pa.article_id = a.article_id
                    JOIN proformas p ON p.proforma_id = pa.proforma_id
                    WHERE p.etat = 'termine'
                    GROUP BY a.article_id, a.designation, a.prix
                )
                SELECT 
                    nom,
                    SUM(total_quantite) as total_quantite,
                    SUM(ca_total) as ca_total,
                    SUM(nb_commandes) as nb_commandes
                FROM article_stats
                WHERE nom IS NOT NULL AND nom != ''
                GROUP BY nom
                ORDER BY ca_total DESC
                LIMIT 5
            """
            
            cur.execute(query)
            results = cur.fetchall()
            
            # Calculer le total CA pour les pourcentages
            total_ca = sum(row[2] for row in results)
            
            articles = []
            for row in results:
                nom, total_quantite, ca_total, nb_commandes = row
                part = (ca_total / total_ca * 100) if total_ca > 0 else 0
                
                articles.append({
                    'nom': nom,
                    'quantite': int(total_quantite or 0),
                    'ca': float(ca_total or 0),
                    'commandes': int(nb_commandes or 0),
                    'part': round(part, 1)
                })
            
            return jsonify({
                "success": True,
                "articles": articles
            })
            
        except Exception as e:
            print(f"Erreur top articles: {e}")
            return jsonify({"success": False, "message": str(e)})
        finally:
            if 'conn' in locals():
                conn.close()

    @app.route('/admin/api/articles/search', methods=['GET'])
    def admin_api_articles_search():
        """API pour rechercher des articles par nom et récupérer leurs prix"""
        try:
            search_term = request.args.get('q', '').strip()
            if not search_term:
                return jsonify({"success": False, "message": "Terme de recherche requis"})
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Recherche d'articles par nom (insensible à la casse et tolérante aux erreurs)
            # D'abord essayer une recherche exacte
            query = """
                SELECT 
                    article_id,
                    designation,
                    prix,
                    type_article,
                    code
                FROM articles 
                WHERE LOWER(designation) LIKE LOWER(%s)
                ORDER BY designation ASC
                LIMIT 10
            """
            
            # Recherche insensible à la casse
            search_pattern = f'%{search_term.lower()}%'
            cur.execute(query, (search_pattern,))
            results = cur.fetchall()
            
            articles = []
            for row in results:
                articles.append({
                    'id': row[0],
                    'nom': row[1],
                    'prix': float(row[2]),
                    'type': row[3],
                    'code': row[4]
                })
            
            # Si pas de résultats, essayer une recherche plus large
            if not articles:
                # Recherche par mots-clés individuels
                words = search_term.split()
                if len(words) >= 2:
                    # Essayer avec les 2 premiers mots
                    short_term = ' '.join(words[:2])
                    short_pattern = f'%{short_term.lower()}%'
                    cur.execute(query, (short_pattern,))
                    results = cur.fetchall()
                    
                    for row in results:
                        articles.append({
                            'id': row[0],
                            'nom': row[1],
                            'prix': float(row[2]),
                            'type': row[3],
                            'code': row[4]
                        })
                
                # Si toujours pas de résultats, essayer une recherche par mots individuels
                if not articles:
                    for word in words:
                        if len(word) > 3:  # Ignorer les mots trop courts
                            word_pattern = f'%{word.lower()}%'
                            cur.execute(query, (word_pattern,))
                            results = cur.fetchall()
                            
                            for row in results:
                                articles.append({
                                    'id': row[0],
                                    'nom': row[1],
                                    'prix': float(row[2]),
                                    'type': row[3],
                                    'code': row[4]
                                })
                            
                            if articles:  # Arrêter dès qu'on trouve quelque chose
                                break
            
            return jsonify({
                "success": True,
                "articles": articles,
                "search_term": search_term
            })
            
        except Exception as e:
            print(f"Erreur recherche articles: {e}")
            return jsonify({"success": False, "message": str(e)})
        finally:
            if 'conn' in locals():
                conn.close()

    @app.route('/admin/api/articles/export', methods=['GET'])
    def admin_api_articles_export():
        """API pour exporter la liste complète des articles"""
        try:
            export_format = request.args.get('format', 'json')  # json, csv, excel
            limit_param = request.args.get('limit', '100')
            limit = int(limit_param) if limit_param and limit_param != 'None' else None
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            if limit is None:
                query = """
                    SELECT 
                        article_id,
                        designation,
                        prix,
                        type_article,
                        code,
                        nature,
                        classe
                    FROM articles 
                    WHERE designation IS NOT NULL AND designation != ''
                    ORDER BY prix DESC, designation ASC
                """
                cur.execute(query)
            else:
                query = """
                    SELECT 
                        article_id,
                        designation,
                        prix,
                        type_article,
                        code,
                        nature,
                        classe
                    FROM articles 
                    WHERE designation IS NOT NULL AND designation != ''
                    ORDER BY prix DESC, designation ASC
                    LIMIT %s
                """
                cur.execute(query, (limit,))
            results = cur.fetchall()
            
            # Compter le nombre total d'articles
            count_query = """
                SELECT COUNT(*) 
                FROM articles 
                WHERE designation IS NOT NULL AND designation != ''
            """
            cur.execute(count_query)
            total_count = cur.fetchone()[0]
            
            articles = []
            for row in results:
                articles.append({
                    'id': row[0],
                    'nom': row[1],
                    'prix': float(row[2]),
                    'type': row[3],
                    'code': row[4],
                    'nature': row[5],
                    'classe': row[6]
                })
            
            if export_format == 'csv':
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['ID', 'Nom', 'Prix (FCFA)', 'Type', 'Code', 'Nature', 'Classe'])
                
                for article in articles:
                    writer.writerow([
                        article['id'],
                        article['nom'],
                        article['prix'],
                        article['type'],
                        article['code'],
                        article['nature'] or '',
                        article['classe'] or ''
                    ])
                
                output.seek(0)
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = 'attachment; filename=articles_bizzio.csv'
                return response
            
            elif export_format == 'excel':
                import pandas as pd
                import io
                
                df = pd.DataFrame(articles)
                output = io.BytesIO()
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Articles', index=False)
                
                output.seek(0)
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                response.headers['Content-Disposition'] = 'attachment; filename=articles_bizzio.xlsx'
                return response
            
            else:  # json par défaut
                return jsonify({
                    "success": True,
                    "articles": articles,
                    "total": len(articles),
                    "total_articles": total_count,
                    "format": export_format
                })
            
        except Exception as e:
            print(f"Erreur export articles: {e}")
            return jsonify({"success": False, "message": str(e)})
        finally:
            if 'conn' in locals():
                conn.close()

    @app.route('/admin/api/articles/top', methods=['GET'])
    def admin_api_articles_top():
        """API pour récupérer le top des articles les plus vendus"""
        try:
            limit = int(request.args.get('limit', 5))
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête pour récupérer les articles les plus vendus
            query = """
                SELECT 
                    a.article_id,
                    a.designation,
                    a.prix,
                    a.type_article,
                    a.code,
                    COALESCE(SUM(d.quantite), 0) as quantite_vendue
                FROM articles a
                LEFT JOIN details_vente d ON a.article_id = d.article_id
                WHERE a.designation IS NOT NULL AND a.designation != ''
                GROUP BY a.article_id, a.designation, a.prix, a.type_article, a.code
                ORDER BY quantite_vendue DESC, a.prix DESC
                LIMIT %s
            """
            
            cur.execute(query, (limit,))
            results = cur.fetchall()
            
            articles = []
            for row in results:
                articles.append({
                    'id': row[0],
                    'nom': row[1],
                    'prix': float(row[2]),
                    'type': row[3],
                    'code': row[4],
                    'quantite_vendue': int(row[5])
                })
            
            # Note sur les données
            note = "Tous ont été vendus en 2 exemplaires. Peut-être" if len(articles) > 0 else "Aucun article trouvé"
            
            return jsonify({
                "success": True,
                "articles": articles,
                "total": len(articles),
                "note": note
            })
            
        except Exception as e:
            print(f"Erreur top articles: {e}")
            return jsonify({"success": False, "message": str(e)})
        finally:
            if 'conn' in locals():
                conn.close()

    @app.route('/admin/api/articles/random', methods=['GET'])
    def admin_api_articles_random():
        """API pour récupérer des articles aléatoires avec leurs prix"""
        try:
            limit = int(request.args.get('limit', 5))
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête pour récupérer des articles aléatoires
            query = """
                SELECT 
                    article_id,
                    designation,
                    prix,
                    type_article,
                    code,
                    nature,
                    classe
                FROM articles 
                WHERE designation IS NOT NULL AND designation != ''
                ORDER BY RANDOM()
                LIMIT %s
            """
            
            cur.execute(query, (limit,))
            results = cur.fetchall()
            
            articles = []
            for row in results:
                articles.append({
                    'id': row[0],
                    'nom': row[1],
                    'prix': float(row[2]),
                    'type': row[3],
                    'code': row[4],
                    'nature': row[5],
                    'classe': row[6]
                })
            
            return jsonify({
                "success": True,
                "articles": articles,
                "total": len(articles)
            })
            
        except Exception as e:
            print(f"Erreur articles aléatoires: {e}")
            return jsonify({"success": False, "message": str(e)})
        finally:
            if 'conn' in locals():
                conn.close()

    @app.route('/uploads/<filename>')
    def serve_uploaded_file(filename):
        """Serve les fichiers générés par Bizzio"""
        try:
            # Si c'est une image (PNG, JPG, etc.), la servir comme image
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                return send_file(f'uploads/{filename}', mimetype='image/png')
            else:
                # Sinon, servir comme fichier à télécharger
                return send_file(f'uploads/{filename}', as_attachment=True)
        except Exception as e:
            return jsonify({"error": f"File not found: {filename}"}), 404

    @app.route('/admin/api/reporting/meilleurs-clients', methods=['GET'])
    def admin_api_reporting_meilleurs_clients():
        """API pour récupérer le top 5 des meilleurs clients"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête pour les meilleurs clients (proformas + factures terminées)
            query = """
                WITH all_clients AS (
                    -- Proformas terminées/partielles
                    SELECT 
                        c.client_id,
                        c.nom,
                        COUNT(p.proforma_id) as nb_commandes,
                        SUM(
                            COALESCE(
                                (SELECT SUM(pa.quantite * a.prix) 
                                FROM proforma_articles pa 
                                JOIN articles a ON a.article_id = pa.article_id 
                                WHERE pa.proforma_id = p.proforma_id), 0
                            ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                        ) as ca_total
                    FROM proformas p
                    JOIN clients c ON c.client_id = p.client_id
                    WHERE p.etat IN ('termine', 'partiel')
                    AND LOWER(c.nom) NOT LIKE '%boutique%'
                    AND LOWER(c.nom) NOT LIKE '%vente%'
                    GROUP BY c.client_id, c.nom
                    
                    UNION ALL
                    
                    -- Factures terminées/partielles
                    SELECT 
                        c.client_id,
                        c.nom,
                        COUNT(f.facture_id) as nb_commandes,
                        SUM(COALESCE(f.montant_total, 0)) as ca_total
                    FROM factures f
                    JOIN clients c ON c.client_id = f.client_id
                    WHERE f.statut IN ('termine', 'partiel')
                    AND LOWER(c.nom) NOT LIKE '%boutique%'
                    AND LOWER(c.nom) NOT LIKE '%vente%'
                    GROUP BY c.client_id, c.nom
                )
                SELECT 
                    nom,
                    SUM(nb_commandes) as total_commandes,
                    SUM(ca_total) as total_ca
                FROM all_clients
                GROUP BY client_id, nom
                HAVING SUM(ca_total) > 0
                ORDER BY total_ca DESC, total_commandes DESC
                LIMIT 5
            """
            
            cur.execute(query)
            results = cur.fetchall()
            
            # Calculer le total CA pour les pourcentages
            total_ca = sum(row[2] for row in results)
            
            clients = []
            for row in results:
                nom, nb_commandes, ca_total = row
                pourcentage = (ca_total / total_ca * 100) if total_ca > 0 else 0
                
                clients.append({
                    'nom': nom,
                    'nb_commandes': nb_commandes,
                    'ca_total': ca_total,
                    'pourcentage': round(pourcentage, 1)
                })
            
            return jsonify({
                "success": True,
                "clients": clients
            })
            
        except Exception as e:
            print(f"Erreur meilleurs clients: {e}")
            return jsonify({
                "success": False,
                "message": str(e)
            })
        finally:
            if 'conn' in locals():
                conn.close()
        """Récupérer le top 5 des articles des proformas terminés/partiels"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête SQL pour les détails des articles des proformas terminés/partiels
            articles_query = """
                SELECT 
                    a.designation as nom_article,
                    a.type_article as prestation,
                    SUM(pa.quantite * a.prix) AS ca_total,
                    COUNT(DISTINCT p.proforma_id) AS commandes,
                    ROUND((SUM(pa.quantite * a.prix) * 100.0 / (
                        SELECT SUM(pa2.quantite * a2.prix) 
                        FROM proforma_articles pa2 
                        JOIN articles a2 ON a2.article_id = pa2.article_id
                        JOIN proformas p2 ON p2.proforma_id = pa2.proforma_id
                        WHERE p2.etat IN ('termine', 'terminé', 'partiel')
                    )), 1) AS pourcentage
                FROM proforma_articles pa
                JOIN articles a ON a.article_id = pa.article_id
                JOIN proformas p ON p.proforma_id = pa.proforma_id
                WHERE p.etat IN ('termine', 'terminé', 'partiel')
                GROUP BY a.article_id, a.designation, a.type_article
                ORDER BY ca_total DESC
                LIMIT 5
            """
            
            cur.execute(articles_query)
            articles_results = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Formater les articles avec le design PERFORMANCE PAR VILLE
            articles = []
            for row in articles_results:
                articles.append({
                    "nom": row[0],  # designation
                    "prestation": row[1],  # type_article
                    "ca": format_currency(row[2] or 0),
                    "commandes": format_number(row[3] or 0),
                    "part": row[4] or 0
                })
            
            return jsonify({
                "success": True,
                "articles": articles
            })
            
        except Exception as e:
            print(f"❌ Erreur top articles: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500
            
            # Requête pour l'année courante
            current_year_query = f"""
                SELECT 
                    COALESCE(SUM(
                        CASE 
                            WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN
                                COALESCE(
                                    (SELECT SUM(pa.quantite * a.prix) 
                                    FROM proforma_articles pa 
                                    JOIN articles a ON a.article_id = pa.article_id 
                                    WHERE pa.proforma_id = p.proforma_id), 0
                                ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                            ELSE 0
                        END
                    ), 0) +
                    COALESCE(SUM(
                        CASE 
                            WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.montant_total 
                            ELSE 0 
                        END
                    ), 0) AS chiffre_affaires,
                    
                    COUNT(DISTINCT CASE WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.facture_id END) +
                    COUNT(DISTINCT CASE WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN p.proforma_id END) AS ventes,
                    
                    COUNT(DISTINCT CASE WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.client_id END) +
                    COUNT(DISTINCT CASE WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN p.client_id END) AS clients,
                    
                    COALESCE(SUM(CASE WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN pa.quantite ELSE 0 END), 0) AS articles

                FROM proformas p
                FULL OUTER JOIN factures f ON f.client_id = p.client_id
                LEFT JOIN proforma_articles pa ON pa.proforma_id = p.proforma_id
                {where_clause_current}
                AND (p.etat IN ('termine', 'terminé', 'partiel') OR f.statut IN ('termine', 'terminé', 'partiel'))
            """
            
            # Requête pour l'année précédente
            previous_year_query = f"""
                SELECT 
                    COALESCE(SUM(
                        CASE 
                            WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN
                                COALESCE(
                                    (SELECT SUM(pa.quantite * a.prix) 
                                    FROM proforma_articles pa 
                                    JOIN articles a ON a.article_id = pa.article_id 
                                    WHERE pa.proforma_id = p.proforma_id), 0
                                ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0)
                            ELSE 0
                        END
                    ), 0) +
                    COALESCE(SUM(
                        CASE 
                            WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.montant_total 
                            ELSE 0 
                        END
                    ), 0) AS chiffre_affaires,
                    
                    COUNT(DISTINCT CASE WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.facture_id END) +
                    COUNT(DISTINCT CASE WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN p.proforma_id END) AS ventes,
                    
                    COUNT(DISTINCT CASE WHEN f.statut IN ('termine', 'terminé', 'partiel') THEN f.client_id END) +
                    COUNT(DISTINCT CASE WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN p.client_id END) AS clients,
                    
                    COALESCE(SUM(CASE WHEN p.etat IN ('termine', 'terminé', 'partiel') THEN pa.quantite ELSE 0 END), 0) AS articles

                FROM proformas p
                FULL OUTER JOIN factures f ON f.client_id = p.client_id
                LEFT JOIN proforma_articles pa ON pa.proforma_id = p.proforma_id
                {where_clause_previous}
                AND (p.etat IN ('termine', 'terminé', 'partiel') OR f.statut IN ('termine', 'terminé', 'partiel'))
            """
            
            # Exécuter les requêtes
            cur.execute(current_year_query, params_current)
            current_data = cur.fetchone()
            
            cur.execute(previous_year_query, params_previous)
            previous_data = cur.fetchone()
            
            # Calculer les pourcentages de variation
            def calculate_percentage_change(current, previous):
                if previous == 0:
                    return 100 if current > 0 else 0
                return round(((current - previous) / previous) * 100, 1)
            
            comparison_data = {
                "current_year": current_year,
                "previous_year": previous_year,
                "current": {
                    "chiffre_affaires": int(current_data[0] or 0),
                    "ventes": int(current_data[1] or 0),
                    "clients": int(current_data[2] or 0),
                    "articles": int(current_data[3] or 0)
                },
                "previous": {
                    "chiffre_affaires": int(previous_data[0] or 0),
                    "ventes": int(previous_data[1] or 0),
                    "clients": int(previous_data[2] or 0),
                    "articles": int(previous_data[3] or 0)
                },
                "variations": {
                    "chiffre_affaires": calculate_percentage_change(current_data[0] or 0, previous_data[0] or 0),
                    "ventes": calculate_percentage_change(current_data[1] or 0, previous_data[1] or 0),
                    "clients": calculate_percentage_change(current_data[2] or 0, previous_data[2] or 0),
                    "articles": calculate_percentage_change(current_data[3] or 0, previous_data[3] or 0)
                }
            }
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "comparison": comparison_data
            })
            
        except Exception as e:
            print(f"❌ Erreur year comparison: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    def calculate_reporting_kpis(cur, filters):
        """Calculer les KPIs avec filtres - version simplifiée"""
        try:
            # Construire les conditions WHERE et paramètres séparément pour chaque table
            proforma_conditions = []
            facture_conditions = []
            proforma_params = []
            facture_params = []
            
            # Filtre par année
            if filters.get('annee'):
                proforma_conditions.append("EXTRACT(YEAR FROM p.date_creation) = %s")
                facture_conditions.append("EXTRACT(YEAR FROM f.date_facture) = %s")
                proforma_params.append(filters['annee'])
                facture_params.append(filters['annee'])
            
            # Filtre par trimestre
            if filters.get('trimestre'):
                quarter_map = {'Q1': [1,2,3], 'Q2': [4,5,6], 'Q3': [7,8,9], 'Q4': [10,11,12]}
                months = quarter_map.get(filters['trimestre'], [])
                if months:
                    placeholders = ','.join(['%s'] * len(months))
                    proforma_conditions.append(f"EXTRACT(MONTH FROM p.date_creation) IN ({placeholders})")
                    facture_conditions.append(f"EXTRACT(MONTH FROM f.date_facture) IN ({placeholders})")
                    proforma_params.extend(months)
                    facture_params.extend(months)
            
            # Filtre par mois
            if filters.get('mois'):
                proforma_conditions.append("EXTRACT(MONTH FROM p.date_creation) = %s")
                facture_conditions.append("EXTRACT(MONTH FROM f.date_facture) = %s")
                proforma_params.append(filters['mois'])
                facture_params.append(filters['mois'])
            
            # Filtre par ville
            if filters.get('ville'):
                proforma_conditions.append("p.ville = %s")
                # Pour les factures, filtrer strictement par ville
                facture_conditions.append("f.ville = %s")
                proforma_params.append(filters['ville'])
                facture_params.append(filters['ville'])
            
            # Filtre par type de prestation (articles)
            if filters.get('type_prestation'):
                proforma_conditions.append("EXISTS (SELECT 1 FROM proforma_articles pa JOIN articles a ON a.article_id = pa.article_id WHERE pa.proforma_id = p.proforma_id AND a.type_article = %s)")
                facture_conditions.append("EXISTS (SELECT 1 FROM facture_articles fa JOIN articles a ON a.article_id = fa.article_id WHERE fa.facture_id = f.facture_id AND a.type_article = %s)")
                proforma_params.append(filters['type_prestation'])
                facture_params.append(filters['type_prestation'])
            
            # Filtre par agent
            if filters.get('agent'):
                proforma_conditions.append("p.cree_par = %s")
                # Pour les factures, inclure celles sans agent pour les anciennes factures
                facture_conditions.append("(f.cree_par = %s OR f.cree_par IS NULL)")
                proforma_params.append(filters['agent'])
                facture_params.append(filters['agent'])
            
            # 1) Chiffre d'Affaires (Proformas + Factures)
            ca_query = """
                WITH all_ca AS (
                    SELECT COALESCE(
                        (SELECT SUM(pa.quantite * a.prix) 
                        FROM proforma_articles pa 
                        JOIN articles a ON a.article_id = pa.article_id 
                        WHERE pa.proforma_id = p.proforma_id), 0
                    ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS ca
                    FROM proformas p
                    WHERE p.etat IN ('termine', 'terminé', 'partiel')
            """
                    
            if proforma_conditions:
                ca_query += " AND " + " AND ".join(proforma_conditions)
            ca_query += """
                    UNION ALL
                    SELECT COALESCE(f.montant_total, 0) AS ca
                    FROM factures f
                    WHERE f.statut IN ('termine', 'partiel')
            """
            
            if facture_conditions:
                ca_query += " AND " + " AND ".join(facture_conditions)
            
            ca_query += """
                )
                SELECT COALESCE(SUM(ca), 0) AS chiffre_affaires
                FROM all_ca
            """
            
            # Combiner tous les paramètres
            all_params = proforma_params + facture_params
            
            print(f"🔍 DEBUG KPIs - Requête CA: {ca_query}")
            print(f"🔍 DEBUG KPIs - Paramètres: {all_params}")
            
            cur.execute(ca_query, all_params)
            result = cur.fetchone()
            ca_total = result[0] if result and result[0] is not None else 0
            print(f"🔍 DEBUG KPIs - CA calculé: {ca_total}")
            
            # 2) Nombre de Ventes (Proformas + Factures)
            ventes_query = """
                WITH all_ventes AS (
                    SELECT p.proforma_id AS id
                    FROM proformas p
                    WHERE p.etat IN ('termine', 'terminé', 'partiel')
            """
                    
            if proforma_conditions:
                ventes_query += " AND " + " AND ".join(proforma_conditions)
            ventes_query += """
                    UNION ALL
                    SELECT f.facture_id AS id
                    FROM factures f
                    WHERE f.statut IN ('termine', 'partiel')
            """
            
            if facture_conditions:
                ventes_query += " AND " + " AND ".join(facture_conditions)
            
            ventes_query += """
                )
                SELECT COUNT(DISTINCT id) AS ventes
                FROM all_ventes
            """
            
            cur.execute(ventes_query, all_params)
            result = cur.fetchone()
            total_ventes = result[0] if result and result[0] is not None else 0
            
            # 3) Articles Vendus (Proformas seulement)
            articles_query = """
                SELECT COALESCE(SUM(pa.quantite), 0) AS articles
                FROM proforma_articles pa
                JOIN proformas p ON p.proforma_id = pa.proforma_id
                WHERE p.etat IN ('termine', 'terminé', 'partiel')
            """
            
            if proforma_conditions:
                articles_query += " AND " + " AND ".join(proforma_conditions)
            
            cur.execute(articles_query, proforma_params)
            result = cur.fetchone()
            articles_vendus = result[0] if result and result[0] is not None else 0
            
            # 4) Nouveaux Clients - Compter les clients uniques qui ont des commandes dans la période
            clients_query = """
                WITH clients_actifs AS (
                    SELECT DISTINCT c.client_id
                    FROM clients c
                    WHERE EXISTS (
                        SELECT 1 FROM proformas p 
                        WHERE p.client_id = c.client_id 
                        AND p.etat IN ('termine', 'terminé', 'partiel')
                    )
                    OR EXISTS (
                        SELECT 1 FROM factures f 
                        WHERE f.client_id = c.client_id 
                        AND f.statut IN ('termine', 'terminé', 'partiel')
                    )
                )
                SELECT COUNT(*) AS nouveaux_clients FROM clients_actifs
            """
            
            clients_params = []
            if filters.get('annee'):
                clients_query = """
                    WITH clients_actifs AS (
                        SELECT DISTINCT c.client_id
                        FROM clients c
                        WHERE EXISTS (
                            SELECT 1 FROM proformas p 
                            WHERE p.client_id = c.client_id 
                            AND p.etat IN ('termine', 'terminé', 'partiel')
                            AND EXTRACT(YEAR FROM p.date_creation) = %s
                        )
                        OR EXISTS (
                            SELECT 1 FROM factures f 
                            WHERE f.client_id = c.client_id 
                            AND f.statut IN ('termine', 'terminé', 'partiel')
                            AND EXTRACT(YEAR FROM f.date_facture) = %s
                        )
                    )
                    SELECT COUNT(*) AS nouveaux_clients FROM clients_actifs
                """
                clients_params = [filters['annee'], filters['annee']]
            
            cur.execute(clients_query, clients_params)
            result = cur.fetchone()
            nouveaux_clients = result[0] if result and result[0] is not None else 0
            
            return {
                "ca": int(ca_total),
                "ventes": int(total_ventes),
                "articles": int(articles_vendus),
                "nouveaux_clients": int(nouveaux_clients)
            }
            
        except Exception as e:
            print(f"❌ Erreur calcul KPIs: {e}")
            return {
                "ca": 0,
                "ventes": 0,
                "articles": 0,
                "nouveaux_clients": 0
            }

    @app.route('/admin/api/reporting/year-comparison', methods=['GET'])
    def admin_api_reporting_year_comparison():
        """Comparer les données entre deux années"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            # Récupérer les paramètres year1 et year2
            year1 = request.args.get('year1')
            year2 = request.args.get('year2')
            
            if not year1 or not year2:
                return jsonify({
                    "success": False, 
                    "message": "Les paramètres year1 et year2 sont requis"
                }), 400
            
            try:
                year1 = int(year1)
                year2 = int(year2)
            except ValueError:
                return jsonify({
                    "success": False, 
                    "message": "Les années doivent être des nombres entiers"
                }), 400
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Calculer les KPIs pour year1
            year1_kpis = calculate_reporting_kpis(cur, {'annee': year1})
            
            # Calculer les KPIs pour year2
            year2_kpis = calculate_reporting_kpis(cur, {'annee': year2})
            
            # Calculer les tendances
            trends = {}
            for key in ['ca', 'ventes', 'articles', 'nouveaux_clients']:
                year1_value = year1_kpis[key]
                year2_value = year2_kpis[key]
                
                if year1_value == 0:
                    trend = 0
                else:
                    trend = ((year2_value - year1_value) / year1_value) * 100
                
                trends[f'{key}_trend'] = round(trend, 1)
            
            conn.close()
            
            return jsonify({
                "success": True,
                "comparison": {
                    "year1": {
                        "year": year1,
                        **year1_kpis
                    },
                    "year2": {
                        "year": year2,
                        **year2_kpis
                    },
                    "trends": trends
                }
            })
            
        except Exception as e:
            print(f"❌ Erreur comparaison années: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    @app.route('/admin/api/reporting/monthly-details', methods=['GET'])
    def admin_api_reporting_monthly_details():
        """Récupérer les détails mensuels (sans filtrage)"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Requête pour les données mensuelles (12 derniers mois)
            monthly_query = """
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
                    WHERE p.etat IN ('termine', 'partiel')
                    AND p.date_creation >= CURRENT_DATE - INTERVAL '12 months'
                    
                    UNION ALL
                    
                    SELECT 
                        TO_CHAR(f.date_facture, 'YYYY-MM') as mois,
                        COALESCE(f.montant_total, 0) AS ca,
                        f.facture_id AS id,
                        f.client_id,
                        0 AS articles
                FROM factures f
                    WHERE f.statut IN ('termine', 'partiel')
                    AND f.date_facture >= CURRENT_DATE - INTERVAL '12 months'
                ),
                monthly_stats AS (
                    SELECT 
                        mois,
                        SUM(ca) AS chiffre_affaires,
                        COUNT(DISTINCT id) AS ventes,
                        COUNT(DISTINCT client_id) AS clients,
                        SUM(articles) AS articles
                    FROM all_data
                    GROUP BY mois
                ),
                nouveaux_clients AS (
                    SELECT 
                        TO_CHAR(created_at, 'YYYY-MM') as mois,
                        COUNT(DISTINCT client_id) AS nouveaux_clients
                    FROM clients
                    WHERE created_at >= CURRENT_DATE - INTERVAL '12 months'
                    GROUP BY TO_CHAR(created_at, 'YYYY-MM')
                )
                SELECT 
                    ms.mois,
                    COALESCE(ms.chiffre_affaires, 0) AS chiffre_affaires,
                    COALESCE(ms.ventes, 0) AS ventes,
                    COALESCE(ms.clients, 0) AS clients,
                    COALESCE(ms.articles, 0) AS articles,
                    COALESCE(nc.nouveaux_clients, 0) AS nouveaux_clients
                FROM monthly_stats ms
                LEFT JOIN nouveaux_clients nc ON ms.mois = nc.mois
                ORDER BY ms.mois DESC
            """
            
            cur.execute(monthly_query)
            results = cur.fetchall()
            
            # Organiser les données
            monthly_data = []
            month_names = {
                '01': 'Janvier', '02': 'Février', '03': 'Mars', '04': 'Avril',
                '05': 'Mai', '06': 'Juin', '07': 'Juillet', '08': 'Août',
                '09': 'Septembre', '10': 'Octobre', '11': 'Novembre', '12': 'Décembre'
            }
            
            for row in results:
                [year, month] = row[0].split('-')
                monthly_data.append({
                    'mois': f"{month_names[month]} {year}",
                    'chiffre_affaires': int(row[1] or 0),
                    'ventes': int(row[2] or 0),
                    'clients': int(row[3] or 0),
                    'articles': int(row[4] or 0),
                    'nouveaux_clients': int(row[5] or 0)
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                "success": True,
                "monthly_details": monthly_data
            })
            
        except Exception as e:
            print(f"❌ Erreur détails mensuels: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    # Fonction dupliquée supprimée - utilise celle à la ligne 3479

    # Fonction dupliquée supprimée - utilise celle à la ligne 3044
            params.append(annee)
            
            if ville:
                where_conditions.append("COALESCE(p.ville, f.ville) = %s")
                params.append(ville)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Requête pour les proformas
            cur.execute(f"""
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
                {where_clause.replace('COALESCE(p.date_creation, f.date_facture)', 'p.date_creation').replace('COALESCE(p.ville, f.ville)', 'p.ville').replace('COALESCE(p.etat, f.statut)', 'p.etat')}
                ORDER BY p.date_creation DESC
            """, params)
            
            proformas = cur.fetchall()
            
            # Requête pour les factures
            cur.execute(f"""
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
                {where_clause.replace('COALESCE(p.date_creation, f.date_facture)', 'f.date_facture').replace('COALESCE(p.ville, f.ville)', 'f.ville').replace('COALESCE(p.etat, f.statut)', 'f.statut')}
                ORDER BY f.date_facture DESC
            """, params)
            
            factures = cur.fetchall()
            
            # Combiner les résultats
            ventes = proformas + factures
            ventes.sort(key=lambda x: x[0] or datetime.min, reverse=True)
            
            # Calculer les KPIs
            total_ca = sum(row[5] or 0 for row in ventes)
            nombre_ventes = len(ventes)
            clients_uniques = len(set(row[1] for row in ventes if row[1]))
            
            # Récupérer les détails des articles pour chaque vente
            ventes_avec_details = []
            for vente in ventes:
                document_id = vente[7]
                type_doc = vente[6]
                
                # Vérifier que document_id est valide
                if not document_id or not isinstance(document_id, int):
                    print(f"⚠️ Document ID invalide: {document_id} pour type: {type_doc}")
                    # Créer une entrée avec message d'ancien système
                ventes_avec_details.append({
                    'date_creation': vente[0],
                    'date': vente[0],
                    'client_nom': vente[1],
                    'nom_client': vente[1],
                    'total_ttc': vente[5],
                    'statut': vente[6],  # Ajouter le statut
                    'etat': vente[6],    # Alias pour compatibilité
                    'articles': [{
                        'designation': 'Non Renseigné',
                        'nom': 'Non Renseigné',
                        'quantite': 1,
                        'prix': vente[5] or 0,
                        'total': vente[5] or 0
                    }]
                })
                continue
                
                # Récupérer les articles selon le type de document
                if type_doc == 'proforma':
                    cur.execute("""
                        SELECT a.designation, pa.quantite, a.prix, (pa.quantite * a.prix) as total
                                  FROM proforma_articles pa
                                  JOIN articles a ON a.article_id = pa.article_id
                        WHERE pa.proforma_id = %s
                        ORDER BY a.designation
                    """, (document_id,))
                else:  # facture
                    cur.execute("""
                        SELECT a.designation, fa.quantite, fa.prix_unitaire, (fa.quantite * fa.prix_unitaire) as total
                        FROM facture_articles fa
                        JOIN articles a ON a.article_id = fa.article_id
                        WHERE fa.facture_id = %s
                        ORDER BY a.designation
                    """, (document_id,))
                
                articles = cur.fetchall()
                # Convertir en dictionnaires pour le template
                articles_dict = []
                for article in articles:
                    articles_dict.append({
                        'designation': article[0],
                        'nom': article[0],  # Alias pour compatibilité
                        'quantite': article[1],
                        'prix': article[2],
                        'total': article[3]
                    })
                
                # Si aucun article trouvé, ajouter un message
                if not articles_dict:
                    articles_dict = [{
                        'designation': 'Aucun détail d\'article disponible',
                        'nom': 'Aucun détail d\'article disponible',
                        'quantite': 1,
                        'prix': vente[5] or 0,
                        'total': vente[5] or 0
                    }]
                
                ventes_avec_details.append({
                    'date_creation': vente[0],
                    'date': vente[0],  # Alias pour compatibilité
                    'client_nom': vente[1],
                    'nom_client': vente[1],  # Alias pour compatibilité
                    'total_ttc': vente[5],
                    'articles': articles_dict
                })
            
            cur.close()
            conn.close()
            
            # Générer le PDF avec WeasyPrint
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            # Rendre le template
            html_content = render_template('reporting_template.html',
                annee=annee or datetime.now().year,
                date_generation=datetime.now().strftime('%d/%m/%Y'),
                ville=ville or "Toutes",
                chiffre_affaire=f"{int(total_ca):,}".replace(',', ' '),
                chiffre_affaires=f"{int(total_ca):,}".replace(',', ' '),  # Alias pour compatibilité
                nombre_ventes=nombre_ventes,
                nombre_clients=clients_uniques,
                pays="Cameroun",
                ventes=ventes_avec_details,
                pagination={
                    'current_page': 1,
                    'total_pages': 1,
                    'total_ventes': nombre_ventes
                }
            )
            
            # Configuration WeasyPrint
            font_config = FontConfiguration()
            css = CSS(string='''
                @page { size: A4; margin: 1cm; }
                body { font-family: Arial, sans-serif; font-size: 12px; }
            ''', font_config=font_config)
            
            # Générer le PDF
            html_doc = HTML(string=html_content)
            pdf_bytes = html_doc.write_pdf(stylesheets=[css], font_config=font_config)
            
            # Préparer la réponse
            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=rapport_{annee or datetime.now().year}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
            
            return response
            
        except Exception as e:
            print(f"❌ Erreur export reporting PDF: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    @app.route('/admin/api/reporting/pdf', methods=['GET'])
    def admin_api_reporting_pdf():
        """Générer le rapport PDF avec pagination"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            # Récupérer les paramètres de filtrage
            annee = request.args.get('annee', '')
            ville = request.args.get('ville', '')
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Construire les conditions WHERE
            where_conditions = []
            params = []
            
            if annee:
                where_conditions.append("EXTRACT(YEAR FROM COALESCE(p.date_creation, f.date_facture)) = %s")
                params.append(annee)
            
            if ville:
                where_conditions.append("COALESCE(p.ville, f.ville) = %s")
                params.append(ville)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Calculer le total des ventes pour la pagination
            count_query = f"""
                SELECT COUNT(*) FROM (
                    SELECT p.proforma_id FROM proformas p
                    WHERE p.etat IN ('termine', 'partiel')
                    {where_clause.replace('COALESCE(p.date_creation, f.date_facture)', 'p.date_creation').replace('COALESCE(p.ville, f.ville)', 'p.ville')}
                    
                    UNION
                    
                    SELECT f.facture_id FROM factures f
                    WHERE f.statut IN ('termine', 'partiel')
                    {where_clause.replace('COALESCE(p.date_creation, f.date_facture)', 'f.date_facture').replace('COALESCE(p.ville, f.ville)', 'f.ville')}
                ) as total_ventes
            """
            
            cur.execute(count_query, params + params)
            total_ventes = cur.fetchone()[0]
            total_pages = (total_ventes + per_page - 1) // per_page
            
            # Calculer les KPIs globaux
            kpis = calculate_reporting_kpis(cur, {})
            
            # Récupérer les ventes avec pagination
            offset = (page - 1) * per_page
            
            ventes_query = f"""
                WITH all_ventes AS (
                SELECT 
                        p.proforma_id as id,
                        'proforma' as type,
                        p.numero as numero,
                        p.date_creation as date_creation,
                    c.nom as client_nom,
                    c.telephone as client_telephone,
                        c.adresse as client_adresse,
                        c.ville as client_ville,
                        c.pays as client_pays,
                        COALESCE(
                            (SELECT SUM(pa.quantite * a.prix) 
                              FROM proforma_articles pa
                              JOIN articles a ON a.article_id = pa.article_id
                            WHERE pa.proforma_id = p.proforma_id), 0
                        ) + COALESCE(p.frais, 0) - COALESCE(p.remise, 0) AS total_ttc,
                        p.etat as statut,
                        u.nom_utilisateur as created_by,
                        p.ville
                FROM proformas p
                LEFT JOIN clients c ON c.client_id = p.client_id
                LEFT JOIN utilisateurs u ON u.user_id = p.cree_par
                    WHERE p.etat IN ('termine', 'partiel')
                    {where_clause.replace('COALESCE(p.date_creation, f.date_facture)', 'p.date_creation').replace('COALESCE(p.ville, f.ville)', 'p.ville')}
                    
                    UNION ALL
                    
                    SELECT 
                        f.facture_id as id,
                        'facture' as type,
                        f.numero as numero,
                        f.date_facture as date_creation,
                        c.nom as client_nom,
                        c.telephone as client_telephone,
                        c.adresse as client_adresse,
                        c.ville as client_ville,
                        c.pays as client_pays,
                        f.montant_total as total_ttc,
                        f.statut as statut,
                        f.agent as created_by,
                        f.ville
                    FROM factures f
                    LEFT JOIN clients c ON c.client_id = f.client_id
                    WHERE f.statut IN ('termine', 'partiel')
                    {where_clause.replace('COALESCE(p.date_creation, f.date_facture)', 'f.date_facture').replace('COALESCE(p.ville, f.ville)', 'f.ville')}
                )
                SELECT * FROM all_ventes
                ORDER BY date_creation DESC
                LIMIT %s OFFSET %s
            """
            
            cur.execute(ventes_query, params + params + [per_page, offset])
            ventes = cur.fetchall()
            
            # Récupérer les articles pour chaque vente
            ventes_with_articles = []
            for vente in ventes:
                vente_dict = {
                    'id': vente[0],
                    'type': vente[1],
                    'numero': vente[2],
                    'date_creation': vente[3],
                    'client_nom': vente[4],
                    'client_telephone': vente[5],
                    'client_adresse': vente[6],
                    'client_ville': vente[7],
                    'client_pays': vente[8],
                    'total_ttc': vente[9],
                    'statut': vente[10],
                    'created_by': vente[11],
                    'ville': vente[12],
                    'articles': []
                }
                
                # Récupérer les articles pour cette vente
                if vente[1] == 'proforma':
                    articles_query = """
                        SELECT a.designation, a.type_article, pa.quantite, a.prix
                        FROM proforma_articles pa
                        JOIN articles a ON a.article_id = pa.article_id
                        WHERE pa.proforma_id = %s
                    """
                    cur.execute(articles_query, [vente[0]])
                    articles = cur.fetchall()
                    for article in articles:
                        vente_dict['articles'].append({
                            'designation': article[0],
                            'type_article': article[1],
                            'quantite': article[2],
                            'prix': article[3]
                        })
                else:
                    # Pour les factures, on peut ajouter une logique similaire si nécessaire
                    pass
                
                ventes_with_articles.append(vente_dict)
            
            cur.close()
            conn.close()
            
            # Préparer les données pour le template
            template_data = {
                'annee': annee or 'Toutes',
                'date_generation': datetime.now().strftime('%d/%m/%Y'),
                'ville': ville or 'Toutes',
                'pays': 'Cameroun',
                'chiffre_affaires': kpis.get('chiffre_affaires_total', 0),
                'nombre_ventes': kpis.get('total_ventes', 0),
                'nombre_clients': kpis.get('nombre_clients', 0),
                'ventes': ventes_with_articles,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_ventes': total_ventes,
                    'per_page': per_page
                }
            }
            
            # Rendre le template
            html = render_template('reporting_template.html', **template_data)
            
            return html
            
        except Exception as e:
            print(f"❌ Erreur génération PDF: {e}")
            return jsonify({
                "success": False,
                "message": f"Erreur: {str(e)}"
            }), 500

    # Onglet: Logs
    @app.route("/admin/logs", methods=["GET"])
    def admin_logs():
        user, resp = _require_admin()
        if resp: return resp
        return render_template("logs_admin.html", admin=user)

    # Onglet: Aide
    @app.route("/admin/aide", methods=["GET"])
    def admin_aide():
        user, resp = _require_admin()
        if resp: return resp
        return render_template("aide_admin.html", admin=user)

    @app.route('/admin/api/bug/send', methods=['POST'], endpoint='admin_api_send_bug_report')
    def admin_api_send_bug_report():
        """Envoyer un rapport de bug par email (espace admin)"""
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Non autorisé"}), 401

        try:
            data = request.get_json()

            # Validation
            if not data.get('sujet') or not data.get('description'):
                return jsonify({
                    "success": False, 
                    "message": "Le sujet et la description sont obligatoires"
                }), 400

            user_info = {
                'nom': session.get('username', 'Utilisateur inconnu'),
                'email': session.get('email', 'Email non renseigné'),
                'ville': session.get('ville', 'Ville non renseignée'),
                'role': session.get('role', 'Rôle non défini')
            }

            sujet_email = f"[BIZZIO BUG] {data['sujet']}"
            corps_email = f"""
                    NOUVEAU RAPPORT DE BUG - BIZZIO
                    ===============================

                    Date: {datetime.now().strftime('%d/%m/%Y à %H:%M')}

                    UTILISATEUR:
                    - Nom: {user_info['nom']}
                    - Email: {user_info['email']}
                    - Ville: {user_info['ville']}
                    - Rôle: {user_info['role']}

                    DÉTAILS DU BUG:
                    - Type: {data.get('type', 'Non spécifié')}
                    - Priorité: {data.get('priorite', 'Normale')}
                    - Page concernée: {data.get('page', 'Non spécifiée')}

                    DESCRIPTION:
                    {data['description']}

                    ÉTAPES POUR REPRODUIRE:
                    {data.get('etapes', 'Non spécifiées')}

                    INFORMATIONS TECHNIQUES:
                    - Navigateur: {data.get('navigateur', 'Non spécifié')}
                    - URL: {data.get('url_actuelle', 'Non spécifiée')}

                    ---
                    Rapport généré automatiquement par Bizzio
                                """

            msg = Message(
                subject=sujet_email,
                recipients=[os.getenv('BUG_REPORT_EMAIL', 'olongolinda@gmail.com')],
                body=corps_email,
                sender=os.getenv('MAIL_DEFAULT_SENDER')
            )

            # ⬇️ utiliser l’objet mail reçu dans init_admin_routes
            mail.send(msg)

            return jsonify({
                "success": True,
                "message": "Rapport de bug envoyé avec succès ! Nous vous répondrons dans les plus brefs délais."
            })

        except Exception as e:
            print(f"❌ Erreur envoi email bug (admin): {e}")
            return jsonify({
                "success": False,
                "message": "Erreur lors de l'envoi. Veuillez réessayer plus tard."
            }), 500