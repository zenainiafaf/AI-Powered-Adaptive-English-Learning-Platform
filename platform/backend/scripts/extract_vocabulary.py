#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'extraction de vocabulaire anglais par niveau CEFR
À partir des PDF Langeek (A1, A2, B1, B2, C1)

Usage:
    python extract_vocabulary.py --input A1.pdf --level A1 --output vocab.json
    python extract_vocabulary.py --input-dir ./pdfs/ --output vocab_complete.json
"""

import re
import json
import argparse
from pathlib import Path


def extract_words_from_langeek_pdf(text_content, level="A1"):
    """
    Extrait les mots anglais du contenu texte d'un PDF Langeek.
    Version corrigée - capture tous les mots y compris 'hello', 'hi', 'bye'

    Args:
        text_content: Contenu texte extrait du PDF
        level: Niveau CEFR (A1, A2, B1, B2, C1)

    Returns:
        Liste des mots extraits
    """
    words = []
    seen = set()
    lines = text_content.split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('Langeek') or 'Wordlist' in line:
            continue

        # Pattern: "Numéro Mot (partie_discours.)"
        # Capture: 1 Hello (intj.) → hello
        # Capture: 5 Good morning (intj.) → good morning
        match = re.match(r'^\d+\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,3})\s*\([a-z]+\.\)', line)
        if match:
            word = match.group(1).strip().lower()
            # Nettoyer les espaces multiples
            word = ' '.join(word.split())
            if word and len(word) > 1 and word not in seen:
                words.append(word)
                seen.add(word)

    return words


def process_single_pdf(pdf_path, level):
    """
    Traite un seul fichier PDF et retourne la liste des mots.

    Nécessite pdfplumber pour l'extraction de texte.
    """
    try:
        import pdfplumber
    except ImportError:
        print("❌ Erreur: pdfplumber n'est pas installé.")
        print("   Installez-le avec: pip install pdfplumber")
        return []

    words = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    page_words = extract_words_from_langeek_pdf(text, level)
                    words.extend(page_words)
    except Exception as e:
        print(f"❌ Erreur lors de la lecture de {pdf_path}: {e}")
        return []

    return words


def process_multiple_pdfs(pdf_dir):
    """
    Traite plusieurs PDF dans un répertoire.
    Attend des fichiers nommés: A1.pdf, A2.pdf, B1.pdf, etc.
    """
    vocabulary = {
        "A1": [],
        "A2": [],
        "B1": [],
        "B2": [],
        "C1": []
    }

    pdf_path = Path(pdf_dir)

    for level in vocabulary.keys():
        # Chercher le fichier PDF pour ce niveau
        pdf_file = pdf_path / f"{level}.pdf"

        if pdf_file.exists():
            print(f"📖 Traitement de {level}.pdf...")
            words = process_single_pdf(str(pdf_file), level)
            vocabulary[level] = words
            print(f"   ✅ {len(words)} mots extraits")
        else:
            print(f"⚠️  Fichier {level}.pdf non trouvé dans {pdf_dir}")

    return vocabulary


def main():
    parser = argparse.ArgumentParser(
        description="Extrait le vocabulaire anglais des PDF Langeek"
    )
    parser.add_argument(
        "--input", "-i",
        help="Chemin vers un fichier PDF unique"
    )
    parser.add_argument(
        "--level", "-l",
        choices=["A1", "A2", "B1", "B2", "C1"],
        default="A1",
        help="Niveau CEFR du PDF (défaut: A1)"
    )
    parser.add_argument(
        "--input-dir", "-d",
        help="Répertoire contenant les PDF (A1.pdf, A2.pdf, etc.)"
    )
    parser.add_argument(
        "--output", "-o",
        default="english_vocabulary.json",
        help="Fichier de sortie JSON (défaut: english_vocabulary.json)"
    )

    args = parser.parse_args()

    # Vérifier les arguments
    if not args.input and not args.input_dir:
        parser.print_help()
        print("\n❌ Erreur: Spécifiez --input ou --input-dir")
        return

    # Traitement
    if args.input_dir:
        print(f"\n📂 Traitement du répertoire: {args.input_dir}")
        vocabulary = process_multiple_pdfs(args.input_dir)
    else:
        print(f"\n📄 Traitement du fichier: {args.input}")
        words = process_single_pdf(args.input, args.level)
        vocabulary = {
            "A1": [],
            "A2": [],
            "B1": [],
            "B2": [],
            "C1": []
        }
        vocabulary[args.level] = words

    # Sauvegarder
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(vocabulary, f, indent=2, ensure_ascii=False)

    # Résumé
    print(f"\n📊 Résumé:")
    total = 0
    for level, words in vocabulary.items():
        count = len(words)
        total += count
        print(f"   {level}: {count} mots")
    print(f"\n✅ Total: {total} mots")
    print(f"💾 Sauvegardé dans: {args.output}")


if __name__ == "__main__":
    main()
