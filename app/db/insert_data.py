import psycopg2
import psycopg2.extras
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import datetime
import uuid
import re

# Charger .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL manquant dans .env")

# Chemins robustes
BASE_DIR = Path(__file__).resolve().parents[2]
FINAL_DIR = BASE_DIR / "data" / "processed" / "final"

# Fichiers finaux
CLIENTS_FILE = FINAL_DIR / "clients_final.csv"
CLIENTS_SANS_NUM_FILE = FINAL_DIR / "nouveaux_clients_sans_numero.csv"
LIVRES_FILE = FINAL_DIR / "manuel_final.csv"
FOURNITURES_FILE = FINAL_DIR / "fournitures_final.csv"
PRIX_VILLE_FILE = FINAL_DIR / "prix_fournitures_ville_final.csv"
FACTURES_FILE = FINAL_DIR / "factures_final.csv"
DETAILS_FACTURES_FILE = FINAL_DIR / "details_factures_final.csv"
VENTES_FILE = FINAL_DIR / "ventes_final.csv"

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def parse_commande_details(commande_text):
    """Parser la colonne commande pour extraire les articles"""
    if not commande_text or pd.isna(commande_text):
        return []
    
    commande_str = str(commande_text).strip()
    articles = []
    
    # Pattern 1: "2 capitaines d'industries" → Quantité + Article
    qty_pattern = r'^(\d+)\s+(.+)$'
    match = re.match(qty_pattern, commande_str)
    if match:
        qty = int(match.group(1))
        designation = match.group(2).strip()
        articles.append({
            'designation': designation,
            'quantite': qty,
            'prix_unitaire': 0
        })
        return articles
    
    # Pattern 2: "SIL, CE1, CM1" → Plusieurs articles séparés par virgules
    if ',' in commande_str:
        parts = [part.strip() for part in commande_str.split(',')]
        for part in parts:
            if part:
                articles.append({
                    'designation': part,
                    'quantite': 1,
                    'prix_unitaire': 0
                })
        return articles
    
    # Pattern 3: Article simple
    articles.append({
        'designation': commande_str,
        'quantite': 1,
        'prix_unitaire': 0
    })
    
    return articles

def insert_clients_batch(cur, file_path):
    """Insertion optimisée des clients par batch"""
    if not file_path.exists():
        print(f"⚠️ Fichier manquant : {file_path}")
        return
        
    print(f"📁 Traitement de {file_path.name}...")
    df = pd.read_csv(file_path)
    
    # Préparer les données
    data_to_insert = []
    for _, row in df.iterrows():
        data_to_insert.append((
            row.get("code_client"),
            row.get("nom"),
            row.get("telephone"),
            row.get("telephone_secondaire"),
            row.get("adresse"),
            row.get("ville"),
            None,  # pays
            int(row.get("nb_commandes", 0)),
            int(row.get("montant_total_paye", 0)),
            datetime.now(),
            datetime.now()
        ))
    
    # Insertion par batch
    psycopg2.extras.execute_batch(
        cur,
        """INSERT INTO clients (client_id, nom, telephone, telephone_secondaire, adresse, ville, pays, nb_commandes, montant_total_paye, created_at, updated_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (client_id) DO NOTHING;""",
        data_to_insert,
        page_size=1000
    )
    
    print(f"✅ {len(df)} clients traités depuis {file_path.name}")

def insert_articles_batch(cur, file_path, type_article):
    """Insertion optimisée des articles par batch"""
    if not file_path.exists():
        print(f"Fichier manquant : {file_path}")
        return
        
    print(f"Traitement articles ({type_article}) depuis {file_path.name}...")
    df = pd.read_csv(file_path)
    
    # Préparer les données avec toutes les colonnes
    data_to_insert = []
    for _, row in df.iterrows():
        # Pour les livres, gérer la colonne ville du CSV
        ville_reference = None
        if type_article == 'livre' and 'ville' in row and pd.notna(row['ville']):
            ville_reference = 'yaounde' if row['ville'] == 1.0 else 'douala'
        
        data_to_insert.append((
            row.get("code"),
            row.get("designation"),
            int(row.get("prix", 0)),
            type_article,
            row.get("nature", None),
            row.get("classe", None),
            ville_reference,
            None,  # type_mission
            None,  # duree
            None,  # capacite_max
            None   # description
        ))
    
    # Insertion avec toutes les colonnes
    psycopg2.extras.execute_batch(
        cur,
        """INSERT INTO articles (code, designation, prix, type_article, nature, classe, ville_reference, type_mission, duree, capacite_max, description)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (code) DO NOTHING;""",
        data_to_insert,
        page_size=1000
    )
    
    print(f"{len(df)} articles ({type_article}) traités")

