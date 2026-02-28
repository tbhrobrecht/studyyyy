import pandas as pd 
df = pd.read_csv('practice_decks/entrepreneurship.csv')

answers = df['correct_answer'].tolist()

anser_counts = { 'a': 0, 'b': 0, 'c': 0, 'd': 0 }
for ans in answers:
    if ans in anser_counts:
        anser_counts[ans] += 1

print(anser_counts)