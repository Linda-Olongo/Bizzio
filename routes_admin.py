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
        kpis = {
            "nb_clients": Client.query.count(),
            "nb_proformas": Proforma.query.count(),
            "nb_articles": Article.query.count(),
        }
        # on passe explicitement 'admin' pour le template
        return render_template("dashboard_admin.html", admin=user, kpis=kpis)

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
            
            # Générer les labels et données pour la période glissante 12 mois
            labels = []
            nb_ventes_data = []
            ca_montants_data = []
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
            # Vérifier que la proforma existe
            cur.execute("SELECT numero FROM proformas WHERE proforma_id = %s", [proforma_id])
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
                      payload_avant={"numero": proforma[0]})

            return jsonify({
                "success": True,
                "message": f"Proforma {proforma[0]} supprimée avec succès"
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
        return render_template("data_analyst_admin.html", admin=user)

    # Onglet: Reporting
    @app.route("/admin/reporting", methods=["GET"])
    def admin_reporting():
        user, resp = _require_admin()
        if resp: return resp
        return render_template("reporting_admin.html", admin=user)

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