def insert_factures_batch(cur, file_path):
    """Insertion optimisée des factures par batch"""
    if not file_path.exists():
        print(f"⚠️ Fichier manquant : {file_path}")
        return
        
    print(f"📁 Traitement factures depuis {file_path.name}...")
    df = pd.read_csv(file_path)
    
    # Préparer les données
    data_to_insert = []
    for _, row in df.iterrows():
        data_to_insert.append((
            row.get("facture_id"),
            row.get("client_id"),
            row.get("date_facture"),
            row.get("mode_paiement", "Inconnu"),
            int(row.get("montant_total", 0)),
            row.get("ville"),
            'termine'
        ))
    
    # Insertion par batch
    psycopg2.extras.execute_batch(
        cur,
        """INSERT INTO factures (code_facture, client_id, date_facture, mode_paiement, montant_total, ville, statut)
           VALUES (%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (code_facture) DO NOTHING;""",
        data_to_insert,
        page_size=1000
    )
    
    print(f"✅ {len(df)} factures traitées")

def insert_ventes_batch(cur, file_path):
    """Insertion optimisée des ventes par batch"""
    if not file_path.exists():
        print(f"⚠️ Fichier manquant : {file_path}")
        return
        
    print(f"📁 Traitement ventes depuis {file_path.name}...")
    df = pd.read_csv(file_path)
    
    # Préparer les données
    data_to_insert = []
    for _, row in df.iterrows():
        annee = row.get("annee")
        date_vente = f"{annee}-01-01" if annee else None
        montant_total = int(row.get("montant")) if pd.notna(row.get("montant")) else 0
        
        data_to_insert.append((
            row.get("vente_id"),
            row.get("client_id"),
            date_vente,
            montant_total,
            row.get("ville") or "Non renseignée",
            'termine'
        ))
    
    # Insertion par batch
    psycopg2.extras.execute_batch(
        cur,
        """INSERT INTO factures (code_facture, client_id, date_facture, montant_total, ville, statut)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (code_facture) DO NOTHING;""",
        data_to_insert,
        page_size=1000
    )
    
    print(f"✅ {len(df)} ventes traitées")

def insert_prix_ville_batch(cur, file_path):
    """Insertion optimisée des prix par ville"""
    if not file_path.exists():
        print(f"⚠️ Fichier manquant : {file_path}")
        return
        
    print(f"📁 Traitement prix fournitures par ville...")
    df = pd.read_csv(file_path)
    
    # D'abord récupérer tous les articles existants
    cur.execute("SELECT code, article_id FROM articles")
    articles_map = dict(cur.fetchall())
    
    # Préparer les données
    data_to_insert = []
    for _, row in df.iterrows():
        code = row["code"]
        if code in articles_map:
            data_to_insert.append((
                articles_map[code],
                row.get("ville"),
                int(row.get("prix", 0))
            ))
    
    # Insertion par batch
    if data_to_insert:
        psycopg2.extras.execute_batch(
            cur,
            """INSERT INTO prix_fournitures_ville (article_id, ville, prix)
               VALUES (%s,%s,%s);""",
            data_to_insert,
            page_size=1000
        )
    
    print(f"✅ {len(data_to_insert)} prix par ville traités")

def insert_details_factures_batch(cur, file_path):
    """Insertion optimisée des détails factures"""
    if not file_path.exists():
        print(f"⚠️ Fichier manquant : {file_path}")
        return

    print(f"📁 Traitement détails factures...")
    df = pd.read_csv(file_path)
    
    key_column = "facture_id" if "facture_id" in df.columns else ("vente_id" if "vente_id" in df.columns else None)
    if not key_column:
        raise ValueError("❌ Aucune colonne facture_id ou vente_id trouvée")

    # Récupérer toutes les factures et articles
    cur.execute("SELECT code_facture, facture_id FROM factures")
    factures_map = dict(cur.fetchall())
    
    cur.execute("SELECT code, article_id FROM articles")
    articles_map = dict(cur.fetchall())

    # Préparer les données
    data_to_insert = []
    for _, row in df.iterrows():
        facture_code = row[key_column]
        article_code = row.get("code_article")
        
        if facture_code in factures_map and article_code in articles_map:
            quantite = int(row["quantite"]) if pd.notna(row.get("quantite")) else 1
            prix_unitaire = int(row["prix_unitaire"]) if pd.notna(row.get("prix_unitaire")) else 0
            
            data_to_insert.append((
                factures_map[facture_code],
                articles_map[article_code],
                quantite,
                prix_unitaire
            ))

    # Insertion par batch
    if data_to_insert:
        psycopg2.extras.execute_batch(
            cur,
            """INSERT INTO facture_articles (facture_id, article_id, quantite, prix_unitaire)
               VALUES (%s, %s, %s, %s);""",
            data_to_insert,
            page_size=1000
        )
    
    print(f"✅ {len(data_to_insert)} détails factures traités")

