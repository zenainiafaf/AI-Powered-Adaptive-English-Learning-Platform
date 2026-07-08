"""
encode_graph.py
===============
Encodage correct du Knowledge Graph → data.pt
- Features catégorielles  → One-Hot Encoding
- Features textuelles     → Sentence-BERT (384-dim)
- Dimension finale        → 128 (zero-pad si < 128, tronqué si > 128)
- Normalisation           → L2
- Arêtes                  → typées sémantiquement depuis le graphe original
- Sortie                  → data.pt (PyTorch Geometric HeteroData)
"""

import os
os.environ['USE_TF'] = '0'
os.environ['TRANSFORMERS_NO_TF'] = '1'

import pickle
import torch
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer
from torch_geometric.data import HeteroData
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
PKL_PATH    = 'knowledge_graph_complete.pkl'
OUT_PATH    = 'data.pt'
FINAL_DIM   = 128
SBERT_MODEL = 'all-MiniLM-L6-v2'   # 384-dim

CEFR_ORDER  = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
CEFR_TO_IDX = {c: i for i, c in enumerate(CEFR_ORDER)}

# ─────────────────────────────────────────────
# Schéma des features par type de nœud
# ─────────────────────────────────────────────
NODE_FEATURE_SCHEMA = {
    'cefr': {
        'categorical': ['cefr'],
        'textual':     ['description'],
        'numerical':   [],
    },
    'unit': {
        'categorical': ['level'],
        'textual':     ['label', 'full_title'],
        'numerical':   ['unit_number'],
    },
    'task': {
        'categorical': ['level'],
        'textual':     ['label', 'full_title', 'topic', 'written_task'],
        'numerical':   [],
    },
    'grammar': {
        'categorical': ['level', 'super_category', 'sub_category'],
        'textual':     ['label', 'guideword', 'can_do_statement', 'example'],
        'numerical':   [],
    },
    'vocabulary': {
        'categorical': ['level', 'part_of_speech'],
        'textual':     ['label', 'full_word'],
        'numerical':   [],
    },
    'reading': {
        'categorical': ['level'],
        'textual':     ['label', 'title', 'text'],
        'numerical':   [],
    },
}

# ─────────────────────────────────────────────
# Mapping arêtes → types sémantiques
# ─────────────────────────────────────────────
EDGE_TYPE_MAP = {
    ('cefr',       'cefr')      : 'progression_to',
    ('cefr',       'unit')      : 'contains',
    ('cefr',       'task')      : 'has_task',
    ('cefr',       'grammar')   : 'requires',
    ('cefr',       'vocabulary'): 'has_vocab',
    ('cefr',       'reading')   : 'has_reading',
    ('unit',       'cefr')      : 'included_in',
    ('unit',       'unit')      : 'related_unit',
    ('unit',       'task')      : 'includes',
    ('unit',       'grammar')   : 'teaches',
    ('unit',       'vocabulary'): 'uses_vocab',
    ('unit',       'reading')   : 'uses_reading',
    ('task',       'cefr')      : 'belongs_to',
    ('task',       'unit')      : 'part_of',
    ('task',       'task')      : 'related_task',
    ('task',       'grammar')   : 'uses_grammar',
    ('task',       'vocabulary'): 'uses_vocab',
    ('task',       'reading')   : 'uses_reading',
    ('grammar',    'cefr')      : 'belongs_to',
    ('grammar',    'unit')      : 'part_of',
    ('grammar',    'grammar')   : 'related_grammar',
    ('vocabulary', 'cefr')      : 'belongs_to',
    ('vocabulary', 'unit')      : 'part_of',
    ('vocabulary', 'vocabulary'): 'related_vocab',
    ('reading',    'cefr')      : 'belongs_to',
    ('reading',    'unit')      : 'part_of',
    ('reading',    'reading')   : 'related_reading',
}

def get_edge_type(src_type, dst_type, original_type):
    key = (src_type, dst_type)
    if key in EDGE_TYPE_MAP:
        return EDGE_TYPE_MAP[key]
    if original_type not in ('unknown', 'connects', ''):
        return original_type
    return f'{src_type}_to_{dst_type}'

def safe_get(d, key, default=''):
    v = d.get(key, default)
    return str(v)[:512] if v is not None else default

def pad_or_trim(vec, target):
    """Zero-pad ou tronquer à target dimensions — PAS de PCA."""
    if len(vec) < target:
        return np.concatenate([vec, np.zeros(target - len(vec), dtype=np.float32)])
    return vec[:target].astype(np.float32)

# ─────────────────────────────────────────────
# 1. CHARGEMENT DU GRAPHE
# ─────────────────────────────────────────────
print("=" * 60)
print("1. Chargement du graphe...")
with open(PKL_PATH, 'rb') as f:
    G = pickle.load(f)
print(f"   Nœuds : {G.number_of_nodes():,}  |  Arêtes : {G.number_of_edges():,}")

nodes_by_type = defaultdict(list)
for node_id, d in G.nodes(data=True):
    t = d.get('type', 'unknown')
    nodes_by_type[t].append((node_id, d))

print("\n   Répartition par type :")
for t, lst in nodes_by_type.items():
    print(f"     {t:15s} : {len(lst):,}")

# ─────────────────────────────────────────────
# 2. CHARGEMENT SENTENCE-BERT
# ─────────────────────────────────────────────
print(f"\n2. Chargement Sentence-BERT ({SBERT_MODEL})...")
sbert = SentenceTransformer(SBERT_MODEL)
print("   Modèle chargé ✓")

# ─────────────────────────────────────────────
# 3. ENCODAGE DES FEATURES PAR TYPE
# ─────────────────────────────────────────────
print("\n3. Encodage des features...")

