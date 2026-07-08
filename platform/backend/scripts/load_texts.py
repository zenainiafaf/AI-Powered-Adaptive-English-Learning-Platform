"""
load_texts.py
─────────────────────────────────────────────────────────────────────
Importe TOUS les textes A1 dans PostgreSQL.
→ Tous les textes d'une SubUnit sont stockés en base
→ L'affichage utilisera le premier texte valide (is_valid=True)

Lancer depuis backend/ :
    python scripts/load_texts.py
─────────────────────────────────────────────────────────────────────
"""

import os
import sys
import json
import re
import django

# ── Setup Django ──────────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Django_prj.settings')
django.setup()

from users.models import Unit, SubUnit, ReadingText

# ── CONFIG ────────────────────────────────────────────────────────
CLASSIFICATION_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'classification_a1.json')
DATASET_PATH        = os.path.join(os.path.dirname(__file__), '..', 'data', 'final_english_dataset.jsonl')
TARGET_LEVEL        = 'A1'
# ──────────────────────────────────────────────────────────────────


def clean_text(raw: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', raw)
    return text.strip()


def load_dataset(path: str) -> dict:
    """Retourne { topic: contenu_texte } pour tous les textes A1."""
    dataset = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            meta  = entry.get('scientific_metadata', {})
            if meta.get('target_level') != TARGET_LEVEL:
                continue
            topic   = meta.get('topic', '')
            content = ''
            for msg in entry.get('messages', []):
                if msg.get('role') == 'assistant':
                    content = clean_text(msg['content'])
                    break
            if topic and content:
                dataset[topic] = content
    return dataset


def find_content(topic: str, dataset: dict) -> str | None:
    """Cherche le texte par topic exact puis par correspondance partielle."""
    if topic in dataset:
        return dataset[topic]
    topic_lower = topic.lower()
    for k, v in dataset.items():
        if topic_lower in k.lower() or k.lower() in topic_lower:
            return v
    return None


def main():
    # Sécurité : ne pas charger deux fois
    if Unit.objects.filter(level=TARGET_LEVEL).exists():
        print(f"⚠️  Des unités {TARGET_LEVEL} existent déjà en base. Script annulé.")
        print("    Supprime-les d'abord si tu veux relancer.")
        return

    print(f"📂  Lecture de la classification...")
    with open(CLASSIFICATION_PATH, encoding='utf-8') as f:
        classification = json.load(f)

    print(f"📂  Lecture du dataset...")
    dataset = load_dataset(DATASET_PATH)
    print(f"✅  {len(dataset)} textes chargés\n")

    total_units    = 0
    total_subunits = 0
    total_texts    = 0
    not_found      = []

    for unit_order, (unit_title, subunits) in enumerate(classification.items(), start=1):

        unit = Unit.objects.create(
            title = unit_title,
            level = TARGET_LEVEL,
            order = unit_order,
        )
        total_units += 1
        print(f"📁 [{unit_order}] {unit_title}")

        for sub_order, (sub_title, topics) in enumerate(subunits.items(), start=1):

            subunit = SubUnit.objects.create(
                unit  = unit,
                title = sub_title,
                order = sub_order,
            )
            total_subunits += 1
            print(f"     📂 {sub_title}  ({len(topics)} texte(s))")

            # ── Stocker TOUS les textes de cette SubUnit ──────────
            for topic in topics:
                content = find_content(topic, dataset)
                if content:
                    ReadingText.objects.create(
                        sub_unit  = subunit,
                        topic     = topic,
                        content   = content,
                        is_valid  = False,
                    )
                    total_texts += 1
                    print(f"          └── ✅ {topic}")
                else:
                    not_found.append(topic)
                    print(f"          └── ⚠️  Introuvable : {topic}")

    print("\n" + "─" * 55)
    print(f"✅  Chargement terminé !")
    print(f"    Units créées    : {total_units}")
    print(f"    SubUnits créées : {total_subunits}")
    print(f"    Textes importés : {total_texts}")
    if not_found:
        print(f"    ⚠️  Introuvables  : {len(not_found)}")
        for t in not_found:
            print(f"       - {t}")
    print()
    print("👉  Lance maintenant : python scripts/validate_texts.py")


if __name__ == '__main__':
    main()
