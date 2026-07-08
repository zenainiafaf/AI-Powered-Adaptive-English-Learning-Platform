import torch
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from collections import defaultdict
import numpy as np

print('=== Construction interactions multi-types ===\n')

# ── Chargement ──────────────────────────────────────────────
kg          = torch.load('data.pt',         map_location='cpu', weights_only=False)
g2_raw      = torch.load('student_data.pt', map_location='cpu', weights_only=False)
act_to_task = torch.load('act_to_task.pt',  map_location='cpu')

ei_all = g2_raw['student', 'attempted', 'activity'].edge_index  # [2, 404773]
ea_all = g2_raw['student', 'attempted', 'activity'].edge_attr   # [404773, 4]

N_STU  = g2_raw['student'].x.shape[0]   # 89589
N_TASK = kg['task'].x.shape[0]          # 128
N_GRAM = kg['grammar'].x.shape[0]       # 1218
N_VOC  = kg['vocabulary'].x.shape[0]    # 7459
N_READ = kg['reading'].x.shape[0]       # 9565

print(f'Etudiants  : {N_STU:,}')
print(f'Tasks      : {N_TASK}')
print(f'Grammar    : {N_GRAM:,}')
print(f'Vocabulary : {N_VOC:,}')
print(f'Reading    : {N_READ:,}')

# ── Remap activity → task ───────────────────────────────────
ei_task = ei_all.clone()
ei_task[1] = act_to_task[ei_all[1]]

# ── Extraire relations KG : cefr → grammar/vocab/reading ────
# task → cefr
task_to_cefr = torch.zeros(N_TASK, dtype=torch.long)
ei_ct = kg['cefr', 'has_task', 'task'].edge_index
for c, t in zip(ei_ct[0].tolist(), ei_ct[1].tolist()):
    task_to_cefr[t] = c

# cefr → grammar
cefr_to_grammar = defaultdict(list)
ei_cg = kg['cefr', 'requires', 'grammar'].edge_index
for c, g in zip(ei_cg[0].tolist(), ei_cg[1].tolist()):
    cefr_to_grammar[c].append(g)

# cefr → vocabulary
cefr_to_vocab = defaultdict(list)
ei_cv = kg['cefr', 'has_vocab', 'vocabulary'].edge_index
for c, v in zip(ei_cv[0].tolist(), ei_cv[1].tolist()):
    cefr_to_vocab[c].append(v)

# cefr → reading
cefr_to_reading = defaultdict(list)
ei_cr = kg['cefr', 'has_reading', 'reading'].edge_index
for c, r in zip(ei_cr[0].tolist(), ei_cr[1].tolist()):
    cefr_to_reading[c].append(r)

print('\nRelations KG extraites :')
for lvl in range(6):
    print(f'  CECRL {lvl} → '
          f'grammar:{len(cefr_to_grammar[lvl])} '
          f'vocab:{len(cefr_to_vocab[lvl])} '
          f'reading:{len(cefr_to_reading[lvl])}')


MAX_GRAM  = 5   
MAX_VOC   = 5  
MAX_READ  = 5    

# ── Construction interactions virtuelles ─────────────────────
print('\nConstruction interactions virtuelles...')

gram_src, gram_dst, gram_attr = [], [], []
voc_src,  voc_dst,  voc_attr  = [], [], []
read_src, read_dst, read_attr = [], [], []

for idx in range(ei_task.shape[1]):
    stu_id  = ei_task[0, idx].item()
    task_id = ei_task[1, idx].item()
    attr    = ea_all[idx]          
    tw      = attr[1].item()       # temporal_weight (Ebbinghaus)
    grade   = attr[0].item()

    cefr_id = task_to_cefr[task_id].item()

    # Grammar
    grams = cefr_to_grammar[cefr_id]
    if grams:
        # Sélectionner MAX_GRAM grammar aléatoirement
        selected = grams[:MAX_GRAM]
        for g_id in selected:
            gram_src.append(stu_id)
            gram_dst.append(g_id)
            gram_attr.append([grade, tw, tw * grade, 1.0])

    # Vocabulary
    vocs = cefr_to_vocab[cefr_id]
    if vocs:
        selected = vocs[:MAX_VOC]
        for v_id in selected:
            voc_src.append(stu_id)
            voc_dst.append(v_id)
            voc_attr.append([grade, tw, tw * grade, 1.0])

    # Reading
    reads = cefr_to_reading[cefr_id]
    if reads:
        selected = reads[:MAX_READ]
        for r_id in selected:
            read_src.append(stu_id)
            read_dst.append(r_id)
            read_attr.append([grade, tw, tw * grade, 1.0])

    if idx % 50000 == 0:
        print(f'  {idx:,}/{ei_task.shape[1]:,} interactions traitées...')

print(f'\nInteractions créées :')
print(f'  student→grammar    : {len(gram_src):,}')
print(f'  student→vocabulary : {len(voc_src):,}')
print(f'  student→reading    : {len(read_src):,}')

# ── Construction du nouveau student_data_multi.pt ────────────
print('\nConstruction student_data_multi.pt...')

g2_multi = HeteroData()

# Nœuds
g2_multi['student'].x   = g2_raw['student'].x
g2_multi['task'].x      = kg['task'].x
g2_multi['grammar'].x   = kg['grammar'].x
g2_multi['vocabulary'].x= kg['vocabulary'].x
g2_multi['reading'].x   = kg['reading'].x

# Interactions originales task
g2_multi['student', 'attempted', 'task'].edge_index = ei_task
g2_multi['student', 'attempted', 'task'].edge_attr  = ea_all

# Interactions virtuelles grammar
if gram_src:
    g2_multi['student', 'practiced', 'grammar'].edge_index = torch.tensor(
        [gram_src, gram_dst], dtype=torch.long)
    g2_multi['student', 'practiced', 'grammar'].edge_attr = torch.tensor(
        gram_attr, dtype=torch.float)

# Interactions virtuelles vocabulary
if voc_src:
    g2_multi['student', 'studied', 'vocabulary'].edge_index = torch.tensor(
        [voc_src, voc_dst], dtype=torch.long)
    g2_multi['student', 'studied', 'vocabulary'].edge_attr = torch.tensor(
        voc_attr, dtype=torch.float)

# Interactions virtuelles reading
if read_src:
    g2_multi['student', 'read', 'reading'].edge_index = torch.tensor(
        [read_src, read_dst], dtype=torch.long)
    g2_multi['student', 'read', 'reading'].edge_attr = torch.tensor(
        read_attr, dtype=torch.float)

torch.save(g2_multi, 'student_data_multi.pt')
print('✓ Sauvegardé : student_data_multi.pt')

# ── Résumé ────────────────────────────────────────────────────
print('\n=== RÉSUMÉ ===')
for et in g2_multi.edge_types:
    ei = g2_multi[et].edge_index
    print(f'  {str(et):45s}: {ei.shape[1]:,} interactions')