def encode_node_type(node_list, schema, node_type):
    n = len(node_list)
    parts = []

    # ── A. Catégorielles → One-Hot
    for col in schema['categorical']:
        vals = [safe_get(d, col, 'unknown') for _, d in node_list]
        enc  = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        oh   = enc.fit_transform(np.array(vals).reshape(-1, 1))
        parts.append(oh.astype(np.float32))
        print(f"     [{node_type}] catégoriel '{col}' → {oh.shape[1]} catégories")

    # ── B. Textuelles → SBERT 384-dim
    if schema['textual']:
        sentences = []
        for _, d in node_list:
            pieces = [safe_get(d, col, '') for col in schema['textual']]
            sentences.append(' | '.join(p for p in pieces if p))

        print(f"     [{node_type}] SBERT {n:,} textes...", end=' ', flush=True)
        emb = sbert.encode(sentences, batch_size=256,
                           show_progress_bar=False,
                           convert_to_numpy=True).astype(np.float32)
        print(f"→ {emb.shape[1]}-dim ✓")
        parts.append(emb)

    # ── C. Numériques → Min-Max
    for col in schema['numerical']:
        vals = np.array([float(safe_get(d, col, 0) or 0)
                         for _, d in node_list], dtype=np.float32).reshape(-1, 1)
        vmin, vmax = vals.min(), vals.max()
        if vmax > vmin:
            vals = (vals - vmin) / (vmax - vmin)
        parts.append(vals)
        print(f"     [{node_type}] numérique '{col}' → scalé")

    # ── D. Concaténation
    X = np.concatenate(parts, axis=1).astype(np.float32) if parts \
        else np.zeros((n, FINAL_DIM), dtype=np.float32)

    print(f"     [{node_type}] dim brute : {X.shape[1]}")

    # ── E. Zero-pad ou tronquer → FINAL_DIM  (sans PCA)
    X_final = np.stack([pad_or_trim(row, FINAL_DIM) for row in X])

    # ── F. L2-normalisation
    X_final = normalize(X_final, norm='l2')
    print(f"     [{node_type}] shape finale {X_final.shape} ✓\n")
    return X_final

node_to_local_idx = {}
features_by_type  = {}
node_ids_by_type  = {}

for node_type, node_list in nodes_by_type.items():
    schema = NODE_FEATURE_SCHEMA.get(node_type,
             {'categorical': [], 'textual': [], 'numerical': []})
    node_ids = [nid for nid, _ in node_list]
    node_ids_by_type[node_type] = node_ids
    for local_idx, nid in enumerate(node_ids):
        node_to_local_idx[nid] = (node_type, local_idx)
    features_by_type[node_type] = encode_node_type(node_list, schema, node_type)

# ─────────────────────────────────────────────
# 4. CONSTRUCTION HeteroData
# ─────────────────────────────────────────────
print("4. Construction du HeteroData...")
data = HeteroData()

# Nœuds
for node_type, X in features_by_type.items():
    data[node_type].x       = torch.tensor(X, dtype=torch.float)
    data[node_type].node_id = node_ids_by_type[node_type]
    print(f"   data['{node_type}'].x → {data[node_type].x.shape}")

# Arêtes typées sémantiquement
print("\n   Construction des arêtes typées...")
edge_buckets = defaultdict(lambda: ([], []))
skipped = 0

for u, v, edata in G.edges(data=True):
    if u not in node_to_local_idx or v not in node_to_local_idx:
        skipped += 1
        continue
    src_type, src_idx = node_to_local_idx[u]
    dst_type, dst_idx = node_to_local_idx[v]
    original_rel      = edata.get('type', 'unknown')
    rel = get_edge_type(src_type, dst_type, original_rel)
    key = (src_type, rel, dst_type)
    edge_buckets[key][0].append(src_idx)
    edge_buckets[key][1].append(dst_idx)

for (src_type, rel, dst_type), (src_list, dst_list) in edge_buckets.items():
    ei = torch.tensor([src_list, dst_list], dtype=torch.long)
    data[src_type, rel, dst_type].edge_index = ei
    print(f"   ('{src_type}', '{rel}', '{dst_type}') → {ei.shape[1]:,} arêtes")

if skipped:
    print(f"   ⚠ {skipped:,} arêtes ignorées")

# ─────────────────────────────────────────────
# 5. SAUVEGARDE
# ─────────────────────────────────────────────
print(f"\n5. Sauvegarde → {OUT_PATH}")
torch.save(data, OUT_PATH)
print("   ✅ Sauvegardé !")

# ─────────────────────────────────────────────
# 6. VÉRIFICATION
# ─────────────────────────────────────────────
print("\n6. Vérification :")
data_loaded = torch.load(OUT_PATH, weights_only=False)
print(f"\n   Types de nœuds :")
for nt in data_loaded.node_types:
    x = data_loaded[nt].x
    print(f"     [{nt:12s}] shape={x.shape}  mean={x.mean():.4f}  std={x.std():.4f}")

print(f"\n   Types d'arêtes :")
for et in data_loaded.edge_types:
    n = data_loaded[et].edge_index.shape[1]
    print(f"     {et[0]:12s} → {et[2]:12s} ({et[1]}) : {n:,}")

print("\n" + "=" * 60)
print("✅ Encodage terminé !")
print(f"   Dim finale        : {FINAL_DIM}")
print(f"   PCA utilisé       : NON  ← zero-pad/tronqué")
print(f"   Arêtes typées     : OUI  ← sémantiques")
print(f"   Fichier de sortie : {OUT_PATH}")
print("=" * 60)