from django.core.management.base import BaseCommand
from users.models import TestAudio, Niveau


class Command(BaseCommand):
    help = 'Importe les audios pour le test CEFR - Peut être exécuté plusieurs fois'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprime tous les audios existants avant import',
        )

    def handle(self, *args, **options):
        if options['clear']:
            TestAudio.objects.all().delete()
            self.stdout.write(self.style.WARNING('✗ Audios existants supprimés'))

        # Les 8 audios actuels (2 par niveau A1-B2)
        audios = [
            # A1
            ('spontaneous-speech-en-71660.mp3', 'A1', 'Sleep routine', 
             'I think I usually get a decent amount of sleep. I usually go to bed around 12 and wake up at 7, so about seven hours. It''s still well short of the recommended seven and a half or eight hours, but not too bad.'),


            ('spontaneous-speech-en-2069.mp3', 'A1', 'Children hopes', 
             'I hope that my children grow up healthy, that they appreciate all the ways in which they are lucky, and that they live lives that are full of joy. I also really hope that they take what they''ve been given seriously and work very hard.'),
           
           
            # A2
            ('spontaneous-speech-en-15.mp3', 'A2', 'Technology privacy', 
             'I worry about any technology that is collecting more information about me than it needs to provide the service that I''m currently using, and I worry about technology that usurps people from creative roles.'),


            ('spontaneous-speech-en-18.mp3', 'A2', 'First phone', 
             'I got my first phone when I was ten because my dad was out a lot working—he was a single dad. And so he got me a phone so that I could call him if I needed to, and me and my little brother were home alone or walking home from school alone.'),
          
           
            # B1
            ('spontaneous-speech-en-11.mp3', 'B1', 'Technology benefits', 
             'I think technology is amazing. I think the benefits bring so much to people in connecting folks, information, a lot of things. Really, the risks are, I think right now, fake news and media, and fake images from Artificial Intelligence.'),

            ('spontaneous-speech-en-22017.mp3', 'B1', 'Children wishes', 
             'I wish that my children grow up, grow up properly and become responsible citizens, and also study hard, help other people and grow the community and become better leaders in the future.'),
          
          
            # B2
            ('spontaneous-speech-en-19.mp3', 'B2', 'Social policies', 
             'We can have strong welfare policies, strong education access, we can think about job creation systemically as a society and also skills laddering so that people can move into better paid professions the more they work at something. We can also be very thoughtful about how we characterize and talk about people of different ethnicities, classes, gender, orientations, identities, etc..'),


            ('audio.wav', 'B2', 'Farming costs', 
             'Napua, you have two minutes, and your question is completely different. Given what it costs for the average farmer to rent a house, lease farmland, pay for equipment, pay for imported amendments and inputs, irrigation costs, etc. In other words.'),
        ]

        for fichier, niveau_id, sujet, transcription in audios:
            try:
                niveau = Niveau.objects.get(id=niveau_id)
                obj, created = TestAudio.objects.get_or_create(
                    fichier=fichier,
                    defaults={
                        'niveau_detecte': niveau,
                        'sujet': sujet,
                        'transcription': transcription,
                    }
                )
                if created:
                    self.stdout.write(f'  ✓ Importé: {fichier} ({niveau_id})')
                else:
                    self.stdout.write(f'  → Mis à jour: {fichier}')
            except Niveau.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  ✗ Niveau {niveau_id} inexistant'))

        self.stdout.write(self.style.SUCCESS('✓ Import audios terminé'))