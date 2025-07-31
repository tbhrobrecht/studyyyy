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

    def review(self, quality):
        """
        Apply SM-2 algorithm based on quality (0-5 scale)
        quality >= 3: correct response, otherwise incorrect
        """
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
        # Update easiness factor
        # EF':= EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        self.ease = max(1.3, self.ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        self.last_review = datetime.now()

    def next_due(self):
        if not self.last_review:
            return datetime.now()
        return self.last_review + timedelta(days=self.interval)

    def to_dict(self):
        result = {
            "term": self.term,
            "definition": self.definition,
            "ease": self.ease,
            "interval": self.interval,
            "repetitions": self.repetitions,
            "last_review": self.last_review.isoformat() if self.last_review else None
        }
        
        # Include formula if it exists
        if hasattr(self, 'formula') and self.formula:
            result["formula"] = self.formula
            
        return result
            