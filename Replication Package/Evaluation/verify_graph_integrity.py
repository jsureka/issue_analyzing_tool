import sys
import os
import logging
from neo4j import GraphDatabase

# Setup paths to import Config
# Script is in Replication Package/Evaluation/
# Config is in INSIGHT Tool/Feature_Components/KnowledgeBase/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
insight_tool_path = os.path.join(project_root, "INSIGHT Tool")
print(f"DEBUG: Adding path: {insight_tool_path}")
if os.path.exists(insight_tool_path):
    print("DEBUG: Path exists!")
    print(f"DEBUG: Contents: {os.listdir(insight_tool_path)}")
else:
    print("DEBUG: Path DOES NOT EXIST!")

sys.path.append(insight_tool_path)

# Debug: Try manual import traverse
try:
    import Feature_Components
    print(f"DEBUG: Imported Feature_Components: {Feature_Components}")
except ImportError as e:
    print(f"DEBUG: Failed to import Feature_Components: {e}")

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_graph(repo_name):
    uri = Config.NEO4J_URI
    user = Config.NEO4J_USER
    password = Config.NEO4J_PASSWORD
    
    logger.info(f"Connecting to Neo4j at {uri}...")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            # 1. Total Nodes (GLOBAL)
            result = session.run("MATCH (n) RETURN count(n) as total")
            total = result.single()['total']
            logger.info(f"Total nodes in DB (Global): {total}")

            # Sample some nodes to see their repo property
            result = session.run("MATCH (n) RETURN labels(n) as labels, n.repo as repo, n.repo_name as repo_name LIMIT 5")
            for record in result:
                logger.info(f"Sample Node: {record['labels']} - repo='{record['repo']}' - repo_name='{record['repo_name']}'")

             # 1. Total Nodes for target repo
            result = session.run(
                "MATCH (n) WHERE n.repo = $repo_name RETURN count(n) as total", 
                repo_name=repo_name
            )
            total = result.single()['total']
            logger.info(f"Total nodes for {repo_name}: {total}")
            
            if total == 0:
                logger.error("No nodes found! Graph indexing might have failed.")
                return False

            # 2. Nodes by Type
            result = session.run(
                "MATCH (n) WHERE n.repo = $repo_name RETURN labels(n) as labels, count(n) as count",
                repo_name=repo_name
            )
            logger.info("Node breakdown:")
            for record in result:
                logger.info(f"  {record['labels']}: {record['count']}")

            # 3. Relationships (CALLS)
            result = session.run(
                "MATCH (a)-[r:CALLS]->(b) WHERE a.repo = $repo_name RETURN count(r) as calls",
                repo_name=repo_name
            )
            calls = result.single()['calls']
            logger.info(f"Total 'CALLS' relationships: {calls}")
            
            if calls == 0:
                logger.warning("No CALLS relationships found. Graph is just a bag of nodes (AST only).")
            else:
                logger.info("Graph connectivity confirmed.")
                
            # 4. Sample Neighbor
            result = session.run(
                """
                MATCH (a:Function)-[:CALLS]->(b) 
                WHERE a.repo = $repo_name 
                RETURN a.name, b.name LIMIT 1
                """,
                repo_name=repo_name
            )
            sample = result.single()
            if sample:
                logger.info(f"Sample Call: {sample['a.name']} -> {sample['b.name']}")
                
            return True
            
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False
    finally:
        driver.close()

if __name__ == "__main__":
    # check for arguments
    repo = "spritelink/nipap" # Default to the one we know is indexed
    if len(sys.argv) > 1:
        repo = sys.argv[1]
    
    verify_graph(repo)
