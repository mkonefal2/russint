#!/usr/bin/env python3
"""Sprawdź dane w Neo4j"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

with driver.session() as session:
    # Sprawdź relacje
    print("🔗 RELACJE W BAZIE:")
    result = session.run('MATCH ()-[r]->() RETURN type(r) as rel_type, count(*) as count ORDER BY count DESC')
    for record in result:
        print(f"   {record['rel_type']}: {record['count']}")
    
    # Sprawdź węzły
    print("\n🔵 WĘZŁY W BAZIE:")
    result = session.run('MATCH (n) RETURN labels(n) as labels, count(*) as count ORDER BY count DESC')
    for record in result:
        print(f"   {record['labels']}: {record['count']}")
    
    # Przykładowe relacje
    print("\n📊 PRZYKŁADOWE RELACJE:")
    result = session.run('MATCH (a)-[r]->(b) RETURN labels(a)[0] as from_type, a.name as from_name, type(r) as rel_type, labels(b)[0] as to_type, b.name as to_name LIMIT 10')
    for record in result:
        print(f"   ({record['from_type']}: {record['from_name']}) -[{record['rel_type']}]-> ({record['to_type']}: {record['to_name']})")

driver.close()
