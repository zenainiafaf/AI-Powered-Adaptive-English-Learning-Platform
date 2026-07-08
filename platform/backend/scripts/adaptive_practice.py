"""
adaptive_practice.py
─────────────────────────────────────────────────────────────────────
SERVICE IAG — Architecture 2 Agents pour l'exercice de pratique adaptatif

Agent 1 (LLaMA 3.1 - 8B) : Decision Agent
  - Phase 1 (LLM)          : analyse la réponse (understanding / reasoning / missing)
  - Phase 2 (LanguageTool) : détection des erreurs linguistiques (grammaire + vocabulaire)
                             uniquement si understanding == "correct" — aucun LLM
  - Toutes les conditions d'arrêt et de difficulté sont gérées LOCALEMENT (pas de LLM)

Agent 2 (LLaMA 3.3 - 70B) : Prompt Builder
  - Génère la question suivante selon la difficulté décidée localement
  - Génère le feedback adapté selon l'action décidée localement

La génération du texte de pratique est déléguée à generate_text_chat.py

EMPLACEMENT : backend/scripts/adaptive_practice.py
─────────────────────────────────────────────────────────────────────
"""

import json
import time
import os
from pathlib import Path
from groq import Groq
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

#  Import de la génération du texte depuis le fichier existant 
from scripts.generate_text_chat import generate_practice_text

# Modèles
AGENT1_MODEL = "llama-3.1-8b-instant"    # Decision Agent — léger, rapide
AGENT2_MODEL = "llama-3.3-70b-versatile"  # Prompt Builder — puissant, qualité

# PARAMÈTRES DE SESSION
MAX_QUESTIONS             = 8   # filet de sécurité absolu
MAX_ATTEMPTS_PER_QUESTION = 3
CONSECUTIVE_TO_LEVEL_UP   = 2   # corrects consécutifs sans aide pour monter de niveau
                                 # aussi utilisé comme condition d'arrêt en hard

# Scoring pondéré par question (basé sur le nombre d'aides données)
SCORE_DIRECT_CORRECT = 1.0    # correct sans aide
SCORE_AFTER_HINT1    = 0.75   # correct après 1 hint
SCORE_AFTER_HINT2    = 0.5    # correct après 2 hints
SCORE_AFTER_GUIDED   = 0.25   # correct après guided_feedback
SCORE_INCORRECT      = 0.0    # incorrect ou partially_correct à la dernière tentative


# UTILITAIRES


