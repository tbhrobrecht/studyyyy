"""Question handler classes for MCQ flashcard question types.

Provides a strategy pattern for handling True/False, single-answer MCQ,
and multi-answer MCQ questions.  Each handler encapsulates prompt display,
option shuffling, user-input parsing, hint logic, and result computation.
"""

import random
import time
import msvcrt
from abc import ABC, abstractmethod


# ---------------------------------------------------------------------------
# UI helpers  (canonical definitions – imported by learn_simulator)
# ---------------------------------------------------------------------------

class Colors:
    GREEN = '\033[92m'    # Bright green for correct answers
    RED = '\033[91m'      # Bright red for incorrect answers
    YELLOW = '\033[93m'   # Yellow for hints
    BLUE = '\033[94m'     # Blue for info
    BOLD = '\033[1m'      # Bold text
    RESET = '\033[0m'     # Reset to default color


def safe_print(text):
    """Print text safely, replacing problematic Unicode characters for Windows console."""
    try:
        print(text)
    except UnicodeEncodeError:
        safe_text = (text
                     .replace('\u2713', 'OK').replace('\u2717', 'X')
                     .replace('\U0001f4d6', '[BOOK]').replace('\U0001f393', '[GRAD]')
                     .replace('\u2192', '->').replace('\u2190', '<-'))
        print(safe_text)


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def shuffle_options(card):
    """Shuffle MCQ options and return *(shuffled_letters, options_dict, max_option)*."""
    options = card.get_all_options()
    available_letters = card.get_available_option_letters()
    shuffled_letters = available_letters.copy()
    random.shuffle(shuffled_letters)
    return shuffled_letters, options, len(shuffled_letters)


def display_options(shuffled_letters, options, available_numbers=None):
    """Print numbered options.  *available_numbers* filters which to show."""
    for i, letter in enumerate(shuffled_letters, 1):
        if available_numbers is None or i in available_numbers:
            print(f"{i}. {options[letter]}")


