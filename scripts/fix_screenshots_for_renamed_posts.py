from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

# Mappings: (old_id_with_fb_prefix, new_id, description)
MAPPINGS = [
    ("fb_BraterstwaLudziWolnych_pfbid0219rwE34d48hfcTuUrccvvxgFizYcByeXwMTjzbrD9dX1ycUz9PvANH2Kw4KAJSN5l", "post-001", "Post: Harmonogram Spotkania Rodzin (25.06.2025)"),
    ("fb_BraterstwaLudziWolnych_pfbid034KmeQ78vzhL5JGdzeQk7ovY52giHAuHjYiyvu9NcT3G2KFPiKsNXnukDm9Yvke2Zl", "post-002", "Post: ABW wtargnęła do naszych domów o 6 rano"),
    ("fb_BraterstwaLudziWolnych_pfbid071cebkweeCzVBJkff82MKmzwvPTpVi9NkdDTiQ76LEhZVxrXuASSki9ViV7t7Xx7l", "post-003", "Post: To jest zamach na polskie rodziny"),
    ("fb_BraterstwaLudziWolnych_pfbid02S7DuXzZkjeeod95uhipsAvELgdLk5rL4Tgstt2qAv85WJhotUZgdjn7csi1HWziyl", "post-004", "Repost: twierdzenia o 'PsyOp' i 'pseudo-elity' (udostępnienie Jakuba Kuśpita)"),
    ("fb_BraterstwaLudziWolnych_pfbid029XSpGTnfbFiUH4SiVRZ1Ahhu9FszHT958rdDE2dwk3xgp3YVfgpe6ev4MYMTQQ5l", "post-006", "Post: Zlot Braterstw Ludzi Wolnych — dzień 4 (wideo)"),
    ("fb_BraterstwaLudziWolnych_pfbid0x8gsmiq27LtWbDkrAgYk8LAX2ucDZ54oDMfKTrh6oNjf47grdZLgj1We5dhp2P36l", "post-fb_BraterstwaLudziWolnych_pfbid0x8gsmiq27LtWbDkrAgYk8LAX2ucDZ54oDMfKTrh6oNjf47grdZLgj1We5dhp2P36l", "Post: NOMINOWANY NA RUSKIEGO SZPIEGA (ABW zarekwiwrowała...)"),
]

def fix_screenshots(uri, user, password, mappings):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            for old_id, new_id, new_name in mappings:
                if not old_id.startswith("fb_"):
                    continue
                
                # Extract handle
                parts = old_id.split('_')
                if len(parts) < 3:
                    continue
                    
                handle = parts[1]
                screenshot_path = f"data/evidence/facebook/{handle}/{old_id}.png"
                
                print(f"Updating {new_id} with screenshot: {screenshot_path}")
                
                session.run(
                    "MATCH (n {id: $new_id}) SET n.screenshot = $screenshot RETURN n",
                    new_id=new_id, screenshot=screenshot_path
                )
                
    finally:
        driver.close()

if __name__ == "__main__":
    fix_screenshots(uri, user, password, MAPPINGS)
