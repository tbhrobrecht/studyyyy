#!/usr/bin/env python3
# File: deck_manager.py
# Utility for managing multiple flashcard decks

import os
import glob
import csv
from datetime import datetime

def list_all_decks():
    """List all available decks with statistics"""
    print("\n=== DECK OVERVIEW ===")
    
    deck_dir = "practice_decks"
    if not os.path.exists(deck_dir):
        print("No practice decks directory found!")
        return
        
    decks = glob.glob(os.path.join(deck_dir, "*.csv"))
    
    if not decks:
        print("No practice decks found!")
        return
        
    print(f"{'Deck Name':<20} {'Cards':<8} {'Avg Ease':<10} {'Avg Reps':<10} {'Last Modified'}")
    print("-" * 70)
    
    for deck_path in sorted(decks):
        deck_name = os.path.splitext(os.path.basename(deck_path))[0]
        
        try:
            with open(deck_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                cards = list(reader)
                
            if not cards:
                print(f"{deck_name:<20} {'0':<8} {'N/A':<10} {'N/A':<10} {'N/A'}")
                continue
                
            card_count = len(cards)
            avg_ease = sum(float(card.get('ease', 2.5)) for card in cards) / card_count
            avg_reps = sum(int(card.get('repetitions', 0)) for card in cards) / card_count
            
            # Get file modification time
            mod_time = datetime.fromtimestamp(os.path.getmtime(deck_path))
            mod_str = mod_time.strftime("%Y-%m-%d")
            
            print(f"{deck_name:<20} {card_count:<8} {avg_ease:<10.2f} {avg_reps:<10.1f} {mod_str}")
            
        except Exception as e:
            print(f"{deck_name:<20} {'ERROR':<8} {str(e)}")

def list_templates():
    """List all available templates"""
    print("\n=== AVAILABLE TEMPLATES ===")
    
    template_dir = "vocabulary_template"
    if not os.path.exists(template_dir):
        print("No vocabulary templates directory found!")
        return
        
    templates = glob.glob(os.path.join(template_dir, "*.csv"))
    
    if not templates:
        print("No vocabulary templates found!")
        return
        
    print(f"{'Template Name':<20} {'Cards':<8} {'Description'}")
    print("-" * 50)
    
    for template_path in sorted(templates):
        template_name = os.path.splitext(os.path.basename(template_path))[0]
        
        try:
            with open(template_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                cards = list(reader)
                
            card_count = len(cards)
            
            # Try to get the first few terms as description
            if cards:
                first_terms = [card.get('term', '') for card in cards[:3]]
                description = ', '.join(first_terms) + ('...' if len(cards) > 3 else '')
            else:
                description = 'Empty template'
                
            print(f"{template_name:<20} {card_count:<8} {description}")
            
        except Exception as e:
            print(f"{template_name:<20} {'ERROR':<8} {str(e)}")

def deck_progress_report(deck_name):
    """Show detailed progress for a specific deck"""
    deck_path = os.path.join("practice_decks", f"{deck_name}.csv")
    
    if not os.path.exists(deck_path):
        print(f"Deck '{deck_name}' not found!")
        return
        
    print(f"\n=== PROGRESS REPORT: {deck_name.upper()} ===")
    
    try:
        with open(deck_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            cards = list(reader)
            
        if not cards:
            print("No cards in this deck!")
            return
            
        # Statistics
        total_cards = len(cards)
        new_cards = sum(1 for card in cards if int(card.get('repetitions', 0)) == 0)
        learning_cards = sum(1 for card in cards if 0 < int(card.get('repetitions', 0)) < 3)
        mature_cards = sum(1 for card in cards if int(card.get('repetitions', 0)) >= 3)
        
        avg_ease = sum(float(card.get('ease', 2.5)) for card in cards) / total_cards
        avg_interval = sum(int(card.get('interval', 1)) for card in cards) / total_cards
        
        print(f"Total Cards: {total_cards}")
        print(f"New Cards: {new_cards} ({new_cards/total_cards*100:.1f}%)")
        print(f"Learning Cards: {learning_cards} ({learning_cards/total_cards*100:.1f}%)")
        print(f"Mature Cards: {mature_cards} ({mature_cards/total_cards*100:.1f}%)")
        print(f"Average Ease: {avg_ease:.2f}")
        print(f"Average Interval: {avg_interval:.1f} days")
        
        # Show most difficult cards
        difficult_cards = sorted(cards, key=lambda x: float(x.get('ease', 2.5)))[:5]
        print(f"\nMost Difficult Cards:")
        for i, card in enumerate(difficult_cards, 1):
            ease = float(card.get('ease', 2.5))
            reps = int(card.get('repetitions', 0))
            print(f"{i}. {card.get('term', 'N/A')} (ease: {ease:.2f}, reps: {reps})")
            
    except Exception as e:
        print(f"Error reading deck: {e}")

def main():
    """Deck management utility main menu"""
    while True:
        print("\n=== DECK MANAGER ===")
        print("1. List all vocabulary sets (templates + practice decks)")
        print("2. List all templates")
        print("3. Show vocabulary set progress report")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            list_all_decks()
        elif choice == "2":
            list_templates()
        elif choice == "3":
            template_name = input("Enter vocabulary set name: ").strip()
            deck_progress_report(template_name)
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice!")

if __name__ == '__main__':
    main()
