from django.core.management.base import BaseCommand
from users.models import Question, Niveau, TestAudio


class Command(BaseCommand):
    help = 'Importe toutes les questions du test CEFR (grammar, vocabulary, listening)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprime toutes les questions existantes avant import',
        )

    def handle(self, *args, **options):
        if options['clear']:
            Question.objects.all().delete()
            self.stdout.write(self.style.WARNING('✗ Questions existantes supprimées'))

        # ============================================================
        # STRUCTURE UNIFORME PAR NIVEAU (5 questions chacun) :
        # 2 manual_input + 1 mcq + 2 fill_blank
        # ============================================================

        questions = [

            # ════════════════════════════════════════════════════════
            #  A1 — 2 listening (2 audios) + 1 grammar + 2 vocabulary
            #  Sources: 
            #    Grammar: 1_english-level-test-elementary-a1.pdf
            #    Vocab: English-Vocabulary-Test.pdf (section A2)
            #  Structure: 2 manual_input + 1 mcq + 2 fill_blank
            # ════════════════════════════════════════════════════════

            # --- A1 GRAMMAR (fill_blank depuis 1_english-level-test-elementary-a1.pdf Q35) ---
            {
                'niveau': 'A1', 'categorie': 'grammar', 'type': 'fill_blank',
                'ordre_dans_niveau': 1,
                'enonce': 'The elephant is ___ land animal in the world.',
                'reponse_attendue': 'the biggest',
                'options': ['the bigger', 'the most big', 'biggest', 'the biggest'],
            },

            # --- A1 VOCABULARY (mcq sans trou - English-Vocabulary-Test A2 Q6) ---
            {
                'niveau': 'A1', 'categorie': 'vocabulary', 'type': 'mcq',
                'ordre_dans_niveau': 2,
                'enonce': 'It might rain today, so bring your ___.',
                'reponse_attendue': 'umbrella',
                'options': ['umbrella', 'jewelry', 'entrance', 'telephone'],
            },
            # --- A1 VOCABULARY (manual_input - English-Vocabulary-Test A2 Q8) ---
            {
                'niveau': 'A1', 'categorie': 'vocabulary', 'type': 'manual_input',
                'ordre_dans_niveau': 3,
                'enonce': 'You must have a ___ to drive a car.',
                'reponse_attendue': 'license',
                'options': None,
            },

            # --- A1 LISTENING (Audio 1: Sleep routine - fill_blank) ---
            {
                'niveau': 'A1', 'categorie': 'listening', 'type': 'fill_blank',
                'ordre_dans_niveau': 4,
                'audio_sujet': 'Sleep routine',
                'enonce': 'The speaker usually goes to bed around ___ and wakes up about ___.',
                'reponse_attendue': '12|7',
                'options': ['10pm', '12', '6am','7am'],
            },
            # --- A1 LISTENING (Audio 2: Children hopes - manual_input) ---
            {
                'niveau': 'A1', 'categorie': 'listening', 'type': 'manual_input',
                'ordre_dans_niveau': 5,
                'audio_sujet': 'Children hopes',
                'enonce': 'I hope that my children grow up healthy, that they appreciate all the ways in which they are ___, and that they live lives that are full of ___.',
                'reponse_attendue': 'lucky|joy',
                'options': None,
            },
            # ════════════════════════════════════════════════════════
            #  A2 — 2 listening (2 audios) + 1 grammar + 2 vocabulary
            #  Sources:
            #    Grammar: 3_english-level-test-pre-intermediate-a2.pdf
            #    Vocab: English-Vocabulary-Test.pdf (section A2)
            #  Structure: 2 manual_input + 1 mcq + 2 fill_blank
            # ════════════════════════════════════════════════════════

            # --- A2 GRAMMAR (fill_blank depuis 3_english-level-test-pre-intermediate-a2.pdf Q14) ---
            {
                'niveau': 'A2', 'categorie': 'grammar', 'type': 'fill_blank',
                'ordre_dans_niveau': 1,
                'enonce': 'My father ___ be a builder.',
                'reponse_attendue': 'used to',
                'options': ['used to', 'was', 'use to', 'did use to'],
            },

            # --- A2 VOCABULARY (fill_blank - English-Vocabulary-Test A2 Q1) ---
            {
                'niveau': 'A2', 'categorie': 'vocabulary', 'type': 'fill_blank',
                'ordre_dans_niveau': 2,
                'enonce': 'I can\'t ___ my passport. Have you seen it?',
                'reponse_attendue': 'find',
                'options': ['fill', 'order', 'find', 'offer'],
            },
            # --- A2 VOCABULARY (manual_input - English-Vocabulary-Test A2 Q13) ---
            {
                'niveau': 'A2', 'categorie': 'vocabulary', 'type': 'manual_input',
                'ordre_dans_niveau': 3,
                'enonce': 'If we don\'t ___, we\'ll be late.',
                'reponse_attendue': 'hurry',
                'options': None,
            },

            # --- A2 LISTENING (Audio 1: Technology privacy - manual_input) ---
            {
                'niveau': 'A2', 'categorie': 'listening', 'type': 'manual_input',
                'ordre_dans_niveau': 4,
                'audio_sujet': 'Technology privacy',
                'enonce': 'The speaker worries about technology collecting more ___ about him than needed.',
                'reponse_attendue': 'information',
                'options': None,
            },
            # --- A2 LISTENING (Audio 2: First phone - mcq sans trou) ---
            {
                'niveau': 'A2', 'categorie': 'listening', 'type': 'mcq',
                'ordre_dans_niveau': 5,
                'audio_sujet': 'First phone',
                'enonce': 'Why did her dad give her a phone?',
                'reponse_attendue': 'So she could call him',
                'options': [
                    'To play games',
                    'So she could call him',
                    'For school homework',
                    'To take photos',
                ],
            },
            # ════════════════════════════════════════════════════════
            #  B1 — 2 listening (2 audios) + 2 grammar + 1 vocabulary
            #  Sources:
            #    Grammar: 2_english-level-test-elementary-b1.pdf
            #    Vocab: English-Vocabulary-Test.pdf (section B1)
            #  Structure: 2 manual_input + 1 mcq + 2 fill_blank
            # ════════════════════════════════════════════════════════

            # --- B1 GRAMMAR (fill_blank depuis 2_english-level-test-elementary-b1.pdf Q5) ---
            {
                'niveau': 'B1', 'categorie': 'grammar', 'type': 'fill_blank',
                'ordre_dans_niveau': 1,
                'enonce': 'I ___ do my homework last night.',
                'reponse_attendue': "couldn't",
                'options': ['not could', "didn't can", "couldn't", "can't"],
            },
            # --- B1 GRAMMAR (manual_input depuis 2_english-level-test-elementary-b1.pdf Q14) ---
            {
                'niveau': 'B1', 'categorie': 'grammar', 'type': 'manual_input',
                'ordre_dans_niveau': 2,
                'enonce': 'What ___ do tomorrow?',
                'reponse_attendue': 'are you going to',
                'options': None,
            },

            # --- B1 VOCABULARY (mcq sans trou - English-Vocabulary-Test B1 Q8) ---
            {
                'niveau': 'B1', 'categorie': 'vocabulary', 'type': 'mcq',
                'ordre_dans_niveau': 3,
                'enonce': 'For a company to succeed, good management is ___.',
                'reponse_attendue': 'essential',
                'options': ['tough', 'broad', 'essential', 'affordable'],
            },

            # --- B1 LISTENING (Audio 1: Technology benefits - fill_blank) ---
            {
                'niveau': 'B1', 'categorie': 'listening', 'type': 'fill_blank',
                'ordre_dans_niveau': 4,
                'audio_sujet': 'Technology benefits',
                'enonce': 'The speaker thinks technology is ___. The main risk right now is ___ news.',
                'reponse_attendue': 'amazing|fake',
                'options': ['real','amazing','important','fake'],
            },
            # --- B1 LISTENING (Audio 2: Children wishes - manual_input) ---
            {
                'niveau': 'B1', 'categorie': 'listening', 'type': 'manual_input',
                'ordre_dans_niveau': 5,
                'audio_sujet': 'Children wishes',
                'enonce': 'I wish that my children become ___ citizens and help ___ the community.',
                'reponse_attendue': 'responsible|grow',
                'options': None,
            },

            # ════════════════════════════════════════════════════════
            #  B2 — 2 listening (2 audios) + 2 grammar + 1 vocabulary
            #  Sources:
            #    Grammar: 4_english-level-test-upper-intermediate-b2.pdf
            #    Vocab: English-Vocabulary-Test.pdf (section B2)
            #  Structure: 2 manual_input + 1 mcq + 2 fill_blank
            # ════════════════════════════════════════════════════════

            # --- B2 GRAMMAR (fill_blank depuis 4_english-level-test-upper-intermediate-b2.pdf Q1) ---
            {
                'niveau': 'B2', 'categorie': 'grammar', 'type': 'fill_blank',
                'ordre_dans_niveau': 1,
                'enonce': 'I ___ to be picking Tom up at the station but I\'ve lost my keys.',
                'reponse_attendue': 'am supposed',
                'options': ['am supposed', 'am requested', 'am intended', 'am obliged'],
            },
            # --- B2 GRAMMAR (manual_input depuis 4_english-level-test-upper-intermediate-b2.pdf Q8) ---
            {
                'niveau': 'B2', 'categorie': 'grammar', 'type': 'manual_input',
                'ordre_dans_niveau': 2,
                'enonce': 'It\'s a huge painting. It ___ taken ages to complete.',
                'reponse_attendue': 'must have',
                'options': None,
            },

            # --- B2 VOCABULARY (mcq sans trou - English-Vocabulary-Test B2 Q8) ---
            {
                'niveau': 'B2', 'categorie': 'vocabulary', 'type': 'mcq',
                'ordre_dans_niveau': 3,
                'enonce': 'After ___ the woman\'s health, the doctor told her she was completely healthy.',
                'reponse_attendue': 'assessing',
                'options': ['infecting', 'assessing', 'maintaining', 'alternating'],
            },

            # --- B2 LISTENING (Audio 1: Social policies - manual_input) ---
            {
                'niveau': 'B2', 'categorie': 'listening', 'type': 'manual_input',
                'ordre_dans_niveau': 4,
                'audio_sujet': 'Social policies',
                'enonce': '"skills ___" so that people can move into better paid professions.',
                'reponse_attendue': 'laddering',
                'options': None,
            },
            # --- B2 LISTENING (Audio 2: Farming costs - fill_blank) ---
            {
                'niveau': 'B2', 'categorie': 'listening', 'type': 'fill_blank',
                'ordre_dans_niveau': 5,
                'audio_sujet': 'Farming costs',
                'enonce': 'house ___, farmland ___, equipment, inputs, irrigation costs.',
                'reponse_attendue': 'rent|lease',
                'options': ['rent','purchase', 'lease', 'taxes'],
            },

            # ════════════════════════════════════════════════════════
            #  C1 — 0 listening + 3 grammar + 2 vocabulary
            #  Sources:
            #    Grammar: 7_english-level-test-advanced-c1.pdf
            #    Vocab: English-Vocabulary-Test.pdf (section C1)
            #  Structure: 2 manual_input + 1 mcq + 2 fill_blank
            # ════════════════════════════════════════════════════════

            # --- C1 GRAMMAR (fill_blank depuis 7_english-level-test-advanced-c1.pdf Q1) ---
            {
                'niveau': 'C1', 'categorie': 'grammar', 'type': 'fill_blank',
                'ordre_dans_niveau': 1,
                'enonce': 'People were amazed that the burglary took place in ___ daylight.',
                'reponse_attendue': 'broad',
                'options': ['wide', 'broad', 'large', 'open'],
            },
            # --- C1 GRAMMAR (fill_blank depuis 7_english-level-test-advanced-c1.pdf Q18) ---
            {
                'niveau': 'C1', 'categorie': 'grammar', 'type': 'fill_blank',
                'ordre_dans_niveau': 2,
                'enonce': 'Very rarely ___ here in July.',
                'reponse_attendue': 'does it rain',
                'options': ['it rains', 'does it rain', 'is it raining', 'it is raining'],
            },
            # --- C1 GRAMMAR (manual_input depuis 7_english-level-test-advanced-c1.pdf Q13) ---
            {
                'niveau': 'C1', 'categorie': 'grammar', 'type': 'manual_input',
                'ordre_dans_niveau': 3,
                'enonce': 'Maintaining an accurate balance sheet is essential, ___ business you\'re in.',
                'reponse_attendue': 'whatever',
                'options': None,
            },

            # --- C1 VOCABULARY (mcq sans trou - English-Vocabulary-Test C1 Q1) ---
            {
                'niveau': 'C1', 'categorie': 'vocabulary', 'type': 'mcq',
                'ordre_dans_niveau': 4,
                'enonce': 'That mobile phone company is ___ for having the worst customer service.',
                'reponse_attendue': 'notorious',
                'options': ['trustworthy', 'acclaimed', 'notorious', 'forbidden'],
            },
            # --- C1 VOCABULARY (manual_input - English-Vocabulary-Test C1 Q7) ---
            {
                'niveau': 'C1', 'categorie': 'vocabulary', 'type': 'manual_input',
                'ordre_dans_niveau': 5,
                'enonce': 'Since he had no siblings, Jason was stuck with the ___ of caring for his aging parents.',
                'reponse_attendue': 'burden',
                'options': None,
            },

            # ════════════════════════════════════════════════════════
            #  C2 — 0 listening + 3 grammar + 2 vocabulary
            #  Sources:
            #    Grammar: c2-english-level-test-with-answers-2.pdf
            #    Vocab: English-Vocabulary-Test.pdf (section C2)
            #  Structure: 2 manual_input + 1 mcq + 2 fill_blank
            # ════════════════════════════════════════════════════════

            # --- C2 GRAMMAR (fill_blank depuis c2-english-level-test-with-answers-2.pdf Q1) ---
            {
                'niveau': 'C2', 'categorie': 'grammar', 'type': 'fill_blank',
                'ordre_dans_niveau': 1,
                'enonce': '_____, don\'t tell anybody about our plans for a merger.',
                'reponse_attendue': 'Whatever you do',
                'options': ['However you do', 'What thing you do', 'Whatever you do', 'Whichever to do'],
            },
            # --- C2 GRAMMAR (manual_input depuis c2-english-level-test-with-answers-2.pdf Q12) ---
            {
                'niveau': 'C2', 'categorie': 'grammar', 'type': 'manual_input',
                'ordre_dans_niveau': 2,
                'enonce': '____ for him, we surely would have missed our flight.',
                'reponse_attendue': 'Had we waited any longer',
                'options': None,
            },
            # --- C2 GRAMMAR (fill_blank depuis c2-english-level-test-with-answers-2.pdf Q13) ---
            {
                'niveau': 'C2', 'categorie': 'grammar', 'type': 'fill_blank',
                'ordre_dans_niveau': 3,
                'enonce': 'Matters finally ___ at the office and they fired him.',
                'reponse_attendue': 'came to a head',
                'options': ['hit the roof', 'tore off a strip', 'brought to a boil', 'came to a head'],
            },

            # --- C2 VOCABULARY (mcq sans trou - English-Vocabulary-Test C2 Q4) ---
            {
                'niveau': 'C2', 'categorie': 'vocabulary', 'type': 'mcq',
                'ordre_dans_niveau': 4,
                'enonce': 'Mick\'s interest in skateboarding began to ___ as he got older.',
                'reponse_attendue': 'wane',
                'options': ['bloat', 'wane', 'tweak', 'instil'],
            },
            # --- C2 VOCABULARY (manual_input - English-Vocabulary-Test C2 Q15) ---
            {
                'niveau': 'C2', 'categorie': 'vocabulary', 'type': 'manual_input',
                'ordre_dans_niveau': 5,
                'enonce': 'Earth\'s resources are limited. The planet cannot ___ current rates of consumption.',
                'reponse_attendue': 'sustain',
                'options': None,
            },
        ]

        # ============================================================
        # IMPORT EN BASE
        # ============================================================

        total_created = 0
        total_skipped = 0

        for q in questions:
            try:
                niveau = Niveau.objects.get(id=q['niveau'])
            except Niveau.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"  ✗ Niveau {q['niveau']} introuvable — vérifiez que import_niveaux a été exécuté"
                ))
                continue

            # Résoudre l'audio si la question est de type listening
            audio = None
            audio_sujet = q.pop('audio_sujet', None)
            
            if q['categorie'] == 'listening' and audio_sujet:
                try:
                    audio = TestAudio.objects.get(sujet=audio_sujet)
                except TestAudio.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠ Audio '{audio_sujet}' introuvable — question créée sans audio"
                    ))
                except TestAudio.MultipleObjectsReturned:
                    audio = TestAudio.objects.filter(sujet=audio_sujet).first()
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠ Multiple audios '{audio_sujet}' — premier utilisé"
                    ))

            # Récupérer les valeurs avant de les retirer du dict
            ordre_dans_niveau = q.pop('ordre_dans_niveau')
            options = q.pop('options', None)

            obj, created = Question.objects.get_or_create(
                niveau=niveau,
                categorie=q['categorie'],
                enonce=q['enonce'],
                defaults={
                    'type':               q['type'],
                    'reponse_attendue':   q['reponse_attendue'],
                    'options':            options,
                    'audio':              audio,
                    'ordre_dans_niveau':  ordre_dans_niveau,
                    'points':             1,
                }
            )

            if created:
                total_created += 1
                self.stdout.write(
                    f"  ✓ [{q['niveau']}][{q['categorie']}] {q['enonce'][:55]}..."
                )
            else:
                total_skipped += 1
                self.stdout.write(
                    f"  → déjà existante: [{q['niveau']}] {q['enonce'][:45]}..."
                )

        # ── Résumé ──
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'✓ Import terminé — {total_created} créées, {total_skipped} ignorées'
        ))

        # ── Vérification par niveau ──
        self.stdout.write('')
        self.stdout.write('  Résumé par niveau :')
        for niv in ['A1', 'B1', 'A2', 'B2', 'C1', 'C2']:
            counts_type = {}
            for t in ['manual_input', 'mcq', 'fill_blank']:
                n = Question.objects.filter(niveau_id=niv, type=t).count()
                if n:
                    counts_type[t] = n
            counts_cat = {}
            for cat in ['grammar', 'vocabulary', 'listening']:
                n = Question.objects.filter(niveau_id=niv, categorie=cat).count()
                if n:
                    counts_cat[cat] = n
            total = Question.objects.filter(niveau_id=niv).count()
            detail_type = ', '.join(f'{t}:{n}' for t, n in counts_type.items())
            detail_cat = ', '.join(f'{cat}:{n}' for cat, n in counts_cat.items())
            self.stdout.write(f'    {niv} : {total} questions ({detail_type}) | ({detail_cat})')