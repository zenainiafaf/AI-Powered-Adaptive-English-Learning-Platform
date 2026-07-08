"""
Processing : English Grammar Profile Online.xlsx
Nettoyage + uniformisation pour HIER-GNN
"""

import pandas as pd
import numpy as np
import re

CEFR_ORDER = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
CEFR_TO_IDX = {c: i for i, c in enumerate(CEFR_ORDER)}

# ─────────────────────────────────────────
# 1. CHARGEMENT
# ─────────────────────────────────────────
def load(filepath):
    print("="*50)
    print("ÉTAPE 1 — Chargement du fichier")
    print("="*50)

    df = pd.read_excel(filepath, engine='openpyxl')
    df.columns = [str(c).strip() for c in df.columns]

    print(f"  Lignes chargées : {len(df)}")
    print(f"  Colonnes        : {list(df.columns)}")
    print(f"  Valeurs manquantes :\n{df.isnull().sum()}")
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
        if c == 'id':
            rename_map[col] = 'id'
        elif 'supercategory' in c or 'super_category' in c:
            rename_map[col] = 'super_category'
        elif 'subcategory' in c or 'sub_category' in c:
            rename_map[col] = 'sub_category'
        elif c == 'level':
            rename_map[col] = 'cefr'
        elif 'lexical' in c:
            rename_map[col] = 'lexical_range'
        elif 'guideword' in c:
            rename_map[col] = 'guideword'
        elif 'can-do' in c or 'cando' in c or 'statement' in c:
            rename_map[col] = 'can_do'
        elif 'example' in c:
            rename_map[col] = 'example'

    df = df.rename(columns=rename_map)
    print(f"  Colonnes renommées : {list(df.columns)}")

    # Garder colonnes utiles
    useful = [c for c in ['id', 'super_category', 'sub_category',
                           'cefr', 'lexical_range', 'guideword',
                           'can_do', 'example'] if c in df.columns]
    df = df[useful]

    # Nettoyer espaces
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace('nan', np.nan)

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
            'BEGINNER':          'A1',
            'ELEMENTARY':        'A2',
            'INTERMEDIATE':      'B1',
            'UPPERINTERMEDIATE': 'B2',
            'ADVANCED':          'C1',
            'UPPERADVANCED':     'C2',
        }
        return corrections.get(val, np.nan)

    df['cefr'] = df['cefr'].apply(fix_cefr)
    df['cefr_index'] = df['cefr'].map(CEFR_TO_IDX)

    invalid = df['cefr'].isna().sum()
    print(f"  Lignes CEFR invalide supprimées : {invalid}")
    df = df.dropna(subset=['cefr'])

    print("\n  Distribution par niveau CEFR :")
    dist = df['cefr'].value_counts()
    for lvl in CEFR_ORDER:
        count = dist.get(lvl, 0)
        bar = '█' * (count // 20)
        print(f"    {lvl} : {count:5d} structures  {bar}")

    return df

# ─────────────────────────────────────────
# 4. NETTOYAGE DES CATÉGORIES
# ─────────────────────────────────────────
def clean_categories(df):
    print("\n" + "="*50)
    print("ÉTAPE 4 — Nettoyage des catégories grammaticales")
    print("="*50)

    if 'super_category' in df.columns:
        df['super_category'] = df['super_category'].str.upper().str.strip()
        print(f"  Catégories principales : {df['super_category'].dropna().unique()[:10]}")

    if 'sub_category' in df.columns:
        df['sub_category'] = df['sub_category'].str.lower().str.strip()

    if 'can_do' in df.columns:
        # Nettoyer les can-do statements
        df['can_do'] = df['can_do'].str.replace(r'\s+', ' ', regex=True)
        df['can_do'] = df['can_do'].str.strip()

    if 'example' in df.columns:
        # Garder seulement le premier exemple
        df['example_clean'] = df['example'].apply(
            lambda x: str(x).split('(')[0].strip() if pd.notna(x) else np.nan
        )

    print(f"  Lignes restantes : {len(df)}")
    return df

# ─────────────────────────────────────────
# 5. SUPPRESSION DES DOUBLONS
# ─────────────────────────────────────────
def remove_duplicates(df):
    print("\n" + "="*50)
    print("ÉTAPE 5 — Suppression des doublons")
    print("="*50)

    before = len(df)
    subset = [c for c in ['super_category', 'sub_category',
                           'cefr', 'guideword'] if c in df.columns]
    df = df.drop_duplicates(subset=subset)
    print(f"  Doublons supprimés : {before - len(df)}")
    print(f"  Structures uniques : {len(df)}")
    return df

# ─────────────────────────────────────────
# 6. VÉRIFICATION QUALITÉ
# ─────────────────────────────────────────
def quality_check(df):
    print("\n" + "="*50)
    print("ÉTAPE 6 — Vérification qualité")
    print("="*50)

    print(f"  Total structures grammaticales : {len(df)}")
    print(f"  Niveaux CEFR                   : {sorted(df['cefr'].unique())}")

    if 'super_category' in df.columns:
        print(f"\n  Distribution par catégorie grammaticale :")
        cats = df['super_category'].value_counts().head(10)
        for cat, count in cats.items():
            print(f"    {cat:<25} : {count:4d}")

    manquants = [l for l in CEFR_ORDER if l not in df['cefr'].values]
    if manquants:
        print(f"\n  ATTENTION niveaux manquants : {manquants}")
    else:
        print(f"\n  Tous les niveaux CEFR présents")

    print("\n  Aperçu final (5 premières lignes) :")
    cols_show = [c for c in ['super_category', 'sub_category',
                              'cefr', 'guideword', 'can_do'] if c in df.columns]
    print(df[cols_show].head(5).to_string(index=False))

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    import sys
    filepath = r"C:\Users\MECHERI INFORMATIQUE\Desktop\pfe\English Grammar Profile Online.xlsx"

    df = load(filepath)
    df = clean_columns(df)
    df = normalize_cefr(df)
    df = clean_categories(df)
    df = remove_duplicates(df)
    quality_check(df)

    out = "grammar_profile_cleaned.csv"
    df.to_csv(out, index=False, encoding='utf-8')
    print(f"\n✓ Fichier sauvegardé : {out}")
    print(f"  {len(df)} structures grammaticales ")