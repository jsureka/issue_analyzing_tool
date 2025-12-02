import sys
import os
sys.path.append(os.path.join(os.getcwd(), "INSIGHT Tool"))
from Feature_Components.KnowledgeBase.graph_store import GraphStore
import logging

logging.basicConfig(level=logging.INFO)
graph_store = GraphStore()
graph_store.connect()

def check_class_methods(class_name):
    query = """
    MATCH (c:Class {name: $class_name})-[:CONTAINS]->(f:Function)
    RETURN f.name as method
    """
    with graph_store.driver.session() as session:
        result = session.run(query, class_name=class_name)
        methods = [record['method'] for record in result]
        print(f"Methods of {class_name}: {methods}")

if __name__ == "__main__":
    check_class_methods("FTS3ApiTransferStatusReport")
