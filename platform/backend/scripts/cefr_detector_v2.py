"""
CEFR Level Detector — v2 (dictionnaires JSON réels)
=====================================================
Détermine le niveau CEFR d'un texte audio transcrit
en se basant sur les fichiers word_vocabulary_XX.json.

Usage :
    python scripts/cefr_detector_v2.py

    ou depuis Django :
        from scripts.cefr_detector_v2 import CefrDetector
        detector = CefrDetector(vocab_dir="data/")
        niveau = detector.detect("texte transcrit ici")
"""

import json
import re
from pathlib import Path
from collections import Counter

# (venv) C:\Users\HP\Desktop\platform\backend>python scripts/cefr_detector_v2.py
# ============================================================
# CONFIGURATION - MODIFIE CE CHEMIN SELON TON ENVIRONNEMENT
# ============================================================

# Option 1: Chemin relatif depuis le dossier backend (RECOMMANDÉ)
VOCAB_DIR = "data"  # Le dossier data est dans backend/

# Option 2: Chemin absolu Windows (si Option 1 ne marche pas)
# VOCAB_DIR = r"C:\Users\HP\Desktop\platform\backend\data"

# Option 3: Chemin absolu avec forward slashes
# VOCAB_DIR = "C:/Users/HP/Desktop/platform/backend/data"

FUNCTION_WORDS = {
    'i','me','my','myself','you','your','yours','yourself',
    'he','him','his','himself','she','her','hers','herself',
    'it','its','itself','we','us','our','ours','ourselves',
    'they','them','their','theirs','themselves',
    'a','an','the',
    'is','am','are','was','were','be','been','being',
    'have','has','had','do','does','did','will','would',
    'shall','should','may','might','must','can','could',
    'and','but','or','nor','for','yet','so',
    'because','although','though','while','since',
    'if','unless','that','which','who','whom','whose',
    'when','where','how','why',
    'of','in','on','at','by','for','with','about','to','from',
    'up','out','into','through','during','before','after',
    'above','below','between','among','against','along','around',
    'this','these','those','all','both','each','every','any',
    'some','no','not','more','most','much','many','few','little',
    'very','quite','just','also','too','even','still','already',
    'now','then','here','there','never','always','often','sometimes',
    'um','uh','oh','yeah','okay','like','well','actually',
    'basically','literally','honestly',
}

LEMMA_MAP = {
    'was':'be','were':'be','being':'be','been':'be',
    'had':'have','having':'have','has':'have',
    'went':'go','gone':'go','goes':'go','going':'go',
    'did':'do','done':'do','does':'do','doing':'do',
    'got':'get','gotten':'get','gets':'get','getting':'get',
    'came':'come','comes':'come','coming':'come',
    'took':'take','taken':'take','takes':'take','taking':'take',
    'made':'make','makes':'make','making':'make',
    'knew':'know','known':'know','knows':'know',
    'thought':'think','thinks':'think','thinking':'think',
    'saw':'see','seen':'see','sees':'see','seeing':'see',
    'ran':'run','runs':'run','running':'run',
    'ate':'eat','eaten':'eat','eats':'eat','eating':'eat',
    'drank':'drink','drunk':'drink','drinks':'drink','drinking':'drink',
    'wrote':'write','written':'write','writes':'write','writing':'write',
    'heard':'hear','hears':'hear','hearing':'hear',
    'felt':'feel','feels':'feel','feeling':'feel',
    'told':'tell','tells':'tell','telling':'tell',
    'found':'find','finds':'find','finding':'find',
    'gave':'give','given':'give','gives':'give','giving':'give',
    'brought':'bring','brings':'bring','bringing':'bring',
    'bought':'buy','buys':'buy','buying':'buy',
    'taught':'teach','teaches':'teach','teaching':'teach',
    'kept':'keep','keeps':'keep','keeping':'keep',
    'said':'say','says':'say','saying':'say',
    'left':'leave','leaves':'leave','leaving':'leave',
    'grew':'grow','grown':'grow','grows':'grow','growing':'grow',
    'became':'become','becomes':'become','becoming':'become',
    'began':'begin','begun':'begin','begins':'begin','beginning':'begin',
    'showed':'show','shown':'show','shows':'show','showing':'show',
    'lived':'live','lives':'live','living':'live',
    'used':'use','uses':'use','using':'use',
    'tried':'try','tries':'try','trying':'try',
    'moved':'move','moves':'move','moving':'move',
    'worked':'work','works':'work','working':'work',
    'helped':'help','helps':'help','helping':'help',
    'asked':'ask','asks':'ask','asking':'ask',
    'called':'call','calls':'call','calling':'call',
    'needed':'need','needs':'need','needing':'need',
    'wanted':'want','wants':'want','wanting':'want',
    'looked':'look','looks':'look','looking':'look',
    'started':'start','starts':'start','starting':'start',
    'played':'play','plays':'play','playing':'play',
    'talked':'talk','talks':'talk','talking':'talk',
    'walked':'walk','walks':'walk','walking':'walk',
    'loved':'love','loves':'love','loving':'love',
    'liked':'like','likes':'like','liking':'like',
    'watched':'watch','watches':'watch','watching':'watch',
    'listened':'listen','listens':'listen','listening':'listen',
    'slept':'sleep','sleeps':'sleep','sleeping':'sleep',
    'woke':'wake up','woken':'wake up','wakes':'wake up',
    'cooked':'cook','cooks':'cook','cooking':'cook',
    'clicking':'click','clicked':'click','clicks':'click',
    'swiping':'swipe','swiped':'swipe','swipes':'swipe',
    'deposited':'deposit','depositing':'deposit','deposits':'deposit',
    'provided':'provide','providing':'provide','provides':'provide',
    'worried':'worry','worries':'worry','worrying':'worry',
    'appreciated':'appreciate','appreciating':'appreciate',
    'displaced':'displace','displacing':'displace',
    'characterized':'characterize','characterizing':'characterize',
    'children':'child','feet':'foot','teeth':'tooth',
    'men':'man','women':'woman','mice':'mouse',
    'lives':'life','leaves':'leaf',
    'better':'good','best':'good','worse':'bad','worst':'bad',
    'bigger':'big','biggest':'big','smaller':'small',
    'older':'old','younger':'young','faster':'fast',
    'higher':'high','lower':'low','taller':'tall',
    'happier':'happy','easier':'easy','harder':'hard',
    'leaders':'leader','citizens':'citizen','classrooms':'classroom',
    'policies':'policy','professions':'profession',
    'ethnicities':'ethnicity','identities':'identity',
    'orientations':'orientation','genders':'gender',
    'amendments':'amendment','classes':'class',
    'benefits':'benefit','risks':'risk','images':'image','roles':'role',
    'papers':'paper','books':'book','journals':'journal',
    'potatoes':'potato','tomatoes':'tomato','libraries':'library',
    'ipads':'ipad','smartphones':'smartphone',
    'laddering':'ladder','systemically':'systematic',
    'thoughtful':'thought','paid':'pay',
    'gonna':'go','gotta':'have','wanna':'want',
    "im":'be',"theyve":'have',"ive":'have',
    "dont":'do',"doesnt":'do',"didnt":'do',
    "cant":'can',"wont":'will',"isnt":'be',
    "arent":'be',"wasnt":'be',"werent":'be',
}


