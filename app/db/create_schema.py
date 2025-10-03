import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL manquant dans le fichier .env")

# Chemin vers schema.sql
BASE_DIR = Path(__file__).resolve().parents[2]  # Racine projet
SCHEMA_FILE = BASE_DIR / "app" / "db" / "schema.sql"

def create_database_schema():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()

        print(f"✅ Connexion réussie à la base : {DATABASE_URL}")
        print(f"📄 Chargement du fichier : {SCHEMA_FILE}")

        if not SCHEMA_FILE.exists():
            raise FileNotFoundError(f"❌ Fichier schema.sql introuvable : {SCHEMA_FILE}")

        # Lecture et découpe des commandes SQL
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        # Découpage plus intelligent des commandes SQL
        # Séparer par ';' mais ignorer ceux dans les commentaires
        commands = []
        current_command = ""
        
        for line in schema_sql.split('\n'):
            line = line.strip()
            
            # Ignorer les commentaires
            if line.startswith('--') or not line:
                continue
                
            current_command += line + " "
            
            # Si la ligne se termine par ';', c'est la fin d'une commande
            if line.endswith(';'):
                commands.append(current_command.strip()[:-1])  # Enlever le ';' final
                current_command = ""
        
        # Ajouter la dernière commande si elle n'est pas vide
        if current_command.strip():
            commands.append(current_command.strip())

        print(f"📌 Nombre de commandes SQL à exécuter : {len(commands)}")

        # Exécuter les commandes une par une
        for i, cmd in enumerate(commands, 1):
            if not cmd.strip():
                continue
                
            try:
                cur.execute(cmd)
                # Affichage simplifié : seulement les erreurs et étapes importantes
                if i % 10 == 0 or "CREATE TABLE" in cmd.upper():
                    print(f"✅ Étape {i}/{len(commands)} terminée")
                
            except Exception as e:
                print(f"⚠️ Erreur commande {i}: {cmd[:60]}...")
                print(f"   └─ {e}")
                
                # Continuer même en cas d'erreur pour certaines commandes
                if "already exists" in str(e).lower() or "does not exist" in str(e).lower():
                    continue
                else:
                    print(f"   └─ Erreur critique, arrêt du script")
                    raise e

        print("✅ Schéma appliqué avec succès")

        # Vérification finale - compter les tables créées
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        
        print(f"📊 Tables présentes dans la base ({len(tables)}):")
        for table in tables:
            print(f"   • {table[0]}")

        cur.close()
        conn.close()
        print("✅ Connexion fermée")

    except FileNotFoundError as e:
        print(f"❌ Fichier non trouvé: {e}")
    except psycopg2.Error as e:
        print(f"❌ Erreur PostgreSQL: {e}")
    except Exception as e:
        print(f"❌ Erreur lors de la création du schéma: {e}")

def verify_schema():
    """Vérifier que le schéma a été correctement appliqué"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("\n🔍 Vérification du schéma...")
        
        # Vérifier les nouvelles tables d'historique
        expected_tables = [
            'commandes_historique',
            'commandes_articles_historique',
            'clients',
            'factures',
            'articles'
        ]
        
        for table in expected_tables:
            cur.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = '{table}' AND table_schema = 'public'
            """)
            exists = cur.fetchone()[0]
            
            if exists:
                print(f"✅ Table '{table}' créée")
                
                # Compter les enregistrements
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    print(f"   └─ {count} enregistrements")
                except:
                    print(f"   └─ Table vide ou inaccessible")
            else:
                print(f"❌ Table '{table}' manquante")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage de la création du schéma de base de données...")
    print("=" * 60)
    
    create_database_schema()
    
    print("\n" + "=" * 60)
    verify_schema()
    
    print("\n🎯 Script terminé !")