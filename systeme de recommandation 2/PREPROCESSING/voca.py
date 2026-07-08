"""
Processing cefrj-vocabulary-profile-1.5.csv

"""

import pandas as pd
import numpy as np
import re

CEFR_ORDER = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

# ─────────────────────────────────────────
# 1. CHARGEMENT — détection automatique
# ─────────────────────────────────────────
def load(filepath):
    print("="*50)
    print("ÉTAPE 1 — Chargement du fichier")
    print("="*50)

    # Essai avec virgule
    df = pd.read_csv(filepath, sep=',', encoding='utf-8')

    # Si une seule colonne → essayer tabulation
    if len(df.columns) == 1:
        df = pd.read_csv(filepath, sep='\t', encoding='utf-8')

    # Si toujours une seule colonne → séparer manuellement
    if len(df.columns) == 1:
        col = df.columns[0]
        parts = col.split(',')
        df = pd.read_csv(filepath, sep=',', encoding='utf-8',
                         names=parts, skiprows=1)

    # Nettoyer noms de colonnes
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    print(f"  Lignes chargées : {len(df)}")
    print(f"  Colonnes        : {list(df.columns)}")
    return df

# ─────────────────────────────────────────
# 2. NETTOYAGE DES COLONNES
# ─────────────────────────────────────────
def clean_columns(df):
    print("\n" + "="*50)
    print("ÉTAPE 2 — Nettoyage des colonnes")
    print("="*50)

    # Renommer les colonnes connues
    rename_map = {}
    for col in df.columns:
        c = col.lower().strip()
        if 'headword' in c or (c == 'word'):
            rename_map[col] = 'word'
        elif c == 'pos':
            rename_map[col] = 'pos'
        elif c == 'cefr':
            rename_map[col] = 'cefr'
        elif 'threshold' in c:
            rename_map[col] = 'threshold'
        elif 'core' in c and '1' in c:
            rename_map[col] = 'core_inventory_1'
        elif 'core' in c and '2' in c:
            rename_map[col] = 'core_inventory_2'

    df = df.rename(columns=rename_map)
    print(f"  Colonnes après renommage : {list(df.columns)}")

    # Garder uniquement les colonnes utiles
    useful = [c for c in ['word', 'pos', 'cefr'] if c in df.columns]
    df = df[useful]

    # Nettoyer espaces
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace('nan', np.nan)

    # Supprimer lignes sans mot
    before = len(df)
    df = df.dropna(subset=['word'])
    print(f"  Lignes sans mot supprimées : {before - len(df)}")
    print(f"  Lignes restantes : {len(df)}")
    return df

# ─────────────────────────────────────────
# 3. UNIFORMISATION CEFR
# ─────────────────────────────────────────
def normalize_cefr(df):
    print("\n" + "="*50)
    print("ÉTAPE 3 — Uniformisation des niveaux CEFR")
    print("="*50)

    print(f"  Valeurs CEFR avant : {df['cefr'].dropna().unique()[:10]}")

    def fix_cefr(val):
        if pd.isna(val) or str(val).strip() in ('nan', ''):
            return np.nan
        val = str(val).strip().upper()
        val = re.sub(r'(LEVEL\s*|CEFR\s*)', '', val)
        val = val.replace(' ', '').replace('-', '')
        corrections = {
            'A1': 'A1', 'A2': 'A2',
            'B1': 'B1', 'B2': 'B2',
            'C1': 'C1', 'C2': 'C2',
            'BEGINNER':         'A1',
            'ELEMENTARY':       'A2',
            'INTERMEDIATE':     'B1',
            'UPPERINTERMEDIATE':'B2',
            'ADVANCED':         'C1',
            'UPPERADVANCED':    'C2',
        }
        return corrections.get(val, np.nan)

    df['cefr'] = df['cefr'].apply(fix_cefr)

    invalid = df['cefr'].isna().sum()
    print(f"  Lignes CEFR invalide supprimées : {invalid}")
    df = df.dropna(subset=['cefr'])

    print("\n  Distribution par niveau CEFR :")
    dist = df['cefr'].value_counts()
    for lvl in CEFR_ORDER:
        count = dist.get(lvl, 0)
        bar = '█' * (count // 100)
        print(f"    {lvl} : {count:5d} mots  {bar}")

    return df

# ─────────────────────────────────────────
# 4. NETTOYAGE DES MOTS
# ─────────────────────────────────────────
def clean_words(df):
    print("\n" + "="*50)
    print("ÉTAPE 4 — Nettoyage des mots")
    print("="*50)

    before = len(df)
    df['word'] = df['word'].str.lower()
    df['word'] = df['word'].str.replace(r"[^a-z'\-\s/]", '', regex=True)
    df['word'] = df['word'].str.strip()
    df = df[df['word'].str.len() > 0]

    print(f"  Mots supprimés   : {before - len(df)}")
    print(f"  Mots restants    : {len(df)}")

    for lvl in CEFR_ORDER:
        sample = df[df['cefr'] == lvl]['word'].head(3).tolist()
        print(f"    {lvl} exemple : {sample}")

    return df

# ─────────────────────────────────────────
# 5. SUPPRESSION DES DOUBLONS
# ─────────────────────────────────────────
def remove_duplicates(df):
    print("\n" + "="*50)
    print("ÉTAPE 5 — Suppression des doublons")
    print("="*50)

    before = len(df)
    df = df.drop_duplicates(subset=['word', 'pos', 'cefr'])
    print(f"  Doublons supprimés : {before - len(df)}")

    # Même mot, niveaux différents → garder le plus bas
    df['cefr_index'] = df['cefr'].map({c: i for i, c in enumerate(CEFR_ORDER)})
    before2 = len(df)
    df = df.sort_values('cefr_index')
    df = df.drop_duplicates(subset=['word', 'pos'], keep='first')
    print(f"  Même mot multi-niveaux → niveau le plus bas gardé : {before2 - len(df)}")
    print(f"  Mots uniques finaux : {len(df)}")

    return df

# ─────────────────────────────────────────
# 6. VÉRIFICATION QUALITÉ
# ─────────────────────────────────────────
def quality_check(df):
    print("\n" + "="*50)
    print("ÉTAPE 6 — Vérification qualité")
    print("="*50)

    print(f"  Total mots           : {len(df)}")
    print(f"  Niveaux CEFR         : {sorted(df['cefr'].unique())}")
    print(f"  POS uniques          : {sorted(df['pos'].dropna().unique())}")
    print(f"  Valeurs manquantes   :\n{df[['word','pos','cefr']].isnull().sum()}")

    manquants = [l for l in CEFR_ORDER if l not in df['cefr'].values]
    if manquants:
        print(f"  ATTENTION niveaux manquants : {manquants}")
    else:
        print(f"  Tous les niveaux CEFR présents")

    print("\n  Aperçu final (10 premières lignes) :")
    print(df[['word', 'pos', 'cefr']].head(10).to_string(index=False))

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    import sys
    filepath = r"C:\Users\MECHERI INFORMATIQUE\Desktop\pfe\cefrj-vocabulary-profile-1.5 .csv"

    df = load(filepath)
    df = clean_columns(df)
    df = normalize_cefr(df)
    df = clean_words(df)
    df = remove_duplicates(df)
    quality_check(df)

    out = "vocab_profile_cleaned.csv"
    df[['word', 'pos', 'cefr', 'cefr_index']].to_csv(out, index=False, encoding='utf-8')
    print(f"\n✓ Fichier sauvegardé : {out}")
    print(f"  {len(df)} mots propres ")