def eliminate_wrong_options(shuffled_letters, correct_answers_set, available_options):
    """Remove roughly half of the wrong options (for hint).  Returns updated list."""
    wrong_numbers = [
        i + 1
        for i, letter in enumerate(shuffled_letters)
        if letter not in correct_answers_set and (i + 1) in available_options
    ]
    count = min(max(1, len(wrong_numbers) // 2), len(wrong_numbers))
    numbers_to_remove = random.sample(wrong_numbers, count)
    return [num for num in available_options if num not in numbers_to_remove]


def compute_correct_display_numbers(shuffled_letters, correct_answers_set):
    """Return list of display numbers corresponding to correct answer letters."""
    return [shuffled_letters.index(ans) + 1 for ans in correct_answers_set]


def show_explanation(card):
    """Print the card's explanation if one exists."""
    if hasattr(card, 'explanation') and card.explanation:
        safe_print(f"{Colors.BLUE}\U0001f4d6 Explanation: {card.explanation}{Colors.RESET}")


def save_and_stop(sim):
    """Print stop message and persist deck progress."""
    print("\nSession stopped early. Saving progress...")
    sim.save_deck(sim.filepath or "deck.csv")


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def _read_line():
    """Read a line character-by-character via *msvcrt*, with backspace support.

    Returns the entered string, or ``None`` if ESC was pressed.
    """
    buf = ""
    while True:
        char = msvcrt.getch()
        if char == b'\x1b':
            return None  # ESC
        if char in (b'\r', b'\n'):
            print()  # move to next line after user presses Enter
            return buf
        if char == b'\x08':  # Backspace
            if buf:
                buf = buf[:-1]
                print('\b \b', end='', flush=True)
        else:
            decoded = char.decode('utf-8', errors='ignore')
            buf += decoded
            print(decoded, end='', flush=True)


# ---------------------------------------------------------------------------
# Single-answer shared loop  (used by TrueFalseHandler & McqSingleHandler)
# ---------------------------------------------------------------------------

def _single_answer_loop(sim, card, shuffled_letters, options, correct_set,
                         max_option, allow_hints, prompt_fn):
    """Common input loop for single-answer questions (TF and single MCQ).

    *prompt_fn(hint_text)* is called each iteration to print the
    type-specific prompt line.
    """
    start_time = time.time()
    used_hint = False
    available_options = list(range(1, max_option + 1))

    while True:
        hint_text = ", 'h' for hint" if allow_hints and not used_hint else ""
        prompt_fn(hint_text)

        key = msvcrt.getch()

        if key == b'\x1b':
            save_and_stop(sim)
            return None, None

        if key in (b'1', b'2', b'3', b'4') and int(key.decode()) <= max_option:
            choice_num = int(key.decode())
            if choice_num in available_options:
                response_time = time.time() - start_time
                choice_letter = shuffled_letters[choice_num - 1]

                if choice_letter in correct_set:
                    if used_hint:
                        print(f"{Colors.YELLOW}\u2713 Correct (with hint): "
                              f"{choice_num}. {options[choice_letter]}{Colors.RESET}")
                    else:
                        print(f"{Colors.GREEN}\u2713 Correct: "
                              f"{choice_num}. {options[choice_letter]}{Colors.RESET}")
                    show_explanation(card)
                    return ("hint_correct" if used_hint else True), response_time
                else:
                    print(f"{Colors.RED}\u2717 Incorrect! You selected: "
                          f"{choice_num}. {options[choice_letter]}{Colors.RESET}")
                    correct_nums = compute_correct_display_numbers(
                        shuffled_letters, correct_set)
                    print(f"The correct answer was: "
                          f"{', '.join(map(str, correct_nums))}")
                    show_explanation(card)
                    return False, response_time
            else:
                print(f"Option {choice_num} not available.")

        elif key.lower() == b'h' and allow_hints and not used_hint:
            available_options = eliminate_wrong_options(
                shuffled_letters, correct_set, available_options)
            print("\nHint used! Here are the remaining options:")
            display_options(shuffled_letters, options, available_options)
            used_hint = True
            start_time = time.time()  # Restart timing after hint

        elif key.lower() == b'h':
            if not allow_hints:
                print("Hints not available at this level.")
            else:
                print("Hint already used for this question.")
        else:
            print("Invalid input. Enter 1-4, or ESC.")


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class QuestionHandler(ABC):
    """Strategy interface for asking a single MCQ-type question."""

    @abstractmethod
    def ask(self, sim, card, allow_hints=True):
        """Present the question, collect the user's answer, and return the result.

        Returns
        -------
        tuple (result, response_time)
            result : True | False | "hint_correct" | ("partial", float) | None
            response_time : float (seconds) | None  (None when ESC pressed)
        """


# ---------------------------------------------------------------------------
# TrueFalseHandler
# ---------------------------------------------------------------------------

class TrueFalseHandler(QuestionHandler):
    """Handler for True/False questions (exactly 2 options, single correct)."""

    def ask(self, sim, card, allow_hints=True):
        print(f"Question: {card.question}")
        print("Choose True or False:")

        # Fixed order for TF: True is always 1, False always 2
        options = card.get_all_options()
        shuffled_letters = card.get_available_option_letters()  # sorted: ['a', 'b']
        max_option = len(shuffled_letters)
        display_options(shuffled_letters, options)
        correct_set = card.get_correct_answers_set()

        def prompt(hint_text):
            print(f"Enter choice (1-2){hint_text}, or ESC to stop:")

        return _single_answer_loop(
            sim, card, shuffled_letters, options, correct_set,
            max_option, allow_hints, prompt)


# ---------------------------------------------------------------------------
# McqSingleHandler
# ---------------------------------------------------------------------------

class McqSingleHandler(QuestionHandler):
    """Handler for single-answer MCQ questions (3-4 options, one correct)."""

    def ask(self, sim, card, allow_hints=True):
        print(f"Question: {card.question}")
        print("Choose the correct answer:")

        shuffled_letters, options, max_option = shuffle_options(card)
        display_options(shuffled_letters, options)
        correct_set = card.get_correct_answers_set()

        def prompt(hint_text):
            print(f"Enter choice (1-{max_option}){hint_text}, or ESC to stop:")

        return _single_answer_loop(
            sim, card, shuffled_letters, options, correct_set,
            max_option, allow_hints, prompt)


# ---------------------------------------------------------------------------
# McqMultiHandler
# ---------------------------------------------------------------------------

class McqMultiHandler(QuestionHandler):
    """Handler for multi-answer MCQ questions (partial-credit scoring)."""

    def ask(self, sim, card, allow_hints=True):
        print(f"Question: {card.question}")

        is_two_option = card.is_true_false_question()

        print("Choose ALL correct answers (multiple answers possible):")
        if is_two_option:
            print("Enter your answers separated by commas (e.g., '1,2'):")
        else:
            print("Enter your answers separated by commas (e.g., '1,3' or '2,4'):")

        shuffled_letters, options, max_option = shuffle_options(card)
        display_options(shuffled_letters, options)
        correct_set = card.get_correct_answers_set()

        start_time = time.time()
        used_hint = False
        available_options = list(range(1, max_option + 1))

        while True:
            hint_text = (", 'h' for hint"
                         if allow_hints and not used_hint else "")
            if is_two_option:
                print(f"Enter your choices (e.g., '1,2')"
                      f"{hint_text}, or ESC to stop:")
            else:
                print(f"Enter your choices (e.g., '1,3' or '2')"
                      f"{hint_text}, or ESC to stop:")

            user_input = _read_line()
            if user_input is None:  # ESC
                save_and_stop(sim)
                return None, None

            # -- Hint request ------------------------------------------------
            if user_input.lower() == 'h' and allow_hints and not used_hint:
                available_options = eliminate_wrong_options(
                    shuffled_letters, correct_set, available_options)
                print("\nHint used! Here are the remaining options:")
                display_options(shuffled_letters, options, available_options)
                used_hint = True
                start_time = time.time()
                continue
            elif user_input.lower() == 'h':
                if not allow_hints:
                    print("Hints not available at this level.")
                else:
                    print("Hint already used for this question.")
                continue

            # -- Parse multiple selections -----------------------------------
            try:
                selected_numbers = []
                for part in user_input.replace(',', ' ').split():
                    num = int(part.strip())
                    if 1 <= num <= max_option and num in available_options:
                        selected_numbers.append(num)

                if not selected_numbers:
                    print(f"Please enter valid option numbers (1-{max_option}).")
                    continue

                response_time = time.time() - start_time
                selected_letters = [shuffled_letters[n - 1]
                                    for n in selected_numbers]

                score, is_perfect, feedback = card.calculate_partial_score(
                    selected_letters)

                return self._report_result(
                    user_input, score, is_perfect, feedback,
                    shuffled_letters, selected_letters, card,
                    used_hint, response_time)

            except ValueError:
                if is_two_option:
                    print("Please enter valid numbers (1 or 2).")
                else:
                    print("Please enter valid numbers separated by "
                          f"commas (1-{max_option}).")
                continue

    # ------------------------------------------------------------------ #
    @staticmethod
    def _report_result(user_input, score, is_perfect, feedback,
                       shuffled_letters, selected_letters, card,
                       used_hint, response_time):
        """Format and print result feedback; return (result, response_time)."""
        if is_perfect:
            if used_hint:
                safe_print(f"{Colors.YELLOW}\u2713 Perfect (with hint): "
                           f"{user_input}. Score: 100%{Colors.RESET}")
            else:
                safe_print(f"{Colors.GREEN}\u2713 Perfect: "
                           f"{user_input}. Score: 100%{Colors.RESET}")
            show_explanation(card)
            return ("hint_correct" if used_hint else True), response_time

        if score > 0:
            score_percent = int(score * 100)
            color = Colors.YELLOW if score >= 0.5 else Colors.RED
            safe_print(f"{color}\u25d0 Partial Credit: "
                       f"{user_input}. Score: {score_percent}%{Colors.RESET}")

            if feedback['correctly_selected'] > 0:
                correct_nums = [
                    shuffled_letters.index(ans) + 1
                    for ans in feedback['correct_answers']
                    if ans in selected_letters
                ]
                safe_print(f"  \u2713 Correct: "
                           f"{', '.join(map(str, correct_nums))}")
            if feedback['wrong_answers']:
                wrong_nums = [shuffled_letters.index(ans) + 1
                              for ans in feedback['wrong_answers']]
                safe_print(f"  \u2717 Incorrect: "
                           f"{', '.join(map(str, wrong_nums))}")
            if feedback['missed_answers']:
                missed_nums = [shuffled_letters.index(ans) + 1
                               for ans in feedback['missed_answers']]
                safe_print(f"  \u25cb Missed: "
                           f"{', '.join(map(str, missed_nums))}")

            show_explanation(card)
            return ("partial", score), response_time

        # score == 0 → fully incorrect
        safe_print(f"{Colors.RED}\u2717 Incorrect: "
                   f"{user_input}. Score: 0%{Colors.RESET}")
        correct_nums = [shuffled_letters.index(ans) + 1
                        for ans in feedback['correct_answers']]
        print(f"The correct answers were: "
              f"{', '.join(map(str, correct_nums))}")
        show_explanation(card)
        return False, response_time


# ---------------------------------------------------------------------------
# Self-check (run with: python question_handlers.py)
# ---------------------------------------------------------------------------

def _self_check():
    """Verify question_kind classification and get_all_options behaviour."""
    from flashcard import Flashcard  # local import to avoid circular at module level

    # -- True/False card --
    tf = Flashcard(
        question="Is the sky blue?",
        option_a="True", option_b="False",
        option_c=None, option_d=None,
        correct_answer="a",
    )
    assert tf.question_kind == 'tf', f"Expected 'tf', got '{tf.question_kind}'"
    assert len(tf.get_all_options()) == 2
    assert tf.is_true_false_question() is True

    # -- Single-answer MCQ --
    single = Flashcard(
        question="What is 2+2?",
        option_a="3", option_b="4", option_c="5", option_d="6",
        correct_answer="b",
    )
    assert single.question_kind == 'mcq_single', \
        f"Expected 'mcq_single', got '{single.question_kind}'"
    assert len(single.get_all_options()) == 4
    assert single.is_true_false_question() is False

    # -- Multi-answer MCQ --
    multi = Flashcard(
        question="Which are prime?",
        option_a="2", option_b="4", option_c="3", option_d="6",
        correct_answer="a,c",
    )
    assert multi.question_kind == 'mcq_multi', \
        f"Expected 'mcq_multi', got '{multi.question_kind}'"
    assert len(multi.get_all_options()) == 4
    assert multi.get_correct_answers_set() == {'a', 'c'}

    # -- Vocabulary card (not MCQ) --
    vocab = Flashcard(term="Hello", definition="Hola")
    assert vocab.question_kind is None

    print("All self-checks passed!")


if __name__ == "__main__":
    _self_check()
