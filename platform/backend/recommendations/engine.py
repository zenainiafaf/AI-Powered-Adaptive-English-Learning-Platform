import os
import torch
import torch_geometric
from torch_geometric.data import HeteroData

# ─────────────────────────────────────────────
#  CHARGEMENT DU MODÈLE (une seule fois au démarrage)
# ─────────────────────────────────────────────

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'data', 'recommandation', 'hier_gnn_v3_final.pt'))

_checkpoint = None

def _load_checkpoint():
    global _checkpoint
    if _checkpoint is None:
        print(f"[Engine] Chargement du modèle depuis {MODEL_PATH} ...")
        _checkpoint = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
        print("[Engine] ✅ Modèle chargé !")
    return _checkpoint


# ─────────────────────────────────────────────
#  MAPPING CEFR → INDEX NUMÉRIQUE
# ─────────────────────────────────────────────

CEFR_TO_IDX = {'A1': 0, 'A2': 1, 'B1': 2, 'B2': 3, 'C1': 4, 'C2': 5}


# ─────────────────────────────────────────────
#  FONCTION PRINCIPALE DE RECOMMANDATION
# ─────────────────────────────────────────────

def get_recommendations(learner, top_k=50):
    """
    Retourne les top_k recommandations pour un apprenant.

    Paramètres :
        learner  : instance du model Learner (users.models.Learner)
        top_k    : nombre de recommandations par type (défaut 5)

    Retourne un dict :
    {
        'vocabulary' : [ {model_idx, score}, ... ],
        'grammar'    : [ {model_idx, score}, ... ],
        'reading'    : [ {model_idx, score}, ... ],
        'tasks'      : [ {model_idx, score}, ... ],
    }
    """
    ckpt        = _load_checkpoint()
    h_nodes     = ckpt['h_nodes']        # embeddings de tout le contenu
    e_student   = ckpt['e_student']      # embeddings des 89k étudiants
    cefr_dict   = ckpt['node_cefr_dict'] # niveau CEFR de chaque nœud
    act_to_task = ckpt['act_to_task']    # mapping activités → tasks

    learner_cefr_idx = CEFR_TO_IDX.get(learner.cefr_level, 0)

    # ── Embedding de l'apprenant ──────────────────────────────
    # Si l'apprenant est dans les 89k → utiliser son embedding
    # Sinon → utiliser la moyenne des étudiants du même niveau
    learner_db_id = learner.learner_id
    if learner_db_id < e_student.shape[0]:
        student_emb = e_student[learner_db_id]       # shape [64]
    else:
        # Nouvel apprenant : moyenne de tous les étudiants
        student_emb = e_student.mean(dim=0)          # shape [64]

    # ── Scores par type de contenu ────────────────────────────
    results = {}

    for content_type in ['vocabulary', 'grammar', 'reading', 'task']:
        h = h_nodes[content_type]                    # shape [N, 64]

        # Filtrer par niveau CEFR de l'apprenant
        cefr_labels = cefr_dict[content_type]        # tensor [N]
        mask = (cefr_labels == learner_cefr_idx)

        h_filtered    = h[mask]                      # shape [M, 64]
        filtered_idxs = mask.nonzero(as_tuple=True)[0]  # indices originaux

        if h_filtered.shape[0] == 0:
            results[content_type] = []
            continue

        # Similarité cosinus entre l'étudiant et chaque contenu
        student_norm = student_emb / (student_emb.norm() + 1e-8)
        h_norm       = h_filtered / (h_filtered.norm(dim=1, keepdim=True) + 1e-8)
        scores       = (h_norm @ student_norm)       # shape [M]

        # Top-k
        k         = min(top_k, scores.shape[0])
        topk      = torch.topk(scores, k)
        top_scores  = topk.values.tolist()
        top_indices = topk.indices.tolist()

        results[content_type] = [
            {
                'model_idx': int(filtered_idxs[i]),
                'score':     round(top_scores[j], 4),
            }
            for j, i in enumerate(top_indices)
        ]

    return results