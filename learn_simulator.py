from datetime import datetime, timedelta
import csv
import time
from flashcard import Flashcard
import msvcrt
import random
import difflib
import sys

# Safe print function for Windows console
def safe_print(text):
    """Print text safely, replacing problematic Unicode characters for Windows console"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace Unicode symbols with ASCII equivalents
        safe_text = text.replace('✓', 'OK').replace('✗', 'X').replace('📖', '[BOOK]').replace('🎓', '[GRAD]')
        safe_text = safe_text.replace('→', '->').replace('←', '<-')
        print(safe_text)

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
                fieldnames = reader.fieldnames
                
                # Detect format based on columns
                mcq_columns = {'question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer'}
                is_mcq = mcq_columns.issubset(set(fieldnames or []))
                
                for row in reader:
                    if is_mcq:
                        # MCQ format
                        cards.append(Flashcard(
                            question=row['question'],
                            option_a=row['option_a'],
                            option_b=row['option_b'],
                            option_c=row['option_c'],
                            option_d=row['option_d'],
                            correct_answer=row['correct_answer'],
                            ease=float(row.get('ease', 2.5)),
                            interval=1,  # Default interval since we're removing this from CSV
                            repetitions=int(row.get('repetitions', 0)),
                            last_review=row.get('last_review')
                        ))
                    else:
                        # Vocabulary format
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
            # Determine format based on first card
            if self.cards and self.cards[0].card_type == 'mcq':
                fieldnames = ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'ease', 'repetitions', 'last_review']
            else:
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
        stage_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for card in self.cards:  # Use all cards, not just set_cards
            if card.repetitions == 0 or card.ease < 2.0:
                stage_counts[1] += 1
            elif card.ease < 3.0:
                stage_counts[2] += 1
            elif card.ease < 4.0:
                stage_counts[3] += 1
            elif card.ease < 5.0:
                stage_counts[4] += 1
            else:
                stage_counts[5] += 1

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
        safe_print(f"   {Colors.GREEN}✓ Correct answers: {stats['correct_count']} ({stats['percent_correct']:.1f}%){Colors.RESET}")
        safe_print(f"   {Colors.RED}✗ Incorrect answers: {stats['incorrect_count']} ({stats['percent_incorrect']:.1f}%){Colors.RESET}")
        if stats['hint_count'] > 0:
            print(f"   {Colors.YELLOW}💡 Correct with hint: {stats['hint_count']} ({stats['percent_with_hint']:.1f}%){Colors.RESET}")
        
        # Overall progress stages
        print(f"\n🎯 OVERALL DECK PROGRESS:")
        print(f"   Total cards in deck: {stats['total_all_cards']}")
        print(f"   📚 Stage 1 (Review Mode): {stats['stage_counts'][1]} cards ({stats['stage_percentages'][1]:.1f}%)")
        print(f"   📖 Stage 2 (Definition → Term): {stats['stage_counts'][2]} cards ({stats['stage_percentages'][2]:.1f}%)")
        print(f"   🎓 Stage 3 (Term → Definition): {stats['stage_counts'][3]} cards ({stats['stage_percentages'][3]:.1f}%)")
        print(f"   🧠 Stage 4 (Advanced Practice): {stats['stage_counts'][4]} cards ({stats['stage_percentages'][4]:.1f}%)")
        print(f"   🚀 Stage 5 (Mastery): {stats['stage_counts'][5]} cards ({stats['stage_percentages'][5]:.1f}%)")

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

        for stage in [1, 2, 3, 4, 5]:
            current = current_stage_counts[stage]
            previous = self.previous_stage_distribution[stage]
            change = current - previous

            stage_names = {1: "Stage 1 (Review)", 2: "Stage 2 (Def→Term)", 3: "Stage 3 (Term→Def)", 4: "Stage 4 (Adv Practice)", 5: "Stage 5 (Mastery)"}
            
            if change > 0:
                print(f"   📈 {stage_names[stage]}: +{change} cards (getting harder)")
            elif change < 0:
                print(f"   📉 {stage_names[stage]}: {change} cards (progressing!)")
            else:
                print(f"   ➡️  {stage_names[stage]}: No change")
        
        # Overall difficulty trend
        # double check if valid
        difficulty_previous = (self.previous_stage_distribution[1] * 1 + 
                              self.previous_stage_distribution[2] * 2 + 
                              self.previous_stage_distribution[3] * 3 + 
                              self.previous_stage_distribution[4] * 4 + 
                              self.previous_stage_distribution[5] * 5)
        difficulty_current = (current_stage_counts[1] * 1 + 
                             current_stage_counts[2] * 2 + 
                             current_stage_counts[3] * 3 + 
                             current_stage_counts[4] * 4 + 
                             current_stage_counts[5] * 5)

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
            print(f"   🧠 Stage 4 (Adv Practice): {final_stats['stage_counts'][4]} cards ({final_stats['stage_percentages'][4]:.1f}%)")
            print(f"   🚀 Stage 5 (Mastery): {final_stats['stage_counts'][5]} cards ({final_stats['stage_percentages'][5]:.1f}%)")
        
        print("🎉" * 20)

    def study_session(self):
        # Sort all cards by repetitions (lowest first) - cards with fewer repetitions need more practice
        all_cards = sorted(self.cards, key=lambda c: c.repetitions)

        if not all_cards:
            print("No cards available for review!")
            return

        print("Press ESC at any time to stop early and save progress.\n")

        # Check if any card is still in Stage 1 (needs initial review)
        # Stage 1 condition: repetitions == 0 OR ease < 2.0
        if any(card.repetitions == 0 or card.ease < 2.0 for card in all_cards):
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
        else:
            # Phase 2: Randomized clusters of 7 + variable number of most difficult
            print("\n=== PHASE 2: Randomized Review ===")
            print("Cards will be randomly grouped into sets of 7 + variable number of hard terms\n")

            recently_practiced = set()

            while True:
                # Select hardest cards from ALL cards (since all cards can be practiced in stages 2-5)
                # Sort by ease (lowest = most difficult) and take up to 8 hardest cards
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

                # Study the set and track which cards were answered incorrectly
                set_results = self._study_card_set_with_tracking(current_set)
                if set_results is None:  # User pressed ESC
                    return
                
                set_completed_cards, incorrect_cards = set_results
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
            response_time = None
            if card.repetitions == 0 or card.ease < 2.0:
                # Stage 1: Show question and answer (first time or very difficult)
                print(f"[STAGE 1 - REVIEW MODE]")
                result = self._show_card_review_mode(card)
                current_stage = 1
            elif card.ease < 3.0:
                # Stage 2: Show question with multiple choices (easy mode for MCQ, definition to term for vocab)
                print(f"[STAGE 2 - BASIC PRACTICE]")
                if card.card_type == 'mcq':
                    result = self._mcq_practice_mode(card)
                else:
                    result = self._quiz_definition_to_term(card)
                current_stage = 2
            elif card.ease < 4.0:
                # Stage 3: Show question with multiple choices (for MCQ) or term to definition (for vocab)
                print(f"[STAGE 3 - INTERMEDIATE PRACTICE]")
                if card.card_type == 'mcq':
                    result = self._mcq_practice_mode(card)
                else:
                    result = self._quiz_term_to_definition(card)
                current_stage = 3
            elif card.ease < 5.0:
                # Stage 4: Advanced MCQ (no hints) or typing for vocab
                print(f"[STAGE 4 - ADVANCED PRACTICE]")
                if card.card_type == 'mcq':
                    result = self._mcq_practice_mode(card, allow_hints=False)
                else:
                    result = self._type_term_to_definition(card)
                current_stage = 4
            else:
                # Stage 5: Expert MCQ (no hints) or typing for vocab
                print(f"[STAGE 5 - EXPERT PRACTICE]")
                if card.card_type == 'mcq':
                    result = self._mcq_practice_mode(card, allow_hints=False)
                else:
                    result = self._type_definition_to_term(card)
                current_stage = 5

            # Handle the result - some methods return tuples, others just values
            if result is None:  # User pressed ESC
                return None
            elif isinstance(result, tuple):
                correct_answer, response_time = result
            else:
                correct_answer = result
                response_time = None
                
            if correct_answer is None:  # Double check for ESC
                return None
            
            # Update card based on performance and track statistics
            was_correct = False
            if correct_answer == "hint_correct":
                q = 3  # Reduced score for correct answer with hint
                print(f"{Colors.YELLOW}✓ Correct (with hint)!{Colors.RESET}")
                was_correct = True
                correct_count += 1
                hint_count += 1
            elif isinstance(correct_answer, tuple) and correct_answer[0] == "partial":
                # Handle partial credit scoring
                partial_score = correct_answer[1]  # Score between 0 and 1
                q = 1 + (partial_score * 4)  # Scale to 1-5 range
                print(f"{Colors.YELLOW}◐ Partial Credit ({int(partial_score * 100)}%)!{Colors.RESET}")
                if partial_score >= 0.5:
                    was_correct = True
                    correct_count += 1
                else:
                    incorrect_cards.append(card)
                    incorrect_count += 1
            elif correct_answer:
                q = 5  # Perfect recall for correct answer
                safe_print(f"{Colors.GREEN}✓ Correct!{Colors.RESET}")
                was_correct = True
                correct_count += 1
            else:
                q = 1  # Poor recall for incorrect answer
                safe_print(f"{Colors.RED}✗ Incorrect!{Colors.RESET}")
                incorrect_cards.append(card)
                incorrect_count += 1
                
            card.review(q, stage=current_stage, response_time=response_time)  # Pass stage info and response time to review method
            print(f"Next interval: {card.interval} days, Easiness: {card.ease:.2f}")
            
            # Show stage progression info
            if card.repetitions == 1 and card.ease < 2.0:
                print("Status: Stage 1 (Review Mode) - First time or needs review")
            elif card.ease < 2.0:
                print("Status: Stage 1 (Review Mode)")
            elif card.ease < 3.0:
                print("Status: Stage 2 (Definition → Term)")
            elif card.ease < 4.0:
                print("Status: Stage 3 (Term → Definition)")
            elif card.ease < 5.0:
                print("Status: Stage 4 (Advanced Review)")
            else:
                print("Status: Stage 5 (Expert Review)")

            print("-" * 30)
            
            set_completed_cards.append(card)
        
        # Calculate and display statistics
        stats = self._calculate_set_statistics(card_set, correct_count, incorrect_count, hint_count)
        self._display_set_statistics(stats)
        
        return set_completed_cards, incorrect_cards
    
    def _show_card_review_mode(self, card):
        """Stage 1: Show question and answer, user acknowledges"""
        start_time = time.time()
        
        if card.card_type == 'mcq':
            print(f"Question: {card.question}")
            print(f"Correct Answer: {card.get_answer_text()}")
        else:
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
                response_time = time.time() - start_time
                safe_print("✓ Reviewed!")
                return True, response_time  # Return tuple: (result, response_time)
            elif key.lower() == b'r':  # R key to repeat
                print("\n" + "="*40)
                if card.card_type == 'mcq':
                    print(f"Question: {card.question}")
                    print(f"Correct Answer: {card.get_answer_text()}")
                else:
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
        
        # Get user input with timing
        start_time = time.time()
        used_hint = False
        response_time = None
        
        while True:
            print("Enter choice (1-5), 'h' for hint, or ESC to stop:")
            key = msvcrt.getch()
            if key == b'\x1b':  # ESC key
                print("\nSession stopped early. Saving progress...")
                self.save_deck(self.filepath or "deck.csv")
                return None, None
            elif key in [b'1', b'2', b'3', b'4', b'5']:
                response_time = time.time() - start_time
                choice = int(key.decode())
                if choice <= len(options):
                    # If hint was used, reduce score
                    correct = choice == correct_index
                    if correct and used_hint:
                        print(f"{Colors.YELLOW}✓ Correct (with hint): {choice}. {correct_definition}{Colors.RESET}")
                        return "hint_correct", response_time  # Special return value for reduced score
                    elif correct:
                        print(f"{Colors.GREEN}✓ Correct: {choice}. {correct_definition}{Colors.RESET}")
                        return True, response_time
                    else:
                        print(f"{Colors.RED}✗ Incorrect! You selected: {choice}. {options[choice-1]}{Colors.RESET}")
                        print(f"The correct answer was: {correct_index}. {correct_definition}")
                        return False, response_time
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
                start_time = time.time()  # Restart timing after hint
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
        
        # Get user input with timing
        start_time = time.time()
        used_hint = False
        response_time = None
        
        while True:
            print("Enter choice (1-5), 'h' for hint, or ESC to stop:")
            key = msvcrt.getch()
            if key == b'\x1b':  # ESC key
                print("\nSession stopped early. Saving progress...")
                self.save_deck(self.filepath or "deck.csv")
                return None, None
            elif key in [b'1', b'2', b'3', b'4', b'5']:
                response_time = time.time() - start_time
                choice = int(key.decode())
                if choice <= len(options):
                    # If hint was used, reduce score
                    correct = choice == correct_index
                    if correct and used_hint:
                        print(f"{Colors.YELLOW}✓ Correct (with hint): {choice}. {correct_term}{Colors.RESET}")
                        return "hint_correct", response_time  # Special return value for reduced score
                    elif correct:
                        print(f"{Colors.GREEN}✓ Correct: {choice}. {correct_term}{Colors.RESET}")
                        return True, response_time
                    else:
                        print(f"{Colors.RED}✗ Incorrect! You selected: {choice}. {options[choice-1]}{Colors.RESET}")
                        print(f"The correct answer was: {correct_index}. {correct_term}")
                        return False, response_time
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
                start_time = time.time()  # Restart timing after hint
            elif key.lower() == b'h' and used_hint:
                print("Hint already used for this question.")
            else:
                print("Invalid input. Enter 1-5, 'h' for hint, or ESC.")

    def _type_term_to_definition(self, card):
        """Phase 4: Show term, user types the correct definition (fuzzy match allowed)"""
        print(f"Term: {card.term}")

        # Show formula if it exists
        if hasattr(card, 'formula') and card.formula:
            print(f"Formula: {card.formula}")

        # Get user input with timing
        start_time = time.time()
        response_time = None

        print("Type the correct definition (or press ESC to stop):")
        user_input = ""
        while True:
            char = msvcrt.getch()
            if char == b'\x1b':  # ESC key
                print("\nSession stopped early. Saving progress...")
                self.save_deck(self.filepath or "deck.csv")
                return None
            elif char in [b'\r', b'\n']:  # Enter key
                break
            elif char == b'\x08':  # Backspace
                if user_input:
                    user_input = user_input[:-1]
                    # Move cursor back, overwrite with space, move back again
                    print('\b \b', end='', flush=True)
            else:
                decoded_char = char.decode('utf-8', errors='ignore')
                user_input += decoded_char
                print(decoded_char, end='', flush=True)
                
        # Fuzzy match: Accept if similarity > 0.7
        similarity = difflib.SequenceMatcher(None, user_input.lower(), card.definition.lower()).ratio()
        response_time = time.time() - start_time
        print("\n", round(similarity, 2))
        if similarity > 0.7:
            print(f"\n{Colors.GREEN}✓ Correct! The correct definition was: {card.definition}{Colors.RESET}")
            return True, response_time
        elif similarity > 0.3:
            print(f"\n{Colors.YELLOW}⚠️ Almost! The correct definition was: {card.definition}{Colors.RESET}")
            return "hint_correct", response_time
        else:
            print(f"\n{Colors.RED}✗ Incorrect! The correct definition was: {card.definition}{Colors.RESET}")
            return False, response_time

    def _type_definition_to_term(self, card):
        """Phase 4: Show definition, user types the correct term (fuzzy match allowed)"""
        print(f"Definition: {card.definition}")

        # Show formula if it exists
        if hasattr(card, 'formula') and card.formula:
            print(f"Formula: {card.formula}")

        # Get user input with timing
        start_time = time.time()
        response_time = None

        print("Type the correct term (or press ESC to stop):")
        user_input = ""
        while True:
            char = msvcrt.getch()
            if char == b'\x1b':  # ESC key
                print("\nSession stopped early. Saving progress...")
                self.save_deck(self.filepath or "deck.csv")
                return None
            elif char in [b'\r', b'\n']:  # Enter key
                break
            elif char == b'\x08':  # Backspace
                if user_input:
                    user_input = user_input[:-1]
                    print('\b \b', end='', flush=True)
            else:
                decoded_char = char.decode('utf-8', errors='ignore')
                user_input += decoded_char
                print(decoded_char, end='', flush=True)
                
        # Fuzzy match: Accept if similarity > 0.7
        similarity = difflib.SequenceMatcher(None, user_input.lower(), card.term.lower()).ratio()
        response_time = time.time() - start_time
        print("\n", round(similarity, 2))
        if similarity > 0.7:
            print(f"\n{Colors.GREEN}✓ Correct! The correct term was: {card.term}{Colors.RESET}")
            return True, response_time
        elif similarity > 0.3:
            print(f"\n{Colors.YELLOW}⚠️ Almost! The correct term was: {card.term}{Colors.RESET}")
            return "hint_correct", response_time
        else:
            print(f"\n{Colors.RED}✗ Incorrect! The correct term was: {card.term}{Colors.RESET}")
            return False, response_time

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
        
        # Get user input with timing
        start_time = time.time()
        used_hint = False
        response_time = None
        
        while True:
            print("Enter choice (1-5), 'h' for hint, or ESC to stop:")
            key = msvcrt.getch()
            if key == b'\x1b':  # ESC key
                print("\nSession stopped early. Saving progress...")
                self.save_deck(self.filepath or "deck.csv")
                return None, None
            elif key in [b'1', b'2', b'3', b'4', b'5']:
                response_time = time.time() - start_time
                choice = int(key.decode())
                if choice <= len(options):
                    # If hint was used, reduce score
                    correct = choice == correct_index
                    if correct and used_hint:
                        print(f"{Colors.YELLOW}✓ Correct (with hint): {choice}. {correct_formula}{Colors.RESET}")
                        return "hint_correct", response_time  # Special return value for reduced score
                    elif correct:
                        print(f"{Colors.GREEN}✓ Correct: {choice}. {correct_formula}{Colors.RESET}")
                        return True, response_time
                    else:
                        print(f"{Colors.RED}✗ Incorrect! You selected: {choice}. {options[choice-1]}{Colors.RESET}")
                        print(f"The correct answer was: {correct_index}. {correct_formula}")
                        return False, response_time
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
                start_time = time.time()  # Restart timing after hint
            elif key.lower() == b'h' and used_hint:
                print("Hint already used for this question.")
            else:
                print("Invalid input. Enter 1-5, 'h' for hint, or ESC.")
    
    def _mcq_practice_mode(self, card, allow_hints=True):
        """MCQ practice mode: Show question with multiple choice options"""
        print(f"Question: {card.question}")
        
        # Check if multiple answers are expected
        is_multiple = card.has_multiple_correct_answers()
        is_true_false = card.is_true_false_question()
        
        if is_multiple:
            print("Choose ALL correct answers (multiple answers possible):")
            if is_true_false:
                print("Enter your answers separated by commas (e.g., '1,2'):")
            else:
                print("Enter your answers separated by commas (e.g., '1,3' or '2,4'):")
        else:
            if is_true_false:
                print("Choose True or False:")
            else:
                print("Choose the correct answer:")
        
        # Get all options and available letters
        options = card.get_all_options()
        correct_answers_set = card.get_correct_answers_set()
        available_letters = card.get_available_option_letters()
        
        # Display options with numbers (dynamic based on available options)
        for i, letter in enumerate(available_letters, 1):
            print(f"{i}. {options[letter]}")
        
        # Get user input with timing
        start_time = time.time()
        used_hint = False
        response_time = None
        max_option = len(available_letters)
        available_options = list(range(1, max_option + 1))
        
        while True:
            hint_text = ", 'h' for hint" if allow_hints and not used_hint else ""
            if is_multiple:
                if is_true_false:
                    print(f"Enter your choices (e.g., '1,2'){hint_text}, or ESC to stop:")
                else:
                    print(f"Enter your choices (e.g., '1,3' or '2'){hint_text}, or ESC to stop:")
            else:
                if is_true_false:
                    print(f"Enter choice (1-2){hint_text}, or ESC to stop:")
                else:
                    print(f"Enter choice (1-{max_option}){hint_text}, or ESC to stop:")
                
            # For multiple answers, we need to read a string input
            if is_multiple:
                user_input = ""
                while True:
                    char = msvcrt.getch()
                    if char == b'\x1b':  # ESC key
                        print("\nSession stopped early. Saving progress...")
                        self.save_deck(self.filepath or "deck.csv")
                        return None, None
                    elif char in [b'\r', b'\n']:  # Enter key
                        break
                    elif char == b'\x08':  # Backspace
                        if user_input:
                            user_input = user_input[:-1]
                            print('\b \b', end='', flush=True)
                    else:
                        decoded_char = char.decode('utf-8', errors='ignore')
                        user_input += decoded_char
                        print(decoded_char, end='', flush=True)
                
                print()  # New line after input
                
                # Handle hint for multiple choice
                if user_input.lower() == 'h' and allow_hints and not used_hint:
                    # Remove some wrong options for hint
                    wrong_numbers = [i+1 for i, letter in enumerate(available_letters) 
                                   if letter not in correct_answers_set and i+1 in available_options]
                    numbers_to_remove = random.sample(wrong_numbers, min(max(1, len(wrong_numbers)//2), len(wrong_numbers)))
                    available_options = [num for num in available_options if num not in numbers_to_remove]
                    
                    print("\nHint used! Here are the remaining options:")
                    for num in available_options:
                        letter = available_letters[num - 1]
                        print(f"{num}. {options[letter]}")
                    used_hint = True
                    start_time = time.time()
                    continue
                elif user_input.lower() == 'h' and (not allow_hints or used_hint):
                    if not allow_hints:
                        print("Hints not available at this level.")
                    else:
                        print("Hint already used for this question.")
                    continue
                
                # Parse multiple selections - ORDER INDEPENDENT
                # Supports formats: "1,3", "3,1", "1 3", "3 1", "1, 3", etc.
                # All variations are treated as equivalent sets
                try:
                    # Parse input like "1,3,4" or "1 3 4" or "1, 3, 4" or "1,2" for True/False
                    # Order doesn't matter - "1,3" and "3,1" produce same result
                    selected_numbers = []
                    for part in user_input.replace(',', ' ').split():
                        num = int(part.strip())
                        if 1 <= num <= max_option and num in available_options:
                            selected_numbers.append(num)
                    
                    if not selected_numbers:
                        print(f"Please enter valid option numbers (1-{max_option}).")
                        continue
                        
                    response_time = time.time() - start_time
                    selected_letters = [available_letters[num - 1] for num in selected_numbers]
                    
                    # Calculate partial score
                    score, is_perfect, feedback = card.calculate_partial_score(selected_letters)
                    
                    # Display results
                    if is_perfect:
                        if used_hint:
                            safe_print(f"{Colors.YELLOW}✓ Perfect (with hint): {user_input}. Score: 100%{Colors.RESET}")
                            return "hint_correct", response_time
                        else:
                            safe_print(f"{Colors.GREEN}✓ Perfect: {user_input}. Score: 100%{Colors.RESET}")
                            return True, response_time
                    elif score > 0:
                        score_percent = int(score * 100)
                        color = Colors.YELLOW if score >= 0.5 else Colors.RED
                        safe_print(f"{color}◐ Partial Credit: {user_input}. Score: {score_percent}%{Colors.RESET}")
                        
                        # Show detailed feedback
                        if feedback['correctly_selected'] > 0:
                            correct_nums = [available_letters.index(ans) + 1 for ans in feedback['correct_answers'] if ans in selected_letters]
                            safe_print(f"  ✓ Correct: {', '.join(map(str, correct_nums))}")
                        if feedback['wrong_answers']:
                            wrong_nums = [available_letters.index(ans) + 1 for ans in feedback['wrong_answers']]
                            safe_print(f"  ✗ Incorrect: {', '.join(map(str, wrong_nums))}")
                        if feedback['missed_answers']:
                            missed_nums = [available_letters.index(ans) + 1 for ans in feedback['missed_answers']]
                            safe_print(f"  ○ Missed: {', '.join(map(str, missed_nums))}")
                        
                        # Return partial score as a special value
                        return ("partial", score), response_time
                    else:
                        safe_print(f"{Colors.RED}✗ Incorrect: {user_input}. Score: 0%{Colors.RESET}")
                        correct_nums = [available_letters.index(ans) + 1 for ans in feedback['correct_answers']]
                        print(f"The correct answers were: {', '.join(map(str, correct_nums))}")
                        return False, response_time
                        
                except ValueError:
                    if is_true_false:
                        print("Please enter valid numbers (1 or 2).")
                    else:
                        print(f"Please enter valid numbers separated by commas (1-{max_option}).")
                    continue
            else:
                # Single answer mode (original logic)
                key = msvcrt.getch()
                if key == b'\x1b':  # ESC key
                    print("\nSession stopped early. Saving progress...")
                    self.save_deck(self.filepath or "deck.csv")
                    return None, None
                elif key in [b'1', b'2', b'3', b'4'] and int(key.decode()) <= max_option:
                    choice_num = int(key.decode())
                    if choice_num in available_options:
                        response_time = time.time() - start_time
                        choice_letter = available_letters[choice_num - 1]
                        
                        if choice_letter in correct_answers_set:
                            if used_hint:
                                print(f"{Colors.YELLOW}✓ Correct (with hint): {choice_num}. {options[choice_letter]}{Colors.RESET}")
                                return "hint_correct", response_time
                            else:
                                print(f"{Colors.GREEN}✓ Correct: {choice_num}. {options[choice_letter]}{Colors.RESET}")
                                return True, response_time
                        else:
                            print(f"{Colors.RED}✗ Incorrect! You selected: {choice_num}. {options[choice_letter]}{Colors.RESET}")
                            correct_nums = [available_letters.index(ans) + 1 for ans in correct_answers_set]
                            print(f"The correct answer was: {', '.join(map(str, correct_nums))}")
                            return False, response_time
                    else:
                        print(f"Option {choice_num} not available.")
                        
                elif key.lower() == b'h' and allow_hints and not used_hint:
                    # For single MCQ, show a hint by eliminating wrong options
                    wrong_numbers = [i+1 for i, letter in enumerate(available_letters) 
                                   if letter not in correct_answers_set and i+1 in available_options]
                    numbers_to_remove = random.sample(wrong_numbers, min(max(1, len(wrong_numbers)//2), len(wrong_numbers)))
                    available_options = [num for num in available_options if num not in numbers_to_remove]
                    
                    print("\nHint used! Here are the remaining options:")
                    for num in available_options:
                        letter = available_letters[num - 1]
                        print(f"{num}. {options[letter]}")
                    used_hint = True
                    start_time = time.time()  # Restart timing after hint
                    
                elif key.lower() == b'h' and (not allow_hints or used_hint):
                    if not allow_hints:
                        print("Hints not available at this level.")
                    else:
                        print("Hint already used for this question.")
                else:
                    print("Invalid input. Enter 1-4, or ESC.")