def lemmatize(word):
    word = word.lower().strip("'''\"-.,")
    if word in LEMMA_MAP:
        return LEMMA_MAP[word]
    if word.endswith('ing') and len(word) > 5:
        return word[:-3]
    if word.endswith('ed') and len(word) > 4:
        return word[:-2]
    if word.endswith('ly') and len(word) > 4:
        return word[:-2]
    if word.endswith('ies') and len(word) > 5:
        return word[:-3] + 'y'
    if word.endswith('es') and len(word) > 4:
        return word[:-2]
    if word.endswith('s') and len(word) > 3:
        return word[:-1]
    if word.endswith('er') and len(word) > 4:
        return word[:-2]
    if word.endswith('est') and len(word) > 5:
        return word[:-3]
    return word


def tokenize(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s']", ' ', text)
    return [w.strip("'") for w in text.split() if len(w) > 1]


class CefrDetector:
    ORDRE = ['A1', 'A2', 'B1', 'B2', 'C1']
    LEVEL_SCORE = {'A1': 1, 'A2': 2, 'B1': 3, 'B2': 4, 'C1': 5, 'C2+': 6}

    def __init__(self, vocab_dir="."):
        self.dicts = self._load(vocab_dir)

    def _load(self, vocab_dir):
        files = {
            'A1': 'word_vocabulary_a1.json',
            'A2': 'word_vocabulary_a2.json',
            'B1': 'word_vocabulary_b1.json',
            'B2': 'word_vocabulary_b2.json',
            'C1': 'word_vocabulary_c1.json',
        }
        dicts = {}
        for level, filename in files.items():
            path = Path(vocab_dir) / filename
            print(f"  Chargement: {path.absolute()}")
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            words = list(data.values())[0]
            dicts[level] = set(w.lower().strip() for w in words)
        return dicts

    def _get_level(self, word):
        for lvl in self.ORDRE:
            if word in self.dicts[lvl]:
                return lvl
        return 'C2+'

    def detect(self, text, verbose=False):
        words = tokenize(text)
        content_words = []
        for w in words:
            if w in FUNCTION_WORDS:
                continue
            lemma = lemmatize(w)
            if lemma and len(lemma) > 2 and lemma not in FUNCTION_WORDS:
                content_words.append(lemma)

        if not content_words:
            return 'A1'

        word_levels  = [self._get_level(w) for w in content_words]
        level_counts = Counter(word_levels)
        total        = len(word_levels)
        scores_num   = [self.LEVEL_SCORE[l] for l in word_levels]
        avg_score    = sum(scores_num) / len(scores_num)
        pct = {lvl: round(level_counts.get(lvl, 0) / total * 100, 1)
               for lvl in self.ORDRE + ['C2+']}

        # Niveau basé sur score moyen
        if avg_score <= 1.8:    niveau = 'A1'
        elif avg_score <= 2.5:  niveau = 'A2'
        elif avg_score <= 3.3:  niveau = 'B1'
        elif avg_score <= 4.1:  niveau = 'B2'
        elif avg_score <= 4.9:  niveau = 'C1'
        else:                   niveau = 'C2'

        # Ajustement si > 30% mots C2+
        if pct['C2+'] > 30:
            upgrade = {'A1':'B1','A2':'B1','B1':'B2','B2':'C1','C1':'C2'}
            niveau = upgrade.get(niveau, niveau)

        if verbose:
            self._print_report(content_words, level_counts, avg_score, pct, niveau)

        return niveau

    def _print_report(self, content_words, level_counts, avg_score, pct, niveau):
        total = len(content_words)
        print("=" * 55)
        print(f"  Niveau détecté          : {niveau}")
        print(f"  Mots de contenu         : {total}")
        print(f"  Score moyen pondéré     : {avg_score:.2f} / 6.0")
        print("=" * 55)
        print("  Répartition :")
        for lvl in self.ORDRE + ['C2+']:
            n   = level_counts.get(lvl, 0)
            bar = "█" * int(pct[lvl] / 5)
            print(f"    {lvl:<4} {pct[lvl]:5.1f}%  {bar}  ({n} mots)")
        c2_words = [w for w in set(content_words) if self._get_level(w) == 'C2+']
        if c2_words:
            print(f"\n  Mots C2+ : {', '.join(c2_words)}")
        print()


if __name__ == "__main__":

    # Vérifier le chemin actuel
    print(f"\nDossier courant: {Path.cwd()}")
    print(f"VOCAB_DIR: {VOCAB_DIR}")
    print(f"Chemin absolu: {Path(VOCAB_DIR).absolute()}")
    print()

    print("\nChargement des dictionnaires...")
    detector = CefrDetector(vocab_dir=VOCAB_DIR)
    for lvl, words in detector.dicts.items():
        print(f"  {lvl} : {len(words):,} mots")
    print()

    audios = {
        "15 — Technology privacy":     "I worry about any technology that is collecting more information about me that it needs to provide the service that im currently using. and I worry about technology that use Ops people from creative roles.",
        "11 — Technology benefits":    "I think technology is amazing. um, I think the benefit spring so much to people and connecting folks. uh, information, um, A. A lot of things. uh, really, the risks are, I think right now, uh, fake news and media and fake images from artificial intelligence.",
        "audio.wav — Farming costs":   "out. nepua. you have 2 minutes. and your question is completely different given what it costs for the average farmer to rent a house, lease farm land, paper, equipment, paper, imported amendments and inputs, irrigation cost, etc. in other words.",
        "71660 — Sleep routine":       "I think I usually get a decent amount of sleep. usually go to bed around wake about 7. so about 7 hours. still well short of recommended 7 of 8 hours, but not too bad.",
        "22017 — Children wishes":     "I wish that might grow up. grow up propiling and become responsible citizings and also study hard and help other people and rule the community and become big leaders in the future.",
        "138 — Priest professor":      "what I do for a living is that im a priest. im also a university professor. so I used knowledge mainly to write things. I write service, I write papers, I write books. and I can also use computer to go the internet to find information. when I was a university, I to go to the library to get a physical book, get look at physical journals. but now that I can use a computer, I can just look stuff. thats why I used for most often I can see, but not twenty seven, twenty eight seconds. I can stop.",
        "19 — Social policies":        "we can have strong wealthy policies, strong education access. we can think about job creations systemically as a society and also skills lathering so that people can move into better paid professions the more they work at something. uh, we can also be very thoughtful about how we characterize and talk about people of different ethnicities, classes, genders, orientations, identities, etc.",
        "18 — First phone":            "I got my first phone when I was 10 because my dad was out a lot are working his single dance. and so he got me a phone so that I could cool him if I need to. with me a my little brother were home a learn or working home for school.",
        "553 — iPads in class":        "I think we could have more iPads in classrooms so that children from a younger age could get used to clicking on things, swiping things and using a screen for that education.",
        "2069 — Children hopes":       "I hope that my children grow up healthy. that they appreciate all the ways in which they are lucky. and that they live lives that a full of joy. I also really hope that they take what theyve been given seriously and work very hard.",
        "4157 — Ideal vacation":       "my ideal vacation is to Malasia because it is very warm here every day so I can go swimming with my children. and I really like the food. its much better than English food which is all made of potatoes.",
        "20349 — Banks":               "I think that banks keep your money safe by having a system where its ensured once its deposited. but also that when you do deposit your money into the bank. its tracked so people know where its gone and you know how much there is or when you can check it online.",
    }

    print("=" * 55)
    print("  RÉSULTATS — DÉTECTION CEFR PAR AUDIO")
    print("=" * 55)

    for name, text in audios.items():
        niveau = detector.detect(text, verbose=False)
        print(f"  {name:<35} →  {niveau}")

    print()
    print("─" * 55)
    print()

    # Rapports détaillés
    for name in ["19 — Social policies", "71660 — Sleep routine", "15 — Technology privacy"]:
        print(f"--- Rapport : {name} ---")
        detector.detect(audios[name], verbose=True)