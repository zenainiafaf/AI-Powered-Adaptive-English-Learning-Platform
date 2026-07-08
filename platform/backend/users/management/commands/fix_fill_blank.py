# ============================================================
# COMMANDE DJANGO : fix_fill_blank
# Corrige les questions fill_blank mal formatées dans la BDD
#
# UTILISATION :
#   python manage.py fix_fill_blank          → aperçu sans modifier (dry run)
#   python manage.py fix_fill_blank --apply  → applique les corrections
#
# EMPLACEMENT DU FICHIER :
#   Créer ce dossier si il n'existe pas :
#   backend/users/management/commands/fix_fill_blank.py
#
#   Structure attendue :
#   backend/
#   └── users/
#       └── management/
#           ├── __init__.py      ← fichier vide (créer si absent)
#           └── commands/
#               ├── __init__.py  ← fichier vide (créer si absent)
#               └── fix_fill_blank.py  ← CE FICHIER
# ============================================================

import re
from django.core.management.base import BaseCommand
from users.models import ReadingQuestion


def sanitize_fill_blank_question(question_text, answer):
    """
    Corrige une question fill_blank :
    Cas 1 : _____ déjà présent         → rien à faire
    Cas 2 : réponse visible dans phrase → remplace le mot par _____
    Cas 3 : réponse absente             → ajoute _____ à la fin
    """
    # Cas 1 : trou déjà présent
    if re.search(r'_{3,}', question_text):
        return question_text, False  # (texte, modifié?)

    # Cas 2 : le mot-réponse existe dans la phrase
    pattern = re.compile(r'\b' + re.escape(answer.strip()) + r'\b', re.IGNORECASE)
    if pattern.search(question_text):
        corrected = pattern.sub('_____', question_text, count=1)
        return corrected, True

    # Cas 3 : réponse absente → ajouter _____ à la fin
    question_stripped = question_text.rstrip()
    if question_stripped.endswith('.'):
        corrected = question_stripped[:-1] + ' _____.'
    else:
        corrected = question_stripped + ' _____'
    return corrected, True


class Command(BaseCommand):
    help = 'Corrige les questions fill_blank mal formatées dans la BDD'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Applique les corrections dans la BDD (sans --apply = dry run)',
        )

    def handle(self, *args, **options):
        apply = options['apply']

        if not apply:
            self.stdout.write(self.style.WARNING(
                '🔍 MODE APERÇU (dry run) — aucune modification en BDD\n'
                '   Ajoute --apply pour appliquer les corrections.\n'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '⚠️  MODE CORRECTION — les questions vont être modifiées en BDD\n'
            ))

        # Récupérer toutes les questions fill_blank
        questions = ReadingQuestion.objects.filter(type='fill_blank')
        total = questions.count()
        self.stdout.write(f'📋 {total} question(s) fill_blank trouvée(s)\n')

        fixed = 0
        already_ok = 0

        for q in questions:
            corrected_text, was_modified = sanitize_fill_blank_question(q.question, q.answer)

            if not was_modified:
                already_ok += 1
                continue

            # Afficher ce qui va changer
            self.stdout.write(
                f'\n  ID {q.id} :\n'
                f'    AVANT  : {q.question}\n'
                f'    APRÈS  : {corrected_text}\n'
                f'    RÉPONSE: {q.answer}'
            )

            if apply:
                q.question = corrected_text
                q.save(update_fields=['question'])

            fixed += 1

        # Résumé final
        self.stdout.write('\n' + '─' * 50)
        self.stdout.write(f'✅ Déjà correctes  : {already_ok}')
        self.stdout.write(f'🔧 À corriger      : {fixed}')

        if apply:
            self.stdout.write(self.style.SUCCESS(
                f'\n✔ {fixed} question(s) corrigée(s) dans la BDD avec succès.'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'\n→ Lance avec --apply pour corriger ces {fixed} question(s).'
            ))