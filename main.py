#!/usr/bin/env python3
# File: main.py

import argparse
import shutil
import os
from learn_simulator import LearnSimulator

def main():
    # Check if deck.csv exists, if not copy from bpm.csv
    if not os.path.exists("deck.csv"):
        if os.path.exists("bpm.csv"):
            shutil.copy2("bpm.csv", "deck.csv")
            print("Created deck.csv from bpm.csv template")
        else:
            print("Error: bpm.csv template file not found!")
            exit(1)
    
    # Always work with deck.csv
    sim = LearnSimulator.load_deck("deck.csv")
    sim.study_session()
    print("\nDeck saved to deck.csv")

if __name__ == '__main__':
    main()
