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
                    # Check if formula column exists and has content
                    formula = row.get('formula', '').strip() if row.get('formula') else None
                    
                    cards.append(Flashcard(
                        term=row['term'],
                        definition=row['definition'],
                        ease=float(row.get('ease', 2.5)),
                        interval=int(row.get('interval', 1)),
                        repetitions=int(row.get('repetitions', 0)),
                        last_review=row.get('last_review'),
                        formula=formula  # Add formula support
                    ))
        except FileNotFoundError:
            print(f"File not found: {filepath}")
            exit(1)
        return cls(cards, filepath)

    def save_deck(self, filepath):
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            # Check if any cards have formulas to determine fieldnames
            has_formulas = any(hasattr(card, 'formula') and card.formula for card in self.cards)
            
            if has_formulas:
                fieldnames = ['term', 'definition', 'formula', 'ease', 'interval', 'repetitions', 'last_review']
            else:
                fieldnames = ['term', 'definition', 'ease', 'interval', 'repetitions', 'last_review']
                
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for card in self.cards:
                writer.writerow(card.to_dict())

    @property
    def flashcards(self):
        """Alias for cards to maintain compatibility with quiz methods"""
        return self.cards

    def study_session(self):
        # Sort all cards by repetitions (lowest first) - cards with fewer repetitions need more practice
        all_cards = sorted(self.cards, key=lambda c: c.repetitions)

        if not all_cards:
            print("No cards available for review!")
            return

        print("Press ESC at any time to stop early and save progress.\n")

        # Phase 1: Initial review sets of 7 least-practiced + 8 most difficult (from reviewed or overall)
        reviewed_cards = []
        current_set_start = 0

        print("=== PHASE 1: Initial Review ===")
        print("Each set: 7 terms + 8 most difficult\n")

        while current_set_start < len(all_cards):
            remaining_cards = all_cards[current_set_start:]

            # Build list of 7 least-practiced
            new_cards = []
            if remaining_cards:
                # Grab 7 cards with the lowest repetition counts (fill from next-lowest groups if needed)
                grouped = {}
                for c in remaining_cards:
                    grouped.setdefault(c.repetitions, []).append(c)

                reps_sorted = sorted(grouped.keys())
                for r in reps_sorted:
                    group = grouped[r]
                    random.shuffle(group)
                    for c in group:
                        if len(new_cards) < 7:
                            new_cards.append(c)
                        else:
                            break
                    if len(new_cards) >= 7:
                        break

            # Choose 8 most difficult (prefer reviewed_cards so we re-test known hard items)
            if reviewed_cards:
                hardest_candidates = reviewed_cards
            else:
                hardest_candidates = self.cards

            hardest_cards = sorted(hardest_candidates, key=lambda c: c.ease)[:8]

            # Combine while avoiding duplicates
            current_set = []
            seen = set()
            for c in new_cards + hardest_cards:
                if c not in seen:
                    current_set.append(c)
                    seen.add(c)

            if not current_set:
                break

            repetition_counts = [card.repetitions for card in new_cards]
            print(f"Set: {len(new_cards)} least practiced cards (reps: {min(repetition_counts) if repetition_counts else 0}-{max(repetition_counts) if repetition_counts else 0}) + {len(hardest_cards)} most difficult = {len(current_set)} total")

            set_completed_cards = self._study_card_set(current_set)
            if set_completed_cards is None:
                return

            # Mark newly reviewed cards
            reviewed_cards.extend(new_cards)

            # Remove the new_cards from all_cards
            all_cards = [card for card in all_cards if card not in new_cards]

            if not all_cards:
                print("\n=== All cards reviewed once! ===")
                break

            print(f"\nRemaining cards to review: {len(all_cards)}")
            input("Press Enter to continue to next set...")
            print()

        # Phase 2: Randomized clusters of 7 + 8 most difficult
        print("\n=== PHASE 2: Randomized Review ===")
        print("Cards will be randomly grouped into sets of 7 + 8 most difficult\n")

        recently_practiced = set()

        while True:
            # 8 most difficult overall
            hardest_cards = sorted(self.cards, key=lambda c: c.ease)[:8]

            # Remaining candidates (excluding hardest)
            remaining_candidates = [c for c in self.cards if c not in hardest_cards]

            if not remaining_candidates:
                current_set = hardest_cards
            else:
                # choose up to 7 unpracticed or least recently practiced
                unpracticed = [c for c in remaining_candidates if c not in recently_practiced]
                if len(unpracticed) >= 7:
                    random.shuffle(unpracticed)
                    selected = unpracticed[:7]
                elif unpracticed:
                    practiced = [c for c in remaining_candidates if c in recently_practiced]
                    random.shuffle(practiced)
                    needed = 7 - len(unpracticed)
                    selected = unpracticed + practiced[:needed]
                else:
                    recently_practiced.clear()
                    random.shuffle(remaining_candidates)
                    selected = remaining_candidates[:7]

                current_set = []
                seen = set()
                for c in selected + hardest_cards:
                    if c not in seen:
                        current_set.append(c)
                        seen.add(c)

            if not current_set:
                print("All cards completed! Excellent work!")
                break

            print(f"Randomized set: {len(current_set)} cards")
            print(f"- New/unpracticed cards: {len([c for c in current_set if c not in recently_practiced and c not in hardest_cards])}")
            print(f"- Recently practiced: {len([c for c in current_set if c in recently_practiced])}")
            print(f"- Most difficult cards included: {len([c for c in current_set if c in hardest_cards])}")

            set_completed_cards = self._study_card_set(current_set)
            if set_completed_cards is None:
                return

            for card in current_set:
                recently_practiced.add(card)

            if len(recently_practiced) > len(self.cards) * 0.6:
                cards_to_keep = list(recently_practiced)
                random.shuffle(cards_to_keep)
                recently_practiced = set(cards_to_keep[:len(recently_practiced)//2])

            print(f"\nSet completed!")
            choice = input("Continue with another randomized set? (y/n): ").lower().strip()
            if choice != 'y' and choice != 'yes':
                break
            print()

        self.save_deck(self.filepath or "deck.csv")
        print("Session complete. Progress saved.")
    
    def _study_card_set(self, card_set):
        """Study a set of cards and return the completed cards (or None if ESC pressed)"""
        print("-" * 50)
        set_completed_cards = []
        
        for i, card in enumerate(card_set, 1):
            print(f"Card {i}/{len(card_set)}")
            
            # Determine learning stage based on repetitions and easiness rating
            current_stage = None
            if card.repetitions == 0 or card.ease < 2.0:
                # Stage 1: Show term and definition (first time or very difficult)
                print(f"[STAGE 1 - REVIEW MODE]")
                correct_answer = self._show_card_review_mode(card)
                current_stage = 1
            elif card.ease < 3.0:
                # Stage 2: Show definition, choose from 5 terms
                print(f"[STAGE 2 - DEFINITION TO TERM]")
                correct_answer = self._quiz_definition_to_term(card)
                current_stage = 2
            else:
                # Stage 3: Show term, choose from 5 definitions
                print(f"[STAGE 3 - TERM TO DEFINITION]")
                correct_answer = self._quiz_term_to_definition(card)
                current_stage = 3
            
            if correct_answer is None:  # User pressed ESC
                return None
            
            # Update card based on performance
            if correct_answer == "hint_correct":
                q = 3  # Reduced score for correct answer with hint
                print("✓ Correct (with hint)!")
            elif correct_answer:
                q = 5  # Perfect recall for correct answer (changed from 4 to 5)
                print("✓ Correct!")
            else:
                q = 1  # Poor recall for incorrect answer
                print("✗ Incorrect!")
                
            card.review(q, stage=current_stage)  # Pass stage info to review method
            print(f"Next interval: {card.interval} days, Easiness: {card.ease:.2f}")
            
            # Show stage progression info
            if card.repetitions == 1 and card.ease < 2.0:
                print("Status: Stage 1 (Review Mode) - First time or needs review")
            elif card.ease < 2.0:
                print("Status: Stage 1 (Review Mode)")
            elif card.ease < 3.0:
                print("Status: Stage 2 (Definition → Term)")
            else:
                print("Status: Stage 3 (Term → Definition)")
                
            print("-" * 30)
            
            set_completed_cards.append(card)
        
        return set_completed_cards
    
    def _show_card_review_mode(self, card):
        """Stage 1: Show term and definition, user acknowledges"""
        print(f"Term: {card.term}")
        print(f"Definition: {card.definition}")
        
        # Show formula if it exists
        if hasattr(card, 'formula') and card.formula:
            print(f"Formula: {card.formula}")
        print()
        
        while True:
            print("Press SPACE to continue, 'r' to repeat, or ESC to stop:")
            key = msvcrt.getch()
            if key == b'\x1b':  # ESC key
                print("\nSession stopped early. Saving progress...")
                self.save_deck(self.filepath or "deck.csv")
                return None
            elif key == b' ':  # SPACE key
                print("✓ Reviewed!")
                return True  # Mark as correct for review mode
            elif key.lower() == b'r':  # R key to repeat
                print("\n" + "="*40)
                print(f"Term: {card.term}")
                print(f"Definition: {card.definition}")
                if hasattr(card, 'formula') and card.formula:
                    print(f"Formula: {card.formula}")
                print("="*40)
            else:
                print("Invalid input. Press SPACE to continue, 'r' to repeat, or ESC.")
    
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
        
        # Show formula if it exists
        if hasattr(card, 'formula') and card.formula:
            print(f"Formula: {card.formula}")
            
        print("Choose the correct definition:")
        
        # Create options with better randomization
        correct_definition = card.definition
        wrong_definitions = self._get_random_options(correct_definition, "definition", 4)
        
        # Randomly place correct answer at any position (1-5)
        correct_index = random.randint(1, 5)
        options = wrong_definitions[:4]  # Take 4 wrong answers
        options.insert(correct_index - 1, correct_definition)  # Insert correct at random position
        
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
                        print(f"✓ Correct (with hint): {choice}. {correct_definition}")
                        return "hint_correct"  # Special return value for reduced score
                    elif correct:
                        print(f"✓ Correct: {choice}. {correct_definition}")
                        return True
                    else:
                        print(f"✗ Incorrect! You selected: {choice}. {options[choice-1]}")
                        print(f"The correct answer was: {correct_index}. {correct_definition}")
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
        
        # Show formula if it exists
        if hasattr(card, 'formula') and card.formula:
            print(f"Formula: {card.formula}")
            
        print("Choose the correct term:")
        
        # Create options with better randomization
        correct_term = card.term
        wrong_terms = self._get_random_options(correct_term, "term", 4)
        
        # Randomly place correct answer at any position (1-5)
        correct_index = random.randint(1, 5)
        options = wrong_terms[:4]  # Take 4 wrong answers
        options.insert(correct_index - 1, correct_term)  # Insert correct at random position
        
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
                        print(f"✓ Correct (with hint): {choice}. {correct_term}")
                        return "hint_correct"  # Special return value for reduced score
                    elif correct:
                        print(f"✓ Correct: {choice}. {correct_term}")
                        return True
                    else:
                        print(f"✗ Incorrect! You selected: {choice}. {options[choice-1]}")
                        print(f"The correct answer was: {correct_index}. {correct_term}")
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

    def _quiz_term_to_formula(self, card):
        """Quiz mode: Show term, choose correct formula (for cards with formulas)"""
        if not hasattr(card, 'formula') or not card.formula:
            # Fallback to term_to_definition if no formula
            return self._quiz_term_to_definition(card)
            
        print(f"Term: {card.term}")
        print("Choose the correct formula:")
        
        # Create options with formulas from other cards
        correct_formula = card.formula
        wrong_formulas = []
        
        # Get formulas from other cards
        for other_card in self.flashcards:
            if (other_card != card and 
                hasattr(other_card, 'formula') and 
                other_card.formula and 
                other_card.formula != correct_formula):
                wrong_formulas.append(other_card.formula)
        
        # If we don't have enough formula options, add some generic ones
        generic_formulas = [
            "Rate × Principal × Time",
            "(Final Value - Initial Value) / Initial Value",
            "Present Value / (1 + r)^n",
            "Cash Flow / Required Rate of Return",
            "Assets - Liabilities"
        ]
        
        for formula in generic_formulas:
            if formula not in wrong_formulas and formula != correct_formula:
                wrong_formulas.append(formula)
            if len(wrong_formulas) >= 4:
                break
        
        # Ensure we have at least 4 options
        while len(wrong_formulas) < 4:
            wrong_formulas.append(f"Formula Option {len(wrong_formulas) + 1}")
        
        # Randomly place correct answer at any position (1-5)
        correct_index = random.randint(1, 5)
        options = wrong_formulas[:4]  # Take 4 wrong answers
        options.insert(correct_index - 1, correct_formula)  # Insert correct at random position
        
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
                        print(f"✓ Correct (with hint): {choice}. {correct_formula}")
                        return "hint_correct"  # Special return value for reduced score
                    elif correct:
                        print(f"✓ Correct: {choice}. {correct_formula}")
                        return True
                    else:
                        print(f"✗ Incorrect! You selected: {choice}. {options[choice-1]}")
                        print(f"The correct answer was: {correct_index}. {correct_formula}")
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
                correct_index = options.index(correct_formula) + 1
                
                # Redisplay options
                print("\nHint used! Here are the remaining options:")
                for i, option in enumerate(options, 1):
                    print(f"{i}. {option}")
                used_hint = True
            elif key.lower() == b'h' and used_hint:
                print("Hint already used for this question.")
            else:
                print("Invalid input. Enter 1-5, 'h' for hint, or ESC.")