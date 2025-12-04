"""
RUSSINT - DuckDB Loader
Skrypt do ładowania danych JSON do bazy DuckDB.
"""

import duckdb
import json
from pathlib import Path
from datetime import datetime

# Ścieżki
BASE_DIR = Path(__file__).parent.parent  # scripts -> RUSSINT
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "russint.duckdb"

# Pliki JSON
ENTITIES_FILE = RAW_DIR / "entities.json"
RELATIONSHIPS_FILE = RAW_DIR / "relationships.json"
EVENTS_FILE = RAW_DIR / "events.json"


def init_database(con):
    """Inicjalizuje schemat bazy danych."""
    
    # Tabela podmiotów (entities)
    con.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            entity_type VARCHAR,
            platform VARCHAR,
            url VARCHAR,
            description TEXT,
            category VARCHAR,
            country VARCHAR,
            first_seen DATE,
            last_activity DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela wydarzeń (events)
    con.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            event_type VARCHAR,
            date_start DATE,
            date_end DATE,
            location_name VARCHAR,
            location_address VARCHAR,
            location_country VARCHAR,
            description TEXT,
            source_url VARCHAR,
            source_date DATE,
            collected_at TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela relacji (relationships)
    con.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id VARCHAR PRIMARY KEY,
            source_id VARCHAR,
            source_name VARCHAR,
            target_id VARCHAR,
            target_name VARCHAR,
            relationship_type VARCHAR NOT NULL,
            event_id VARCHAR,
            event_name VARCHAR,
            date DATE,
            confidence DECIMAL(3,2),
            evidence TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES entities(id),
            FOREIGN KEY (target_id) REFERENCES entities(id),
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)
    
    # Tabela event_participants (dla wielu-do-wielu)
    con.execute("""
        CREATE TABLE IF NOT EXISTS event_participants (
            event_id VARCHAR,
            entity_id VARCHAR,
            role VARCHAR,
            PRIMARY KEY (event_id, entity_id, role),
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (entity_id) REFERENCES entities(id)
        )
    """)
    
    print("✅ Schemat bazy danych zainicjalizowany")


def clear_tables(con):
    """Czyści tabele przed załadowaniem nowych danych."""
    con.execute("DELETE FROM event_participants")
    con.execute("DELETE FROM relationships")
    con.execute("DELETE FROM events")
    con.execute("DELETE FROM entities")
    print("🗑️ Wyczyszczono stare dane")


