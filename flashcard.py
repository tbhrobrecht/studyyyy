from datetime import datetime, timedelta

class Flashcard:
    def __init__(self, term, definition, ease=2.5, interval=1, repetitions=0, last_review=None, formula=None):
        self.term = term
        self.definition = definition
        self.ease = float(ease)
        self.interval = int(interval)
        self.repetitions = int(repetitions)
        self.last_review = datetime.fromisoformat(last_review) if last_review else None
        self.formula = formula  # Add formula support

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
            self.repetitions = 0
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
        
        # # Update easiness factor with stage-specific adjustments
        # if stage == 2 and quality >= 4:  # Stage 2 (Definition -> Term) with correct answer
        #     # Custom increase for stage 2: +0.25 ease points, modified by time
        #     ease_change = 0.25 * time_modifier
        #     self.ease = max(1.3, self.ease + ease_change)
        # else:
        #     # Standard SM-2 algorithm with time modification
        #     # EF':= EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)) * time_modifier
        #     base_ease_change = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        #     ease_change = base_ease_change * time_modifier
        #     self.ease = max(1.3, self.ease + ease_change)

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
            