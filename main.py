#!/usr/bin/env python3
# File: main.py

import argparse
import shutil
import os
import glob
import csv
from learn_simulator import LearnSimulator
from deck_manager import detect_deck_format

def discover_templates():
    """Find all available vocabulary templates"""
    template_dir = "vocabulary_template"
    if not os.path.exists(template_dir):
        return []
    
    templates = []
    for file in glob.glob(os.path.join(template_dir, "*.csv")):
        template_name = os.path.splitext(os.path.basename(file))[0]
        templates.append(template_name)
    return templates

def discover_existing_decks():
    """Find all existing practice decks"""
    deck_dir = "practice_decks"
    if not os.path.exists(deck_dir):
        os.makedirs(deck_dir)
        return []
    
    decks = []
    for file in glob.glob(os.path.join(deck_dir, "*.csv")):
        deck_name = os.path.splitext(os.path.basename(file))[0]
        decks.append(deck_name)
    return decks

def get_deck_path_for_template(template_name):
    """Get the corresponding deck path for a template"""
    return os.path.join("practice_decks", f"{template_name}.csv")

def initialize_deck_from_template(template_name):
    """Initialize a deck from template if it doesn't exist"""
    template_path = os.path.join("vocabulary_template", f"{template_name}.csv")
    deck_path = get_deck_path_for_template(template_name)
    
    if not os.path.exists(template_path):
        print(f"Error: Template '{template_name}.csv' not found!")
        return None
        
    if not os.path.exists(deck_path):
        shutil.copy2(template_path, deck_path)
        print(f"Initialized deck '{template_name}' from template")
    
    return deck_path

def select_deck():
    """Interactive deck selection with one-to-one template-deck mapping"""
    templates = discover_templates()
    
    print("\n=== FLASHCARD DECK MANAGER ===")
    print("Available learning sets:")
    
    if not templates:
        print("No learning templates found in vocabulary_template folder!")
        return []
    
    # Show all available templates with their status and type
    print(f"{'#':<3} {'Template':<15} {'Type':<12} {'Status':<12} {'Description'}")
    print("-" * 65)
    
    for i, template in enumerate(templates, 1):
        deck_path = get_deck_path_for_template(template)
        status = "Initialized" if os.path.exists(deck_path) else "New"
        
        # Detect template format
        template_path = os.path.join("vocabulary_template", f"{template}.csv")
        template_format = detect_deck_format(template_path)
        format_display = "Vocabulary" if template_format == "vocabulary" else "MCQ" if template_format == "mcq" else "Unknown"
        
        # Try to get a preview of the template
        try:
            with open(template_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                first_row = next(reader, None)
                if template_format == 'mcq':
                    description = first_row.get('question', 'N/A') if first_row else 'Empty'
                else:
                    description = first_row.get('term', 'N/A') if first_row else 'Empty'
        except:
            description = 'N/A'
        
        # Handle Unicode characters for Windows console
        try:
            description_safe = description[:50] if description else 'N/A'
            # Replace problematic Unicode characters
            description_safe = description_safe.encode('ascii', 'replace').decode('ascii')
        except:
            description_safe = 'N/A'
            
        print(f"{i:<3} {template:<15} {format_display:<12} {status:<12} {description_safe}...")
    
    # Single template selection only
    try:
        template_choice = int(input(f"\nSelect learning set (1-{len(templates)}): ")) - 1
        if 0 <= template_choice < len(templates):
            template_name = templates[template_choice]
            deck_path = initialize_deck_from_template(template_name)
            if deck_path:
                return [deck_path]
            else:
                return select_deck()
        else:
            print("Invalid choice!")
            return select_deck()
    except ValueError:
        print("Invalid input!")
        return select_deck()

def main():
    # Create directories if they don't exist
    os.makedirs("practice_decks", exist_ok=True)
    os.makedirs("vocabulary_template", exist_ok=True)
    
    # Select deck to practice
    selected_decks = select_deck()
    
    # Single deck practice
    print(f"\nStarting practice session with: {os.path.basename(selected_decks[0])}")
    sim = LearnSimulator.load_deck(selected_decks[0])
    sim.study_session()
    print(f"\nDeck saved to {selected_decks[0]}")

if __name__ == '__main__':
    main()
