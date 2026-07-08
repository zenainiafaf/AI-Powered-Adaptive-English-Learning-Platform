import os
import pandas as pd
from django.core.management.base import BaseCommand
from recommendations.models import VocabularyItem, GrammarRule, ReadingContent, TaskContent

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))


class Command(BaseCommand):
    help = 'Importe les 4 CSV dans la base de données'

    def handle(self, *args, **kwargs):
        self.import_vocabulary()
        self.import_grammar()
        self.import_reading()
        self.import_tasks()
        self.stdout.write(self.style.SUCCESS('✅ Import terminé !'))

    def import_vocabulary(self):                                          # ← indenté
        self.stdout.write('📥 Import vocabulary...')
        VocabularyItem.objects.all().delete()
        df = pd.read_csv(os.path.join(DATA_DIR,'recommandation','vocabulary_cleaned.csv'), encoding='latin1')
        objects = [
            VocabularyItem(
                vocab_id=str(row['vocab_id']),
                headword=str(row['headword']),
                pos=str(row.get('pos', '')),
                cefr=str(row['CEFR'])[:2],
                label=str(row.get('label', '')),
                model_idx=int(idx),
            )
            for idx, row in df.iterrows()
        ]
        VocabularyItem.objects.bulk_create(objects, ignore_conflicts=True)
        self.stdout.write(f'   → {len(objects)} mots importés')

    def import_grammar(self):                                             # ← indenté
        self.stdout.write('📥 Import grammar...')
        GrammarRule.objects.all().delete()
        df = pd.read_csv(os.path.join(DATA_DIR,'recommandation','grammar_profile_cleaned.csv'), encoding='latin1')
        objects = [
            GrammarRule(
                grammar_id=str(row['id']),
                super_category=str(row.get('super_category', '')),
                sub_category=str(row.get('sub_category', '')),
                cefr=str(row['cefr'])[:2],
                guideword=str(row.get('guideword', '')),
                can_do=str(row.get('can_do', '')),
                example=str(row.get('example_clean', '')),
                model_idx=int(idx),
            )
            for idx, row in df.iterrows()
        ]
        GrammarRule.objects.bulk_create(objects, ignore_conflicts=True)
        self.stdout.write(f'   → {len(objects)} règles importées')

    def import_reading(self):                                             # ← indenté
        self.stdout.write('📥 Import reading...')
        ReadingContent.objects.all().delete()
        df = pd.read_csv(os.path.join(DATA_DIR,'recommandation','newsela_final.csv'), encoding='latin1')
        objects = [
            ReadingContent(
                reading_id=str(row['reading_id']),
                slug=str(row.get('slug', '')),
                title=str(row['title']),
                cefr=str(row['cefr'])[:2],
                grade_level=float(row['grade_level']) if pd.notna(row.get('grade_level')) else None,
                version=int(row.get('version', 0)),
                text=str(row['text']),
                text_length=int(row.get('text_length', 0)),
                word_count=int(row.get('word_count', 0)),
                model_idx=int(idx),
            )
            for idx, row in df.iterrows()
        ]
        for i in range(0, len(objects), 500):
            ReadingContent.objects.bulk_create(objects[i:i+500], ignore_conflicts=True)
        self.stdout.write(f'   → {len(objects)} textes importés')

    def import_tasks(self):                                               # ← indenté
        self.stdout.write('📥 Import tasks...')
        TaskContent.objects.all().delete()
        df = pd.read_csv(os.path.join(DATA_DIR,'recommandation','EFwrittenTasks_cleaned.csv'), encoding='latin1')
        objects = [
            TaskContent(
                level_number=int(row['levelNumber']),
                level=str(row['level']),
                unit=int(row['unit']),
                title=str(row['title']),
                topic=str(row['topic']),
                cefr=str(row['cefr'])[:2],
                written_task=str(row['writtenTask']),
                model_idx=int(idx),
            )
            for idx, row in df.iterrows()
        ]
        TaskContent.objects.bulk_create(objects, ignore_conflicts=True)
        self.stdout.write(f'   → {len(objects)} tâches importées')