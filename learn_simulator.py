from datetime import datetime, timedelta
import csv
from flashcard import Flashcard
import msvcrt
import random

class LearnSimulator:
    def __init__(self, deck, filepath=None):
        self.cards = deck
        self.filepath = filepath

    @classmethod
    def load_deck(cls, filepath):
        cards = []
        try:
            with open(filepath, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cards.append(Flashcard(
                        term=row['term'],
                        definition=row['definition'],
                        ease=row.get('ease', 2.5),
                        interval=row.get('interval', 1),
                        repetitions=row.get('repetitions', 0),
                        last_review=row.get('last_review')
                    ))
        except FileNotFoundError:
            print(f"File not found: {filepath}")
            exit(1)
        return cls(cards, filepath)

    def save_deck(self, filepath):
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['term', 'definition', 'ease', 'interval', 'repetitions', 'last_review']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for card in self.cards:
                writer.writerow(card.to_dict())

    def study_session(self):
        # Sort all cards by ease factor (lowest first) - cards with lower ease are more difficult
        all_cards = sorted(self.cards, key=lambda c: c.ease)
        
        if not all_cards:
            print("No cards available for review!")
            return
            
        print("Press ESC at any time to stop early and save progress.\n")
        
        # Initialize set tracking
        current_set_start = 0
        completed_cards = []
        
        while current_set_start < len(all_cards):
            # Create current set of up to 30 cards
            if not completed_cards:
                # First set: take first 30 cards (weakest)
                current_set = all_cards[current_set_start:current_set_start + 30]
                print(f"Starting with the {len(current_set)} most difficult cards...\n")
            else:
                # Subsequent sets: 15 weakest from previous + 15 new cards
                weak_cards = sorted(completed_cards, key=lambda c: c.ease)[:15]
                
                # Get next 15 new cards
                remaining_start = current_set_start
                remaining_end = min(current_set_start + 15, len(all_cards))
                new_cards = all_cards[remaining_start:remaining_end]
                
                current_set = weak_cards + new_cards
                
                if not new_cards:
                    # No more new cards, just review the weakest ones
                    current_set = weak_cards
                    if not current_set:
                        print("All cards completed! Great job!")
                        break
                
                print(f"New set: {len(weak_cards)} weak cards + {len(new_cards)} new cards = {len(current_set)} total\n")
            
            # Study the current set
            set_completed_cards = []
            print(f"Studying set of {len(current_set)} cards:")
            print("-" * 50)
            
            for i, card in enumerate(current_set, 1):
                print(f"Card {i}/{len(current_set)}")
                
                # Determine quiz mode based on ease factor (threshold: 3.0)
                if card.ease < 3.0:
                    # Term to definition mode (easier)
                    correct_answer = self._quiz_term_to_definition(card)
                else:
                    # Definition to term mode (harder)
                    correct_answer = self._quiz_definition_to_term(card)
                
                if correct_answer is None:  # User pressed ESC
                    return
                
                # Update card based on performance
                if correct_answer == "hint_correct":
                    q = 3  # Reduced score for correct answer with hint
                    print("✓ Correct (with hint)!")
                elif correct_answer:
                    q = 4  # Good recall for correct answer
                    print("✓ Correct!")
                else:
                    q = 1  # Poor recall for incorrect answer
                    print("✗ Incorrect!")
                    
                card.review(q)
                print(f"Next interval: {card.interval} days, Easiness: {card.ease:.2f}")
                print("-" * 30)
                
                set_completed_cards.append(card)
            
            # Set completed
            completed_cards = set_completed_cards
            
            # Move to next set
            if not completed_cards or len([c for c in completed_cards if c not in all_cards[current_set_start:]]) == 0:
                # If we only studied new cards, advance the starting position
                current_set_start += min(15, len([c for c in current_set if c in all_cards[current_set_start:]]))
            
            # Check if we should continue
            remaining_new_cards = len(all_cards) - current_set_start
            weak_cards_available = len([c for c in completed_cards if c.ease < 3.0])
            
            if remaining_new_cards == 0 and weak_cards_available == 0:
                print("\nAll cards completed! Excellent work!")
                break
            elif remaining_new_cards == 0 and weak_cards_available < 15:
                print(f"\nOnly {weak_cards_available} weak cards remaining. Continuing with final review...")
            else:
                print(f"\nSet completed! Continuing with next set...")
                print(f"Remaining new cards: {remaining_new_cards}")
                print(f"Weak cards to review: {min(15, weak_cards_available)}")
                input("Press Enter to continue to next set...")
                print()
            
        self.save_deck(self.filepath or "deck.csv")
        print("Session complete. Progress saved.")
    
    def _get_random_options(self, correct_item, item_type, count=4):
        """Get random incorrect options for multiple choice"""
        all_items = []
        if item_type == "definition":
            all_items = [card.definition for card in self.cards if card.definition != correct_item]
        else:  # term
            all_items = [card.term for card in self.cards if card.term != correct_item]
        
        if len(all_items) < count:
            # If not enough options, pad with placeholder text
            options = all_items[:]
            while len(options) < count:
                options.append(f"[Option {len(options) + 1}]")
            return options
        
        return random.sample(all_items, count)
    
    def _quiz_term_to_definition(self, card):
        """Quiz mode: Show term, choose correct definition"""
        print(f"Term: {card.term}")
        print("Choose the correct definition:")
        
        # Create options
        correct_definition = card.definition
        wrong_definitions = self._get_random_options(correct_definition, "definition", 4)
        
        options = [correct_definition] + wrong_definitions
        random.shuffle(options)
        correct_index = options.index(correct_definition) + 1
        
        # Display options
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        # Get user input
        used_hint = False
        while True:
            print("Enter choice (1-5), 'h' for hint, or ESC to stop:")
            key = msvcrt.getch()
            if key == b'\x1b':  # ESC key
                print("\nSession stopped early. Saving progress...")
                self.save_deck(self.filepath or "deck.csv")
                return None
            elif key in [b'1', b'2', b'3', b'4', b'5']:
                choice = int(key.decode())
                if choice <= len(options):
                    # If hint was used, reduce score
                    correct = choice == correct_index
                    if correct and used_hint:
                        print("✓ Correct (with hint)")
                        return "hint_correct"  # Special return value for reduced score
                    elif correct:
                        return True
                    else:
                        print(f"✗ Incorrect! The correct answer was: {correct_index}. {correct_definition}")
                        return False
                else:
                    print(f"Invalid choice. Enter 1-{len(options)}.")
            elif key.lower() == b'h' and not used_hint:
                # Remove 2 wrong options randomly
                wrong_indices = [i for i in range(len(options)) if i != (correct_index - 1)]
                indices_to_remove = random.sample(wrong_indices, min(2, len(wrong_indices)))
                indices_to_remove.sort(reverse=True)  # Remove from end to avoid index issues
                
                for idx in indices_to_remove:
                    options.pop(idx)
                
                # Update correct_index after removal
                correct_index = options.index(correct_definition) + 1
                
                # Redisplay options
                print("\nHint used! Here are the remaining options:")
                for i, option in enumerate(options, 1):
                    print(f"{i}. {option}")
                used_hint = True
            elif key.lower() == b'h' and used_hint:
                print("Hint already used for this question.")
            else:
                print("Invalid input. Enter 1-5, 'h' for hint, or ESC.")
    
    def _quiz_definition_to_term(self, card):
        """Quiz mode: Show definition, choose correct term"""
        print(f"Definition: {card.definition}")
        print("Choose the correct term:")
        
        # Create options
        correct_term = card.term
        wrong_terms = self._get_random_options(correct_term, "term", 4)
        
        options = [correct_term] + wrong_terms
        random.shuffle(options)
        correct_index = options.index(correct_term) + 1
        
        # Display options
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        # Get user input
        used_hint = False
        while True:
            print("Enter choice (1-5), 'h' for hint, or ESC to stop:")
            key = msvcrt.getch()
            if key == b'\x1b':  # ESC key
                print("\nSession stopped early. Saving progress...")
                self.save_deck(self.filepath or "deck.csv")
                return None
            elif key in [b'1', b'2', b'3', b'4', b'5']:
                choice = int(key.decode())
                if choice <= len(options):
                    # If hint was used, reduce score
                    correct = choice == correct_index
                    if correct and used_hint:
                        print("✓ Correct (with hint)")
                        return "hint_correct"  # Special return value for reduced score
                    elif correct:
                        return True
                    else:
                        print(f"✗ Incorrect! The correct answer was: {correct_index}. {correct_term}")
                        return False
                else:
                    print(f"Invalid choice. Enter 1-{len(options)}.")
            elif key.lower() == b'h' and not used_hint:
                # Remove 2 wrong options randomly
                wrong_indices = [i for i in range(len(options)) if i != (correct_index - 1)]
                indices_to_remove = random.sample(wrong_indices, min(2, len(wrong_indices)))
                indices_to_remove.sort(reverse=True)  # Remove from end to avoid index issues
                
                for idx in indices_to_remove:
                    options.pop(idx)
                
                # Update correct_index after removal
                correct_index = options.index(correct_term) + 1
                
                # Redisplay options
                print("\nHint used! Here are the remaining options:")
                for i, option in enumerate(options, 1):
                    print(f"{i}. {option}")
                used_hint = True
            elif key.lower() == b'h' and used_hint:
                print("Hint already used for this question.")
            else:
                print("Invalid input. Enter 1-5, 'h' for hint, or ESC.")