def migrate_to_historique_batch(cur):
    """Migration optimisée vers l'historique"""
    print("🔄 Migration des données vers l'historique détaillé...")
    
    # 1. Migrer les factures vers commandes_historique
    cur.execute("""
        INSERT INTO commandes_historique (client_id, date_commande, code_commande, montant_total, statut, created_at, updated_at)
        SELECT 
            f.client_id,
            COALESCE(f.date_facture, CURRENT_DATE),
            f.code_facture,
            f.montant_total,
            COALESCE(f.statut, 'termine'),
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM factures f
        WHERE f.client_id IS NOT NULL
        ON CONFLICT (code_commande) DO NOTHING;
    """)
    
    migrated_count = cur.rowcount
    print(f"✅ {migrated_count} commandes migrées vers l'historique")
    
    # 2. Parser les détails par batch
    print("🔄 Parsing des détails de commandes...")
    
    # Récupérer toutes les commandes historiques
    cur.execute("SELECT historique_id, code_commande FROM commandes_historique")
    historique_map = dict(cur.fetchall())
    
    csv_files = [FACTURES_FILE, VENTES_FILE]
    articles_to_insert = []
    
    for csv_file in csv_files:
        if not csv_file.exists():
            continue
            
        print(f"📁 Parsing depuis {csv_file.name}...")
        df = pd.read_csv(csv_file)
        
        for _, row in df.iterrows():
            code_facture = row.get('facture_id') or row.get('vente_id')
            commande_details = row.get('commande')
            
            if not code_facture or not commande_details or code_facture not in historique_map:
                continue
            
            historique_id = historique_map[code_facture]
            articles = parse_commande_details(commande_details)
            
            for article in articles:
                articles_to_insert.append((
                    historique_id,
                    article['designation'],
                    'PARSED',
                    article['quantite'],
                    article['prix_unitaire']
                ))
    
    # Insertion par batch
    if articles_to_insert:
        psycopg2.extras.execute_batch(
            cur,
            """INSERT INTO commandes_articles_historique 
               (historique_id, article_designation, article_code, quantite, prix_unitaire)
               VALUES (%s, %s, %s, %s, %s)""",
            articles_to_insert,
            page_size=1000
        )
    
    print(f"✅ {len(articles_to_insert)} articles détaillés parsés et insérés")

def show_progress(current, total, message="Progression"):
    """Afficher la progression"""
    percent = (current / total) * 100
    print(f"📊 {message}: {current}/{total} ({percent:.1f}%)")

def verify_data():
    """Vérifier l'état des données après insertion"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        print("\n📊 Vérification des données insérées:")
        print("=" * 50)
        
        tables_to_check = [
            ('clients', 'Clients'),
            ('articles', 'Articles'),
            ('factures', 'Factures'),
            ('facture_articles', 'Détails factures'),
            ('commandes_historique', 'Historique commandes'),
            ('commandes_articles_historique', 'Articles historique')
        ]
        
        for table, label in tables_to_check:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"✅ {label}: {count:,} enregistrements")
            except Exception as e:
                print(f"❌ {label}: Erreur - {e}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")

def main():
    try:
        conn = get_connection()
        cur = conn.cursor()
        print("✅ Connexion à la base réussie")
        
        # Configuration pour améliorer les performances (paramètres compatibles Render)
        try:
            cur.execute("SET synchronous_commit = OFF;")
            cur.execute("SET work_mem = '256MB';")
            cur.execute("SET maintenance_work_mem = '256MB';")
            print("⚡ Configuration optimisée pour l'insertion")
        except Exception as e:
            print(f"⚠️ Certains paramètres non modifiables: {e}")
            print("⚡ Utilisation de la configuration par défaut")

        # Insertion des données de base avec batch processing
        print("\n🚀 Insertion des données par batch...")
        insert_clients_batch(cur, CLIENTS_FILE)
        insert_clients_batch(cur, CLIENTS_SANS_NUM_FILE) 
        insert_articles_batch(cur, LIVRES_FILE, "livre")
        insert_articles_batch(cur, FOURNITURES_FILE, "fourniture")
        insert_prix_ville_batch(cur, PRIX_VILLE_FILE)
        insert_factures_batch(cur, FACTURES_FILE)
        insert_details_factures_batch(cur, DETAILS_FACTURES_FILE)
        insert_ventes_batch(cur, VENTES_FILE)

        # Migration vers le nouvel historique
        migrate_to_historique_batch(cur)

        # Commit final
        print("💾 Sauvegarde des données...")
        conn.commit()
        print("✅ Toutes les données insérées avec succès")

        cur.close()
        conn.close()
        
        # Vérification finale
        verify_data()
        
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion : {e}")
        if 'conn' in locals():
            conn.rollback()

if __name__ == "__main__":
    print("=" * 60)
    main()
    print("\n🎯 Script terminé !")