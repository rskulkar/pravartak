import os
import csv
import time
import string
from collections import Counter


# -------------------------------
# Configuration
# -------------------------------

FOLDER_NAME = "sample_texts"
TOP_N = 50
OUTPUT_ALL = "keyword_counts.csv"
OUTPUT_TOP = "top_keywords.csv"

STOPWORDS = {
    'the', 'is', 'at', 'on', 'of', 'a', 'and', 'to', 'in', 'it',
    'for', 'that', 'as', 'with', 'was', 'were', 'be',
    'this', 'by', 'an'
}


# -------------------------------
# Utilities
# -------------------------------

def get_text_files(folder):
    """Return list of .txt files in folder."""
    return [
        f for f in os.listdir(folder)
        if f.endswith(".txt")
    ]


def clean_text(text):
    """Lowercase, remove punctuation, and split into words."""
    translator = str.maketrans(
        string.punctuation,
        " " * len(string.punctuation)
    )

    cleaned = text.lower().translate(translator)

    return cleaned.split()


def process_files(folder):
    """Read files and count words."""
    counter = Counter()

    files = get_text_files(folder)

    print("Found", len(files), "text files")

    for filename in files:
        path = os.path.join(folder, filename)

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        words = clean_text(text)

        for word in words:
            if word and word not in STOPWORDS:
                counter[word] += 1

    return counter


def write_csv(filename, data):
    """Write word counts to CSV."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow(["Word", "Count"])

        for word, count in data:
            writer.writerow([word, count])


def print_statistics(counter):
    """Print word statistics."""
    total_words = sum(counter.values())
    unique_words = len(counter)

    average = round(total_words / unique_words, 2)

    print("Total words:", total_words)
    print("Unique words:", unique_words)
    print("Average frequency:", average)


# -------------------------------
# Main Program
# -------------------------------

def main():

    start_time = time.time()

    # Check folder
    if not os.path.exists(FOLDER_NAME):
        print("folder not found")
        return

    print("reading folder:", FOLDER_NAME)

    # Process files
    wordcounts = process_files(FOLDER_NAME)

    # Sort results
    sorted_counts = wordcounts.most_common()

    # Top N
    top_n = sorted_counts[:TOP_N]

    print(f"Top {TOP_N} keywords:")

    for word, count in top_n:
        print(word, ":", count)

    # Write CSVs
    write_csv(OUTPUT_ALL, sorted_counts)
    write_csv(OUTPUT_TOP, top_n)

    # Stats
    print_statistics(wordcounts)

    # Timing
    elapsed = time.time() - start_time

    print("Time taken to execute the script:", round(elapsed, 3), "seconds")

    if elapsed > 5:
        print("This script is very slow! You might want to optimize it...")
    else:
        print("Good speed but still can be optimized.")

    # Output check
    if os.path.exists(OUTPUT_ALL) and os.path.exists(OUTPUT_TOP):
        print("Output files generated successfully.")
    else:
        print("Something went wrong in writing files.")

    print("---- END OF SCRIPT ----")


# -------------------------------
# Entry Point
# -------------------------------

if __name__ == "__main__":
    main()