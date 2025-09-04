# src/build_graph.py
import networkx as nx
from pathlib import Path
import uuid, json, pickle
from src.parse_headings import parse_numbered_headings


def build_graph_from_md(md_path: str):
    text = Path(md_path).read_text(encoding="utf-8")
    chunks = parse_numbered_headings(text)
    G = nx.DiGraph()
    standard_id = str(uuid.uuid4())
    G.add_node(
        standard_id,
        title=Path(md_path).stem,
        level=0,
        type="standard",
        source=str(md_path),
        content="",
    )
    for c in chunks:
        node_id = c["id"]
        G.add_node(
            node_id,
            title=c["title"],
            level=c["level"],
            type=("part" if c["level"] == 1 else "clause"),
            content=c["content"],
            source=str(md_path),
        )
        parent_id = c.get("parent_id")
        if parent_id:
            # if parent_id string not in G yet (different UUID), fallback to connect to standard
            if parent_id in G.nodes:
                G.add_edge(parent_id, node_id)
            else:
                G.add_edge(standard_id, node_id)
        else:
            G.add_edge(standard_id, node_id)
    return G


def merge_graphs(graphs):
    G = nx.DiGraph()
    for g in graphs:
        G = nx.compose(G, g)
    return G


if __name__ == "__main__":
    md_dir = Path("../data/md")
    graphs = []
    for md in md_dir.glob("*.md"):
        g = build_graph_from_md(str(md))
        graphs.append(g)
    G = merge_graphs(graphs)
    out_dir = Path("../data/graphs")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "standards_graph.gpickle", "wb") as f:
        pickle.dump(G, f)
    nodes = {n: dict(G.nodes[n]) for n in G.nodes()}
    (out_dir / "standards_graph_nodes.json").write_text(
        json.dumps(nodes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Graph saved:", out_dir / "standards_graph.gpickle")
