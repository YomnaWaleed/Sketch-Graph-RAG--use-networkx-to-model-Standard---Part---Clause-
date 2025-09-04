# src/build_index.py
from sentence_transformers import SentenceTransformer
import faiss, numpy as np
import networkx as nx
import json, pickle
from pathlib import Path

EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def build_index_from_graph(
    graph_pickle_path, out_dir="../outputs/indices", index_name="graph_index"
):
    out_dir = Path(out_dir)  # ✅ convert to Path
    out_dir.mkdir(parents=True, exist_ok=True)

    # load graph
    with open(graph_pickle_path, "rb") as f:
        G = pickle.load(f)

    # choose nodes to embed (clause & part)
    nodes_to_embed = [
        n for n, d in G.nodes(data=True) if d.get("type") in ("clause", "part")
    ]
    texts = [
        (G.nodes[n]["content"] or G.nodes[n]["title"]).strip() for n in nodes_to_embed
    ]

    # encode embeddings
    model = SentenceTransformer(EMB_MODEL)
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    faiss.normalize_L2(embeddings)

    # build FAISS index
    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(embeddings)

    # save FAISS index
    idx_path = out_dir / f"{index_name}.index"
    faiss.write_index(index, str(idx_path))

    # save mapping from FAISS id -> node_id & metadata
    mapping = {
        i: {"node_id": node, **G.nodes[node]} for i, node in enumerate(nodes_to_embed)
    }
    meta_path = out_dir / f"{index_name}_meta.json"
    meta_path.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Saved FAISS index:", idx_path)
    print("Saved metadata JSON:", meta_path)

    return str(idx_path), str(meta_path)


if __name__ == "__main__":
    build_index_from_graph(
        "../data/graphs/standards_graph.gpickle",
        out_dir="../outputs/indices",
        index_name="graph_index",
    )
