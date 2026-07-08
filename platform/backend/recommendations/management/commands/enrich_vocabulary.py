import os
import time
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from recommendations.models import VocabularyItem
from groq import Groq

client_def = Groq(api_key=os.environ.get('GROQ_API_KEY_1'))
client_syn = Groq(api_key=os.environ.get('GROQ_API_KEY_2'))
client_ex  = Groq(api_key=os.environ.get('GROQ_API_KEY_3'))

def ask_groq(client, prompt):
    try:
        response = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=100,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f'    ⚠️  Groq error: {e}')
        return ''

def enrich_word(word):
    """Fait les 3 appels Groq en parallèle pour un mot"""

    prompt_def = (
        f'Define the English word "{word.headword}" ({word.pos}) in exactly 1 short sentence of max 15 words. '
        f'Return only the definition sentence, no extra text.'
    )
    prompt_syn = (
        f'Give exactly 1 synonym of the English word "{word.headword}" ({word.pos}). '
        f'If the word has no real synonym (like "am", "a", "the", "I"), return only: _'
        f'Return ONLY 1 word or _, nothing else.'
    )
    prompt_ex = (
        f'Write exactly 1 grammatically correct English sentence using "{word.headword}" as a {word.pos}. '
        f'The word must be used correctly with proper conjugation. '
        f'For "am": "I am very happy today." — For "a": "I have a red car." '
        f'Return ONLY the sentence, nothing else.'
    )

    with ThreadPoolExecutor(max_workers=3) as executor:
        f_def = executor.submit(ask_groq, client_def, prompt_def)
        f_syn = executor.submit(ask_groq, client_syn, prompt_syn)
        f_ex  = executor.submit(ask_groq, client_ex,  prompt_ex)
        definition = f_def.result()
        synonym    = f_syn.result()
        example    = f_ex.result()

    return definition, synonym, example


class Command(BaseCommand):
    help = 'Enrichit le vocabulaire avec définition, synonyme et exemple via Groq'

    def add_arguments(self, parser):
        parser.add_argument('--start', type=int, default=0)
        parser.add_argument('--limit', type=int, default=None)

    def handle(self, *args, **options):
        start = options['start']
        limit = options['limit']

        qs = VocabularyItem.objects.filter(definition='').order_by('id')[start:]
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f'📚 {total} mots à enrichir...')

        for i, word in enumerate(qs):
            self.stdout.write(f'[{i+1}/{total}] {word.headword} ({word.cefr})')

            definition, synonym, example = enrich_word(word)

            word.definition = definition
            word.synonym    = synonym
            word.example    = example
            word.save()

            self.stdout.write(
                f'    ✅ def: {definition[:50]}...\n'
                f'    ✅ syn: {synonym}\n'
                f'    ✅ ex:  {example[:60]}...'
            )

            time.sleep(4)

        self.stdout.write(self.style.SUCCESS(f'\n✅ Terminé ! {total} mots traités.'))