def load_entities(con):
    """Ładuje podmioty z JSON do DuckDB."""
    if not ENTITIES_FILE.exists():
        print("⚠️ Brak pliku entities.json")
        return 0
    
    with open(ENTITIES_FILE, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    
    count = 0
    for e in entities:
        try:
            con.execute("""
                INSERT OR REPLACE INTO entities 
                (id, name, entity_type, platform, url, description, category, country, first_seen, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                e.get('id'),
                e.get('name'),
                e.get('entity_type'),
                e.get('platform'),
                e.get('url'),
                e.get('description'),
                e.get('category'),
                e.get('country'),
                e.get('first_seen'),
                e.get('notes')
            ])
            count += 1
        except Exception as ex:
            print(f"❌ Błąd przy ładowaniu entity {e.get('name')}: {ex}")
    
    print(f"✅ Załadowano {count} podmiotów")
    return count


def load_events(con):
    """Ładuje wydarzenia z JSON do DuckDB."""
    if not EVENTS_FILE.exists():
        print("⚠️ Brak pliku events.json")
        return 0
    
    with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    count = 0
    for e in events:
        try:
            location = e.get('location', {})
            con.execute("""
                INSERT OR REPLACE INTO events 
                (id, name, event_type, date_start, date_end, 
                 location_name, location_address, location_country,
                 description, source_url, source_date, collected_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                e.get('id'),
                e.get('name'),
                e.get('event_type'),
                e.get('date_start'),
                e.get('date_end'),
                location.get('name'),
                location.get('address'),
                location.get('country'),
                e.get('description'),
                e.get('source_url'),
                e.get('source_date'),
                e.get('collected_at'),
                e.get('notes')
            ])
            count += 1
            
            # Dodaj organizatorów
            for org in e.get('organizers', []):
                con.execute("""
                    INSERT OR REPLACE INTO event_participants (event_id, entity_id, role)
                    VALUES (?, ?, ?)
                """, [e.get('id'), org.get('entity_id'), org.get('role', 'organizer')])
            
            # Dodaj prelegentów
            for speaker in e.get('speakers', []):
                con.execute("""
                    INSERT OR REPLACE INTO event_participants (event_id, entity_id, role)
                    VALUES (?, ?, ?)
                """, [e.get('id'), speaker.get('entity_id'), 'speaker'])
                
        except Exception as ex:
            print(f"❌ Błąd przy ładowaniu eventu {e.get('name')}: {ex}")
    
    print(f"✅ Załadowano {count} wydarzeń")
    return count


def load_relationships(con):
    """Ładuje relacje z JSON do DuckDB."""
    if not RELATIONSHIPS_FILE.exists():
        print("⚠️ Brak pliku relationships.json")
        return 0
    
    with open(RELATIONSHIPS_FILE, 'r', encoding='utf-8') as f:
        relationships = json.load(f)
    
    count = 0
    for r in relationships:
        try:
            con.execute("""
                INSERT OR REPLACE INTO relationships 
                (id, source_id, source_name, target_id, target_name, 
                 relationship_type, event_id, event_name, date, confidence, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                r.get('id'),
                r.get('source_id'),
                r.get('source_name'),
                r.get('target_id'),
                r.get('target_name'),
                r.get('relationship_type'),
                r.get('event_id'),
                r.get('event_name'),
                r.get('date'),
                r.get('confidence'),
                r.get('evidence')
            ])
            count += 1
        except Exception as ex:
            print(f"❌ Błąd przy ładowaniu relacji {r.get('id')}: {ex}")
    
    print(f"✅ Załadowano {count} relacji")
    return count


def show_stats(con):
    """Wyświetla statystyki bazy."""
    print("\n" + "="*50)
    print("📊 STATYSTYKI BAZY DANYCH")
    print("="*50)
    
    # Podmioty
    result = con.execute("SELECT COUNT(*) FROM entities").fetchone()
    print(f"👥 Podmioty (entities): {result[0]}")
    
    # Wydarzenia
    result = con.execute("SELECT COUNT(*) FROM events").fetchone()
    print(f"📅 Wydarzenia (events): {result[0]}")
    
    # Relacje
    result = con.execute("SELECT COUNT(*) FROM relationships").fetchone()
    print(f"🔗 Relacje (relationships): {result[0]}")
    
    # Typy relacji
    print("\n📊 Typy relacji:")
    result = con.execute("""
        SELECT relationship_type, COUNT(*) as cnt 
        FROM relationships 
        GROUP BY relationship_type
        ORDER BY cnt DESC
    """).fetchall()
    for row in result:
        print(f"   - {row[0]}: {row[1]}")
    
    # Sieć powiązań
    print("\n🕸️ Sieć powiązań (kto → kogo):")
    result = con.execute("""
        SELECT source_name, relationship_type, target_name
        FROM relationships
        ORDER BY source_name
        LIMIT 20
    """).fetchall()
    for row in result:
        print(f"   {row[0]} --[{row[1]}]--> {row[2]}")


def export_for_visualization(con):
    """Eksportuje dane do formatów wizualizacji (CSV dla Gephi)."""
    export_dir = DATA_DIR / "export"
    export_dir.mkdir(exist_ok=True)
    
    # Nodes
    con.execute(f"""
        COPY (
            SELECT id as Id, name as Label, entity_type as Type, category as Category
            FROM entities
        ) TO '{export_dir}/nodes.csv' (HEADER, DELIMITER ',')
    """)
    print(f"✅ Eksportowano węzły do {export_dir}/nodes.csv")
    
    # Edges
    con.execute(f"""
        COPY (
            SELECT 
                source_id as Source, 
                target_id as Target, 
                relationship_type as Type,
                event_name as Label,
                confidence as Weight
            FROM relationships
        ) TO '{export_dir}/edges.csv' (HEADER, DELIMITER ',')
    """)
    print(f"✅ Eksportowano krawędzie do {export_dir}/edges.csv")


def main():
    print("="*50)
    print("🦆 RUSSINT - DuckDB Loader")
    print("="*50)
    print(f"📁 Baza danych: {DB_PATH}")
    print()
    
    # Połącz z bazą (utworzy jeśli nie istnieje)
    con = duckdb.connect(str(DB_PATH))
    
    try:
        # Inicjalizuj schemat
        init_database(con)
        
        # Wyczyść stare dane
        clear_tables(con)
        
        # Ładuj dane
        print("\n📥 Ładowanie danych...")
        load_entities(con)
        load_events(con)
        load_relationships(con)
        
        # Pokaż statystyki
        show_stats(con)
        
        # Eksport do wizualizacji
        print("\n📤 Eksport do wizualizacji...")
        export_for_visualization(con)
        
        print("\n✅ Zakończono!")
        
    finally:
        con.close()


if __name__ == "__main__":
    main()
