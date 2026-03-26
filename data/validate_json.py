import json
import sys

def validate_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        print("JSON is valid")
    except json.JSONDecodeError as e:
        print(f"JSON validation failed: {e}")
        print(f"Error at line {e.lineno}, column {e.colno}")
        # Print context
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            start = max(0, e.lineno - 5)
            end = min(len(lines), e.lineno + 5)
            for i in range(start, end):
                prefix = ">>>" if i + 1 == e.lineno else "   "
                print(f"{prefix} {i+1}: {lines[i].strip()}")

if __name__ == "__main__":
    validate_json(r'c:\Users\DELL\OneDrive\Desktop\sementic_sewarch\products.json')
