from datetime import datetime, timedelta
import math

class Flashcard:
    def __init__(self, term=None, definition=None, ease=2.5, interval=1, repetitions=0, last_review=None, formula=None, 
                 question=None, option_a=None, option_b=None, option_c=None, option_d=None, correct_answer=None, explanation=None):
        # Vocabulary format fields
        self.term = term
        self.definition = definition
        self.formula = formula  # Add formula support
        
        # MCQ format fields
        self.question = question
        self.option_a = option_a
        self.option_b = option_b
        self.option_c = option_c
        self.option_d = option_d
        self.explanation = explanation  # Add explanation for MCQ questions
        
        # Handle multiple correct answers (can be 'a', 'a,b', 'a,c,d', etc.)
        if correct_answer and isinstance(correct_answer, str):
            self.correct_answers = [ans.strip().lower() for ans in correct_answer.split(',')]
        else:
            self.correct_answers = [correct_answer.lower()] if correct_answer else []
        
        # Keep backward compatibility
        self.correct_answer = correct_answer
        
        # Common fields for both formats
        self.ease = float(ease)
        self.interval = int(interval)
        self.repetitions = int(repetitions)
        self.last_review = datetime.fromisoformat(last_review) if last_review else None
        
        # Determine card type
        self.card_type = 'mcq' if question is not None else 'vocabulary'

    def review(self, quality, stage=None, response_time=None):
        """
        Apply SM-2 algorithm based on quality (0-5 scale) with time factor
        quality >= 3: correct response, otherwise incorrect
        stage: Optional stage info for custom ease adjustments
        response_time: Time in seconds it took to answer (for ease adjustment)
        """
        old_ease = self.ease  # Store old ease for debugging
        
        if quality < 3:
            # Reset repetition
            self.repetitions = math.floor(self.repetitions / 2)
            self.interval = 1
        else:
            # Increase repetition
            self.repetitions += 1
            if self.repetitions == 1:
                self.interval = 1
            elif self.repetitions == 2:
                self.interval = 6
            else:
                self.interval = int(self.interval * self.ease)
        
        # Calculate time-based modifier for ease adjustment
        time_modifier = self._calculate_time_modifier(response_time) if response_time is not None else 1.0
        
        # Standard SM-2 algorithm with time modification
        base_ease_change = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        ease_change = 5 * base_ease_change * time_modifier
        self.ease = max(1.3, self.ease + ease_change)
         
        self.last_review = datetime.now()
    
    def _calculate_time_modifier(self, response_time):
        """
        Calculate a time-based modifier for ease adjustments
        
        Time ranges and modifiers:
        - 0-3 seconds: 1.2x bonus (very fast, confident)
        - 3-6 seconds: 1.1x bonus (fast, good recall)
        - 6-12 seconds: 1.0x normal (average time)
        - 12-20 seconds: 0.9x penalty (slow, uncertain)
        - 20+ seconds: 0.8x penalty (very slow, struggling)
        """
        if response_time <= 3:
            return 1.2  # Fast response bonus
        elif response_time <= 6:
            return 1.1  # Good response bonus
        elif response_time <= 12:
            return 1.0  # Normal response
        elif response_time <= 20:
            return 0.9  # Slow response penalty
        else:
            return 0.8  # Very slow response penalty

    def next_due(self):
        if not self.last_review:
            return datetime.now()
        return self.last_review + timedelta(days=self.interval)

    def to_dict(self):
        if self.card_type == 'mcq':
            result = {
                "question": self.question,
                "option_a": self.option_a,
                "option_b": self.option_b,
                "option_c": self.option_c,
                "option_d": self.option_d,
                "correct_answer": self.correct_answer,
                "explanation": self.explanation if hasattr(self, 'explanation') and self.explanation else "",
                "ease": round(self.ease, 3),  # Round to 3 decimal places for precision
                "repetitions": self.repetitions,
                "last_review": self.last_review.strftime('%Y-%m-%d') if self.last_review else None
            }
        else:  # vocabulary format
            result = {
                "term": self.term,
                "definition": self.definition,
                "ease": round(self.ease, 3),  # Round to 3 decimal places for precision
                "repetitions": self.repetitions,
                "last_review": self.last_review.strftime('%Y-%m-%d') if self.last_review else None
            }
            
            # Include formula if it exists
            if hasattr(self, 'formula') and self.formula:
                result["formula"] = self.formula
                
        return result
    
    def get_question_text(self):
        """Get the question text depending on card type"""
        return self.question if self.card_type == 'mcq' else self.term
    
    def get_answer_text(self):
        """Get the answer text depending on card type"""
        if self.card_type == 'mcq':
            options = {
                'a': self.option_a,
                'b': self.option_b,
                'c': self.option_c,
                'd': self.option_d
            }
            if len(self.correct_answers) == 1:
                return options.get(self.correct_answers[0], 'Unknown')
            else:
                # Multiple correct answers
                answers = [options.get(ans, 'Unknown') for ans in self.correct_answers]
                return ', '.join(answers)
        else:
            return self.definition
    
    def get_all_options(self):
        """Get all options for MCQ cards"""
        if self.card_type == 'mcq':
            options = {
                'a': self.option_a,
                'b': self.option_b,
                'c': self.option_c,
                'd': self.option_d
            }
            # Filter out empty/None options for True/False questions
            return {k: v for k, v in options.items() if v is not None and str(v).strip()}
        return None
    
    @property
    def question_kind(self):
        """Classify MCQ question type: 'tf', 'mcq_single', 'mcq_multi', or None (vocab)."""
        if self.card_type != 'mcq':
            return None
        options = self.get_all_options()
        if (len(options) == 2 and 'a' in options and 'b' in options
                and len(self.correct_answers) == 1):
            return 'tf'
        elif len(self.correct_answers) > 1:
            return 'mcq_multi'
        else:
            return 'mcq_single'

    def is_true_false_question(self):
        """Check if this is a True/False question (only options A and B)"""
        if self.card_type != 'mcq':
            return False
        options = self.get_all_options()
        return len(options) == 2 and 'a' in options and 'b' in options
    
    def get_available_option_letters(self):
        """Get list of available option letters (for True/False vs full MCQ)"""
        if self.card_type != 'mcq':
            return []
        options = self.get_all_options()
        return sorted(options.keys())
    
    def has_multiple_correct_answers(self):
        """Check if this MCQ has multiple correct answers"""
        return self.card_type == 'mcq' and len(self.correct_answers) > 1
    
    def get_correct_answers_set(self):
        """Get the set of correct answer letters"""
        return set(self.correct_answers) if self.card_type == 'mcq' else set()
    
    def calculate_partial_score(self, selected_answers):
        """
        Calculate partial score for multiple correct answer questions
        Returns a tuple: (score, is_perfect, feedback_info)
        
        ORDER INDEPENDENT: Uses sets for comparison, so ['a','c'] and ['c','a'] 
        produce identical results. User can enter answers in any order.
        
        score: float between 0 and 1 representing percentage correct
        is_perfect: bool indicating if all correct answers were selected and no incorrect ones
        feedback_info: dict with details for feedback display
        """
        if self.card_type != 'mcq':
            return 1.0, True, {}
            
        # Convert to sets for order-independent comparison
        correct_set = self.get_correct_answers_set()
        selected_set = set(selected_answers) if isinstance(selected_answers, list) else {selected_answers}
        
        # Calculate score components
        total_correct = len(correct_set)
        correctly_selected = len(correct_set.intersection(selected_set))
        incorrectly_selected = len(selected_set - correct_set)
        
        # Partial scoring: points for correct selections, penalty for incorrect ones
        if total_correct == 0:
            return 0.0, False, {}
            
        # Base score: proportion of correct answers found
        base_score = correctly_selected / total_correct
        
        # Penalty for selecting wrong answers (reduces score)
        penalty = incorrectly_selected * 0.25  # 25% penalty per wrong selection
        final_score = max(0.0, base_score - penalty)
        
        # Perfect score only if all correct and no incorrect selections
        is_perfect = correctly_selected == total_correct and incorrectly_selected == 0
        
        feedback_info = {
            'total_correct': total_correct,
            'correctly_selected': correctly_selected,
            'incorrectly_selected': incorrectly_selected,
            'correct_answers': sorted(list(correct_set)),
            'selected_answers': sorted(list(selected_set)),
            'missed_answers': sorted(list(correct_set - selected_set)),
            'wrong_answers': sorted(list(selected_set - correct_set))
        }
        
        return final_score, is_perfect, feedback_info
            