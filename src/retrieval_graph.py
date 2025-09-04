# src/retrieval_graph.py
import faiss, json, pickle
import networkx as nx
from sentence_transformers import SentenceTransformer
from pathlib import Path
from collections import deque

EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class GraphRAG:
    def __init__(self, graph_pickle, index_path, meta_path, emb_model=EMB_MODEL):
        with open(graph_pickle, "rb") as f:
            self.G = pickle.load(f)
        self.index = faiss.read_index(index_path)
        self.meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        self.model = SentenceTransformer(emb_model)
        self.faiss_to_node = {int(k): v["node_id"] for k, v in self.meta.items()}

    def _embed(self, q):
        v = self.model.encode([q], convert_to_numpy=True)
        faiss.normalize_L2(v)
        return v

    def semantic_search(self, query, k=5):
        v = self._embed(query)
        D, I = self.index.search(v, k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx == -1:
                continue
            node_id = self.faiss_to_node[int(idx)]
            results.append(
                {"node": node_id, "score": float(score), **dict(self.G.nodes[node_id])}
            )
        return results

    def expand_context(self, node_id, max_hops=1):
        q = deque([(node_id, 0)])
        seen = {node_id}
        nodes = [node_id]
        while q:
            cur, dist = q.popleft()
            if dist >= max_hops:
                continue
            for nbr in list(self.G.predecessors(cur)) + list(self.G.successors(cur)):
                if nbr not in seen:
                    seen.add(nbr)
                    nodes.append(nbr)
                    q.append((nbr, dist + 1))
        return [{"node": n, **dict(self.G.nodes[n])} for n in nodes]

    def hybrid_retrieve(self, query, top_k_sem=5, expand_hops=1, max_nodes=20):
        sem = self.semantic_search(query, k=top_k_sem)
        context_nodes = []
        for r in sem:
            context_nodes.extend(self.expand_context(r["node"], max_hops=expand_hops))
        # deduplicate preserving order
        seen = set()
        dedup = []
        for n in context_nodes:
            if n["node"] in seen:
                continue
            seen.add(n["node"])
            dedup.append(n)
        return dedup[:max_nodes]

    # graph-first: find nodes by title/code exact match, then expand
    def graph_first(self, code_or_title, expand_hops=2, max_nodes=30):
        # find nodes where title contains given token (case-insensitive)
        matches = [
            n
            for n, d in self.G.nodes(data=True)
            if code_or_title.lower() in str(d.get("title", "")).lower()
        ]
        context_nodes = []
        for m in matches:
            context_nodes.extend(self.expand_context(m, max_hops=expand_hops))
        # dedup
        seen = set()
        out = []
        for n in context_nodes:
            if n["node"] in seen:
                continue
            seen.add(n["node"])
            out.append(n)
        return out[:max_nodes]
