"""
validate_texts.py
─────────────────────────────────────────────────────────────────────
Script à lancer UNE SEULE FOIS après load_texts.py.

Pour chaque ReadingText en base :
  1. Nettoie le texte (lowercase, enlève ponctuation)
  2. Compare les mots avec le dictionnaire A1
  3. Calcule le coverage_score (% de mots A1)
  4. Met is_valid = True si score ≥ 40%

Lancer depuis backend/ :
    python scripts/validate_texts.py
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

from users.models import ReadingText

# ── CONFIG ────────────────────────────────────────────────────────
DICTIONARY_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'english_vocabulary_by_level.json')
TARGET_LEVEL    = 'A1'
MIN_SCORE       = 0.40   # 40% minimum pour is_valid = True
# ──────────────────────────────────────────────────────────────────


def load_a1_words(path: str) -> set:
    """Charge les mots A1 depuis le JSON et retourne un set."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    words = set(w.lower().strip() for w in data.get('A1', []))
    print(f"✅  {len(words)} mots A1 chargés depuis le dictionnaire")
    return words


def clean_and_tokenize(text: str) -> list[str]:
    """
    Nettoie le texte et retourne une liste de mots.
    - lowercase
    - enlève ponctuation
    - enlève les mots trop courts (≤ 1 caractère)
    """
    text  = text.lower()
    text  = re.sub(r"[^\w\s\-']", ' ', text)  # garde lettres, chiffres, tirets
    words = text.split()
    words = [w.strip("-'") for w in words if len(w) > 1]
    return words


def calculate_coverage(text: str, a1_words: set) -> float:
    """
    Calcule le % de mots du texte qui sont dans le dictionnaire A1.
    Retourne un float entre 0.0 et 1.0
    """
    words = clean_and_tokenize(text)
    if not words:
        return 0.0

    # Vérification mot simple + expressions multi-mots (ex: "wake up")
    matched = 0
    i = 0
    while i < len(words):
        # Essaye d'abord expression de 3 mots
        if i + 2 < len(words):
            phrase3 = f"{words[i]} {words[i+1]} {words[i+2]}"
            if phrase3 in a1_words:
                matched += 3
                i += 3
                continue
        # Essaye expression de 2 mots
        if i + 1 < len(words):
            phrase2 = f"{words[i]} {words[i+1]}"
            if phrase2 in a1_words:
                matched += 2
                i += 2
                continue
        # Mot simple
        if words[i] in a1_words:
            matched += 1
        i += 1

    return matched / len(words)


def main():
    # Charger le dictionnaire
    print(f"📂  Lecture du dictionnaire : {DICTIONARY_PATH}")
    a1_words = load_a1_words(DICTIONARY_PATH)

    # Récupérer tous les textes A1 depuis la base
    texts = ReadingText.objects.filter(
        sub_unit__unit__level=TARGET_LEVEL
    ).select_related('sub_unit__unit')

    total       = texts.count()
    valid_count = 0
    invalid_count = 0

    print(f"\n📊  {total} textes A1 à valider...\n")

    for text in texts:
        score = calculate_coverage(text.content, a1_words)

        text.coverage_score = round(score, 4)
        text.is_valid       = score >= MIN_SCORE
        text.save(update_fields=['coverage_score', 'is_valid'])

        status = "✅" if text.is_valid else "❌"
        if text.is_valid:
            valid_count += 1
        else:
            invalid_count += 1

        print(f"  {status}  [{score:.0%}]  {text.topic[:60]}")

    print("\n" + "─" * 55)
    print(f"✅  Validation terminée !")
    print(f"    Total textes   : {total}")
    print(f"    Valides (≥40%) : {valid_count}")
    print(f"    Invalides      : {invalid_count}")
    print()
    print("👉  Prochaine étape : créer les vues API (views.py)")


if __name__ == '__main__':
    main()
