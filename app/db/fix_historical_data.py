import psycopg2
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import datetime
import re

# Charger .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def clean_phone_simple(phone):
    """Nettoyer un numéro de téléphone international"""
    if not phone or pd.isna(phone):
        return None
    
    # Convertir en string et nettoyer
    phone_str = str(phone).strip()
    cleaned = re.sub(r'[^\d]', '', phone_str)
    
    # Supprimer 00 du début (préfixe international)
    if cleaned.startswith('00'):
        cleaned = cleaned[2:]
    
    # IMPORTANT: Ne pas ajouter de préfixe automatiquement
    # Les numéros internationaux gardent leur indicatif d'origine
    # Ex: +33123456789 (France), +1234567890 (USA), +237123456789 (Cameroun)
    
    return cleaned if len(cleaned) >= 8 else None

def fix_clients_data():
    """Corriger les données clients pour éviter les doublons"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("🔧 Correction des données clients...")
        
        # 1. Récupérer tous les clients
        cur.execute("SELECT client_id, nom, telephone, telephone_secondaire FROM clients")
        clients = cur.fetchall()
        
        updates = 0
        for client in clients:
            client_id, nom, tel, tel_sec = client
            
            # Nettoyer les téléphones
            clean_tel = clean_phone_simple(tel)
            clean_tel_sec = clean_phone_simple(tel_sec)
            
            if clean_tel != tel or clean_tel_sec != tel_sec:
                cur.execute("""
                    UPDATE clients 
                    SET telephone = %s, telephone_secondaire = %s, updated_at = NOW()
                    WHERE client_id = %s
                """, [clean_tel, clean_tel_sec, client_id])
                updates += 1
        
        print(f"✅ {updates} clients mis à jour")
        
        # 2. Supprimer les doublons basés sur le téléphone
        cur.execute("""
            WITH doublons AS (
                SELECT telephone, 
                       array_agg(client_id ORDER BY created_at) as client_ids,
                       COUNT(*) as nb
                FROM clients 
                WHERE telephone IS NOT NULL AND telephone != ''
                GROUP BY telephone 
                HAVING COUNT(*) > 1
            )
            SELECT telephone, client_ids, nb FROM doublons
        """)
        doublons = cur.fetchall()
        
        suppressed = 0
        for doublon in doublons:
            telephone, client_ids, nb = doublon
            # Garder le premier, supprimer les autres
            clients_to_delete = client_ids[1:]  # Tous sauf le premier
            
            for client_id in clients_to_delete:
                # Vérifier s'il n'a pas de commandes dans les nouvelles tables
                cur.execute("SELECT COUNT(*) FROM commandes_historique WHERE client_id = %s", [client_id])
                nb_commandes = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM factures WHERE client_id = %s", [client_id])
                nb_factures = cur.fetchone()[0]
                
                if nb_factures == 0 and nb_commandes == 0:
                    cur.execute("DELETE FROM clients WHERE client_id = %s", [client_id])
                    suppressed += 1
                    print(f"   Supprimé doublon: {client_id} (téléphone: {telephone})")
        
        print(f"✅ {suppressed} doublons supprimés")
        
        # 3. Mettre à jour les montants depuis les factures ET l'historique
        cur.execute("""
            UPDATE clients 
            SET montant_total_paye = COALESCE((
                SELECT SUM(montant_total) 
                FROM factures 
                WHERE factures.client_id = clients.client_id
            ), 0) + COALESCE((
                SELECT SUM(montant_total) 
                FROM commandes_historique 
                WHERE commandes_historique.client_id = clients.client_id
            ), 0),
            nb_commandes = COALESCE((
                SELECT COUNT(*) 
                FROM factures 
                WHERE factures.client_id = clients.client_id
            ), 0) + COALESCE((
                SELECT COUNT(*) 
                FROM commandes_historique 
                WHERE commandes_historique.client_id = clients.client_id
            ), 0)
        """)
        
        print("✅ Montants et nombres de commandes recalculés")
        
        # 4. Ajouter le pays Cameroun pour les clients sans pays
        cur.execute("""
            UPDATE clients 
            SET pays = 'Cameroun' 
            WHERE pays IS NULL 
            AND ville IN ('Yaoundé', 'Douala', 'Nanga', 'Tonga', 'Bafoussam', 'Bamenda')
        """)
        
        print("✅ Pays ajouté pour les clients camerounais")
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Correction terminée avec succès")
        
    except Exception as e:
        print(f"❌ Erreur lors de la correction: {e}")
        if 'conn' in locals():
            conn.rollback()

def verify_historique():
    """Vérifier spécifiquement l'historique détaillé"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("\n🔍 Vérification de l'historique détaillé:")
        print("=" * 50)
        
        # Vérifier les commandes avec articles
        cur.execute("""
            SELECT 
                ch.code_commande,
                ch.date_commande,
                ch.montant_total,
                ch.statut,
                COUNT(cah.id) as nb_articles,
                STRING_AGG(cah.article_designation, ', ') as articles
            FROM commandes_historique ch
            LEFT JOIN commandes_articles_historique cah ON cah.historique_id = ch.historique_id
            GROUP BY ch.historique_id, ch.code_commande, ch.date_commande, ch.montant_total, ch.statut
            ORDER BY ch.date_commande DESC
            LIMIT 5
        """)
        
        exemples = cur.fetchall()
        print("📋 Exemples d'historique avec détails :")
        for ex in exemples:
            articles_text = ex[5][:100] + "..." if ex[5] and len(ex[5]) > 100 else ex[5] or "Aucun article"
            print(f"   • {ex[0]} - {ex[1]} - {ex[2]:,} FCFA - {ex[3]} - {ex[4]} articles")
            print(f"     └─ Articles: {articles_text}")
        
        # Statistiques globales
        cur.execute("SELECT COUNT(*) FROM commandes_historique")
        nb_commandes = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM commandes_articles_historique")
        nb_articles = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) FROM commandes_historique ch
            JOIN commandes_articles_historique cah ON cah.historique_id = ch.historique_id
        """)
        nb_avec_articles = cur.fetchone()[0]
        
        print(f"\n📊 Statistiques historique :")
        print(f"   • Total commandes: {nb_commandes}")
        print(f"   • Total articles détaillés: {nb_articles}")
        print(f"   • Commandes avec articles: {nb_avec_articles}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification historique: {e}")

def verify_data():
    """Vérifier l'état des données après correction"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("\n📊 État des données après correction:")
        
        # Compter les clients
        cur.execute("SELECT COUNT(*) FROM clients")
        nb_clients = cur.fetchone()[0]
        print(f"   Total clients: {nb_clients}")
        
        # Clients avec téléphone
        cur.execute("SELECT COUNT(*) FROM clients WHERE telephone IS NOT NULL AND telephone != ''")
        nb_tel = cur.fetchone()[0]
        print(f"   Clients avec téléphone: {nb_tel}")
        
        # Factures et historique
        cur.execute("SELECT COUNT(*) FROM factures")
        nb_factures = cur.fetchone()[0]
        print(f"   Total factures: {nb_factures}")
        
        cur.execute("SELECT COUNT(*) FROM commandes_historique")
        nb_historique = cur.fetchone()[0]
        print(f"   Total historique: {nb_historique}")
        
        # Clients avec historique (factures OU commandes_historique)
        cur.execute("""
            SELECT COUNT(DISTINCT client_id) FROM (
                SELECT client_id FROM factures WHERE client_id IS NOT NULL
                UNION
                SELECT client_id FROM commandes_historique WHERE client_id IS NOT NULL
            ) AS combined
        """)
        nb_clients_hist = cur.fetchone()[0]
        print(f"   Clients avec historique: {nb_clients_hist}")
        
        # Vérifier quelques exemples d'historique
        cur.execute("""
            SELECT 
                c.nom, 
                c.telephone, 
                COALESCE(f.nb_factures, 0) + COALESCE(h.nb_historique, 0) as total_commandes,
                c.montant_total_paye
            FROM clients c
            LEFT JOIN (
                SELECT client_id, COUNT(*) as nb_factures
                FROM factures 
                GROUP BY client_id
            ) f ON f.client_id = c.client_id
            LEFT JOIN (
                SELECT client_id, COUNT(*) as nb_historique
                FROM commandes_historique 
                GROUP BY client_id
            ) h ON h.client_id = c.client_id
            WHERE COALESCE(f.nb_factures, 0) + COALESCE(h.nb_historique, 0) > 0
            ORDER BY total_commandes DESC
            LIMIT 5
        """)
        exemples = cur.fetchall()
        
        print("\n📋 Exemples de clients avec historique:")
        for ex in exemples:
            print(f"   {ex[0]} ({ex[1]}) - {ex[2]} commandes - {ex[3]:,} FCFA")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage du nettoyage des données historiques...")
    print("=" * 60)
    
    fix_clients_data()
    verify_data()
    verify_historique()
    
    print("\n🎯 Nettoyage terminé ! Prêt pour l'étape 2.")