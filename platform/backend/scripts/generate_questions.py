"""
generate_questions.py
─────────────────────────────────────────────────────────────────────
Script à lancer UNE SEULE FOIS après validate_texts.py.

Pour chaque ReadingText valide (is_valid=True) :
  1. Envoie le texte à Groq
  2. Groq génère 10 questions de vraie compréhension :
       - 3 true/false
       - 3 multiple choice (compréhension réelle, pas copier-coller)
       - 4 fill in the blank (résumé, pas copier-coller)
  3. Les questions sont stockées dans reading_question en base

Lancer depuis backend/ :
    python scripts/generate_questions.py
─────────────────────────────────────────────────────────────────────
"""

import os
import sys
import json
import time
import django
from groq import Groq

# ── Setup Django ──────────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Django_prj.settings')
django.setup()

from users.models import ReadingText, ReadingQuestion

# ── CONFIG ────────────────────────────────────────────────────────
TARGET_LEVEL  = 'A1'
MODEL_NAME    = "llama-3.1-8b-instant"
SLEEP_BETWEEN = 2
# ──────────────────────────────────────────────────────────────────

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def call_groq(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"    ⚠️  Erreur API (tentative {attempt+1}/{retries}): {e}")
            time.sleep(10)
    raise Exception("❌ Groq API inaccessible.")


def extract_json(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text  = "\n".join(lines[1:-1])
    return json.loads(text)


def generate_questions_for_text(text_content: str, topic: str) -> list:
    prompt = f"""You are an English teacher creating REAL comprehension questions for CEFR A1 beginner students.

Read this passage about "{topic}":

---
{text_content[:1500]}
---

Generate exactly 10 comprehension questions with this exact distribution:
- 3 TRUE/FALSE questions
- 3 MULTIPLE CHOICE questions (4 options each)
- 4 FILL IN THE BLANK questions

═══════════════════════════════════════════
VERY IMPORTANT RULE FOR ALL 10 QUESTIONS:
The student must READ and UNDERSTAND the text to answer.
NEVER write questions where the answer is just one word copied from one sentence.
The student must think and understand the MEANING.
═══════════════════════════════════════════

Rules for TRUE/FALSE:
- Write a statement that requires understanding, not just finding a word
- BAD example:  "Ana wakes up at six." (just copy from text)
- GOOD example: "Ana has a busy morning routine." (requires understanding)
- GOOD example: "Ana does not like her job." (requires understanding the whole text)
- Mix True and False answers

Rules for MULTIPLE CHOICE:
- Ask questions about meaning, feelings, reasons, or general ideas
- NEVER ask "What word is used for X in the text?"
- BAD example:  "What does Ana eat for breakfast?" (student just finds the sentence)
- GOOD example: "Why does Ana feel happy at work?" (student must understand her feelings)
- GOOD example: "What kind of person is Ana?" (student must understand her character)
- GOOD example: "How does Ana spend her evenings?" (student must understand the routine)
- Only one correct answer, 3 wrong but believable options
- Options must be short (1-4 words)

Rules for FILL IN THE BLANK:
- Write a NEW sentence that SUMMARIZES or PARAPHRASES something from the text
- NEVER copy a sentence directly from the text
- BAD:  "Every morning, I wake up at ___ o'clock." (copied from text)
- GOOD: "Ana begins her day very ___ in the morning." → answer: "early"
- GOOD: "Ana's job is to take care of ___." → answer: "plants"
- GOOD: "Ana feels ___ when she is with her family." → answer: "happy"
- The answer must require understanding the text

Respond ONLY with a valid JSON array of exactly 10 objects, no explanation, no markdown backticks:

[
  {{
    "question": "statement requiring understanding",
    "type": "true_false",
    "choices": ["True", "False"],
    "answer": "True or False"
  }},
  {{
    "question": "Question about meaning/feeling/reason?",
    "type": "multiple_choice",
    "choices": ["correct answer", "wrong1", "wrong2", "wrong3"],
    "answer": "correct answer"
  }},
  {{
    "question": "New paraphrased sentence with ___ missing.",
    "type": "fill_blank",
    "choices": null,
    "answer": "the missing word"
  }}
]"""

    raw    = call_groq(prompt)
    result = extract_json(raw)

    if len(result) != 10:
        print(f"    ⚠️  {len(result)} questions reçues au lieu de 10")

    return result


def main():
    print("🚀  Génération des questions pour les textes A1 valides...\n")
    print("    Répartition : 3 true/false | 3 multiple choice | 4 fill blank\n")

    texts = ReadingText.objects.filter(
        sub_unit__unit__level=TARGET_LEVEL,
        is_valid=True
    ).prefetch_related('questions')

    texts_without_questions = [t for t in texts if t.questions.count() == 0]

    total   = len(texts_without_questions)
    success = 0
    failed  = 0

    print(f"📊  {total} textes valides sans questions\n")

    for i, text in enumerate(texts_without_questions, start=1):
        print(f"  [{i}/{total}] {text.topic[:60]}...")

        try:
            questions = generate_questions_for_text(text.content, text.topic)

            for q in questions:
                ReadingQuestion.objects.create(
                    text     = text,
                    question = q['question'],
                    type     = q['type'],
                    choices  = q['choices'],
                    answer   = q['answer'],
                )

            success += 1
            print(f"         ✅ {len(questions)} questions stockées")

        except Exception as e:
            failed += 1
            print(f"         ❌ Erreur : {e}")

        time.sleep(SLEEP_BETWEEN)

    print("\n" + "─" * 55)
    print(f"✅  Génération terminée !")
    print(f"    Textes traités  : {total}")
    print(f"    Succès          : {success}")
    print(f"    Échecs          : {failed}")
    print(f"    Total questions : ~{success * 10}")
    print()
    print("👉  Prochaine étape : créer les vues API (views.py)")


if __name__ == '__main__':
    main()
