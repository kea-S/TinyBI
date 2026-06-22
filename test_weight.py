import json
import networkx as nx
from collections import defaultdict
from src.utils.pydantic_models import ColumnVectorIndexEntry
from src.utils.value_resolution.db_schema_graph import build_schema_graph

with open("data/app_data/columns.json") as f:
    columns = json.load(f)

entries = [ColumnVectorIndexEntry(**c) for c in columns]

G = build_schema_graph(entries)

path = nx.shortest_path(G, source="trans", target="client", weight="weight")
print("Weighted Path:", path)

unweighted_path = nx.shortest_path(G, source="trans", target="client")
print("Unweighted Path:", unweighted_path)

# Print weights
print("Edge weights:")
for u, v in zip(path[:-1], path[1:]):
    print(f"{u} - {v}: {G[u][v].get('weight')}")
    
for u, v in zip(unweighted_path[:-1], unweighted_path[1:]):
    print(f"{u} - {v}: {G[u][v].get('weight')}")