def _call_groq(prompt: str, model: str, max_tokens: int = 600,
               retries: int = 3, temperature: float = 0.3) -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY manquant dans .env")
    for attempt in range(retries):
        try:
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  ⚠️  Groq error (attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(5)
    raise Exception(f"Groq API ({model}) inaccessible après {retries} tentatives.")


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    start = text.find('{')
    if start == -1:
        start = text.find('[')
    if start != -1:
        text = text[start:]
    
    # Tentative directe
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Tentative de réparation : refermer les structures ouvertes
    # Compter les accolades/crochets pour détecter la troncature
    open_braces   = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    
    # Fermer les guillemets ouverts si la dernière valeur est tronquée
    # On cherche si on est au milieu d'une string
    repaired = text.rstrip().rstrip(',')
    # Fermer dans l'ordre inverse : d'abord les tableaux, puis les objets
    repaired += ']' * max(0, open_brackets)
    repaired += '}' * max(0, open_braces)
    
    return json.loads(repaired)


# DÉCISION LOCALE : Difficulté suivante et condition d'arrêt
# (SANS appel LLM — économie de tokens)

def compute_final_weighted_score(score_history: list) -> float:
    """
    Calcule le score de PERFORMANCE pur de l'apprenant, indépendamment du niveau atteint.

    Principe : moyenne simple de tous les scores par question, pondérée uniquement
    par les aides utilisées (1.0 → 0.75 → 0.5 → 0.25 → 0.0).
    Le niveau atteint (easy/medium/hard) n'intervient PAS ici — il est géré séparément
    par highest_difficulty_reached dans interpret_final_score().

    Pourquoi cette séparation :
      - Le score reflète UNIQUEMENT la qualité des réponses (autonomie, précision)
      - Le niveau atteint reflète UNIQUEMENT jusqu'où l'apprenant est allé
      - interpret_final_score() combine les deux pour un message contextuel juste

    Exemples :
      bloqué easy, alterne 1.0/0.75  → score = 0.875  (bonne perf, niveau easy)
      atteint hard, beaucoup d'aides → score = 0.40   (niveau hard, perf moyenne)
      Ces deux cas ont des scores proches mais des interprétations très différentes
      grâce à highest_difficulty_reached.

    Retourne un float entre 0.0 et 1.0.
    """
    if not score_history:
        return 0.0

    score = sum(score_history) / len(score_history)
    return round(score, 4)


def decide_next_difficulty_local(
    previous_difficulty: str,
    final_understanding: str,
    help_given: bool,
    question_count: int,
    consecutive_correct_no_help: int,
    score_history: list,
) -> dict:
    """
    Décide localement (sans LLM) :
    - si la session doit s'arrêter
    - quelle difficulté donner à la prochaine question

    RÈGLE DE PROGRESSION (unidirectionnelle — jamais de régression) :
      - correct sans aide, CONSECUTIVE_TO_LEVEL_UP fois de suite → monte au niveau suivant
        (compteur remis à 0 après la montée)
      - correct avec aide                                        → reste au même niveau, compteur reset
      - incorrect ou partially_correct                           → reste au même niveau, compteur reset

    CONDITIONS D'ARRÊT (par priorité) :
      1. MAX_QUESTIONS atteint                                   → arrêt absolu
      2. 2 corrects consécutifs sans aide en hard                → arrêt anticipé (maîtrise maximale prouvée)

    Retourne : {
        "next_difficulty"           : "easy|medium|hard",
        "continue"                  : True|False,
        "stop_reason"               : "max_questions|mastered_hard|none",
        "consecutive_correct_no_help": int,   # valeur mise à jour à passer à la prochaine question
        "final_weighted_score"      : float,  # score pondéré courant (pour log/résultat final)
        "reasoning"                 : str
    }
    """
    difficulties = ["easy", "medium", "hard"]
    idx = difficulties.index(previous_difficulty) if previous_difficulty in difficulties else 0

    was_correct  = (final_understanding == "correct")
    final_score  = compute_final_weighted_score(score_history)

    # Mise à jour du compteur consécutif
    if was_correct and not help_given:
        new_consecutive = consecutive_correct_no_help + 1
    else:
        new_consecutive = 0  # reset : aide donnée ou échec

    # 1. Arrêt absolu : max questions atteint
    if question_count >= MAX_QUESTIONS:
        return {
            "next_difficulty":            previous_difficulty,
            "continue":                   False,
            "stop_reason":                "max_questions",
            "consecutive_correct_no_help": new_consecutive,
            "final_weighted_score":       final_score,
            "reasoning":                  f"Maximum de {MAX_QUESTIONS} questions atteint"
        }

    # 2. Arrêt anticipé : maîtrise prouvée en hard
    if previous_difficulty == "hard" and new_consecutive >= CONSECUTIVE_TO_LEVEL_UP:
        return {
            "next_difficulty":            "hard",
            "continue":                   False,
            "stop_reason":                "mastered_hard",
            "consecutive_correct_no_help": new_consecutive,
            "final_weighted_score":       final_score,
            "reasoning":                  f"{CONSECUTIVE_TO_LEVEL_UP} réponses correctes consécutives sans aide en hard — maîtrise maximale prouvée"
        }

    # La session continue : calcul de la prochaine difficulté (unidirectionnelle)
    if new_consecutive >= CONSECUTIVE_TO_LEVEL_UP and idx < 2:
        # Monte au niveau suivant, reset du compteur
        next_diff    = difficulties[idx + 1]
        new_consecutive = 0
        reason       = f"{CONSECUTIVE_TO_LEVEL_UP} corrects consécutifs sans aide → montée en {next_diff}"
    else:
        # Reste au même niveau
        next_diff = previous_difficulty
        if was_correct and not help_given:
            reason = "Correct sans aide — compteur en cours, reste au même niveau"
        elif was_correct and help_given:
            reason = "Correct avec aide → compteur reset, reste au même niveau"
        else:
            reason = "Incorrect ou partiellement correct → compteur reset, reste au même niveau"

    return {
        "next_difficulty":            next_diff,
        "continue":                   True,
        "stop_reason":                "none",
        "consecutive_correct_no_help": new_consecutive,
        "final_weighted_score":       final_score,
        "reasoning":                  reason
    }


# DÉCISION LOCALE : Action pédagogique selon tentative
# (SANS appel LLM : logique déterministe)

def decide_action_local(attempt: int, understanding: str) -> str:
    """
    Décide l'action pédagogique selon la tentative et le understanding.

    Règle :
      - correct (toujours)               → "validation"
      - dernière tentative (même partial) → "explanation"
      - tentative 1                       → "hint" (peu importe incorrect ou partial)
      - tentative 2+ :
          partially_correct              → "hint"            (encore incomplet → autre indice ciblé sur missing)
          incorrect                      → "guided_feedback" (toujours faux → aide directe)

    Retourne : "hint" | "guided_feedback" | "explanation" | "validation"
    """
    # Correct → validation directe peu importe la tentative
    if understanding == "correct":
        return "validation"

    # Dernière tentative → explication (même si partially_correct)
    if attempt >= MAX_ATTEMPTS_PER_QUESTION:
        return "explanation"

    # Première tentative → hint toujours (on ne brûle pas les étapes)
    if attempt == 1:
        return "hint"

    # Tentative 2+ → la distinction partial/incorrect prend effet
    if understanding == "partially_correct":
        return "hint"            # encore incomplet → indice ciblé sur ce qui manque (missing)
    else:
        return "guided_feedback" # toujours incorrect → aide directe


# DÉTECTION DÉTERMINISTE : Erreurs grammaticales via LanguageTool

try:
    import language_tool_python as _ltp
    _LT_TOOL = _ltp.LanguageTool("en-US")
except Exception:
    _LT_TOOL = None  # fallback : LLM seul si LanguageTool indisponible

# Règles LanguageTool à ignorer — non pertinentes pour un apprenant CEFR
_LT_IGNORED_RULES = {
    "WHITESPACE_RULE",
    "COMMA_PARENTHESIS_WHITESPACE",
    "EN_QUOTES",
    "SENTENCE_WHITESPACE",
    "UPPERCASE_SENTENCE_START",       # on ignore la majuscule en début de phrase
    "PUNCTUATION_PARAGRAPH_END",      # on ignore le point final manquant
    "EN_UNPAIRED_BRACKETS",
    "TOO_LONG_SENTENCE",
}

# Catégories LanguageTool à garder — uniquement grammaire et style objectif
_LT_KEPT_CATEGORIES = {
    "GRAMMAR",        # subject-verb agreement, tense, articles obligatoires, etc.
    "TYPOS",          # vrais mots mal orthographiés (pas de style)
}


def _detect_grammar_errors_deterministic(student_answer: str, text_content: str) -> dict:
    """
    Détecte les erreurs grammaticales et vocabulaire de manière déterministe
    via LanguageTool.
    """

    default = {
        "has_errors": False,
        "grammar_errors": [],
        "vocabulary_errors": [],
    }

    if _LT_TOOL is None:
        return default

    try:
        matches = _LT_TOOL.check(student_answer)

        text_lower = text_content.lower()

        grammar_errors = []
        vocabulary_errors = []

        for m in matches:

            # ─────────────────────────────────────────────
            # Compatibilité multi-versions LanguageTool
            # ─────────────────────────────────────────────

            # rule_id
            rule_id = getattr(m, "ruleId", None)

            if rule_id is None and hasattr(m, "rule"):
                rule_id = getattr(m.rule, "id", "")

            # category
            category = getattr(m, "category", None)

            if category is None and hasattr(m, "rule") and hasattr(m.rule, "category"):
                category = getattr(m.rule.category, "id", "")

            category = str(category or "")

            # error length
            error_length = getattr(m, "errorLength", None)

            if error_length is None:
                error_length = getattr(m, "error_length", None)

            if error_length is None:
                matched_text = getattr(m, "matchedText", "")
                error_length = len(matched_text)

            # offset
            offset = getattr(m, "offset", 0)

            # replacements
            replacements = getattr(m, "replacements", [])

            # message
            #  prend l'explication native de LanguageTool
            message = getattr(m, "message", "")

            # ─────────────────────────────────────────────
            # Filtres
            # ─────────────────────────────────────────────

            if rule_id in _LT_IGNORED_RULES:
                continue

            if category not in _LT_KEPT_CATEGORIES:
                continue

            #  extrait la forme erronée directement depuis la réponse de l'apprenant
            #   via la position et la longueur données par LanguageTool
            wrong = student_answer[offset: offset + error_length] 
            
           #  prend la première suggestion de correction de LanguageTool
            correct = replacements[0] if replacements else "?"

            # ─────────────────────────────────────────────
            # Filtre faux positifs
            # ─────────────────────────────────────────────

            ctx_start = max(0, offset - 10)
            ctx_end = offset + error_length + 10

            context_fragment = student_answer[ctx_start:ctx_end].lower()

            if context_fragment in text_lower and len(wrong) >= 3:
                continue

            # ─────────────────────────────────────────────
            # Construction erreur
            # ─────────────────────────────────────────────

            error_obj = {
                "wrong": wrong,
                "correct": correct,
                "message": message,
            }

            if category == "GRAMMAR":
                grammar_errors.append(error_obj)
            else:
                vocabulary_errors.append(error_obj)

        return {
            "has_errors": bool(grammar_errors or vocabulary_errors),
            "grammar_errors": grammar_errors,
            "vocabulary_errors": vocabulary_errors,
        }

    except Exception as e:
        print(f"⚠️ LanguageTool detection error: {e}")

        return default



def agent1_analyze_answer(
    text_content: str,
    question: str,
    expected_answer: str,
    student_answer: str,
    attempt: int,
    cefr_level: str
) -> dict:
    """
    Agent 1 — Phase feedback.
    2 phases séparées et indépendantes :
      - Phase 1 (LLM)          : UNIQUEMENT la compréhension (understanding / reasoning / missing)
      - Phase 2 (LanguageTool) : UNIQUEMENT les erreurs linguistiques — exécutée SEULEMENT
                                 si understanding == "correct". Aucun appel LLM.

    Retourne : {
        "understanding"  : "correct|partially_correct|incorrect",
        "reasoning"      : "...",
        "missing"        : "...",
        "language_errors": {
            "has_errors"       : True|False,
            "grammar_errors"   : ["..."],
            "vocabulary_errors": ["..."]
        }
    }
    """

    # ══════════════════════════════════════════════════════════════════
    # APPEL 1 — Compréhension uniquement
    # Aucune mention d'erreurs linguistiques → ne peut pas les influencer
    # ══════════════════════════════════════════════════════════════════
    comprehension_prompt = f"""You are an educational evaluation agent analyzing a student's reading comprehension answer.

READING TEXT:
{text_content[:1000]}

QUESTION: {question}
EXPECTED ANSWER: {expected_answer}
STUDENT ANSWER: {student_answer}
ATTEMPT NUMBER: {attempt}
STUDENT CEFR LEVEL: {cefr_level}

TASK: Does the student's answer correctly respond to the QUESTION based on the text? Choose ONE:
- "correct"           : the student's answer satisfies the QUESTION completely, 
                        even if phrased differently, even if short, even if grammar errors.
- "partially_correct" : use this when EITHER:
                        (1) the question explicitly asks for multiple elements and 
                            the student addresses only some, OR
                        (2) the correct answer contains multiple distinct items 
                            (e.g. "rice and miso soup", "name and age") and the 
                            student mentions only some of them.
- "incorrect"         : the answer is wrong, off-topic, or does not answer the question.

STRICT RULES:
- Ignore completely how the answer is written (grammar, spelling, vocabulary, pronouns)
- NEVER mark partially_correct just because the answer is short
- NEVER mark partially_correct if the answer is complete and accurate
- If the expected_answer has multiple items and student gives only one → partially_correct
- Never penalize grammar errors if the meaning is correct
- The expected_answer is a reference, not a strict checklist

Respond ONLY in JSON (no markdown, no explanation):
{{
  "understanding": "correct|partially_correct|incorrect",
  "reasoning": "brief reason focused only on factual content",
  "missing": "the exact fact(s) missing (only for partially_correct, else empty string)"
}}"""

    _default_le = {"has_errors": False, "grammar_errors": [], "vocabulary_errors": []}

    try:
        raw1 = _call_groq(comprehension_prompt, AGENT1_MODEL, max_tokens=200, temperature=0.1)
        result = _extract_json(raw1)

       

    except Exception as e:
        print(f"  ⚠️  Agent 1 (comprehension) error: {e}")
        return {
            "understanding":   "incorrect",
            "missing":         "",
            "reasoning":       "fallback — evaluation error",
            "language_errors": _default_le,
        }

    # ══════════════════════════════════════════════════════════════════
    # APPEL 2 — Erreurs linguistiques : LanguageTool UNIQUEMENT
    #
    # Grammaire + Vocabulaire (TYPOS) → _detect_grammar_errors_deterministic
    # Aucun appel LLM pour la détection linguistique
    # Si LanguageTool est indisponible → language_errors vide, pas de fallback
    # ══════════════════════════════════════════════════════════════════
    if result["understanding"] != "correct":
        result["language_errors"] = _default_le
        return result

    if _LT_TOOL is not None:
        lt_result = _detect_grammar_errors_deterministic(student_answer, text_content)
        if not isinstance(lt_result, dict):
            lt_result = _default_le
        result["language_errors"] = {
            "has_errors"       : lt_result.get("has_errors", False),
            "grammar_errors"   : lt_result.get("grammar_errors", []),
            "vocabulary_errors": lt_result.get("vocabulary_errors", []),
        }
    else:
        print("  ⚙️  [Agent1] LanguageTool indisponible — détection linguistique ignorée")
        result["language_errors"] = _default_le

    return result

# AGENT 2 : Génère la prochaine question ouverte

def agent2_generate_question(
    text_content: str,
    cefr_level: str,
    difficulty: str,
    previous_questions: list
) -> dict:
    """
    Agent 2 — Génère une nouvelle question ouverte ancrée dans le texte.

    Retourne : {
        "question": "...",
        "expected_answer": "...",
        "difficulty": "easy|medium|hard"
    }
    """
    # Toutes les questions precedentes (pas seulement les 6 dernieres)
    prev_qs = "\n".join([f"- {q}" for q in previous_questions]) if previous_questions else "None"

    # Resume des idees deja couvertes
    ideas_covered_note = ""
    if previous_questions:
        ideas_covered_note = f"""
IMPORTANT — IDEAS ALREADY COVERED (do NOT ask about the same idea, even with different words):
{prev_qs}

For example: if a previous question asked "Why does Sara put signs outside?", do NOT ask
"What happens when Sara puts big signs?" — these target the SAME idea.
You must target a completely DIFFERENT part or idea of the text."""

    difficulty_guide = {
    "A1": {
        "easy":   "Ask about ONE simple fact explicitly stated in the text (who, what, where). The answer must be found in a single sentence from the text.",
        "medium": "Ask about a specific detail or a simple action and its direct result, both clearly stated in the SAME sentence or consecutive sentences.",
        "hard": "Ask about a very simple and obvious inference: what a character probably feels or likes, where the answer is directly suggested by ONE explicit sentence in the text (e.g. 'I like my daily routine' → Yui is happy with her life). The student should not need to combine multiple ideas."
    },
    
    "A2": {
        "easy":   "Ask about a simple fact or a basic detail explicitly stated in the text. The answer must be findable in one sentence.",
        "medium": "Ask about a simple cause/effect or a connection between two explicitly stated elements.",
        "hard": "Ask what a character's action or choice reveals about their personality or habit, where the answer requires a small reasoning step beyond what is literally stated (e.g. 'she always arrives early' → she is punctual)."
    },
    "B1": {
        "easy":   "Ask about one directly stated fact or the main idea. The answer must be findable in a single sentence of the text.",
        "medium": "Ask about a cause/consequence relationship or a connection between two events in the text.",
        "hard": "Ask about an implied meaning or motivation that requires combining several elements of the text — the answer is not stated anywhere directly."
    },
    "B2": {
        "easy": "Ask about the central argument or the overall message of the text, as a student would paraphrase it.",
        "medium": "Ask about the author's attitude, a subtle inference, or the relationship between two ideas.",
        "hard":   "Ask about register, implicit meaning, rhetorical choice, or what the text suggests beyond what it states."
    },
    "C1": {
       "easy": "Ask about how the argument is organized or what logical steps the author follows to build the main point.",
        "medium": "Ask about an unstated assumption, implicit argumentation, or a nuanced relationship between ideas.",
        "hard":   "Ask about tone, irony, the rhetorical strategy used, or the deeper implication of the text."
    },
    "C2": {
        "easy": "Ask about the author's thesis and the ideological or epistemological stance it reflects.",
        "medium": "Ask about a subtle implicit reasoning, an ideological stance, or an underlying assumption.",
        "hard":   "Ask the student to deconstruct the author's rhetorical strategy, bias, or deeper philosophical implication."
    },
}

    level_guide      = difficulty_guide.get(cefr_level)
    diff_instruction = level_guide.get(difficulty)

    prompt = f"""You are an expert English teacher creating reading comprehension questions for CEFR {cefr_level} students.

READING TEXT:
{text_content}

DIFFICULTY LEVEL: {difficulty} (for CEFR {cefr_level})
WHAT THIS DIFFICULTY MEANS: {diff_instruction}
{ideas_covered_note}

YOUR TASK: Generate exactly 1 open comprehension question that:
1. Targets a DIFFERENT idea or part of the text than all previous questions
2. Matches the difficulty level exactly as described above. Use vocabulary and sentence complexity appropriate for CEFR {cefr_level}.
3.Can be answered in 1-2 sentences, but a short accurate answer (even one clause) is acceptable
4. Is directly answerable from the text (no outside knowledge needed)
5. Does NOT ask about vocabulary definitions
6.NEVER include the answer inside the question itself
- NEVER ask about a name if the name is already in the question
- The question must require the student to actually READ the text to answer

SELF-CHECK before responding:
- Does this question target a NEW idea not covered by previous questions? must be YES
- Is the difficulty correct for CEFR {cefr_level} {difficulty}? must be YES
- Can it be answered in 1-2 sentences from the text? must be YES
If any answer is NO, generate a different question.

Respond ONLY in JSON (no markdown, no explanation):
{{
  "question": "Your question here?",
  "expected_answer": "The ideal answer based on the text (1-2 sentences)",
  "difficulty": "{difficulty}"
}}"""

    try:
        raw = _call_groq(prompt, AGENT2_MODEL, max_tokens=400, temperature=0.4)
        result = _extract_json(raw)
        result["difficulty"] = difficulty
        return result
    except Exception as e:
        print(f"  ⚠️  Agent 2 (question generation) error: {e}")
        return {
            "question": "What is the main idea of this text?",
            "expected_answer": "The main idea is about the topic described in the text.",
            "difficulty": difficulty
        }


def _build_validation_prompt(cefr_level: str, language_errors: dict) -> str:
    """
    Construit le prompt de validation pour Agent 2.
    Si des erreurs linguistiques ont été détectées, la plus importante est
    signalée comme remarque — sans pénaliser l'apprenant.

    Les erreurs sont des dicts structurés {"wrong": str, "correct": str, "message": str}
    produits soit par LanguageTool soit parsés depuis la réponse LLM.
    wrong/correct sont injectés directement dans le prompt : Agent 2 n'a plus
    qu'à reformuler la raison en langage adapté au niveau CEFR.
    """
    has_errors = (
        language_errors is not None
        and isinstance(language_errors, dict)
        and language_errors.get("has_errors", False)
    )

    if not has_errors:
        return """The student gave a correct answer. Give VALIDATION that:
- Confirms the answer is correct
- Adds a brief explanation to reinforce understanding
- Is warm and encouraging
- Is 1-2 sentences maximum"""

    grammar_list = language_errors.get("grammar_errors", [])
    vocab_list   = language_errors.get("vocabulary_errors", [])

    # Grammaire prioritaire sur vocabulaire pour le choix de l'erreur principale
    all_errors = grammar_list + vocab_list
    top = all_errors[0] if all_errors else {}

    # Extraction structurée (dict) ou fallback string legacy
    if isinstance(top, dict) and top.get("wrong") and top.get("correct"):
        wrong_form   = top["wrong"]
        correct_form = top["correct"]
        reason_raw   = top.get("message", "")
        explicit_fix = (
            f"WRONG FORM  : {wrong_form}\n"
            f"CORRECT FORM: {correct_form}\n"
            f"RAW REASON  : {reason_raw}"
        )
    else:
        # Fallback : string brut (legacy ou parsing raté)
        fallback_str = top if isinstance(top, str) else top.get("message", str(top))
        wrong_form = correct_form = None
        explicit_fix = f"MISTAKE: {fallback_str}"

    # Résumé complet de toutes les erreurs pour contexte (au cas où il y en a plusieurs)
    def _fmt(e):
        if isinstance(e, dict):
            return f"  - '{e.get('wrong','?')}' → '{e.get('correct','?')}' ({e.get('message','')})"
        return f"  - {e}"

    error_lines = []
    if grammar_list:
        error_lines.append("Grammar mistake(s):\n" + "\n".join(_fmt(e) for e in grammar_list))
    if vocab_list:
        error_lines.append("Vocabulary mistake(s):\n" + "\n".join(_fmt(e) for e in vocab_list))
    error_summary = "\n".join(error_lines)

    return f"""The student gave a correct answer but made language mistakes in their writing.
You MUST write EXACTLY 2 parts — do not skip either part:

PART 1 — Validation (1 sentence):
Warmly confirm the answer is correct. Do NOT start with an emoji.

PART 2 — Writing tip (1 sentence, MANDATORY — do not omit):
Use this EXACT format:
"✏️ Writing tip: you wrote '{wrong_form or "[wrong form]"}' — it should be '{correct_form or "[correct form]"}' ([your simple explanation here for CEFR {cefr_level}]). This didn't affect your score!"

THE MAIN MISTAKE TO ADDRESS (already extracted for you — do NOT change wrong/correct):
{explicit_fix}

Rules for Part 2:
- The wrong form and correct form are given above — copy them exactly into the template.
- Your ONLY job is to write the explanation in simple words appropriate for CEFR {cefr_level}.
- Do NOT copy the raw reason verbatim — reformulate it simply.
- Do NOT pick a different mistake.

ALL MISTAKES DETECTED (for context only — address only the main one above):
{error_summary}

Do NOT add any other remarks."""

# AGENT 2 : Génère le feedback adapté

def agent2_generate_feedback(
    action: str,
    text_content: str,
    question: str,
    expected_answer: str,
    student_answer: str,
    cefr_level: str,
    reasoning: str = "",
    missing: str = "",
    language_errors: dict = None
) -> str:
    """
    Agent 2 — Génère le message de feedback selon l'action décidée localement.
    Retourne : string (le message de feedback en anglais)
    """
    action_prompts = {
        "hint": f"""Give a HINT to help the student. Rules:
- If this is attempt 1: give a general hint pointing to the relevant part of the text WITHOUT revealing the answer
- If the student was partially correct (WHAT IS MISSING field is filled): acknowledge what was right, then give a hint specifically targeting what is missing
- IMPORTANT: if the student's answer already contains the correct information, do NOT ask for more — only hint toward what is genuinely missing
- Use simple language for CEFR {cefr_level}
- Be encouraging and positive
- 1-2 sentences maximum
Do NOT give the answer. Do NOT copy from the text directly.""",

        "guided_feedback": f"""The student answered incorrectly twice. Give GUIDED FEEDBACK that:
- Gently signals that the answer is still off
- Guides them toward the right idea without giving the full answer
- Is encouraging and constructive
- Is 2-3 sentences maximum
Do NOT give the full answer yet.""",

        "explanation": f"""The student has used all their attempts. Give a clear EXPLANATION that:
- Explains what the correct answer is and WHY, based on the text
- Uses simple language appropriate for CEFR {cefr_level}
- Is kind and encouraging (not discouraging)
- Is 2-4 sentences maximum""",

        "validation": _build_validation_prompt(cefr_level, language_errors),
    }

    instruction = action_prompts.get(action, action_prompts["hint"])

    prompt = f"""You are a friendly English teacher giving feedback to a CEFR {cefr_level} student.

READING TEXT:
{text_content[:800]}

QUESTION: {question}
{"" if action == "validation" else f"EXPECTED ANSWER: {expected_answer}"}
STUDENT ANSWER: {student_answer}
EVALUATION REASONING: {reasoning}
WHAT IS MISSING IN THE STUDENT ANSWER: {missing if missing else "N/A"}

FEEDBACK INSTRUCTION:
{instruction}

Write the feedback message directly (no JSON, no preamble, just the feedback text):"""

    try:
        raw = _call_groq(prompt, AGENT2_MODEL, max_tokens=300, temperature=0.4)
        return raw.strip()
    except Exception as e:
        print(f"  ⚠️  Agent 2 (feedback) error: {e}")
        fallback_messages = {
            "hint":           "Think about what the text says about this topic. Read the relevant section again carefully.",
            "guided_feedback":"You're on the right track! Try to be more specific about the details mentioned in the text.",
            "explanation":    f"The correct answer is: {expected_answer}. This is found in the text.",
            "validation":     "Correct! Well done. You understood the text well."
        }
        return fallback_messages.get(action, "Keep trying!")


# CALCUL DU SCORE PONDÉRÉ

def calculate_weighted_score(action_history: list, understanding: str) -> float:
    """
    Calcule le score pondéré d'une question selon la tentative à laquelle
    l'apprenant a répondu correctement.

    Barème (basé sur la tentative) :
        tentative 1 — correct sans aide             → 1.0
        tentative 2 — correct après 1 hint          → 0.75
        tentative 3 — correct après 2 hints         → 0.5
        tentative 3 — correct après guided_feedback → 0.25
        tentative 3 — partial ou incorrect          → 0.0  (3 chances données)
    """
    # Pas correct à la fin → 0.0 (on lui a donné toutes ses chances)
    if understanding in ["partially_correct", "incorrect"]:
        return SCORE_INCORRECT

    # Correct → identifier à quelle tentative
    nb_hints   = sum(1 for a in action_history if a == "hint")
    has_guided = any(a == "guided_feedback" for a in action_history)

    if has_guided:
        return SCORE_AFTER_GUIDED   # 0.25 — correct à la tentative 3 après guided
    elif nb_hints >= 2:
        return SCORE_AFTER_HINT2    # 0.5  — correct à la tentative 3 après 2 hints
    elif nb_hints == 1:
        return SCORE_AFTER_HINT1    # 0.75 — correct à la tentative 2 après 1 hint
    else:
        return SCORE_DIRECT_CORRECT # 1.0  — correct à la tentative 1


def interpret_final_score(performance_score: float, highest_difficulty_reached: str) -> dict:
    """
    Interprète le résultat final de la session en combinant DEUX dimensions indépendantes :

    - performance_score          : moyenne des scores par question (0.0 → 1.0)
                                   reflète la qualité des réponses (aides utilisées)
    - highest_difficulty_reached : "easy" | "medium" | "hard"
                                   reflète jusqu'où l'apprenant est allé

    Grille d'interprétation :
                        perf ≥ 0.75       perf 0.50-0.74      perf < 0.50
      easy atteint   → needs_more_work   needs_more_work     needs_more_work
      medium atteint → good              partial             needs_more_work
      hard atteint   → mastered          good                partial
    """
    if performance_score >= 0.75:
        perf_tier = "high"
    elif performance_score >= 0.50:
        perf_tier = "mid"
    else:
        perf_tier = "low"

    grid = {
        "easy":   {"high": "needs_more_work", "mid": "needs_more_work", "low": "needs_more_work"},
        "medium": {"high": "good",            "mid": "partial",         "low": "needs_more_work"},
        "hard":   {"high": "mastered",        "mid": "good",            "low": "partial"},
    }

    level = grid.get(highest_difficulty_reached, grid["easy"])[perf_tier]

    messages = {
        "mastered": {
            "message":        "Excellent! You reached the advanced level with great autonomy.",
            "recommendation": "You are ready to move to the next CEFR level!"
        },
        "good": {
            "message":        f"Good progress! You reached the {'advanced' if highest_difficulty_reached == 'hard' else 'intermediate'} level.",
            "recommendation": "Keep practicing at this level to consolidate."
        },
        "partial": {
            "message":        f"You are making progress at the {'advanced' if highest_difficulty_reached == 'hard' else 'intermediate'} level, but need more autonomy.",
            "recommendation": "Practice more without hints to build confidence."
        },
        "needs_more_work": {
            "message":        "You need more practice at this level before moving forward.",
            "recommendation": "Review the key concepts and try again."
        },
    }

    return {"level": level, **messages[level]}