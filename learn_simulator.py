from datetime import datetime, timedelta
import csv
from flashcard import Flashcard
import msvcrt
import random

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'    # Bright green for correct answers
    RED = '\033[91m'      # Bright red for incorrect answers
    YELLOW = '\033[93m'   # Yellow for hints
    BLUE = '\033[94m'     # Blue for info
    BOLD = '\033[1m'      # Bold text
    RESET = '\033[0m'     # Reset to default color

class LearnSimulator:
    def __init__(self, deck, filepath=None):
        self.cards = deck
        self.filepath = filepath
        self.session_stats = []  # Track statistics for each set
        self.previous_stage_distribution = None  # Track changes in stage distribution

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
                        interval=1,  # Default interval since we're removing this from CSV
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
                fieldnames = ['term', 'definition', 'formula', 'ease', 'repetitions', 'last_review']
            else:
                fieldnames = ['term', 'definition', 'ease', 'repetitions', 'last_review']
                
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for card in self.cards:
                writer.writerow(card.to_dict())

    @property
    def flashcards(self):
        """Alias for cards to maintain compatibility with quiz methods"""
        return self.cards

    def _calculate_set_statistics(self, set_cards, correct_count, incorrect_count, hint_count=0):
        """Calculate statistics for a completed set"""
        total_cards = len(set_cards)
        if total_cards == 0:
            return None
            
        # Basic percentages
        percent_correct = (correct_count / total_cards) * 100
        percent_incorrect = (incorrect_count / total_cards) * 100
        percent_with_hint = (hint_count / total_cards) * 100 if hint_count > 0 else 0
        
        # Stage distribution (current state of all cards)
        stage_counts = {1: 0, 2: 0, 3: 0}
        for card in self.cards:  # Use all cards, not just set_cards
            if card.repetitions == 0 or card.ease < 2.0:
                stage_counts[1] += 1
            elif card.ease < 3.0:
                stage_counts[2] += 1
            else:
                stage_counts[3] += 1
        
        total_all_cards = len(self.cards)
        stage_percentages = {
            stage: (count / total_all_cards) * 100 
            for stage, count in stage_counts.items()
        }
        
        stats = {
            'total_cards': total_cards,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'hint_count': hint_count,
            'percent_correct': percent_correct,
            'percent_incorrect': percent_incorrect,
            'percent_with_hint': percent_with_hint,
            'stage_counts': stage_counts,
            'stage_percentages': stage_percentages,
            'total_all_cards': total_all_cards
        }
        
        return stats
    
    def _display_set_statistics(self, stats):
        """Display statistics for a completed set"""
        if not stats:
            return
            
        print("\n" + "="*60)
        print("SET STATISTICS")
        print("="*60)
        
        # Performance in this set
        print(f"📊 SET PERFORMANCE:")
        print(f"   Total cards in set: {stats['total_cards']}")
        print(f"   {Colors.GREEN}✓ Correct answers: {stats['correct_count']} ({stats['percent_correct']:.1f}%){Colors.RESET}")
        print(f"   {Colors.RED}✗ Incorrect answers: {stats['incorrect_count']} ({stats['percent_incorrect']:.1f}%){Colors.RESET}")
        if stats['hint_count'] > 0:
            print(f"   {Colors.YELLOW}💡 Correct with hint: {stats['hint_count']} ({stats['percent_with_hint']:.1f}%){Colors.RESET}")
        
        # Overall progress stages
        print(f"\n🎯 OVERALL DECK PROGRESS:")
        print(f"   Total cards in deck: {stats['total_all_cards']}")
        print(f"   📚 Stage 1 (Review Mode): {stats['stage_counts'][1]} cards ({stats['stage_percentages'][1]:.1f}%)")
        print(f"   📖 Stage 2 (Definition → Term): {stats['stage_counts'][2]} cards ({stats['stage_percentages'][2]:.1f}%)")
        print(f"   🎓 Stage 3 (Term → Definition): {stats['stage_counts'][3]} cards ({stats['stage_percentages'][3]:.1f}%)")
        
        # Show trends if we have previous data
        if self.previous_stage_distribution:
            self._display_trends(stats['stage_counts'])
        
        # Store current distribution for next comparison
        self.previous_stage_distribution = stats['stage_counts'].copy()
        
        # Store stats for session summary
        self.session_stats.append(stats)
        
        print("="*60)
        
        # Pause to let user read the statistics
        input("\nPress Enter to continue...")
        print()
    
    def _display_trends(self, current_stage_counts):
        """Display trends comparing current stage distribution to previous"""
        print(f"\n📈 PROGRESS TRENDS:")
        
        for stage in [1, 2, 3]:
            current = current_stage_counts[stage]
            previous = self.previous_stage_distribution[stage]
            change = current - previous
            
            stage_names = {1: "Stage 1 (Review)", 2: "Stage 2 (Def→Term)", 3: "Stage 3 (Term→Def)"}
            
            if change > 0:
                print(f"   📈 {stage_names[stage]}: +{change} cards (getting harder)")
            elif change < 0:
                print(f"   📉 {stage_names[stage]}: {change} cards (progressing!)")
            else:
                print(f"   ➡️  {stage_names[stage]}: No change")
        
        # Overall difficulty trend
        difficulty_previous = (self.previous_stage_distribution[1] * 1 + 
                              self.previous_stage_distribution[2] * 2 + 
                              self.previous_stage_distribution[3] * 3)
        difficulty_current = (current_stage_counts[1] * 1 + 
                             current_stage_counts[2] * 2 + 
                             current_stage_counts[3] * 3)
        
        if difficulty_current > difficulty_previous:
            print(f"   🚀 Overall trend: Advancing to higher stages!")
        elif difficulty_current < difficulty_previous:
            print(f"   ⚠️  Overall trend: Some cards moved to lower stages")
        else:
            print(f"   ⚖️  Overall trend: Maintaining current level")

    def _display_session_summary(self):
        """Display a summary of the entire study session"""
        if not self.session_stats:
            return
            
        print("\n" + "🎉" * 20)
        print("SESSION SUMMARY")
        print("🎉" * 20)
        
        total_sets = len(self.session_stats)
        total_cards_practiced = sum(stats['total_cards'] for stats in self.session_stats)
        total_correct = sum(stats['correct_count'] for stats in self.session_stats)
        total_incorrect = sum(stats['incorrect_count'] for stats in self.session_stats)
        total_hints = sum(stats['hint_count'] for stats in self.session_stats)
        
        overall_accuracy = (total_correct / total_cards_practiced * 100) if total_cards_practiced > 0 else 0
        
        print(f"📚 Sets completed: {total_sets}")
        print(f"🎯 Total cards practiced: {total_cards_practiced}")
        print(f"✅ Overall accuracy: {overall_accuracy:.1f}%")
        print(f"💡 Hints used: {total_hints}")
        
        if total_sets > 1:
            print(f"\n📈 PROGRESS OVER TIME:")
            for i, stats in enumerate(self.session_stats, 1):
                print(f"   Set {i}: {stats['percent_correct']:.1f}% correct ({stats['correct_count']}/{stats['total_cards']})")
            
            # Show improvement trend
            first_accuracy = self.session_stats[0]['percent_correct']
            last_accuracy = self.session_stats[-1]['percent_correct']
            
            if last_accuracy > first_accuracy:
                improvement = last_accuracy - first_accuracy
                print(f"   🚀 Improvement: +{improvement:.1f}% from first to last set!")
            elif last_accuracy < first_accuracy:
                decline = first_accuracy - last_accuracy
                print(f"   📉 Accuracy decreased by {decline:.1f}% (normal for harder material)")
            else:
                print(f"   ⚖️  Consistent performance maintained")
        
        # Final stage distribution
        if self.session_stats:
            final_stats = self.session_stats[-1]
            print(f"\n🏆 FINAL DECK STATUS:")
            print(f"   📚 Stage 1 (Review): {final_stats['stage_counts'][1]} cards ({final_stats['stage_percentages'][1]:.1f}%)")
            print(f"   📖 Stage 2 (Def→Term): {final_stats['stage_counts'][2]} cards ({final_stats['stage_percentages'][2]:.1f}%)")
            print(f"   🎓 Stage 3 (Term→Def): {final_stats['stage_counts'][3]} cards ({final_stats['stage_percentages'][3]:.1f}%)")
        
        print("🎉" * 20)

    def study_session(self):
        # Sort all cards by repetitions (lowest first) - cards with fewer repetitions need more practice
        all_cards = sorted(self.cards, key=lambda c: c.repetitions)

        if not all_cards:
            print("No cards available for review!")
            return

        print("Press ESC at any time to stop early and save progress.\n")

        # Phase 1: Sets of 7 new terms + same 7 terms repeated
        print("=== PHASE 1: Initial Review ===")
        print("Each set: 7 new terms + same 7 terms repeated\n")

        current_set_start = 0
        carry_forward_cards = []  # Cards that were answered incorrectly

        while current_set_start < len(all_cards) or carry_forward_cards:
            # Build list of 7 cards for this set
            new_cards = []
            
            # First, add any carry-forward cards (up to 7)
            for card in carry_forward_cards[:7]:
                new_cards.append(card)
            carry_forward_cards = carry_forward_cards[7:]  # Remove used cards
            
            # Fill remaining slots with new cards from all_cards
            if len(new_cards) < 7 and current_set_start < len(all_cards):
                remaining_cards = all_cards[current_set_start:]
                for card in remaining_cards:
                    if len(new_cards) < 7:
                        new_cards.append(card)
                        current_set_start += 1
                    else:
                        break

            if not new_cards:
                break

            # Create the set: 7 terms + same 7 terms again
            current_set = new_cards + new_cards  # Duplicate the 7 terms
            
            print(f"Set: {len(new_cards)} terms + {len(new_cards)} repeats = {len(current_set)} total")

            # Study the set and track which cards were answered incorrectly
            set_results = self._study_card_set_with_tracking(current_set)
            if set_results is None:  # User pressed ESC
                return
            
            set_completed_cards, incorrect_cards = set_results
            
            # Add incorrect cards to carry_forward for next set
            # Only add unique cards (avoid duplicates from the repeated portion)
            unique_incorrect = []
            for card in incorrect_cards:
                if card not in unique_incorrect and card in new_cards:
                    unique_incorrect.append(card)
            carry_forward_cards.extend(unique_incorrect)
            
            if carry_forward_cards:
                print(f"\n{len(unique_incorrect)} cards answered incorrectly will appear in the next set.")
            
            if current_set_start >= len(all_cards) and not carry_forward_cards:
                print("\n=== All cards completed! ===")
                break

            print(f"\nRemaining new cards: {len(all_cards) - current_set_start}")
            if carry_forward_cards:
                print(f"Cards to retry: {len(carry_forward_cards)}")
            input("Press Enter to continue to next set...")
            print()
        # Phase 2: Randomized clusters of 7 + variable number of most difficult
        print("\n=== PHASE 2: Randomized Review ===")
        print("Cards will be randomly grouped into sets of 7 + variable number of hard terms\n")

        recently_practiced = set()

        while True:
            # Select hardest cards only from reviewed cards (repetitions > 0).
            hardest_cards = sorted([c for c in self.cards if c.repetitions > 0], key=lambda c: c.ease)[:8]

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
        self._display_session_summary()
        print("Session complete. Progress saved.")
    
    def _study_card_set(self, card_set):
        """Study a set of cards and return the completed cards (or None if ESC pressed)"""
        print("-" * 50)
        set_completed_cards = []
        correct_count = 0
        incorrect_count = 0
        hint_count = 0
        
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
            
            # Update card based on performance and track statistics
            if correct_answer == "hint_correct":
                q = 3  # Reduced score for correct answer with hint
                print(f"{Colors.YELLOW}✓ Correct (with hint)!{Colors.RESET}")
                correct_count += 1
                hint_count += 1
            elif correct_answer:
                q = 5  # Perfect recall for correct answer (changed from 4 to 5)
                print(f"{Colors.GREEN}✓ Correct!{Colors.RESET}")
                correct_count += 1
            else:
                q = 1  # Poor recall for incorrect answer
                print(f"{Colors.RED}✗ Incorrect!{Colors.RESET}")
                incorrect_count += 1
                
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
        
        # Calculate and display statistics
        stats = self._calculate_set_statistics(card_set, correct_count, incorrect_count, hint_count)
        self._display_set_statistics(stats)
        
        return set_completed_cards
    
    def _study_card_set_with_tracking(self, card_set):
        """Study a set of cards and return (completed_cards, incorrect_cards) or None if ESC pressed"""
        print("-" * 50)
        set_completed_cards = []
        incorrect_cards = []
        correct_count = 0
        incorrect_count = 0
        hint_count = 0
        
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
            
            # Update card based on performance and track statistics
            was_correct = False
            if correct_answer == "hint_correct":
                q = 3  # Reduced score for correct answer with hint
                print(f"{Colors.YELLOW}✓ Correct (with hint)!{Colors.RESET}")
                was_correct = True
                correct_count += 1
                hint_count += 1
            elif correct_answer:
                q = 5  # Perfect recall for correct answer (changed from 4 to 5)
                print(f"{Colors.GREEN}✓ Correct!{Colors.RESET}")
                was_correct = True
                correct_count += 1
            else:
                q = 1  # Poor recall for incorrect answer
                print(f"{Colors.RED}✗ Incorrect!{Colors.RESET}")
                incorrect_cards.append(card)
                incorrect_count += 1
                
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
        
        # Calculate and display statistics
        stats = self._calculate_set_statistics(card_set, correct_count, incorrect_count, hint_count)
        self._display_set_statistics(stats)
        
        return set_completed_cards, incorrect_cards
    
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
                        print(f"{Colors.YELLOW}✓ Correct (with hint): {choice}. {correct_definition}{Colors.RESET}")
                        return "hint_correct"  # Special return value for reduced score
                    elif correct:
                        print(f"{Colors.GREEN}✓ Correct: {choice}. {correct_definition}{Colors.RESET}")
                        return True
                    else:
                        print(f"{Colors.RED}✗ Incorrect! You selected: {choice}. {options[choice-1]}{Colors.RESET}")
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
                        print(f"{Colors.YELLOW}✓ Correct (with hint): {choice}. {correct_term}{Colors.RESET}")
                        return "hint_correct"  # Special return value for reduced score
                    elif correct:
                        print(f"{Colors.GREEN}✓ Correct: {choice}. {correct_term}{Colors.RESET}")
                        return True
                    else:
                        print(f"{Colors.RED}✗ Incorrect! You selected: {choice}. {options[choice-1]}{Colors.RESET}")
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
                        print(f"{Colors.YELLOW}✓ Correct (with hint): {choice}. {correct_formula}{Colors.RESET}")
                        return "hint_correct"  # Special return value for reduced score
                    elif correct:
                        print(f"{Colors.GREEN}✓ Correct: {choice}. {correct_formula}{Colors.RESET}")
                        return True
                    else:
                        print(f"{Colors.RED}✗ Incorrect! You selected: {choice}. {options[choice-1]}{Colors.RESET}")
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