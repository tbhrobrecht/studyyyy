#!/usr/bin/env python3
"""
CSV Formatter for MCQ Templates
Converts raw CSV files into the proper MCQ format for the flashcard system.

Usage: python csv_formatter.py input_file.csv

Output will be automatically saved to vocabulary_template/ directory with auto-increment naming.
"""

import csv
import sys
import os
import re
from typing import List, Dict, Tuple

class CSVFormatter:
    def __init__(self):
        self.converted_rows = []
        self.conversion_stats = {
            'total_rows': 0,
            'true_false_converted': 0,
            'fill_in_blank_converted': 0,
            'already_formatted': 0,
            'skipped': 0
        }
    
    def detect_row_type(self, row: Dict) -> str:
        """Detect what type of question this row represents"""
        # Check if it's already properly formatted MCQ
        required_mcq_columns = ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
        if all(col in row for col in required_mcq_columns):
            # Check if the options are actually filled out
            if (str(row.get('option_a') or '').strip() and str(row.get('option_b') or '').strip() and 
                str(row.get('option_c') or '').strip() and str(row.get('option_d') or '').strip() and
                str(row.get('correct_answer') or '').strip()):
                return 'formatted_mcq'
        
        # Check for question + option_a format (answer in option_a column)
        if ('question' in row and 'option_a' in row and 
            row.get('question') and row.get('option_a') and
            (not row.get('option_b') or not str(row.get('option_b') or '').strip()) and
            (not row.get('correct_answer') or not str(row.get('correct_answer') or '').strip())):
            
            answer = str(row['option_a'] or '').strip()
            if answer in ['0', '1']:
                return 'question_optiona_tf'
            elif answer:
                return 'question_optiona_fill'
        
        # Check for comma-separated format in question column (like "question, answer")
        question_content = str(row.get('question') or '').strip()
        if ',' in question_content:
            parts = question_content.split(',')
            if len(parts) == 2:
                question_part = parts[0].strip()
                answer_part = parts[1].strip()
                
                # True/False: answer is 0 or 1
                if answer_part in ['0', '1']:
                    return 'comma_separated_tf'
                
                # Fill-in-blank: answer is text
                if answer_part and answer_part not in ['0', '1']:
                    return 'comma_separated_fill'
        
        # Check if it has question and answer columns
        if 'question' in row and 'correct_answer' in row:
            answer = str(row.get('correct_answer') or '').strip()
            
            # True/False: answer is 0 or 1
            if answer in ['0', '1']:
                return 'true_false'
            
            # Fill-in-blank: answer is text
            if answer and answer not in ['0', '1']:
                return 'fill_in_blank'
        
        # Check if it's a two-column format (question, answer)
        keys = [k for k in row.keys() if k and str(row.get(k) or '').strip()]
        if len(keys) == 2:
            values = [str(row[k] or '').strip() for k in keys if str(row.get(k) or '').strip()]
            if len(values) == 2:
                # Check if second value is 0/1 (True/False)
                if values[1] in ['0', '1']:
                    return 'two_column_tf'
                # Otherwise it's fill-in-blank
                return 'two_column_fill'
        
        return 'unknown'
    
    def convert_true_false(self, question: str, answer: str) -> Dict:
        """Convert True/False question to standardized format"""
        # Standardize: 1=True (option_a), 2=False (option_b)
        correct_letter = 'a' if answer == '1' else 'b'
        
        return {
            'question': question.strip(),
            'option_a': 'True',
            'option_b': 'False', 
            'option_c': '',
            'option_d': '',
            'correct_answer': correct_letter
        }
    
    def convert_fill_in_blank(self, question: str, answer: str) -> Dict:
        """Convert fill-in-blank to multiple choice format"""
        correct_answer = answer.strip()
        
        # Generate plausible wrong answers based on the question context
        wrong_answers = self.generate_wrong_answers(question, correct_answer)
        
        # Randomly place correct answer in one of the four positions
        import random
        correct_position = random.choice(['a', 'b', 'c', 'd'])
        
        options = {'a': '', 'b': '', 'c': '', 'd': ''}
        options[correct_position] = correct_answer
        
        # Fill other positions with wrong answers
        remaining_positions = [pos for pos in ['a', 'b', 'c', 'd'] if pos != correct_position]
        for i, pos in enumerate(remaining_positions):
            if i < len(wrong_answers):
                options[pos] = wrong_answers[i]
            else:
                options[pos] = f"Option {pos.upper()}"
        
        return {
            'question': question.strip(),
            'option_a': options['a'],
            'option_b': options['b'],
            'option_c': options['c'],
            'option_d': options['d'],
            'correct_answer': correct_position
        }
    
    def generate_wrong_answers(self, question: str, correct_answer: str) -> List[str]:
        """Generate plausible wrong answers based on question context"""
        wrong_answers = []
        
        # Algorithm/CS specific wrong answers
        cs_terms = [
            'O(n)', 'O(n^2)', 'O(log n)', 'O(1)', 'O(n log n)',
            'Θ(n)', 'Θ(n^2)', 'Θ(log n)', 'Θ(1)', 'Θ(n log n)',
            'Ω(n)', 'Ω(n^2)', 'Ω(log n)', 'Ω(1)', 'Ω(n log n)',
            'Incremental', 'Divide-and-Conquer', 'Dynamic Programming',
            'Greedy', 'Brute Force', 'Backtracking',
            'QuickSort', 'MergeSort', 'HeapSort', 'BubbleSort',
            'floor(log n)', 'ceil(log n)', '2^n', '2^(h+1)', '2^h',
            'Linear', 'Quadratic', 'Exponential', 'Logarithmic'
        ]
        
        # Math specific wrong answers
        math_terms = [
            'n', 'n^2', 'n^3', 'log n', '2^n', 'n!',
            'floor(n)', 'ceil(n)', 'sqrt(n)', 
            '2^(n+1)', '2^(n-1)', 'n-1', 'n+1'
        ]
        
        # Combine relevant terms
        all_terms = cs_terms + math_terms
        
        # Filter out the correct answer and select different ones
        candidates = [term for term in all_terms if term.lower() != correct_answer.lower()]
        
        # Try to pick contextually relevant wrong answers
        question_lower = question.lower()
        
        # For algorithm questions
        if any(word in question_lower for word in ['sort', 'heap', 'merge', 'quick']):
            algorithm_answers = ['Incremental', 'Divide-and-Conquer', 'Dynamic Programming']
            wrong_answers.extend([ans for ans in algorithm_answers if ans != correct_answer][:2])
        
        # For complexity questions
        elif any(symbol in question for symbol in ['O(', 'Θ(', 'Ω(', 'o(', 'ω(']):
            complexity_answers = ['O(n)', 'O(n^2)', 'O(log n)', 'Θ(n log n)']
            wrong_answers.extend([ans for ans in complexity_answers if ans != correct_answer][:2])
        
        # For heap questions
        elif 'heap' in question_lower:
            heap_answers = ['floor(log n)', 'ceil(log n)', '2^h', '2^(h+1)']
            wrong_answers.extend([ans for ans in heap_answers if ans != correct_answer][:2])
        
        # Fill remaining slots with random candidates
        while len(wrong_answers) < 3:
            if candidates:
                import random
                choice = random.choice(candidates)
                if choice not in wrong_answers:
                    wrong_answers.append(choice)
                candidates.remove(choice)
            else:
                wrong_answers.append(f"Alternative {len(wrong_answers) + 1}")
        
        return wrong_answers[:3]  # Return exactly 3 wrong answers
    
    def process_row(self, row: Dict, row_num: int) -> Dict:
        """Process a single row and convert it to MCQ format"""
        row_type = self.detect_row_type(row)
        
        try:
            if row_type == 'formatted_mcq':
                self.conversion_stats['already_formatted'] += 1
                return row
            
            elif row_type == 'comma_separated_tf':
                # Handle "question, answer" format where answer is 0/1
                question_content = str(row['question'] or '').strip()
                parts = question_content.split(',', 1)  # Split only on first comma
                question = parts[0].strip()
                answer = parts[1].strip()
                converted = self.convert_true_false(question, answer)
                self.conversion_stats['true_false_converted'] += 1
                return converted
            
            elif row_type == 'comma_separated_fill':
                # Handle "question, answer" format where answer is text
                question_content = str(row['question'] or '').strip()
                parts = question_content.split(',', 1)  # Split only on first comma
                question = parts[0].strip()
                answer = parts[1].strip()
                converted = self.convert_fill_in_blank(question, answer)
                self.conversion_stats['fill_in_blank_converted'] += 1
                return converted
            
            elif row_type == 'question_optiona_tf':
                # Handle question in 'question' column, True/False answer in 'option_a' column
                question = str(row['question'] or '').strip()
                answer = str(row['option_a'] or '').strip()
                converted = self.convert_true_false(question, answer)
                self.conversion_stats['true_false_converted'] += 1
                return converted
            
            elif row_type == 'question_optiona_fill':
                # Handle question in 'question' column, text answer in 'option_a' column
                question = str(row['question'] or '').strip()
                answer = str(row['option_a'] or '').strip()
                converted = self.convert_fill_in_blank(question, answer)
                self.conversion_stats['fill_in_blank_converted'] += 1
                return converted
            
            elif row_type == 'true_false':
                question = str(row['question'] or '').strip()
                answer = str(row['correct_answer'] or '').strip()
                converted = self.convert_true_false(question, answer)
                self.conversion_stats['true_false_converted'] += 1
                return converted
            
            elif row_type == 'fill_in_blank':
                question = str(row['question'] or '').strip()
                answer = str(row['correct_answer'] or '').strip()
                converted = self.convert_fill_in_blank(question, answer)
                self.conversion_stats['fill_in_blank_converted'] += 1
                return converted
            
            elif row_type == 'two_column_tf':
                # Handle two-column True/False format
                keys = [k for k in row.keys() if k and str(row.get(k) or '').strip()]
                question = str(row[keys[0]] or '').strip()
                answer = str(row[keys[1]] or '').strip()
                converted = self.convert_true_false(question, answer)
                self.conversion_stats['true_false_converted'] += 1
                return converted
            
            elif row_type == 'two_column_fill':
                # Handle two-column fill-in-blank format
                keys = [k for k in row.keys() if k and str(row.get(k) or '').strip()]
                question = str(row[keys[0]] or '').strip()
                answer = str(row[keys[1]] or '').strip()
                converted = self.convert_fill_in_blank(question, answer)
                self.conversion_stats['fill_in_blank_converted'] += 1
                return converted
            
            else:
                print(f"Warning: Row {row_num} has unknown format, skipping: {row}")
                self.conversion_stats['skipped'] += 1
                return None
                
        except Exception as e:
            print(f"Error processing row {row_num}: {e}")
            self.conversion_stats['skipped'] += 1
            return None
    
    def convert_file(self, input_file: str, output_file: str):
        """Convert entire CSV file from raw format to MCQ format"""
        print(f"Converting {input_file} to {output_file}...")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as infile:
                # Try to detect the delimiter and format
                sample = infile.read(1024)
                infile.seek(0)
                
                # Detect if it has headers
                has_headers = 'question' in sample.lower() or 'option_' in sample.lower()
                
                if has_headers:
                    reader = csv.DictReader(infile)
                else:
                    # No headers, create generic ones
                    reader = csv.DictReader(infile, fieldnames=['question', 'correct_answer'])
                
                rows_processed = 0
                for row_num, row in enumerate(reader, 1):
                    self.conversion_stats['total_rows'] += 1
                    
                    converted_row = self.process_row(row, row_num)
                    if converted_row:
                        self.converted_rows.append(converted_row)
                        rows_processed += 1
            
            # Write converted data
            if self.converted_rows:
                with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
                    fieldnames = ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
                    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.converted_rows)
                
                print(f"✅ Conversion completed successfully!")
                print(f"📊 Conversion Statistics:")
                print(f"   Total rows processed: {self.conversion_stats['total_rows']}")
                print(f"   True/False converted: {self.conversion_stats['true_false_converted']}")
                print(f"   Fill-in-blank converted: {self.conversion_stats['fill_in_blank_converted']}")
                print(f"   Already formatted: {self.conversion_stats['already_formatted']}")
                print(f"   Skipped: {self.conversion_stats['skipped']}")
                print(f"   Output rows: {len(self.converted_rows)}")
                print(f"📁 Output saved to: {output_file}")
            else:
                print("❌ No rows could be converted. Please check the input format.")
                
        except FileNotFoundError:
            print(f"❌ Error: Input file '{input_file}' not found.")
        except Exception as e:
            print(f"❌ Error during conversion: {e}")

