"""
============================================================
SCRIPT D'IMPORT : JSON → Base de données Django
backend/scripts/evaluation_test/import_eval_test.py
============================================================
"""

import json
import os
import sys
import re
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Django_prj.settings')
django.setup()

from users.models import EvaluationTest, EvaluationQuestion

DATA_DIR = os.path.join(BASE_DIR, 'data', 'evaluation_test')
JSON_PATH = os.path.join(DATA_DIR, 'cefr_a1_evaluation_test.json')

if not os.path.exists(JSON_PATH):
    print(f"❌ Fichier non trouvé : {JSON_PATH}")
    sys.exit(1)

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"📄 JSON chargé : {data['test_id']}")
print(f"   Niveau : {data['level']}")
print(f"   Questions : {data['total_questions']}")
print(f"   Passing score : {data['passing_score']}%")
print()

# ── 1. Créer le test ───────────────────────────────────────
test, created = EvaluationTest.objects.get_or_create(
    level=data['level'],
    defaults={
        'title': data['title'],
        'description': data['description'],
        'time_limit_minutes': data['time_limit_minutes'],
        'total_questions': data['total_questions'],
        'passing_score': data['passing_score'],
    }
)

if created:
    print(f"✅ Test créé : {test}")
else:
    print(f"ℹ️  Test existant : {test}")
    test.title = data['title']
    test.description = data['description']
    test.time_limit_minutes = data['time_limit_minutes']
    test.total_questions = data['total_questions']
    test.passing_score = data['passing_score']
    test.save()
    print("   → Mis à jour depuis le JSON")

# ── Mapping section_id → section_key ────────────────────────
SECTION_MAP = {
    'SEC_01_LISTENING': 'listening',
    'SEC_02_READING': 'reading',
    'SEC_03_IMAGES': 'visual',
    'SEC_04_GRAMMAR': 'grammar',
    'SEC_05_VOCABULARY': 'vocabulary',
}

# ── 2. Importer les questions ──────────────────────────────
count_created = 0
count_updated = 0

for section in data['sections']:
    section_key = SECTION_MAP.get(section['section_id'], section['section_id'].split('_')[-1].lower())

    print(f"\n📂 Section : {section['section_title']} ({section['total_questions']} questions)")

    for q in section['questions']:
        # ── Normalise le type ──────────────────────────────
        q_type = q['type']
        if q_type == 'multiple_choice':
            q_type = 'mcq'

        # ── Options : stocker UNIQUEMENT le texte pur (sans préfixe A:/B:) ──
        options = None
        if 'options' in q and q['options']:
            if isinstance(q['options'], list) and len(q['options']) > 0:
                first_opt = q['options'][0]

                if isinstance(first_opt, dict) and ('id' in first_opt or 'letter' in first_opt):
                    # Format {"id": "A", "text": "..."} ou {"letter": "A", "text": "..."}
                    # → stocker uniquement le texte pur
                    options = [opt['text'] for opt in q['options']]

                elif isinstance(first_opt, str):
                    # Format ["love", "loves", ...] → déjà du texte pur
                    options = q['options']

        # ── Réponse correcte ───────────────────────────────
        correct = ''

        if isinstance(q.get('correct_answer'), bool):
            # Booléen Python/JSON → "True" ou "False"
            correct = 'True' if q['correct_answer'] else 'False'

        elif 'blanks' in q and q['blanks']:
            # fill_blank avec blanks → concatène les réponses avec |
            correct = '|'.join(b['correct_answer'] for b in q['blanks'])

        elif 'correct_answer' in q:
            raw = q['correct_answer']

            # Si correct_answer est une lettre unique (A/B/C/D)
            # → chercher le texte correspondant dans options
            if (
                isinstance(raw, str)
                and re.match(r'^[A-Da-d]$', raw.strip())
                and 'options' in q
                and q['options']
            ):
                letter = raw.strip().upper()
                found = False
                for opt in q['options']:
                    if isinstance(opt, dict):
                        opt_id = opt.get('id') or opt.get('letter', '')
                        if opt_id.strip().upper() == letter:
                            correct = opt['text']
                            found = True
                            break
                if not found:
                    # fallback : garder la lettre si option non trouvée
                    correct = raw

            else:
                # Texte direct ("loves", "snows", "TRUE", etc.)
                correct = str(raw)

        elif 'answer' in q:
            correct = str(q['answer'])

        # ── Texte de la question ───────────────────────────
        question_text = q.get('question') or q.get('statement', '')

        # ── Ordre ──────────────────────────────────────────
        try:
            order = int(''.join(filter(str.isdigit, q.get('question_id', '0'))))
        except Exception:
            order = 0

        # ── Création ou mise à jour ─────────────────────────
        defaults = {
            'test': test,
            'section': section_key,
            'type': q_type,
            'question_text': question_text,
            'audio_path': q.get('audio_path', ''),
            'image_path': q.get('image_path', ''),
            'reading_text': q.get('text', ''),
            'options': options,
            'correct_answer': correct,
            'explanation': q.get('explanation', ''),
            'points': q.get('points', 1),
            'order': order,
        }

        obj, created_q = EvaluationQuestion.objects.update_or_create(
            question_id=q['question_id'],
            defaults=defaults
        )

        if created_q:
            count_created += 1
            print(f"   + {q['question_id']} créé  |  correct_answer = '{correct}'")
        else:
            count_updated += 1
            print(f"   ~ {q['question_id']} mis à jour  |  correct_answer = '{correct}'")

# ── Résumé ─────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"✅ IMPORT TERMINÉ")
print(f"{'='*50}")
print(f"   Questions créées       : {count_created}")
print(f"   Questions mises à jour : {count_updated}")
print(f"   Total en base          : {EvaluationQuestion.objects.filter(test=test).count()}")
print()

for section_key, section_name in EvaluationQuestion.SECTIONS:
    count = EvaluationQuestion.objects.filter(test=test, section=section_key).count()
    print(f"   • {section_name:<25} : {count} questions")