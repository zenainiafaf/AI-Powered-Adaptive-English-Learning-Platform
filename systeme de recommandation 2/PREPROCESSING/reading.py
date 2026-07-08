"""
Processing : Newsela Article Corpus
articles_metadata.csv → reading_activities.csv

"""

import pandas as pd
import numpy as np

CEFR_ORDER  = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
CEFR_TO_IDX = {c: i for i, c in enumerate(CEFR_ORDER)}

def grade_to_cefr(grade):
    try:
        g = float(grade)
    except:
        return 'B1'
    if g < 4.0:    return 'A1'
    elif g < 6.0:  return 'A2'
    elif g < 8.0:  return 'B1'
    elif g < 10.0: return 'B2'
    elif g < 12.0: return 'C1'
    else:          return 'C2'

# ─────────────────────────────────────────
# 1. CHARGEMENT — détection automatique
# ─────────────────────────────────────────
def load(filepath):
    print("="*50)
    print("ÉTAPE 1 — Chargement du fichier")
    print("="*50)

    # Détecter le séparateur automatiquement
    with open(filepath, 'r', encoding='utf-8') as f:
        first_line = f.readline()

    if '\t' in first_line:
        sep = '\t'
        print("  Séparateur détecté : tabulation")
    else:
        sep = ','
        print("  Séparateur détecté : virgule")

    df = pd.read_csv(filepath, sep=sep, encoding='utf-8')

    # Si une seule colonne → séparer manuellement
    if len(df.columns) == 1:
        col     = df.columns[0]
        headers = col.split(sep)
        df      = pd.read_csv(filepath, sep=sep,
                              encoding='utf-8',
                              names=headers, skiprows=1)

    df.columns = [c.strip() for c in df.columns]

    print(f"  Lignes chargées : {len(df)}")
    print(f"  Colonnes        : {list(df.columns)}")
    print(f"  Langues         : {df['language'].unique()}")
    print(f"  Grade levels    : {sorted(df['grade_level'].unique())[:10]}")
    return df

# ─────────────────────────────────────────
# 2. NETTOYAGE
# ─────────────────────────────────────────
def clean(df):
    print("\n" + "="*50)
    print("ÉTAPE 2 — Nettoyage")
    print("="*50)

    before = len(df)
    df = df[df['language'] == 'en']
    print(f"  Gardé anglais uniquement : {before - len(df)} lignes supprimées")

    before = len(df)
    df = df.dropna(subset=['slug', 'title', 'grade_level'])
    print(f"  Valeurs manquantes supprimées : {before - len(df)}")

    df['title']       = df['title'].str.strip()
    df['grade_level'] = pd.to_numeric(df['grade_level'], errors='coerce')

    before = len(df)
    df = df.dropna(subset=['grade_level'])
    print(f"  Grade levels invalides supprimés : {before - len(df)}")
    print(f"  Lignes restantes : {len(df)}")
    return df

# ─────────────────────────────────────────
# 3. MAPPING CEFR
# ─────────────────────────────────────────
def map_cefr(df):
    print("\n" + "="*50)
    print("ÉTAPE 3 — Mapping grade_level → CEFR")
    print("="*50)

    print("  Règle de mapping :")
    print("    grade < 4.0  → A1")
    print("    grade < 6.0  → A2")
    print("    grade < 8.0  → B1")
    print("    grade < 10.0 → B2")
    print("    grade < 12.0 → C1")
    print("    grade >= 12  → C2")

    df['cefr']       = df['grade_level'].apply(grade_to_cefr)
    df['cefr_index'] = df['cefr'].map(CEFR_TO_IDX)

    print(f"\n  Distribution par niveau CEFR :")
    dist = df['cefr'].value_counts()
    for lvl in CEFR_ORDER:
        count = dist.get(lvl, 0)
        bar   = '█' * (count // max(1, len(df) // 40))
        print(f"    {lvl} : {count:5d} articles  {bar}")
    return df

# ─────────────────────────────────────────
# 4. CRÉER LES ACTIVITÉS READING
# ─────────────────────────────────────────
def create_activities(df):
    print("\n" + "="*50)
    print("ÉTAPE 4 — Création des activités reading")
    print("="*50)

    activities = []
    for i, (_, row) in enumerate(df.iterrows(), 1):
        activities.append({
            'activity_id':  f"READ_{i:05d}",
            'slug':         str(row['slug']),
            'title':        str(row['title'])[:80],
            'language':     'en',
            'grade_level':  float(row['grade_level']),
            'version':      int(row['version']),
            'filename':     str(row['filename']),
            'cefr':         str(row['cefr']),
            'cefr_index':   int(row['cefr_index']),
            'skill':        'reading',
            'domain':       'news',
            'duration_min': 20,
        })

    result = pd.DataFrame(activities)
    print(f"  {len(result)} activités reading créées")
    return result

# ─────────────────────────────────────────
# 5. SUPPRESSION DES DOUBLONS
# ─────────────────────────────────────────
def remove_duplicates(df):
    print("\n" + "="*50)
    print("ÉTAPE 5 — Suppression des doublons")
    print("="*50)

    before = len(df)
    df = df.drop_duplicates(subset=['slug', 'cefr'])
    print(f"  Doublons supprimés : {before - len(df)}")
    print(f"  Activités uniques  : {len(df)}")
    return df

# ─────────────────────────────────────────
# 6. VÉRIFICATION QUALITÉ
# ─────────────────────────────────────────
def quality_check(df):
    print("\n" + "="*50)
    print("ÉTAPE 6 — Vérification qualité")
    print("="*50)

    print(f"  Total activités reading : {len(df)}")
    print(f"  Niveaux CEFR            : {sorted(df['cefr'].unique())}")
    print(f"  Articles uniques        : {df['slug'].nunique()}")

    manquants = [l for l in CEFR_ORDER if l not in df['cefr'].values]
    if manquants:
        print(f"  ATTENTION niveaux manquants : {manquants}")
    else:
        print(f"  Tous les niveaux CEFR présents")

    print(f"\n  Aperçu (5 premières lignes) :")
    print(df[['activity_id', 'title', 'grade_level',
              'cefr', 'version', 'skill']].head(5).to_string(index=False))

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 \
               else "articles_metadata.csv"

    df         = load(filepath)
    df         = clean(df)
    df         = map_cefr(df)
    activities = create_activities(df)
    activities = remove_duplicates(activities)
    quality_check(activities)

    out = "reading_activities.csv"
    activities.to_csv(out, index=False, encoding='utf-8')
    print(f"\n✓ Fichier sauvegardé : {out}")
    print(f"  {len(activities)} activités reading ")