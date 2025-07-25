#!/usr/bin/env python3
# File: main.py

import argparse
import shutil
import os
from learn_simulator import LearnSimulator

def main():
    # Check if deck.csv exists, if not copy from bpm.csv
    deck_path = os.path.join("practice_decks", "deck.csv")
    template_path = os.path.join("vocabulary_template", "bpm.csv")
    
    if not os.path.exists(deck_path):
        if os.path.exists(template_path):
            shutil.copy2(template_path, deck_path)
            print("Created deck.csv from bpm.csv template")
        else:
            print("Error: bpm.csv template file not found!")
            exit(1)
    
    # Always work with deck.csv
    sim = LearnSimulator.load_deck(deck_path)
    sim.study_session()
    print(f"\nDeck saved to {deck_path}")

if __name__ == '__main__':
    main()
