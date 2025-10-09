# Configuration et API calls pour Gemini - Data Analyst Bizzio

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Supprimer complètement les warnings du terminal
import warnings
warnings.filterwarnings("ignore")
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['ABSL_LOGGING_VERBOSITY'] = '0'

# Rediriger tous les logs stderr
import sys
from contextlib import redirect_stderr
import io
import logging

# Supprimer tous les loggers
logging.getLogger().setLevel(logging.CRITICAL)
for logger_name in ['absl', 'grpc', 'google']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Import des prompts
try:
    from .prompts import BizzioPrompts
except ImportError:
    from prompts import BizzioPrompts

# Chargement des variables d'environnement
load_dotenv()

class BizzioDataAccess:
    """
    Classe pour accéder aux données réelles du système Bizzio
    """
    
    def __init__(self):
        """Initialisation de la connexion à la base de données"""
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("❌ DATABASE_URL n'est pas définie dans le fichier .env")
    
    def get_db_connection(self):
        """Récupère une connexion à la base de données"""
        try:
            conn = psycopg2.connect(self.database_url)
            return conn
        except Exception as e:
            print(f"❌ Erreur de connexion à la base de données : {e}")
            return None
    
    def get_top_articles(self, limit: int = 5) -> Dict[str, Any]:
        """
        Récupère les articles les plus vendus
        
        Args:
            limit: Nombre d'articles à retourner
        
        Returns:
            Dict contenant les données des articles
        """
        try:
            conn = self.get_db_connection()
            if not conn:
                return {"success": False, "error": "Connexion à la base de données échouée"}
            
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
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
                LIMIT %s
            """
            
            cur.execute(query, (limit,))
            results = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Conversion en format utilisable
            articles = []
            for row in results:
                articles.append({
                    'nom': row['nom'],
                    'quantite_totale': int(row['total_quantite']),
                    'ca_total': float(row['ca_total']),
                    'nb_commandes': int(row['nb_commandes'])
                })
            
            return {
                "success": True,
                "articles": articles,
                "total_articles": len(articles),
                "limit": limit
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_prestations_category(self) -> Dict[str, Any]:
        """
        Récupère les prestations par catégorie
        
        Returns:
            Dict contenant les données des prestations
        """
        try:
            conn = self.get_db_connection()
            if not conn:
                return {"success": False, "error": "Connexion à la base de données échouée"}
            
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Requête pour les prestations par catégorie
            query = """
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
            """
            
            cur.execute(query)
            results = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Conversion en format utilisable
            prestations = []
            total_ca = 0
            for row in results:
                ca = float(row['total_revenue'])
                total_ca += ca
                prestations.append({
                    'type_article': row['type_article'],
                    'quantite_totale': int(row['total_quantity']),
                    'ca_total': ca
                })
            
            # Calcul des pourcentages
            for prestation in prestations:
                if total_ca > 0:
                    prestation['pourcentage'] = round((prestation['ca_total'] / total_ca) * 100, 1)
                else:
                    prestation['pourcentage'] = 0
            
            return {
                "success": True,
                "prestations": prestations,
                "total_ca": total_ca,
                "has_data": len(prestations) > 0
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_prestation_performance(self) -> Dict[str, Any]:
        """
        Récupère les performances des prestations
        
        Returns:
            Dict contenant les données de performance
        """
        try:
            conn = self.get_db_connection()
            if not conn:
                return {"success": False, "error": "Connexion à la base de données échouée"}
            
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Requête pour les performances par prestation
            query = """
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
            
            cur.execute(query)
            results = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Conversion en format utilisable
            performances = []
            for row in results:
                performances.append({
                    'prestation': row['prestation'],
                    'ca_total': float(row['ca_total']),
                    'nb_commandes': int(row['nb_commandes']),
                    'nb_clients': int(row['nb_clients']),
                    'pourcentage': float(row['pourcentage'])
                })
            
            return {
                "success": True,
                "performances": performances,
                "has_data": len(performances) > 0
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# Version de la bibliothèque
print(f"Version google-generativeai : {genai.__version__}")

class BizzioGemini:
    """
    Classe principale pour l'intégration Gemini avec la personnalité Bizzio
    Data Analyst expert et partenaire de confiance
    """
    
    def __init__(self):
        """Initialisation du système Gemini avec Bizzio"""
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY n'est pas définie dans le fichier .env")
        
        # Configuration de l'API Gemini
        with redirect_stderr(io.StringIO()):
            genai.configure(api_key=self.api_key)
            
        # Utilisation des nouveaux modèles Gemini 2.x
        # Options par ordre de préférence (du plus léger au plus puissant) :
        # 1. gemini-2.0-flash-lite (le plus économe en quota)
        # 2. gemini-2.0-flash (bon compromis)
        # 3. gemini-2.5-flash (plus puissant mais consomme plus de quota)
        
        with redirect_stderr(io.StringIO()):
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Initialisation des prompts
        self.prompts = BizzioPrompts()
        
        # Initialisation de l'accès aux données réelles
        try:
            self.data_access = BizzioDataAccess()
            print("✅ Accès aux données réelles initialisé")
        except Exception as e:
            print(f"⚠️ Accès aux données limité : {e}")
            self.data_access = None
        
        # Configuration du logging (silencieux)
        self.setup_logging()
        
        # Historique des conversations
        self.conversation_history = []
        
        print("Bizzio Data Analyst initialisé avec succès !")
        print(f"Modèle utilisé : gemini-2.0-flash-lite (gratuit & économe)")
        print("----")
    
    def setup_logging(self):
        """Configuration du système de logging (silencieux)"""
        # Créer le dossier logs s'il n'existe pas
        os.makedirs('logs', exist_ok=True)
        
        # Logger silencieux - seulement dans le fichier
        logging.basicConfig(
            level=logging.CRITICAL,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/bizzio_gemini.log'),
            ]
        )
        self.logger = logging.getLogger('BizzioGemini')
        self.logger.setLevel(logging.CRITICAL)
    
    def get_system_prompt(self) -> str:
        """Récupère le prompt système de Bizzio"""
        return self.prompts.get_system_prompt()
    
    def is_about_capabilities(self, message: str) -> bool:
        """
        Détecte si l'utilisateur demande des informations sur les capacités de Bizzio
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si c'est une question sur les capacités
        """
        message_lower = message.lower().strip()
        
        # Questions directes sur l'identité et les capacités
        capability_phrases = [
            'qui es tu', 'qui êtes vous', 'ton nom', 'votre nom', 'bizzio',
            'que peux tu faire', 'que pouvez vous faire', 'tes capacités', 'vos capacités',
            'tes compétences', 'vos compétences', 'tes fonctions', 'vos fonctions',
            'aide moi', 'peux tu m aider', 'pouvez vous m aider',
            'que sais tu faire', 'que savez vous faire', 'tes services', 'vos services',
            'présente toi', 'présentez vous', 'raconte moi', 'racontez moi',
            'comment tu t\'appelle', 'comment tu t\'appelles'  # Gestion des erreurs de frappe
        ]
        
        for phrase in capability_phrases:
            if phrase in message_lower:
                return True
        
        return False
    
    def is_educational_question(self, message: str) -> bool:
        """
        Détecte si l'utilisateur pose une question éducative sur la BI, NLP, etc.
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si c'est une question éducative
        """
        message_lower = message.lower().strip()
        
        # Mots-clés éducatifs
        educational_keywords = [
            'qu\'est-ce que', 'qu\'est ce que', 'c\'est quoi', 'c\'est quoi',
            'explique', 'définis', 'définition', 'concept', 'notion',
            'business intelligence', 'bi', 'nlp', 'traitement du langage',
            'data analysis', 'analyse de données', 'kpi', 'tableau de bord',
            'reporting', 'statistiques', 'machine learning', 'ia', 'intelligence artificielle',
            'chatbot', 'conversationnel', 'gestion commerciale', 'crm', 'erp'
        ]
        
        for keyword in educational_keywords:
            if keyword in message_lower:
                return True
        
        return False
    
    def is_top_request(self, user_message: str) -> bool:
        """
        Détecte si l'utilisateur demande un top (top 5, top 10, etc.)
        
        Args:
            user_message: Message de l'utilisateur
        
        Returns:
            True si c'est une demande de top
        """
        message_lower = user_message.lower().strip()
        
        # Mots-clés pour les tops
        top_keywords = [
            'top', 'meilleur', 'meilleurs', 'meilleure', 'meilleures',
            'classement', 'ranking', 'premier', 'premiers', 'première', 'premières',
            'plus vendu', 'plus vendus', 'plus vendue', 'plus vendues',
            'mieux vendu', 'mieux vendus', 'mieux vendue', 'mieux vendues',
            'populaire', 'populaires', 'favori', 'favoris', 'favorite', 'favorites'
        ]
        
        # Patterns pour détecter "top X"
        import re
        top_patterns = [
            r'top \d+',
            r'meilleur \d+',
            r'meilleurs \d+',
            r'premier \d+',
            r'premiers \d+',
            r'\d+ meilleur',
            r'\d+ meilleurs',
            r'\d+ premier',
            r'\d+ premiers'
        ]
        
        has_top_keyword = any(keyword in message_lower for keyword in top_keywords)
        has_top_pattern = any(re.search(pattern, message_lower) for pattern in top_patterns)
        
        return has_top_keyword or has_top_pattern

    def is_export_request(self, message: str) -> bool:
        """
        Détecte si l'utilisateur demande un export (Excel, CSV, visualisation)
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si c'est une demande d'export
        """
        message_lower = message.lower().strip()
        
        # Mots-clés d'export
        export_keywords = [
            'excel', 'csv', 'export', 'exporter', 'tableau', 'fichier',
            'télécharger', 'download', 'liste complète', 'liste complete',
            'visualisation', 'graphique', 'chart', 'graph', 'diagramme',
            'exporte', 'génère', 'genere', 'crée', 'cree', 'fais'
        ]
        
        for keyword in export_keywords:
            if keyword in message_lower:
                return True
        
        return False
    
    def is_article_price_request(self, message: str) -> bool:
        """
        Détecte si l'utilisateur demande le prix d'un ou plusieurs articles
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si c'est une demande de prix d'article
        """
        message_lower = message.lower().strip()
        
        # Mots-clés pour les demandes de prix
        price_keywords = [
            'prix', 'price', 'coût', 'cout', 'tarif', 'combien',
            'quel est le prix', 'combien coûte', 'combien coute',
            'prix de', 'prix du', 'prix de la', 'prix des',
            'donne moi le prix', 'donne-moi le prix', 'montre moi le prix',
            'montre-moi le prix', 'affiche le prix', 'affiche-moi le prix'
        ]
        
        # Mots-clés pour les articles (plus généraux)
        article_keywords = [
            'article', 'articles', 'produit', 'produits', 'livre', 'livres',
            'fourniture', 'fournitures', 'service', 'services',
            'formation', 'formations', 'chimie', 'chemistry', 'oxford', 
            'advanced', 'physics', 'math', 'mathematics', 'economics',
            'geography', 'histoire', 'français', 'anglais', 'allemand'
        ]
        
        # Détecter les demandes de prix multiples (ex: "prix de 5 articles")
        multiple_price_patterns = [
            r'prix de \d+ articles?',
            r'prix des \d+ articles?',
            r'\d+ articles?.*prix',
            r'prix.*\d+ articles?'
        ]
        
        import re
        has_multiple_price = any(re.search(pattern, message_lower) for pattern in multiple_price_patterns)
        
        has_price_keyword = any(keyword in message_lower for keyword in price_keywords)
        has_article_keyword = any(keyword in message_lower for keyword in article_keywords)
        
        return has_price_keyword and (has_article_keyword or has_multiple_price)
    
    def handle_capabilities_question(self, user_message: str) -> Dict[str, Any]:
        """
        Gère les questions sur les capacités de Bizzio
        
        Args:
            user_message: Message de l'utilisateur
        
        Returns:
            Dict contenant la réponse sur les capacités
        """
        try:
            language = self.detect_language(user_message)
            
            if language == 'en':
                response = """Hi ! I'm **Bizzio**, your Data Analyst & BI educator.
            
**What I can do:**
• Analyze sales & product performance
• Generate business reports & KPIs
• Export data (CSV/Excel)
• Create visualizations & charts
• Explain BI, NLP, data analysis concepts
• Provide strategic recommendations

**Ask me anything about:**
- Business Intelligence & KPIs
- Data analysis & statistics
- NLP & conversational AI
- Commercial management systems

I'm here to help with your business data! 📊"""
            else:
                response = """Salut ! Je suis **Bizzio**, ton Data Analyst & éducateur BI.
            
**Ce que je peux faire :**
• Analyser les ventes & performances produits
• Générer des rapports & KPIs business
• Exporter les données (CSV/Excel)
• Créer des visualisations & graphiques
• Expliquer la BI, NLP, analyse de données
• Fournir des recommandations stratégiques

**Demande-moi :**
- "Qu'est-ce que la Business Intelligence ?"
- "Explique-moi les KPIs"
- "Montre-moi nos meilleurs produits"
- "Analyse les tendances de ventes"

Je suis là pour t'aider avec tes données business ! 📊"""
            
            # Enregistrement
            capability_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'capabilities',
                'user_message': user_message,
                'response': response,
                'model_used': 'capabilities_info',
                'language_detected': language
            }
            self.conversation_history.append(capability_entry)
            
            return {
                'success': True,
                'response': response,
                'timestamp': capability_entry['timestamp'],
                'model_used': 'capabilities_info',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'info'
            }
            
        except Exception as e:
            fallback_response = "Salut ! Je suis Bizzio, ton Data Analyst. Je peux analyser tes données business, créer des rapports et des graphiques. Que veux-tu savoir ?"
            
            return {
                'success': True,
                'response': fallback_response,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'capabilities_fallback',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'fallback'
            }
    
    def handle_educational_question(self, user_message: str) -> Dict[str, Any]:
        """
        Gère les questions éducatives sur la BI, NLP, etc.
        
        Args:
            user_message: Message de l'utilisateur
        
        Returns:
            Dict contenant la réponse éducative
        """
        try:
            language = self.detect_language(user_message)
            
            # Utiliser Gemini pour répondre aux questions éducatives
            model = genai.GenerativeModel('gemini-pro')
            
            educational_prompt = f"""
Tu es Bizzio, expert en Business Intelligence et Data Analysis. Réponds de manière concise et éducative à cette question :

Question: {user_message}

Réponds en {language} de manière claire et professionnelle, en expliquant les concepts demandés.
"""
            
            response = model.generate_content(educational_prompt)
            response_text = response.text if response.text else "Désolé, je n'ai pas pu traiter ta question éducative."
            
            # Enregistrement
            educational_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'educational',
                'user_message': user_message,
                'response': response_text,
                'model_used': 'gemini-educational',
                'language_detected': language
            }
            self.conversation_history.append(educational_entry)
            
            return {
                'success': True,
                'response': response_text,
                'timestamp': educational_entry['timestamp'],
                'model_used': 'gemini-educational',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'educational'
            }
            
        except Exception as e:
            fallback_response = "Désolé, je n'ai pas pu traiter ta question éducative pour le moment."
            
            return {
                'success': True,
                'response': fallback_response,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'educational_fallback',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'fallback'
            }
    
    def handle_article_price_request(self, user_message: str) -> Dict[str, Any]:
        """
        Gère les demandes de prix d'articles spécifiques (un ou plusieurs)
        
        Args:
            user_message: Message de l'utilisateur
        
        Returns:
            Dict contenant la réponse avec le prix de l'article
        """
        try:
            language = self.detect_language(user_message)
            
            # Vérifier si c'est une demande de prix multiples
            import re
            multiple_match = re.search(r'prix de (\d+) articles?|(\d+) articles?.*prix', user_message.lower())
            if multiple_match:
                return self.handle_multiple_articles_price_request(user_message, language)
            
            # Extraire le nom de l'article du message
            article_name = self.extract_article_name_from_message(user_message)
            
            if not article_name:
                if language == 'en':
                    response = "I couldn't identify which article you're asking about. Please specify the article name."
                else:
                    response = "Je n'ai pas pu identifier l'article dont vous parlez. Veuillez préciser le nom de l'article."
            else:
                # Rechercher l'article dans la base de données
                search_result = self.search_article_by_name(article_name)
                
                if search_result.get('success') and search_result.get('found'):
                    article = search_result['article']
                    price = article['prix']
                    article_type = article['type']
                    
                    # Vérifier si c'est une correspondance similaire
                    if search_result.get('similar_match'):
                        if language == 'en':
                            responses = [
                                f"🔍 **Found a similar article:**\n\n",
                                f"✨ **Here's what I found:**\n\n",
                                f"🎯 **Great match found:**\n\n"
                            ]
                            import random
                            response = random.choice(responses)
                            response += f"**{article['nom']}**\n"
                            response += f"💰 Price: **{price:,.0f} FCFA**\n"
                            response += f"📦 Type: {article_type}\n"
                            response += f"🔢 Code: {article['code']}\n\n"
                            response += f"💡 *I found this based on your search for '{article_name}'*"
                        else:
                            responses = [
                                f"🔍 **Article similaire trouvé :**\n\n",
                                f"✨ **Voici ce que j'ai trouvé :**\n\n",
                                f"🎯 **Excellente correspondance :**\n\n"
                            ]
                            import random
                            response = random.choice(responses)
                            response += f"**{article['nom']}**\n"
                            response += f"💰 Prix : **{price:,.0f} FCFA**\n"
                            response += f"📦 Type : {article_type}\n"
                            response += f"🔢 Code : {article['code']}\n\n"
                            response += f"💡 *J'ai trouvé cet article basé sur votre recherche de '{article_name}'*"
                    else:
                        if language == 'en':
                            response = f"**{article['nom']}**\n"
                            response += f"💰 Price: **{price:,.0f} FCFA**\n"
                            response += f"📦 Type: {article_type}\n"
                            response += f"🔢 Code: {article['code']}"
                        else:
                            response = f"**{article['nom']}**\n"
                            response += f"💰 Prix : **{price:,.0f} FCFA**\n"
                            response += f"📦 Type : {article_type}\n"
                            response += f"🔢 Code : {article['code']}"
                else:
                    if language == 'en':
                        response = f"❌ Article '{article_name}' not found in our database.\n\n"
                        response += "Available articles include:\n"
                        response += "• Advanced Chemistry (Oxford)\n"
                        response += "• Advanced Level Physics\n"
                        response += "• Complete Physical Geography\n"
                        response += "• And many more...\n\n"
                        response += "Try searching with a more specific name or check our catalog."
                    else:
                        response = f"❌ L'article '{article_name}' n'a pas été trouvé dans notre base de données.\n\n"
                        response += "Articles disponibles :\n"
                        response += "• Advanced Chemistry (Oxford)\n"
                        response += "• Advanced Level Physics\n"
                        response += "• Complete Physical Geography\n"
                        response += "• Et bien d'autres...\n\n"
                        response += "Essayez avec un nom plus spécifique ou consultez notre catalogue."
            
            # Enregistrement
            price_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'article_price',
                'user_message': user_message,
                'response': response,
                'model_used': 'article_search',
                'language_detected': language,
                'article_searched': article_name
            }
            self.conversation_history.append(price_entry)
            
            return {
                'success': True,
                'response': response,
                'timestamp': price_entry['timestamp'],
                'model_used': 'article_search',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'article_price',
                'article_found': search_result.get('found', False) if 'search_result' in locals() else False
            }
            
        except Exception as e:
            fallback_response = "Désolé, je n'ai pas pu rechercher l'article pour le moment."
            
            return {
                'success': True,
                'response': fallback_response,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'article_price_fallback',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'fallback'
            }

    def handle_multiple_articles_price_request(self, user_message: str, language: str) -> Dict[str, Any]:
        """
        Gère les demandes de prix de plusieurs articles
        
        Args:
            user_message: Message de l'utilisateur
            language: Langue détectée
        
        Returns:
            Dict contenant la réponse avec les prix des articles
        """
        try:
            import re
            
            # Extraire le nombre d'articles demandés
            number_match = re.search(r'prix de (\d+) articles?|(\d+) articles?.*prix', user_message.lower())
            if number_match:
                number = int(number_match.group(1) or number_match.group(2))
            else:
                number = 5  # Par défaut 5 articles
            
            # Récupérer des articles aléatoires avec leurs prix
            articles_result = self.get_random_articles_with_prices(number)
            
            if not articles_result.get('success', False):
                if language == 'en':
                    response = f"Sorry, I couldn't retrieve {number} articles. {articles_result.get('error', 'Unknown error')}"
                else:
                    response = f"Désolé, je n'ai pas pu récupérer {number} articles. {articles_result.get('error', 'Erreur inconnue')}"
            else:
                articles = articles_result.get('articles', [])
                
                if language == 'en':
                    response = f"**Here are the prices of {len(articles)} random articles:**\n\n"
                else:
                    response = f"**Voici les prix de {len(articles)} articles aléatoires :**\n\n"
                
                for i, article in enumerate(articles, 1):
                    response += f"{i}. **{article.get('nom', 'N/A')}**\n"
                    response += f"   💰 Prix : **{article.get('prix', 0):,.0f} FCFA**\n"
                    response += f"   📦 Type : {article.get('type', 'N/A')}\n"
                    response += f"   🔢 Code : {article.get('code', 'N/A')}\n\n"
            
            # Enregistrement
            price_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'multiple_article_price',
                'user_message': user_message,
                'response': response,
                'model_used': 'multiple_article_search',
                'language_detected': language,
                'number_requested': number
            }
            self.conversation_history.append(price_entry)
            
            return {
                'success': True,
                'response': response,
                'timestamp': price_entry['timestamp'],
                'model_used': 'multiple_article_search',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'multiple_article_price',
                'number_articles': len(articles) if 'articles' in locals() else 0
            }
            
        except Exception as e:
            fallback_response = "Désolé, je n'ai pas pu récupérer les prix des articles pour le moment."
            
            return {
                'success': True,
                'response': fallback_response,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'multiple_article_price_fallback',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'fallback'
            }

    def get_random_articles_with_prices(self, limit: int = 5) -> Dict[str, Any]:
        """
        Récupère des articles aléatoires avec leurs prix
        
        Args:
            limit: Nombre d'articles à retourner
        
        Returns:
            Dict contenant les données des articles
        """
        try:
            import requests
            
            # Appel à l'API pour récupérer des articles aléatoires
            response = requests.get(f'http://localhost:5001/admin/api/articles/random?limit={limit}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {
                        "success": True,
                        "articles": data['articles'],
                        "total": data['total']
                    }
            else:
                return {"success": False, "error": f"Erreur API articles aléatoires: {response.status_code} - {response.text}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def extract_article_name_from_message(self, message: str) -> str:
        """
        Extrait le nom de l'article du message utilisateur avec gestion des erreurs de frappe
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            Nom de l'article extrait
        """
        message_lower = message.lower()
        
        # Patterns pour extraire le nom de l'article
        patterns = [
            r'prix de l\'article (.+)',
            r'prix du (.+)',
            r'prix de la (.+)',
            r'prix des (.+)',
            r'combien coûte (.+)',
            r'combien coute (.+)',
            r'price of (.+)',
            r'cost of (.+)',
            r'prix de (.+)',
            r'price (.+)'
        ]
        
        import re
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                article_name = match.group(1).strip()
                # Nettoyer le nom de l'article mais garder les parenthèses et tirets
                article_name = re.sub(r'[^\w\s\-\(\)]', '', article_name)
                # Supprimer les mots vides au début
                words = article_name.split()
                stop_words = ['de', 'du', 'des', 'la', 'le', 'les', 'the', 'of', 'a', 'an']
                while words and words[0].lower() in stop_words:
                    words.pop(0)
                article_name = ' '.join(words)
                return article_name
        
        # Si aucun pattern ne correspond, essayer d'extraire les mots après "article"
        if 'article' in message_lower:
            words = message_lower.split()
            try:
                article_index = words.index('article')
                if article_index + 1 < len(words):
                    # Prendre les 2-3 mots suivants
                    article_name = ' '.join(words[article_index + 1:article_index + 4])
                    return article_name
            except ValueError:
                pass
        
        # Si le message contient directement un nom d'article connu
        known_articles = [
            'advanced chemistry', 'advanced chemistry (oxford)', 'oxford chemistry',
            'advanced level physics', 'complete physical geography',
            'langue française', 'allemand', 'sciences', 'histoire'
        ]
        
        for article in known_articles:
            if article in message_lower:
                return article
        
        return ""
    
    def normalize_article_name(self, article_name: str) -> str:
        """
        Normalise le nom d'un article pour la recherche (gestion des erreurs de frappe)
        
        Args:
            article_name: Nom de l'article à normaliser
        
        Returns:
            Nom normalisé
        """
        if not article_name:
            return ""
        
        # Convertir en minuscules
        normalized = article_name.lower().strip()
        
        # Supprimer les mots vides
        stop_words = ['le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'the', 'of', 'a', 'an']
        words = normalized.split()
        words = [word for word in words if word not in stop_words]
        normalized = ' '.join(words)
        
        # Corriger les erreurs de frappe communes (dans l'ordre de priorité)
        corrections = [
            ('chemistr', 'chemistry'),
            ('chemist', 'chemistry'), 
            ('chemis', 'chemistry'),
            ('oxfor', 'oxford'),
            ('oxfod', 'oxford'),
            ('advaned', 'advanced'),
            ('advan', 'advanced'),
            ('physic', 'physics'),
            ('physcs', 'physics'),
            ('geograph', 'geography'),
            ('geograp', 'geography'),
            ('francais', 'française'),
            ('franc', 'française'),
            ('alleman', 'allemand'),
            ('allem', 'allemand'),
            ('scienc', 'sciences'),
            ('scien', 'sciences'),
            ('histoir', 'histoire'),
            ('histo', 'histoire')
        ]
        
        # Appliquer les corrections mot par mot
        corrected_words = []
        for word in normalized.split():
            corrected_word = word
            # Appliquer les corrections dans l'ordre de priorité
            for typo, correct in corrections:
                if typo in corrected_word:
                    corrected_word = corrected_word.replace(typo, correct)
                    break  # Arrêter après la première correction trouvée
            corrected_words.append(corrected_word)
        
        return ' '.join(corrected_words)
    
    def generate_excel_file(self, articles: list, data_type: str) -> str:
        """
        Génère un fichier Excel réel et retourne l'URL de téléchargement
        
        Args:
            articles: Liste des articles
            data_type: Type de données (articles ou prestations)
        
        Returns:
            URL du fichier généré ou None si erreur
        """
        try:
            import pandas as pd
            import os
            from datetime import datetime
            
            # Créer un DataFrame
            df = pd.DataFrame(articles)
            
            # Créer le nom du fichier
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{data_type}_{timestamp}.xlsx"
            
            # Créer le dossier uploads s'il n'existe pas
            uploads_dir = "uploads"
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            filepath = os.path.join(uploads_dir, filename)
            
            # Sauvegarder le fichier Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=data_type.title(), index=False)
            
            # Retourner l'URL relative
            return f"/uploads/{filename}"
            
        except Exception as e:
            print(f"Erreur génération Excel: {e}")
            return None
    
    def generate_csv_file(self, articles: list, data_type: str) -> str:
        """
        Génère un fichier CSV réel et retourne l'URL de téléchargement
        
        Args:
            articles: Liste des articles
            data_type: Type de données (articles ou prestations)
        
        Returns:
            URL du fichier généré ou None si erreur
        """
        try:
            import pandas as pd
            import os
            from datetime import datetime
            
            # Créer un DataFrame
            df = pd.DataFrame(articles)
            
            # Créer le nom du fichier
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{data_type}_{timestamp}.csv"
            
            # Créer le dossier uploads s'il n'existe pas
            uploads_dir = "uploads"
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            filepath = os.path.join(uploads_dir, filename)
            
            # Sauvegarder le fichier CSV
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            # Retourner l'URL relative
            return f"/uploads/{filename}"
            
        except Exception as e:
            print(f"Erreur génération CSV: {e}")
            return None
    
    def generate_varied_export_response(self, export_type: str, language: str, file_url: str, data_result: dict) -> str:
        """
        Génère une réponse variée pour les exports en utilisant Gemini
        
        Args:
            export_type: Type d'export (excel, csv, visualisation)
            language: Langue de la réponse
            file_url: URL du fichier généré
            data_result: Résultat des données
            
        Returns:
            Réponse variée générée par Gemini
        """
        try:
            # Prompt pour générer une réponse variée et courte
            if language == 'en':
                if export_type == 'visualisation':
                    prompt = f"""Generate a SHORT, creative response for a successful {export_type} export. 
                    The chart shows the top 20 items from {len(data_result.get('articles', []))} total items.
                    Use 1-2 emojis, be enthusiastic but brief. Maximum 2 sentences.
                    
                    Examples of good responses:
                    - "🎉 Chart ready! Top 20 items visualized!"
                    - "✨ Dynamic chart generated with top performers!"
                    - "🚀 Interactive visualization loaded!"
                    
                    Keep it short and punchy!"""
                else:
                    prompt = f"""Generate a SHORT, creative response for a successful {export_type} export. 
                    The file contains {len(data_result.get('articles', []))} items.
                    Use 1-2 emojis, be enthusiastic but brief. Maximum 2 sentences.
                    
                    Examples of good responses:
                    - "🎉 Brilliant! Your {export_type} export is ready to rock!"
                    - "✨ Mission accomplished! {len(data_result.get('articles', []))} items exported successfully!"
                    - "🚀 Boom! Your {export_type} file is locked and loaded!"
                    
                    Keep it short and punchy!"""
            else:
                if export_type == 'visualisation':
                    prompt = f"""Génère une réponse COURTE et créative pour un export {export_type} réussi.
                    Le graphique montre le top 20 des éléments sur {len(data_result.get('articles', []))} au total.
                    Utilise 1-2 emojis, sois enthousiaste mais bref. Maximum 2 phrases.
                    
                    Exemples de bonnes réponses :
                    - "🎉 Graphique prêt ! Top 20 visualisé !"
                    - "✨ Graphique dynamique généré avec les meilleurs !"
                    - "🚀 Visualisation interactive chargée !"
                    
                    Reste court et percutant !"""
                else:
                    prompt = f"""Génère une réponse COURTE et créative pour un export {export_type} réussi.
                    Le fichier contient {len(data_result.get('articles', []))} éléments.
                    Utilise 1-2 emojis, sois enthousiaste mais bref. Maximum 2 phrases.
                    
                    Exemples de bonnes réponses :
                    - "🎉 Parfait ! Votre export {export_type} est prêt à tout casser !"
                    - "✨ Mission accomplie ! {len(data_result.get('articles', []))} éléments exportés avec succès !"
                    - "🚀 Boom ! Votre fichier {export_type} est chargé et prêt !"
                    
                    Reste court et percutant !"""
            
            # Générer la réponse avec Gemini
            with redirect_stderr(io.StringIO()):
                response = self.model.generate_content(prompt)
            
            return f"**{response.text.strip()}**\n\n"
            
        except Exception as e:
            # Fallback en cas d'erreur
            if language == 'en':
                return f"✅ **Your {export_type.upper()} file is ready!**\n\n"
            else:
                return f"✅ **Votre fichier {export_type.upper()} est prêt !**\n\n"

    def generate_dynamic_chart(self, articles: list, data_type: str) -> str:
        """
        Génère un graphique dynamique avec Chart.js
        
        Args:
            articles: Liste des articles
            data_type: Type de données (articles ou prestations)
        
        Returns:
            HTML du graphique dynamique
        """
        try:
            # Prendre les 20 premiers articles pour le graphique
            top_articles = articles[:20]
            
            # Préparer les données pour Chart.js
            labels = []
            prices = []
            colors = []
            
            # Palette viridis
            viridis_colors = [
                '#440154', '#482777', '#3f4a8a', '#31678e', '#26838f',
                '#1f9d8a', '#6cce5a', '#b6de2b', '#fee825', '#f0f921',
                '#fde725', '#f0f921', '#fee825', '#b6de2b', '#6cce5a',
                '#1f9d8a', '#26838f', '#31678e', '#3f4a8a', '#482777'
            ]
            
            for i, article in enumerate(top_articles):
                # Tronquer les noms trop longs
                name = article.get('nom', 'N/A')
                if len(name) > 20:
                    name = name[:17] + '...'
                labels.append(name)
                prices.append(float(article.get('prix', 0)))
                colors.append(viridis_colors[i % len(viridis_colors)])
            
            # Générer l'HTML avec Chart.js
            chart_html = f"""
            <div style="width: 100%; height: 400px; margin: 20px 0;">
                <canvas id="priceChart_{data_type}" width="800" height="400"></canvas>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const ctx_{data_type} = document.getElementById('priceChart_{data_type}').getContext('2d');
                const chart_{data_type} = new Chart(ctx_{data_type}, {{
                    type: 'bar',
                    data: {{
                        labels: {labels},
                        datasets: [{{
                            label: 'Prix (FCFA)',
                            data: {prices},
                            backgroundColor: {colors},
                            borderColor: {colors},
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            title: {{
                                display: true,
                                text: 'Prix des {data_type.title()} - Top 20 (sur {len(articles)} au total)',
                                font: {{
                                    size: 16,
                                    weight: 'bold'
                                }}
                            }},
                            legend: {{
                                display: false
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Prix (FCFA)'
                                }}
                            }},
                            x: {{
                                title: {{
                                    display: true,
                                    text: 'Articles'
                                }},
                                ticks: {{
                                    maxRotation: 45,
                                    minRotation: 45
                                }}
                            }}
                        }},
                        animation: {{
                            duration: 2000,
                            easing: 'easeInOutQuart'
                        }}
                    }}
                }});
            </script>
            """
            
            return chart_html
            
        except Exception as e:
            print(f"Erreur génération graphique dynamique: {e}")
            return f"<p>Erreur lors de la génération du graphique dynamique: {e}</p>"

    def generate_visualization(self, articles: list, data_type: str) -> str:
        """
        Génère un graphique réel et retourne l'URL de téléchargement
        
        Args:
            articles: Liste des articles
            data_type: Type de données (articles ou prestations)
        
        Returns:
            URL du fichier généré ou None si erreur
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # Backend non-interactif
            import os
            from datetime import datetime
            
            # Préparer les données pour le graphique
            if not articles:
                return None
            
            # Prendre les 20 premiers articles pour le graphique (plus représentatif)
            top_articles = articles[:20]
            names = [article.get('nom', 'N/A')[:15] + '...' if len(article.get('nom', '')) > 15 else article.get('nom', 'N/A') for article in top_articles]
            prices = [float(article.get('prix', 0)) for article in top_articles]
            
            # Créer le graphique
            plt.figure(figsize=(12, 8))
            bars = plt.bar(range(len(names)), prices, color='skyblue', alpha=0.7)
            
            # Personnaliser le graphique
            plt.title(f'Prix des {data_type.title()} - Top 20 (sur {len(articles)} au total)', fontsize=16, fontweight='bold')
            plt.xlabel('Articles', fontsize=12)
            plt.ylabel('Prix (FCFA)', fontsize=12)
            plt.xticks(range(len(names)), names, rotation=45, ha='right')
            
            # Ajouter les valeurs sur les barres
            for i, (bar, price) in enumerate(zip(bars, prices)):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(prices)*0.01,
                        f'{price:,.0f}', ha='center', va='bottom', fontsize=9)
            
            plt.tight_layout()
            
            # Créer le nom du fichier
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"graphique_{data_type}_{timestamp}.png"
            
            # Créer le dossier uploads s'il n'existe pas
            uploads_dir = "uploads"
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            filepath = os.path.join(uploads_dir, filename)
            
            # Sauvegarder le graphique
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            # Retourner l'URL relative
            return f"/uploads/{filename}"
            
        except Exception as e:
            print(f"Erreur génération graphique: {e}")
            return None

    def handle_top_request(self, user_message: str) -> Dict[str, Any]:
        """
        Gère les demandes de top (top 5, top 10, etc.)
        
        Args:
            user_message: Message de l'utilisateur
        
        Returns:
            Dict contenant la réponse avec le top demandé
        """
        try:
            language = self.detect_language(user_message)
            
            # Extraire le nombre du top (par défaut 5)
            import re
            number_match = re.search(r'top (\d+)|(\d+) meilleur|(\d+) premier', user_message.lower())
            if number_match:
                top_number = int(number_match.group(1) or number_match.group(2) or number_match.group(3))
            else:
                top_number = 5  # Par défaut top 5
            
            # Récupérer les articles les plus vendus
            articles_result = self.get_top_articles(top_number)
            
            if not articles_result.get('success', False):
                if language == 'en':
                    response = f"Sorry, I couldn't retrieve the top {top_number} articles. {articles_result.get('error', 'Unknown error')}"
                else:
                    response = f"Désolé, je n'ai pas pu récupérer le top {top_number} des articles. {articles_result.get('error', 'Erreur inconnue')}"
            else:
                articles = articles_result.get('articles', [])
                
                if language == 'en':
                    response = f"**Here is the top {top_number} best-selling articles:**\n\n"
                else:
                    response = f"**Voici le top {top_number} des articles les plus vendus :**\n\n"
                
                for i, article in enumerate(articles, 1):
                    response += f"{i}. **{article.get('nom', 'N/A')}**\n"
                    if article.get('quantite_vendue'):
                        response += f"   📊 Quantité vendue : {article.get('quantite_vendue')} exemplaires\n"
                    if article.get('prix'):
                        response += f"   💰 Prix : {article.get('prix'):,.0f} FCFA\n"
                    response += "\n"
                
                if articles_result.get('note'):
                    response += f"*{articles_result['note']}*"
            
            # Enregistrement
            top_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'top_request',
                'user_message': user_message,
                'response': response,
                'model_used': 'top_handler',
                'language_detected': language,
                'top_number': top_number
            }
            self.conversation_history.append(top_entry)
            
            return {
                'success': True,
                'response': response,
                'timestamp': top_entry['timestamp'],
                'model_used': 'top_handler',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'top_request',
                'top_number': top_number
            }
            
        except Exception as e:
            fallback_response = "Désolé, je n'ai pas pu traiter ta demande de top pour le moment."
            
            return {
                'success': True,
                'response': fallback_response,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'top_fallback',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'fallback'
            }

    def get_top_articles(self, limit: int = 5) -> Dict[str, Any]:
        """
        Récupère le top des articles les plus vendus
        
        Args:
            limit: Nombre d'articles à retourner
        
        Returns:
            Dict contenant les données des articles
        """
        try:
            import requests
            
            # Appel à l'API pour récupérer le top des articles
            response = requests.get(f'http://localhost:5001/admin/api/articles/top?limit={limit}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {
                        "success": True,
                        "articles": data['articles'],
                        "total": data['total'],
                        "note": data.get('note', '')
                    }
            else:
                return {"success": False, "error": f"Erreur API top articles: {response.status_code} - {response.text}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def handle_export_request(self, user_message: str) -> Dict[str, Any]:
        """
        Gère les demandes d'export (Excel, CSV, visualisations)
        
        Args:
            user_message: Message de l'utilisateur
        
        Returns:
            Dict contenant la réponse d'export
        """
        try:
            language = self.detect_language(user_message)
            response = ""  # Initialiser la variable response
            
            # Détecter le type d'export demandé
            message_lower = user_message.lower()
            
            if 'excel' in message_lower or 'tableau' in message_lower:
                export_type = 'excel'
            elif 'csv' in message_lower:
                export_type = 'csv'
            elif 'visualisation' in message_lower or 'graphique' in message_lower or 'chart' in message_lower:
                export_type = 'visualisation'
            else:
                export_type = 'excel'  # Par défaut Excel
            
            # Récupérer les données selon le type demandé
            if 'prestation' in message_lower or 'service' in message_lower:
                data_result = self.get_prestations_data(limit=None)  # Pas de limite - TOUS les prestations
                data_type = 'prestations'
            else:
                # Par défaut, articles (pour tous les exports) - TOUS les articles
                data_result = self.get_articles_prices(limit=None)  # Pas de limite - TOUS les articles
                data_type = 'articles'
            
            if not data_result.get('success', False):
                if language == 'en':
                    response = f"Sorry, I couldn't retrieve the {data_type} data for export. {data_result.get('error', 'Unknown error')}"
                else:
                    response = f"Désolé, je n'ai pas pu récupérer les données {data_type} pour l'export. {data_result.get('error', 'Erreur inconnue')}"
            else:
                # Générer le fichier réel
                if export_type == 'excel':
                    file_url = self.generate_excel_file(data_result['articles'], data_type)
                elif export_type == 'csv':
                    file_url = self.generate_csv_file(data_result['articles'], data_type)
                elif export_type == 'visualisation':
                    file_url = self.generate_visualization(data_result['articles'], data_type)
                else:
                    file_url = self.generate_excel_file(data_result['articles'], data_type)
                
                if file_url:
                    if language == 'en':
                        response = f"✅ **Your {export_type.upper()} file is ready!**\n\n"
                        response += f"📁 **Download:** <a href='{file_url}' target='_blank' style='color: #007bff; text-decoration: underline;'>Click here to download</a>\n\n"
                        response += f"📊 **Contains:** {len(data_result['articles'])} {data_type}\n"
                        response += f"• Product names and prices\n"
                        response += f"• Performance data\n"
                        response += f"• Strategic recommendations"
                    else:
                        # Générer une réponse variée avec Gemini
                        response = self.generate_varied_export_response(export_type, language, file_url, data_result)
                        response += f"📁 **Télécharger :** <a href='{file_url}' target='_blank' style='color: #007bff; text-decoration: underline;'>Cliquez ici pour télécharger</a>\n\n"
                        
                        # Si c'est une visualisation, afficher le graphique dynamique
                        if export_type == 'visualisation':
                            # Générer un graphique dynamique avec Chart.js
                            chart_html = self.generate_dynamic_chart(data_result['articles'], data_type)
                            response += f"{chart_html}\n\n"
                        else:
                            # Pour Excel et CSV, garder les détails
                            response += f"📊 **Contient :** {len(data_result['articles'])} {data_type}"
                            if 'total_articles' in data_result:
                                response += f" sur {data_result['total_articles']} au total"
                            response += f"\n"
                            response += f"• Noms et prix des produits\n"
                            response += f"• Données de performance\n"
                            response += f"• Recommandations stratégiques"
                else:
                    if language == 'en':
                        response = f"Sorry, I couldn't generate the {export_type} file. Please try again."
                    else:
                        response = f"Désolé, je n'ai pas pu générer le fichier {export_type}. Veuillez réessayer."
                
                # Si response est toujours vide, définir une réponse par défaut
                if not response:
                    if language == 'en':
                        response = f"Export {export_type} completed successfully."
                    else:
                        response = f"Export {export_type} terminé avec succès."
            
            # Enregistrement
            export_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'export',
                'user_message': user_message,
                'response': response,
                'model_used': 'export_handler',
                'language_detected': language,
                'export_type': export_type,
                'data_type': data_type
            }
            self.conversation_history.append(export_entry)
            
            return {
                'success': True,
                'response': response,
                'timestamp': export_entry['timestamp'],
                'model_used': 'export_handler',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'export',
                'export_type': export_type,
                'data_type': data_type,
                'data': data_result,
                'file_url': file_url if 'file_url' in locals() else None
            }
            
        except Exception as e:
            fallback_response = "Désolé, je n'ai pas pu traiter ta demande d'export pour le moment."
            
            return {
                'success': True,
                'response': fallback_response,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'export_fallback',
                'conversation_id': len(self.conversation_history),
                'capability_type': 'fallback'
            }
    
    def chat_with_bizzio(self, user_message: str) -> Dict[str, Any]:
        """
        Première fonctionnalité : Chat avec Bizzio Data Analyst
        
        Args:
            user_message: Message de l'utilisateur
        
        Returns:
            Dict contenant la réponse de Bizzio
        """
        try:
            # Détection des salutations simples - PRIORITÉ HAUTE
            if self.is_simple_greeting(user_message):
                return self.handle_simple_greeting(user_message)
            
            # Détection des questions sur les capacités - PRIORITÉ HAUTE
            if self.is_about_capabilities(user_message):
                return self.handle_capabilities_question(user_message)
            
            # Détection des questions éducatives - PRIORITÉ HAUTE
            if self.is_educational_question(user_message):
                return self.handle_educational_question(user_message)
            
            # Détection des demandes de top - PRIORITÉ HAUTE
            if self.is_top_request(user_message):
                return self.handle_top_request(user_message)
            
            # Détection des demandes d'export - PRIORITÉ HAUTE
            if self.is_export_request(user_message):
                return self.handle_export_request(user_message)
            
            # Détection des demandes de prix d'articles - PRIORITÉ HAUTE
            if self.is_article_price_request(user_message):
                return self.handle_article_price_request(user_message)
            
            # Détection automatique des questions catalogue et redirection
            if self.is_catalogue_question(user_message):
                return self.analyse_catalogue_products(user_message)
            
            # Vérification si c'est une question data analyst
            if not self.is_data_analyst_question(user_message):
                return self.handle_non_data_analyst_question(user_message)
            
            # Troisième fonctionnalité : Comportement Intelligent
            # 1. Détection des messages malveillants - mais laisse Bizzio répondre naturellement
            is_malicious = self.detect_malicious_content(user_message)
            
            # 2. Détection du niveau technique et des clarifications nécessaires
            technical_level = self.detect_technical_level(user_message)
            needs_clarification = self.needs_clarification(user_message)
            
            # Construction du prompt avec comportement intelligent
            conversation_context = ""
            if len(self.conversation_history) > 0:
                recent_conversations = self.conversation_history[-3:]
                conversation_context = "\n\nContexte de la conversation :\n"
                for conv in recent_conversations:
                    conversation_context += f"Utilisateur: {conv['user_message']}\n"
                    conversation_context += f"Bizzio: {conv['response']}\n"
            
            # Ajout des instructions de comportement intelligent
            malicious_context = "ATTENTION : L'utilisateur semble frustré ou mécontent. Excuse-toi humblement et propose ton aide." if is_malicious else ""
            
            intelligent_instructions = f"""
{self.prompts.get_intelligent_behavior_prompt()}

INFORMATIONS CONTEXTUELLES :
- Niveau technique détecté : {technical_level}
- Clarification nécessaire : {needs_clarification}
- Message utilisateur : {user_message}
{malicious_context}
"""
            
            chat_prompt = f"{self.get_system_prompt()}{conversation_context}{intelligent_instructions}"
            
            # Supprimer les warnings lors de l'appel API
            with redirect_stderr(io.StringIO()):
                response = self.model.generate_content(chat_prompt)
            
            # Enregistrement de la conversation
            conversation_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'chat',
                'user_message': user_message,
                'response': response.text,
                'model_used': 'gemini-2.0-flash-lite',
                'technical_level': technical_level,
                'needs_clarification': needs_clarification,
                'is_malicious': is_malicious
            }
            self.conversation_history.append(conversation_entry)
            
            return {
                'success': True,
                'response': response.text,
                'timestamp': conversation_entry['timestamp'],
                'model_used': 'gemini-2.0-flash-lite',
                'conversation_id': len(self.conversation_history),
                'technical_level': technical_level,
                'needs_clarification': needs_clarification
            }
            
        except Exception as e:
            # Gestion des erreurs avec excuses automatiques
            return self.handle_error(e, user_message)
    
    def handle_error(self, error: Exception, user_message: str) -> Dict[str, Any]:
        """
        Deuxième fonctionnalité : Gestion des erreurs avec excuses et suggestions
        
        Args:
            error: Exception survenue
            user_message: Message de l'utilisateur qui a causé l'erreur
        
        Returns:
            Dict contenant la réponse d'erreur de Bizzio
        """
        error_msg = str(error)
        error_type = "Erreur technique"
        
        # Classification des erreurs
        if "429" in error_msg or "quota" in error_msg.lower():
            error_type = "Quota dépassé"
        elif "timeout" in error_msg.lower():
            error_type = "Délai d'attente dépassé"
        elif "connection" in error_msg.lower():
            error_type = "Problème de connexion"
        elif "api" in error_msg.lower():
            error_type = "Erreur API"
        else:
            error_type = "Erreur technique"
        
        try:
            # Générer une réponse d'erreur humaine avec Bizzio
            error_prompt = f"{self.get_system_prompt()}\n\n{self.prompts.get_error_handling_prompt(error_type, error_msg)}"
            
            with redirect_stderr(io.StringIO()):
                response = self.model.generate_content(error_prompt)
            
            # Enregistrement de l'erreur
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'error',
                'user_message': user_message,
                'error_type': error_type,
                'error_message': error_msg,
                'response': response.text,
                'model_used': 'gemini-2.0-flash-lite'
            }
            self.conversation_history.append(error_entry)
            
            return {
                'success': True,
                'response': response.text,
                'timestamp': error_entry['timestamp'],
                'model_used': 'gemini-2.0-flash-lite',
                'conversation_id': len(self.conversation_history),
                'error_handled': True,
                'error_type': error_type
            }
            
        except Exception as fallback_error:
            # En cas d'échec de la gestion d'erreur, réponse de base
            fallback_responses = [
                "Désolé, j'ai un petit souci technique. Peux-tu reformuler ta question ?",
                "Oups, erreur de ma part. Essaie de me poser la question différemment.",
                "Pardon, j'ai buggé. Peux-tu répéter s'il te plaît ?",
                "Désolé, problème technique. Peux-tu être plus précis dans ta question ?"
            ]
            
            import random
            fallback_response = random.choice(fallback_responses)
            
            return {
                'success': True,
                'response': fallback_response,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'gemini-2.0-flash-lite',
                'conversation_id': len(self.conversation_history),
                'error_handled': True,
                'error_type': 'fallback'
            }
    
    
    def get_conversation_history(self) -> list:
        """Récupère l'historique des conversations"""
        return self.conversation_history
    
    def clear_history(self):
        """Efface l'historique des conversations"""
        self.conversation_history = []
        self.logger.info("Historique des conversations effacé")
    
    def simulate_error(self, error_type: str = "test") -> Dict[str, Any]:
        """
        Fonction pour simuler des erreurs et tester la gestion d'erreurs
        
        Args:
            error_type: Type d'erreur à simuler
        
        Returns:
            Dict contenant la réponse d'erreur de Bizzio
        """
        if error_type == "quota":
            error = Exception("429 Quota exceeded")
        elif error_type == "timeout":
            error = Exception("Request timeout")
        elif error_type == "connection":
            error = Exception("Connection failed")
        elif error_type == "api":
            error = Exception("API error 500")
        else:
            error = Exception("Test error simulation")
        
        return self.handle_error(error, "Test message")
    
    def detect_malicious_content(self, message: str) -> bool:
        """
        Détecte les messages malveillants ou inappropriés avec Gemini
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si le message est malveillant
        """
        try:
            # Utiliser Gemini pour détecter intelligemment les propos inappropriés
            detection_prompt = f"""
Analyse ce message et détermine s'il contient des propos inappropriés, grossiers, malveillants ou offensants.

Message: "{message}"

Réponds uniquement par "OUI" si le message est inapproprié, "NON" sinon.
"""
            
            with redirect_stderr(io.StringIO()):
                response = self.model.generate_content(detection_prompt)
            
            return "OUI" in response.text.upper()
            
        except:
            # Fallback simple pour les messages très courts répétitifs
            if len(message.strip()) < 3 and len(self.conversation_history) > 2:
                recent_messages = [conv['user_message'] for conv in self.conversation_history[-3:]]
                if len(set(recent_messages)) == 1:
                    return True
            return False
    
    def detect_technical_level(self, message: str) -> str:
        """
        Détecte le niveau technique de l'utilisateur
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            'beginner', 'intermediate', ou 'expert'
        """
        technical_terms = [
            'sql', 'python', 'r', 'pandas', 'numpy', 'matplotlib', 'seaborn',
            'regression', 'correlation', 'variance', 'standard deviation',
            'machine learning', 'ai', 'algorithm', 'model', 'prediction',
            'database', 'query', 'join', 'index', 'optimization', 'performance'
        ]
        
        advanced_terms = [
            'neural network', 'deep learning', 'tensorflow', 'pytorch',
            'clustering', 'classification', 'feature engineering',
            'cross-validation', 'hyperparameter', 'gradient descent',
            'api', 'microservices', 'docker', 'kubernetes', 'scalability'
        ]
        
        message_lower = message.lower()
        
        advanced_count = sum(1 for term in advanced_terms if term in message_lower)
        technical_count = sum(1 for term in technical_terms if term in message_lower)
        
        if advanced_count >= 2:
            return 'expert'
        elif technical_count >= 2 or advanced_count >= 1:
            return 'intermediate'
        else:
            return 'beginner'
    
    def needs_clarification(self, message: str) -> bool:
        """
        Détermine si le message nécessite des clarifications
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si des clarifications sont nécessaires
        """
        vague_indicators = [
            'ça', 'ça va', 'comment', 'quoi', 'hein', 'ok', 'oui', 'non',
            'help', 'help me', 'je sais pas', 'je ne comprends pas',
            'explique', 'comment faire', 'que faire'
        ]
        
        message_lower = message.lower().strip()
        
        # Messages très courts sans contexte
        if len(message_lower) < 5:
            return True
        
        # Messages vagues
        for indicator in vague_indicators:
            if message_lower == indicator:
                return True
        
        # Questions sans contexte spécifique
        if message_lower in ['analyse', 'données', 'data', 'chiffres']:
            return True
        
        return False
    
    def is_catalogue_question(self, message: str) -> bool:
        """
        Détecte si la question concerne l'analyse catalogue/produits
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si c'est une question catalogue
        """
        message_lower = message.lower()
        
        # Mots-clés étendus pour les questions catalogue (français + anglais + variantes)
        catalogue_keywords = [
            # Français - variantes étendues
            'produits', 'articles', 'catalogue', 'prestations',
            'plus vendus', 'meilleurs', 'top', 'performance',
            'revenus', 'génère', 'rentabilité', 'catégorie',
            'répartition', 'évolution', 'mensuel', 'tendance',
            'offres', 'explosé', 'croissance', 'trimestre',
            'ventes', 'chiffre', 'ca', 'business', 'commercial',
            'marché', 'client', 'achat', 'commande',
            # Anglais - variantes étendues
            'products', 'items', 'best-selling', 'top-performing',
            'category', 'categories', 'revenue', 'sales',
            'month', 'quarter', 'performance', 'offers',
            'business', 'commercial', 'market', 'client',
            'purchase', 'order', 'selling', 'profit'
        ]
        
        # Vérifier si au moins un mot-clé catalogue est présent
        for keyword in catalogue_keywords:
            if keyword in message_lower:
                return True
        
        # Questions spécifiques étendues (français + anglais + variantes)
        specific_questions = [
            # Français - variantes
            'quels sont nos', 'donne-moi les', 'montre-moi',
            'quelle prestation', 'comment sont', 'comment évolue',
            'quels produits', 'quelles prestations', 'nos meilleurs',
            'top de', 'classement', 'ranking', 'stats', 'statistiques',
            # Anglais - variantes
            'what are our', 'show me the', 'which category',
            'what are the', 'top 10', 'best-selling', 'our best',
            'ranking of', 'stats on', 'data on', 'analysis of'
        ]
        
        for question in specific_questions:
            if message_lower.startswith(question):
                return True
        
        # Patterns spécifiques étendus
        patterns = [
            'top.*items', 'best.*products', 'category.*perform',
            'top.*offers', 'quarter.*performance', 'month.*top',
            'nos.*plus', 'meilleurs.*', 'classement.*',
            'stats.*', 'data.*', 'analysis.*'
        ]
        
        import re
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return True
        
        return False
    
    
    def is_simple_greeting(self, message: str) -> bool:
        """
        Détecte si le message est UNIQUEMENT une salutation simple
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si c'est UNIQUEMENT une salutation simple
        """
        message_lower = message.lower().strip()
        
        # Salutations PUREMENT simples (sans contexte business)
        pure_greetings = [
            # Très courts uniquement
            'yo', 'hey', 'hi', 'salut', 'coucou', 'hello',
            # Salutations de base
            'bonjour', 'bonsoir', 'bonne soirée', 'bon après-midi',
            'good morning', 'good afternoon', 'good evening',
            # Questions d'état simples
            'ça va', 'comment ça va', 'how are you', 'how are you doing'
        ]
        
        # Vérifier si c'est EXACTEMENT une salutation simple
        if message_lower in pure_greetings:
            return True
        
        # Messages très courts (1-2 mots) qui sont des salutations pures
        words = message_lower.split()
        if len(words) <= 2 and any(word in pure_greetings for word in words):
            return True
        
        # EXCLUSION : Si le message contient des mots business, ce n'est PAS une salutation
        business_keywords = ['prix', 'article', 'prestation', 'performance', 'vente', 'client', 'données', 'analyse', 'liste', 'complet', 'livre', 'chimie', 'oxford']
        if any(keyword in message_lower for keyword in business_keywords):
            return False
        
        return False
    
    def detect_language(self, message: str) -> str:
        """
        Détecte la langue du message utilisateur
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            'fr' pour français, 'en' pour anglais
        """
        message_lower = message.lower()
        
        # Mots-clés anglais
        english_words = ['hello', 'hi', 'hey', 'how', 'what', 'where', 'when', 'why', 'good', 'morning', 'afternoon', 'evening', 'thanks', 'thank you', 'show me', 'give me', 'can you', 'please']
        
        # Mots-clés français (plus étendus)
        french_words = ['salut', 'bonjour', 'bonsoir', 'comment', 'quoi', 'où', 'quand', 'pourquoi', 'merci', 'matin', 'après-midi', 'soir', 'montre', 'donne', 'peux', 'peut', 'liste', 'complet', 'articles', 'prestations', 'prix', 'performance', 'analyse', 'données', 'business', 'ventes', 'clients']
        
        english_count = sum(1 for word in english_words if word in message_lower)
        french_count = sum(1 for word in french_words if word in message_lower)
        
        # Si le message contient des mots français spécifiques, priorité au français
        if any(word in message_lower for word in ['montre-moi', 'donne-moi', 'peux-tu', 'peut-il', 'liste complète', 'articles', 'prestations', 'prix', 'performance']):
            return 'fr'
        
        if english_count > french_count:
            return 'en'
        elif french_count > english_count:
            return 'fr'
        else:
            # Par défaut français si ambigu
            return 'fr'
    
    def handle_simple_greeting(self, user_message: str) -> Dict[str, Any]:
        """
        Gère les salutations simples avec des réponses courtes et naturelles
        
        Args:
            user_message: Message de salutation de l'utilisateur
        
        Returns:
            Dict contenant la réponse courte de Bizzio
        """
        try:
            # Détection de la langue
            language = self.detect_language(user_message)
            message_lower = user_message.lower().strip()
            
            # Réponses selon la langue détectée
            if language == 'en':
                # Salutations informelles en anglais
                if any(term in message_lower for term in ['yo', 'hey', 'hi', 'hello']):
                    responses = [
                        "Hi ! How are you ?",
                        "Hey ! What's up ?",
                        "Hello ! How can I help ?"
                    ]
                # Questions sur l'état en anglais
                elif any(term in message_lower for term in ['how are you', 'how are you doing', 'how\'s it going', 'how\'s everything']):
                    responses = [
                        "I'm good, thanks ! How about you ?",
                        "Great ! What can I analyze for you ?",
                        "Fine ! Ready for some data analysis ?"
                    ]
                # Salutations formelles en anglais
                else:
                    responses = [
                        "Hello ! How can I help with your data ?",
                        "Hi ! What would you like to analyze ?",
                        "Hello ! Ready for data analysis ?"
                    ]
            else:
                # Salutations informelles en français
                if any(term in message_lower for term in ['yo', 'hey', 'salut', 'coucou']):
                    responses = [
                        "Salut ! Comment ça va ?",
                        "Hey ! Qu'est-ce qu'on fait ?",
                        "Salut ! Prêt pour l'analyse ?"
                    ]
                # Questions sur l'état en français
                elif any(term in message_lower for term in ['ça va', 'comment ça va', 'comment tu vas', 'comment allez-vous']):
                    responses = [
                        "Ça va bien, merci ! Et toi ?",
                        "Très bien ! Qu'est-ce qu'on analyse ?",
                        "Parfait ! Prêt pour les données ?"
                    ]
                # Salutations formelles en français
                else:
                    responses = [
                        "Bonjour ! Comment puis-je t'aider ?",
                        "Salut ! Qu'est-ce qu'on analyse ?",
                        "Bonjour ! Prêt pour l'analyse ?"
                    ]
            
            # Sélection aléatoire d'une réponse
            import random
            selected_response = random.choice(responses)
            
            # Enregistrement de la salutation
            greeting_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'greeting',
                'user_message': user_message,
                'response': selected_response,
                'model_used': 'simple_greeting',
                'greeting_type': 'simple',
                'language_detected': language
            }
            self.conversation_history.append(greeting_entry)
            
            return {
                'success': True,
                'response': selected_response,
                'timestamp': greeting_entry['timestamp'],
                'model_used': 'simple_greeting',
                'conversation_id': len(self.conversation_history),
                'greeting_type': 'simple',
                'language_detected': language
            }
            
        except Exception as e:
            # Fallback simple en cas d'erreur
            fallback_response = "Salut ! Comment puis-je t'aider ?"
            
            return {
                'success': True,
                'response': fallback_response,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'simple_greeting_fallback',
                'conversation_id': len(self.conversation_history),
                'greeting_type': 'fallback'
            }
    
    def is_data_analyst_question(self, message: str) -> bool:
        """
        Détecte si la question concerne le domaine data analyst
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si c'est une question data analyst
        """
        message_lower = message.lower()
        
        # Mots-clés pour le domaine data analyst
        data_keywords = [
            # Français
            'données', 'analyse', 'statistiques', 'rapport', 'kpi',
            'métriques', 'performance', 'ventes', 'chiffre', 'ca',
            'business', 'commercial', 'clients', 'produits', 'articles',
            'prestations', 'revenus', 'rentabilité', 'croissance',
            'tendance', 'évolution', 'comparaison', 'segmentation',
            # Anglais
            'data', 'analysis', 'statistics', 'report', 'kpi',
            'metrics', 'performance', 'sales', 'revenue', 'business',
            'commercial', 'clients', 'products', 'items', 'services',
            'profit', 'growth', 'trend', 'evolution', 'comparison',
            'segmentation'
        ]
        
        # Vérifier si au moins un mot-clé data analyst est présent
        for keyword in data_keywords:
            if keyword in message_lower:
                return True
        
        # Questions spécifiques data analyst
        data_questions = [
            'analyse', 'données', 'rapport', 'stats', 'métriques',
            'performance', 'ventes', 'chiffre', 'business', 'commercial'
        ]
        
        for question in data_questions:
            if question in message_lower:
                return True
        
        return False
    
    def handle_non_data_analyst_question(self, user_message: str) -> Dict[str, Any]:
        """
        Gère les questions qui ne sont pas dans le domaine data analyst
        
        Args:
            user_message: Message de l'utilisateur
        
        Returns:
            Dict contenant la réponse de redirection polie
        """
        try:
            # Générer une réponse de redirection polie avec Gemini
            redirection_prompt = f"""
Tu es Bizzio, un Data Analyst expert. L'utilisateur t'a posé cette question : "{user_message}"

Cette question ne concerne pas ton domaine d'expertise (analyse de données business).

Réponds de façon polie et professionnelle en :
1. Expliquant gentiment que tu es spécialisé dans l'analyse de données business
2. Redirigeant vers ton domaine d'expertise
3. Proposant des exemples de questions que tu peux traiter
4. Restant courtois et utile

Exemples de questions que tu peux traiter :
- Analyses de ventes et produits
- Performance des prestations
- Statistiques business
- Rapports et métriques
- Analyses de clients et revenus

Sois naturel et humain dans ta réponse.
"""
            
            with redirect_stderr(io.StringIO()):
                response = self.model.generate_content(redirection_prompt)
            
            # Enregistrement de la redirection
            redirection_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'redirection',
                'user_message': user_message,
                'response': response.text,
                'model_used': 'gemini-2.0-flash',
                'reason': 'question_hors_domaine'
            }
            self.conversation_history.append(redirection_entry)
            
            return {
                'success': True,
                'response': response.text,
                'timestamp': redirection_entry['timestamp'],
                'model_used': 'gemini-2.0-flash',
                'conversation_id': len(self.conversation_history),
                'redirection': True,
                'reason': 'question_hors_domaine'
            }
            
        except Exception as e:
            # Fallback en cas d'erreur
            fallback_response = "Désolé, je suis spécialisé dans l'analyse de données business. Je peux t'aider avec des analyses de ventes, produits, clients, ou rapports. Peux-tu me poser une question dans mon domaine d'expertise ?"
            
            return {
                'success': True,
                'response': fallback_response,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'gemini-2.0-flash',
                'conversation_id': len(self.conversation_history),
                'redirection': True,
                'reason': 'fallback'
            }
    
    def analyse_catalogue_products(self, user_message: str) -> Dict[str, Any]:
        """
        Neuvième fonctionnalité : Analyses Produits et Catalogue
        
        Analyse les données produits et catalogue en utilisant les routes API disponibles :
        - /admin/api/reporting/top-articles : Articles les plus vendus
        - /admin/api/catalogue/top-prestations : Prestations par catégorie
        - /admin/api/reporting/prestation-performance : Performance des prestations
        - /admin/api/catalogue/monthly-evolution : Évolution mensuelle du catalogue
        
        Args:
            user_message: Question de l'utilisateur sur les produits/catalogue
        
        Returns:
            Dict contenant l'analyse de Bizzio
        """
        try:
            # Détection du type d'analyse demandé
            analysis_type = self.detect_catalogue_analysis_type(user_message)
            
            # Détection de la quantité demandée
            requested_quantity = self.detect_requested_quantity(user_message)
            
            # Récupération des VRAIES données selon le type d'analyse
            real_data = self.get_real_catalogue_data(analysis_type, requested_quantity)
            
            # Construction du prompt spécialisé avec les vraies données et contexte enrichi
            enhanced_context = f"""
QUESTION UTILISATEUR : {user_message}
TYPE D'ANALYSE DÉTECTÉ : {analysis_type}
QUANTITÉ DEMANDÉE : {requested_quantity} éléments

CONTEXTE BUSINESS :
- L'utilisateur cherche des insights sur les performances produits/catalogue
- Il veut probablement des recommandations actionnables
- Il s'attend à une analyse professionnelle et humaine

DONNÉES RÉELLES DISPONIBLES :
{real_data['data_summary']}

DONNÉES DÉTAILLÉES :
{real_data['detailed_data']}

INSTRUCTIONS SPÉCIALES :
- COMPRENDS le contexte avant de répondre
- VARIE ton style de réponse (ne sois pas robotique)
- Sois PROACTIF dans tes insights
- Propose des analyses spontanées
- Montre de l'enthousiasme pour les bonnes performances
"""
            
            catalogue_prompt = f"{self.get_system_prompt()}\n\n{self.prompts.get_catalogue_analysis_prompt(analysis_type, enhanced_context)}"
            
            # Génération de la réponse avec Gemini
            with redirect_stderr(io.StringIO()):
                response = self.model.generate_content(catalogue_prompt)
            
            # Enregistrement de l'analyse
            analysis_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': 'catalogue_analysis',
                'analysis_type': analysis_type,
                'requested_quantity': requested_quantity,
                'user_message': user_message,
                'response': response.text,
                'model_used': 'gemini-2.0-flash',
                'data_sources': self.get_catalogue_data_sources(analysis_type)
            }
            self.conversation_history.append(analysis_entry)
            
            return {
                'success': True,
                'response': response.text,
                'timestamp': analysis_entry['timestamp'],
                'model_used': 'gemini-2.0-flash',
                'conversation_id': len(self.conversation_history),
                'analysis_type': analysis_type,
                'requested_quantity': requested_quantity,
                'data_sources': analysis_entry['data_sources']
            }
            
        except Exception as e:
            return self.handle_error(e, user_message)
    
    def detect_catalogue_analysis_type(self, message: str) -> str:
        """
        Détecte le type d'analyse catalogue demandé par l'utilisateur
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            Type d'analyse détecté
        """
        message_lower = message.lower()
        
        # Export de données (priorité haute)
        if any(term in message_lower for term in [
            'export', 'exporter', 'csv', 'excel', 'fichier', 'télécharger', 'download',
            'liste complète', 'tous les articles', 'all articles', 'complete list',
            'données complètes', 'full data', 'export data'
        ]):
            return "articles_prices"
        
        # Questions sur les prix (priorité haute)
        elif any(term in message_lower for term in [
            'prix', 'price', 'coût', 'cost', 'tarif', 'tariff', 'combien coûte',
            'how much', 'pricing', 'prix des articles', 'article prices',
            'liste des prix', 'price list', 'tarification'
        ]):
            return "articles_prices"
        
        # Vue d'ensemble du catalogue - rediriger vers top_articles
        elif any(term in message_lower for term in ['vue d\'ensemble', 'vue ensemble', 'ensemble', 'global', 'synthèse', 'résumé', 'nos meilleurs', 'meilleurs']):
            return "top_articles"
        
        # Questions temporelles (mensuel, trimestre) - rediriger vers top_articles
        elif any(term in message_lower for term in ['mensuel', 'month', 'trimestre', 'quarter', 'ce mois', 'this month', 'ce trimestre', 'this quarter']):
            return "top_articles"
        
        # Analyse des articles les plus vendus (français + anglais)
        elif any(term in message_lower for term in [
            'articles', 'produits', 'plus vendus', 'top articles', 'meilleurs produits',
            'items', 'products', 'best-selling', 'top 10', 'top-performing',
            'explosé', 'croissance', 'offres', 'offers', 'stats', 'statistiques',
            'ventes', 'sales', 'chiffre', 'ca', 'business'
        ]):
            return "top_articles"
        
        # Performance des prestations (français + anglais)
        elif any(term in message_lower for term in [
            'performance', 'rentabilité', 'revenus', 'génère', 'rapport',
            'performs', 'revenue', 'generates', 'best', 'top-performing'
        ]):
            return "prestation_performance"
        
        # Analyse des prestations par catégorie (français + anglais)
        elif any(term in message_lower for term in [
            'prestations', 'catégorie', 'type', 'répartition',
            'category', 'categories', 'which category'
        ]):
            return "prestations_category"
        
        # Analyse générale du catalogue
        else:
            return "catalogue_overview"
    
    def detect_requested_quantity(self, message: str) -> int:
        """
        Détecte le nombre d'éléments demandés par l'utilisateur
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            Nombre d'éléments demandés (défaut: 5)
        """
        import re
        
        # Recherche de nombres dans le message
        numbers = re.findall(r'\b(\d+)\b', message)
        
        if numbers:
            # Prendre le premier nombre trouvé
            requested_qty = int(numbers[0])
            # Limiter à un maximum raisonnable
            return min(requested_qty, 50)
        
        # Mots-clés pour détecter des quantités spécifiques (français + anglais)
        message_lower = message.lower()
        
        if any(term in message_lower for term in ['top 10', '10 meilleurs', 'dix', '10 produits', '10 items']):
            return 10
        elif any(term in message_lower for term in ['top 20', '20 meilleurs', 'vingt', '20 produits', '20 items']):
            return 20
        elif any(term in message_lower for term in ['top 5', '5 meilleurs', 'cinq', '5 produits', '5 items']):
            return 5
        elif any(term in message_lower for term in ['tous', 'toutes', 'complet', 'entier', 'all', 'complete']):
            return 50  # Maximum raisonnable
        
        # Par défaut, retourner 5
        return 5
    
    def get_catalogue_data_context(self, analysis_type: str, requested_quantity: int = 5) -> str:
        """
        Génère le contexte de données pour l'analyse catalogue
        
        Args:
            analysis_type: Type d'analyse demandé
            requested_quantity: Nombre d'éléments demandés par l'utilisateur
        
        Returns:
            Contexte de données formaté
        """
        contexts = {
            "top_articles": f"""
DONNÉES DISPONIBLES - Articles les plus vendus :
- Route API : /admin/api/reporting/top-articles
- Métriques : nom, quantité totale, CA total, nombre de commandes
- Tri : par CA total décroissant
- Limite demandée : {requested_quantity} articles

ANALYSE ATTENDUE :
- Identification des {requested_quantity} produits stars avec données réelles
- Analyse de la contribution au CA avec chiffres exacts
- Recommandations de promotion basées sur les performances réelles
- Opportunités d'optimisation identifiées dans les données
- Réponse adaptée au nombre demandé par l'utilisateur ({requested_quantity} éléments)
""",
            
            "prestations_category": """
DONNÉES DISPONIBLES - Prestations par catégorie :
- Route API : /admin/api/catalogue/top-prestations
- Métriques : type_article, quantité totale, CA total
- Tri : par quantité décroissante
- Inclut : frais et remises dans le calcul

ANALYSE ATTENDUE :
- Répartition des revenus par catégorie
- Identification des catégories dominantes
- Analyse de la diversité du catalogue
- Recommandations d'équilibrage
""",
            
            "prestation_performance": """
DONNÉES DISPONIBLES - Performance des prestations :
- Route API : /admin/api/reporting/prestation-performance
- Métriques : prestation, CA total, nb commandes, nb clients, pourcentage
- Filtre : seulement terminé/partiel
- Tri : par CA total décroissant

ANALYSE ATTENDUE :
- Analyse de rentabilité par prestation
- Identification des prestations à fort potentiel
- Recommandations stratégiques
- Optimisation de l'offre
""",
            
            "monthly_evolution": """
DONNÉES DISPONIBLES - Évolution mensuelle :
- Route API : /admin/api/catalogue/monthly-evolution
- Métriques : évolution mensuelle des prestations
- Période : données historiques disponibles
- Format : série temporelle

ANALYSE ATTENDUE :
- Tendances de croissance/décroissance
- Saisonnalité des prestations
- Prévisions et recommandations
- Optimisation temporelle
""",
            
            "catalogue_overview": """
DONNÉES DISPONIBLES - Vue d'ensemble catalogue :
- Routes multiples : top-articles, top-prestations, prestation-performance
- Métriques complètes : articles, prestations, performance, évolution
- Vue globale : analyse 360° du catalogue

ANALYSE ATTENDUE :
- Synthèse complète du catalogue
- Insights stratégiques globaux
- Recommandations d'optimisation
- Plan d'action prioritaire
"""
        }
        
        return contexts.get(analysis_type, contexts["catalogue_overview"])
    
    def get_catalogue_data_sources(self, analysis_type: str) -> list:
        """
        Retourne les sources de données utilisées pour l'analyse
        
        Args:
            analysis_type: Type d'analyse
        
        Returns:
            Liste des sources de données
        """
        sources_map = {
            "top_articles": ["/admin/api/reporting/top-articles"],
            "prestations_category": ["/admin/api/catalogue/top-prestations"],
            "prestation_performance": ["/admin/api/reporting/prestation-performance"],
            "monthly_evolution": ["/admin/api/catalogue/monthly-evolution"],
            "catalogue_overview": [
                "/admin/api/reporting/top-articles",
                "/admin/api/catalogue/top-prestations", 
                "/admin/api/reporting/prestation-performance",
                "/admin/api/catalogue/monthly-evolution"
            ]
        }
        
        return sources_map.get(analysis_type, [])
    
    def search_article_by_name(self, article_name: str) -> Dict[str, Any]:
        """
        Recherche un article par nom et retourne son prix avec gestion des erreurs de frappe
        
        Args:
            article_name: Nom de l'article à rechercher
        
        Returns:
            Dict contenant les données de l'article trouvé
        """
        try:
            import requests
            
            # Normaliser le nom de l'article pour gérer les erreurs de frappe
            normalized_name = self.normalize_article_name(article_name)
            
            # Stratégies de recherche multiples
            search_strategies = [
                article_name,  # Recherche exacte
                normalized_name,  # Recherche normalisée
                ' '.join(normalized_name.split()[:2]) if len(normalized_name.split()) >= 2 else normalized_name,  # 2 premiers mots
                ' '.join(normalized_name.split()[:1]) if len(normalized_name.split()) >= 1 else normalized_name,  # 1er mot
            ]
            
            # Ajouter des variantes intelligentes
            keywords = normalized_name.lower().split()
            for keyword in keywords:
                if len(keyword) > 3:  # Ignorer les mots trop courts
                    search_strategies.append(keyword)
            
            # Essayer chaque stratégie de recherche
            for strategy in search_strategies:
                if not strategy or strategy.strip() == '':
                    continue
                    
                response = requests.get(f'http://localhost:5001/admin/api/articles/search?q={strategy}')
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and data.get('articles'):
                        # Retourner le premier article trouvé
                        article = data['articles'][0]
                        return {
                            "success": True,
                            "article": article,
                            "found": True,
                            "original_query": article_name,
                            "normalized_query": normalized_name,
                            "search_strategy": strategy,
                            "typo_corrected": strategy != article_name
                        }
            
            # Recherche intelligente par mots-clés similaires
            similar_articles = self.find_similar_articles(article_name)
            if similar_articles:
                return {
                    "success": True,
                    "article": similar_articles[0],
                    "found": True,
                    "original_query": article_name,
                    "normalized_query": normalized_name,
                    "similar_match": True,
                    "suggestions": similar_articles
                }
            
            return {
                "success": True,
                "article": None,
                "found": False,
                "message": f"Article '{article_name}' non trouvé",
                "original_query": article_name,
                "normalized_query": normalized_name
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def find_similar_articles(self, article_name: str) -> list:
        """
        Trouve des articles similaires basés sur des mots-clés
        
        Args:
            article_name: Nom de l'article recherché
        
        Returns:
            Liste des articles similaires trouvés
        """
        try:
            import requests
            
            # Mots-clés de correspondance intelligente
            keywords = article_name.lower().split()
            
            # Correspondances partielles intelligentes
            search_terms = []
            
            # Recherche intelligente par mots-clés - basée sur la vraie base de données
            # D'abord essayer une recherche directe avec le nom de l'article
            search_terms.append(article_name)
            
            # Puis essayer des variantes intelligentes
            if 'advanced' in keywords:
                search_terms.extend(['advanced', 'advanced level', 'advanced chemistry'])
            
            if 'level' in keywords:
                search_terms.extend(['level', 'advanced level', 'level physics'])
            
            if 'oxford' in keywords:
                search_terms.extend(['oxford', 'chemistry oxford', 'oxford chemistry'])
            
            if 'chemistry' in keywords:
                search_terms.extend(['chemistry', 'advanced chemistry', 'chemistry oxford'])
            
            if 'physics' in keywords:
                search_terms.extend(['physics', 'advanced level physics', 'level physics'])
            
            # Recherche par mots-clés généraux
            for keyword in keywords:
                if len(keyword) > 3:  # Ignorer les mots trop courts
                    search_terms.append(keyword)
            
            # Essayer chaque terme de recherche
            for term in search_terms:
                response = requests.get(f'http://localhost:5001/admin/api/articles/search?q={term}')
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and data.get('articles'):
                        return data['articles']
            
            return []
            
        except Exception as e:
            return []
    
    def get_articles_prices(self, limit: int = 50) -> Dict[str, Any]:
        """
        Récupère la liste complète des articles avec leurs prix
        
        Args:
            limit: Nombre d'articles à retourner
        
        Returns:
            Dict contenant les données des articles avec prix
        """
        try:
            import requests
            
            # Appel à l'API d'export d'articles
            response = requests.get(f'http://localhost:5001/admin/api/articles/export?format=json&limit={limit}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {
                        "success": True,
                        "articles": data.get('articles', []),
                        "total_articles": data.get('total', 0),
                        "limit": limit
                    }
                else:
                    return {"success": False, "error": data.get('message', 'Erreur API')}
            else:
                return {"success": False, "error": "Erreur API d'export"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_prestations_data(self, limit: int = 50) -> Dict[str, Any]:
        """
        Récupère la liste des prestations avec leurs tarifs
        
        Args:
            limit: Nombre de prestations à retourner
        
        Returns:
            Dict contenant les données des prestations
        """
        try:
            conn = self.data_access.get_db_connection()
            if not conn:
                return {"success": False, "error": "Connexion à la base de données échouée"}
            
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Requête pour récupérer les prestations
            query = """
                SELECT 
                    p.prestation_id,
                    p.nom_prestation,
                    p.tarif,
                    p.type_prestation,
                    p.description
                FROM prestations p
                WHERE p.nom_prestation IS NOT NULL AND p.nom_prestation != ''
                ORDER BY p.tarif DESC, p.nom_prestation ASC
                LIMIT %s
            """
            
            cur.execute(query, (limit,))
            results = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Conversion en format utilisable
            prestations = []
            for row in results:
                prestations.append({
                    'id': row['prestation_id'],
                    'nom': row['nom_prestation'],
                    'tarif': float(row['tarif']) if row['tarif'] else 0.0,
                    'type': row['type_prestation'],
                    'description': row['description']
                })
            
            return {
                "success": True,
                "prestations": prestations,
                "total_prestations": len(prestations),
                "limit": limit
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_real_catalogue_data(self, analysis_type: str, requested_quantity: int) -> Dict[str, str]:
        """
        Récupère les vraies données du catalogue selon le type d'analyse
        
        Args:
            analysis_type: Type d'analyse demandé
            requested_quantity: Quantité demandée
        
        Returns:
            Dict contenant le résumé et les données détaillées
        """
        if not self.data_access:
            return {
                "data_summary": "❌ Accès aux données non disponible. Vérifiez la configuration de la base de données.",
                "detailed_data": "Impossible de récupérer les données réelles."
            }
        
        try:
            if analysis_type == "top_articles":
                data = self.data_access.get_top_articles(requested_quantity)
                if data["success"]:
                    articles = data["articles"]
                    summary = f"✅ {len(articles)} articles trouvés (limite: {requested_quantity})"
                    
                    detailed = "ARTICLES LES PLUS VENDUS :\n"
                    for i, article in enumerate(articles, 1):
                        detailed += f"{i}. {article['nom']}\n"
                        detailed += f"   - Quantité vendue: {article['quantite_totale']}\n"
                        detailed += f"   - CA généré: {article['ca_total']:,.0f} FCFA\n"
                        detailed += f"   - Nombre de commandes: {article['nb_commandes']}\n\n"
                    
                    return {"data_summary": summary, "detailed_data": detailed}
                else:
                    return {
                        "data_summary": f"❌ Erreur lors de la récupération des articles: {data['error']}",
                        "detailed_data": "Données non disponibles."
                    }
            
            elif analysis_type == "articles_prices":
                data = self.get_articles_prices(requested_quantity)
                if data["success"]:
                    articles = data["articles"]
                    summary = f"✅ {len(articles)} articles avec prix trouvés"
                    
                    detailed = "LISTE DES ARTICLES AVEC PRIX :\n"
                    for i, article in enumerate(articles, 1):
                        detailed += f"{i}. {article['nom']}\n"
                        detailed += f"   - Prix: {article['prix']:,.0f} FCFA\n"
                        detailed += f"   - Type: {article['type']}\n"
                        if article['description']:
                            detailed += f"   - Description: {article['description'][:100]}...\n"
                        detailed += "\n"
                    
                    return {"data_summary": summary, "detailed_data": detailed}
                else:
                    return {
                        "data_summary": f"❌ Erreur lors de la récupération des prix: {data['error']}",
                        "detailed_data": "Données non disponibles."
                    }
            
            elif analysis_type == "prestations_category":
                data = self.data_access.get_prestations_category()
                if data["success"]:
                    prestations = data["prestations"]
                    total_ca = data["total_ca"]
                    summary = f"✅ {len(prestations)} catégories de prestations trouvées (CA total: {total_ca:,.0f} FCFA)"
                    
                    detailed = "PRESTATIONS PAR CATÉGORIE :\n"
                    for prestation in prestations:
                        detailed += f"- {prestation['type_article']}\n"
                        detailed += f"  - Quantité: {prestation['quantite_totale']}\n"
                        detailed += f"  - CA: {prestation['ca_total']:,.0f} FCFA ({prestation['pourcentage']}%)\n\n"
                    
                    return {"data_summary": summary, "detailed_data": detailed}
                else:
                    return {
                        "data_summary": f"❌ Erreur lors de la récupération des prestations: {data['error']}",
                        "detailed_data": "Données non disponibles."
                    }
            
            elif analysis_type == "prestation_performance":
                data = self.data_access.get_prestation_performance()
                if data["success"]:
                    performances = data["performances"]
                    summary = f"✅ {len(performances)} prestations analysées"
                    
                    detailed = "PERFORMANCE DES PRESTATIONS :\n"
                    for perf in performances:
                        detailed += f"- {perf['prestation']}\n"
                        detailed += f"  - CA: {perf['ca_total']:,.0f} FCFA ({perf['pourcentage']}%)\n"
                        detailed += f"  - Commandes: {perf['nb_commandes']}\n"
                        detailed += f"  - Clients: {perf['nb_clients']}\n\n"
                    
                    return {"data_summary": summary, "detailed_data": detailed}
                else:
                    return {
                        "data_summary": f"❌ Erreur lors de la récupération des performances: {data['error']}",
                        "detailed_data": "Données non disponibles."
                    }
            
            else:
                return {
                    "data_summary": f"Type d'analyse '{analysis_type}' non supporté pour l'instant.",
                    "detailed_data": "Utilisez les types: top_articles, articles_prices, prestations_category, prestation_performance"
                }
                
        except Exception as e:
            return {
                "data_summary": f"❌ Erreur lors de l'accès aux données: {str(e)}",
                "detailed_data": "Vérifiez la connexion à la base de données."
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Récupère les informations sur le modèle utilisé"""
        return {
            'model_name': 'gemini-2.0-flash',
            'api_provider': 'Google Gemini',
            'personality': 'Bizzio Data Analyst',
            'capabilities': [
                'Chat interactif avec personnalité Bizzio',
                'Salutations personnalisées selon l\'heure',
                'Réponses naturelles et humaines',
                'Gestion intelligente des erreurs',
                'Détection du niveau technique',
                'Comportement adaptatif et empathique',
                'Analyses Produits et Catalogue spécialisées'
            ],
            'pricing': 'Gratuit (avec quotas)',
            'catalogue_analysis': {
                'available_routes': [
                    '/admin/api/reporting/top-articles',
                    '/admin/api/catalogue/top-prestations',
                    '/admin/api/reporting/prestation-performance',
                    '/admin/api/catalogue/monthly-evolution'
                ],
                'analysis_types': [
                    'top_articles',
                    'prestations_category', 
                    'prestation_performance',
                    'monthly_evolution',
                    'catalogue_overview'
                ]
            }
        }


# Interface simple pour tester la première fonctionnalité
def main():
    """
    Interface simple pour tester Bizzio
    """
    try:
        # Initialisation de Bizzio
        bizzio = BizzioGemini()
        
        
        while True:
            # Interface utilisateur simple
            user_input = input("\nUtilisateur: ")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Au revoir !")
                break
            
            # Commandes spéciales pour tester les erreurs
            if user_input.lower().startswith('/test_error'):
                error_type = user_input.split(' ')[1] if len(user_input.split(' ')) > 1 else 'test'
                print(f"\nTest d'erreur : {error_type}")
                result = bizzio.simulate_error(error_type)
                print(f"\nBizzio: {result['response']}")
                continue
            
            # Commandes spéciales pour tester le comportement intelligent
            if user_input.lower().startswith('/test_malicious'):
                test_message = user_input.split(' ', 1)[1] if len(user_input.split(' ')) > 1 else "idiot"
                print(f"\nTest message malveillant : {test_message}")
                result = bizzio.chat_with_bizzio(test_message)
                print(f"\nBizzio: {result['response']}")
                continue
            
            if user_input.lower().startswith('/test_technical'):
                test_message = user_input.split(' ', 1)[1] if len(user_input.split(' ')) > 1 else "python machine learning"
                print(f"\nTest niveau technique : {test_message}")
                level = bizzio.detect_technical_level(test_message)
                print(f"Niveau détecté : {level}")
                result = bizzio.chat_with_bizzio(test_message)
                print(f"\nBizzio: {result['response']}")
                continue
            
            # Commandes spéciales pour tester l'analyse catalogue
            if user_input.lower().startswith('/test_catalogue'):
                test_message = user_input.split(' ', 1)[1] if len(user_input.split(' ')) > 1 else "Quels sont nos produits les plus vendus ?"
                print(f"\nTest analyse catalogue : {test_message}")
                analysis_type = bizzio.detect_catalogue_analysis_type(test_message)
                requested_quantity = bizzio.detect_requested_quantity(test_message)
                print(f"Type d'analyse détecté : {analysis_type}")
                print(f"Quantité demandée : {requested_quantity}")
                result = bizzio.analyse_catalogue_products(test_message)
                print(f"\nBizzio: {result['response']}")
                continue
            
            # Chat avec Bizzio
            result = bizzio.chat_with_bizzio(user_input)
            
            if result['success']:
                print(f"\nBizzio: {result['response']}")
            else:
                print(f"\nErreur: {result['error']}")
        
    except Exception as e:
        print(f"Erreur lors de l'initialisation : {str(e)}")


if __name__ == "__main__":
    # Exécution de l'interface
    main()