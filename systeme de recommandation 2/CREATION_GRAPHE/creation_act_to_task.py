import torch
import torch.nn.functional as F

kg = torch.load('data.pt', weights_only=False)
g2 = torch.load('student_data.pt', weights_only=False)

act_feats  = g2['activity'].x       
task_feats = kg['task'].x           

a_norm = F.normalize(act_feats, dim=1)
t_norm = F.normalize(task_feats, dim=1)
sim = a_norm @ t_norm.T             

# Mapping : activity_id → task_id
act_to_task = sim.argmax(dim=1)    
print("Mapping construit :", act_to_task.shape)

all_tasks = set(range(128))
used_tasks = set(act_to_task.tolist())
missing = all_tasks - used_tasks
print(f"Tasks sans interactions étudiants : {sorted(missing)}")

torch.save(act_to_task, 'act_to_task.pt')
print("✓ Sauvegardé : act_to_task.pt")