def generate_output_filename(input_file: str) -> str:
    """Generate output filename in vocabulary_template directory with auto-increment if needed"""
    # Extract base filename without extension
    input_path = os.path.basename(input_file)
    name_without_ext = os.path.splitext(input_path)[0]
    
    # Create vocabulary_template directory if it doesn't exist
    output_dir = "vocabulary_template"
    os.makedirs(output_dir, exist_ok=True)
    
    # Try the original name first
    output_file = os.path.join(output_dir, f"{name_without_ext}.csv")
    
    # If file exists, add incrementing number
    counter = 1
    while os.path.exists(output_file):
        output_file = os.path.join(output_dir, f"{name_without_ext}_{counter}.csv")
        counter += 1
    
    return output_file

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) != 2:
        print("Usage: python csv_formatter.py input_file.csv")
        print("\nExample: python csv_formatter.py 'algorithms copy.csv'")
        print("Output will be automatically saved to vocabulary_template/ directory")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Validate input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file '{input_file}' does not exist.")
        sys.exit(1)
    
    # Generate output filename automatically
    output_file = generate_output_filename(input_file)
    
    print(f"📁 Input: {input_file}")
    print(f"📁 Output: {output_file}")
    print()
    
    # Create formatter and convert
    formatter = CSVFormatter()
    formatter.convert_file(input_file, output_file)

if __name__ == "__main__":
    main()