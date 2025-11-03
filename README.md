# studyyyy

## Set Up 

### Vocabulary Cards
Add the template file (.csv file, with headers "term", "definition", (and, if applicable, "formula") be sure to label it as "term,definition,formula") to the vocabulary_template

### Multiple Choice Questions (MCQ)
Add MCQ template files (.csv file, with headers "question", "option_a", "option_b", "option_c", "option_d", "correct_answer") to the vocabulary_template

#### MCQ Features:
- **Single Answer MCQs**: Set `correct_answer` to a single letter (e.g., "a")
- **Multi-Answer MCQs**: Set `correct_answer` to comma-separated letters (e.g., "a,c" or "b,d")
- **True/False Questions**: Leave `option_c` and `option_d` empty (e.g., "True", "False", "", "")
- **Order Independent**: User can enter answers in any order ("1,3", "3,1", "1 3", etc.)
- **Partial Scoring**: Multi-answer questions award partial credit based on correct selections
- **Flexible Input**: Supports comma-separated, space-separated, or mixed formatting
- **Dynamic Options**: Automatically detects 2-option (True/False) vs 4-option (regular MCQ) format

## Run the Program 
Open the terminal and run `python main.py` from the repository directory

## MCQ Format Examples

### True/False Questions:
**Standardized Format**: Option 1 = True, Option 2 = False
```csv
question,option_a,option_b,option_c,option_d,correct_answer
"Python is a programming language",True,False,"","",a
"HTML is a programming language",True,False,"","",b
```
*Note: `correct_answer` is `a` when statement is True, `b` when statement is False*

### Regular MCQ (4 options):
```csv
question,option_a,option_b,option_c,option_d,correct_answer
"Which are programming languages?",Python,HTML,JavaScript,CSS,"a,c"
"What is 2+2?",3,4,5,6,b
```

## Answer Input Formats
For multi-answer MCQs, you can enter answers in any of these formats:
- `1,3` (comma-separated)
- `3,1` (reverse order)
- `1 3` (space-separated)  
- `3, 1` (comma with spaces)
- ` 1 , 3 ` (extra spaces)

**The order doesn't matter** - all formats above are treated as equivalent.

For True/False questions:
- Enter `1` for True statements
- Enter `2` for False statements  
- Format is standardized: 1=True, 2=False across all True/False questions

## Storing Results 
The results should be stored in the corresponding practice_decks folder. Multiple study sets are currently supported. 