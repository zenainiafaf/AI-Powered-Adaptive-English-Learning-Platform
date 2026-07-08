"""
fix.py
=============
Corrige le mapping topic_id → KG task node_id et
met à jour student_data.pt avec les vraies features KG.

Règle découverte :
  topic_id (int)  =  global_idx dans T{level}_{unit}_{global_idx}
  → kg_data['task'].node_id[topic_id]  correspond exactement

  Exemple :
    topic_id = '1'   → task_ids[1]  = 'T1_2_1'
    topic_id = '49'  → task_ids[49] = 'T7_2_49'
    topic_id = '120' → task_ids[120]= 'T16_1_120'
"""

import torch

print("=" * 60)
print("Chargement des graphes...")

kg_data      = torch.load('data.pt',         weights_only=False)
student_data = torch.load('student_data.pt', weights_only=False)

task_ids = list(kg_data['task'].node_id)   # liste ordonnée, 128 éléments
task_x   = kg_data['task'].x               # [128, 128]

print(f"   KG tasks       : {len(task_ids)} nœuds")
print(f"   Student acts   : {len(student_data['activity'].node_id)} activités")

# ── Vérification du pattern
print("\nVérification mapping topic_id → task node_id :")
test_ids = ['1', '49', '81', '120']
for tid in test_ids:
    idx = int(tid)
    if idx < len(task_ids):
        print(f"   topic_id={tid:4s}  →  task_ids[{idx}] = {task_ids[idx]}")
    else:
        print(f"   topic_id={tid:4s}  →  ❌ hors limite ({len(task_ids)} tâches)")

# ── Construction du mapping complet
print("\nConstruction du mapping complet...")
act_node_ids = student_data['activity'].node_id   # ['1','2',…,'120']
n_act        = len(act_node_ids)
feat_dim     = task_x.shape[1]                    # 128

act_feats  = torch.zeros((n_act, feat_dim), dtype=torch.float)
found, missing = 0, []

for i, aid in enumerate(act_node_ids):
    idx = int(aid)                  # topic_id = global_idx dans KG
    if 0 <= idx < len(task_ids):
        act_feats[i] = task_x[idx]
        found += 1
    else:
        missing.append(aid)

print(f"   ✅ Matchées : {found}/{n_act}")
if missing:
    print(f"   ❌ Manquantes : {missing}")

# ── Mise à jour des features activité dans student_data
student_data['activity'].x       = act_feats
student_data['activity'].node_id = act_node_ids  # garde les ids originaux

# ── Ajoute aussi le mapping inverse pour usage dans le modèle
# topic_id → kg_task_node_id (utile pour le filtre CEFR)
student_data['activity'].kg_task_node_id = [
    task_ids[int(aid)] if 0 <= int(aid) < len(task_ids) else 'UNKNOWN'
    for aid in act_node_ids
]

print("\nAperçu du mapping final :")
for i in range(min(8, n_act)):
    aid = act_node_ids[i]
    kg_nid = student_data['activity'].kg_task_node_id[i]
    print(f"   topic_id={aid:4s}  →  KG task = {kg_nid:15s}"
          f"  feat_norm={act_feats[i].norm():.4f}")

# ── Sauvegarde
print("\nSauvegarde → student_data.pt")
torch.save(student_data, 'student_data.pt')
print("   ✅ Sauvegardé !")

# ── Vérification finale
print("\nVérification finale :")
d = torch.load('student_data.pt', weights_only=False)
x_act = d['activity'].x
print(f"   activity.x shape  : {x_act.shape}")
print(f"   activity.x mean   : {x_act.mean():.4f}  (était 0.0000 avant)")
print(f"   activity.x std    : {x_act.std():.4f}")
print(f"   activity.x norm>0 : {(x_act.norm(dim=1) > 0).sum().item()} / {x_act.shape[0]}")

print("\n" + "=" * 60)
print("✅  Bridge corrigé — student_data.pt prêt pour le modèle !")
print(f"   Étudiants    : {d['student'].x.shape[0]:,}")
print(f"   Activités    : {d['activity'].x.shape[0]}")
print(f"   Interactions : {d['student','attempted','activity'].edge_index.shape[1]:,}")
print("=" * 60)

# ── Fonction bridge pour le forward pass du modèle
def load_graphs():
    """
    Charge les deux graphes avec bridge déjà appliqué.
    Les features des activités dans student_data sont les vraies
    features KG (task embeddings de 128-dim).
    Les deux graphes restent séparés.
    """
    kg_data      = torch.load('data.pt',         weights_only=False)
    student_data = torch.load('student_data.pt', weights_only=False)
    return kg_data, student_data