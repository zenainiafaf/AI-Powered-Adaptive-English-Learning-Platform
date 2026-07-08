"""
generate_practice_text.py
─────────────────────────────────────────────────────────────────────
SERVICE GAI — Génère uniquement le texte de pratique.
La logique des questions et du feedback est gérée par adaptive_practice.py

EMPLACEMENT : backend/scripts/generate_practice_text.py
─────────────────────────────────────────────────────────────────────
"""

import json
from pathlib import Path
import time
import re
from groq import Groq

import os
from dotenv import load_dotenv
# Cherche le .env en remontant depuis ce fichier jusqu'à trouver manage.py
import sys
from pathlib import Path

def _find_dotenv():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / 'manage.py').exists():
            return parent / '.env'
    return Path('.env')  # fallback

load_dotenv(_find_dotenv())
#print(">>> .env path:", _find_dotenv())
#print(">>> GROQ_API_KEY:", os.getenv("reading_agent_api"))
GROQ_API_KEY = os.getenv("reading_agent_api")

MODEL_NAME = "llama-3.3-70b-versatile"


def get_client():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is missing. Please check your .env file.")
    return Groq(api_key=GROQ_API_KEY)


def _call_groq(prompt: str, max_tokens: int = 2000, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            client = get_client()
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  ⚠️  Groq error (attempt {attempt+1}/{retries}): {e}")
            time.sleep(8)
    raise Exception("Groq API unreachable after retries.")


def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text  = "\n".join(lines[1:-1])
    # Nettoyer les caractères de contrôle invalides
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return json.loads(text)


def _clean_text(raw: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', raw)
    return text.strip()


def generate_practice_text(topic: str, subunit_title: str, learner_level: str,
                            existing_contents: list = None) -> tuple[str, str]:
    """
    Génère un nouveau texte de pratique sur le même thème,
    différent des textes déjà générés.

    Paramètres :
        topic             : thème du texte original (ex: "Daily Routines")
        subunit_title     : titre de la sous-unité (ex: "Morning Activities")
        learner_level     : niveau CEFR (ex: "B1")
        existing_contents : liste des contenus déjà générés (pour garantir l'unicité)

    Retourne : (title, content)
    """

    uniqueness_constraint = ""
    if existing_contents and len(existing_contents) > 0:
        summaries = []
        for i, content in enumerate(existing_contents, 1):
            first_sentence = content.split('.')[0] if '.' in content else content[:100]
            summaries.append(f"Text {i}: {first_sentence}...")

        uniqueness_constraint = f"""
CRITICAL - EXISTING TEXTS TO AVOID:
{chr(10).join(summaries)}

YOU MUST create a text that is COMPLETELY DIFFERENT from the above. Use:
- Different character names (NOT the same as any existing text)
- Different location or setting
- Different specific situation or scenario
- Different time, weather, or context
DO NOT repeat any character names, places, or specific situations from existing texts.
"""

    variation_angles = [
        "Focus on a different character's experience or perspective",
        "Change the location to a completely different place",
        "Use a different time of day or different weather",
        "Make it about a different specific activity or event",
        "Change the relationship between characters",
        "Use a different season or time of year",
    ]

    angle = variation_angles[len(existing_contents) % len(variation_angles)] if existing_contents else variation_angles[0]

    prompt = f"""You are an expert English teacher creating reading materials for CEFR level {learner_level} students.

The student just practiced reading a text about: "{topic}" (theme: {subunit_title})

Write a NEW reading passage on the SAME THEME but COMPLETELY DIFFERENT from any previous texts.
{uniqueness_constraint}

VARIATION REQUIREMENT: {angle}

Rules:
- Level: CEFR {learner_level} — use simple, clear vocabulary appropriate for this level
- Length: 150-200 words
- Create a UNIQUE scenario with NEW characters and NEW setting
- Do NOT copy any sentences, names, or places from existing texts
- Write in a simple, friendly style with short sentences
- Give the new text a SHORT title (max 6 words) that is different from previous titles

Respond ONLY with valid JSON, no explanation, no markdown backticks:
{{
  "title": "Short Title Here",
  "content": "Full text here. Use \\n\\n to separate paragraphs."
}}"""

    raw  = _call_groq(prompt, max_tokens=800)
    data = _extract_json(raw)

    title   = data.get("title", f"Practice: {topic}")
    content = _clean_text(data.get("content", ""))
    return title, content