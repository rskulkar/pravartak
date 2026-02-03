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
# Precompiled Translator (Speedup #1)
# -------------------------------

TRANSLATOR = str.maketrans(
    string.punctuation,
    " " * len(string.punctuation)
)


# -------------------------------
# Utilities
# -------------------------------

def get_text_files(folder):
    """Return list of .txt files in folder."""
    return [
        f for f in os.listdir(folder)
        if f.endswith(".txt")
    ]


def clean_words(line):
    """
    Clean and tokenize a line of text.

    - Lowercase
    - Remove punctuation
    - Split into words
    """
    return line.lower().translate(TRANSLATOR).split()


# -------------------------------
# Core Processing (Speedup #2 + #3)
# -------------------------------

def process_files(folder):
    """
    Stream files and count word frequencies.

    Uses:
    - Line-by-line reading (low memory)
    - Counter.update with generator
    """
    counter = Counter()

    files = get_text_files(folder)

    print("Found", len(files), "text files")

    for filename in files:

        path = os.path.join(folder, filename)

        with open(
            path,
            "r",
            encoding="utf-8",
            buffering=1024 * 1024  # Large buffer (IO speedup)
        ) as f:

            for line in f:

                words = (
                    w for w in clean_words(line)
                    if w and w not in STOPWORDS
                )

                counter.update(words)

    return counter


# -------------------------------
# Output
# -------------------------------

def write_csv(filename, data):
    """Write word counts to CSV."""
    with open(filename, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)
        writer.writerow(["Word", "Count"])

        for word, count in data:
            writer.writerow([word, count])


def print_statistics(counter):
    """Print summary statistics."""
    total = sum(counter.values())
    unique = len(counter)

    avg = round(total / unique, 2)

    print("Total words:", total)
    print("Unique words:", unique)
    print("Average frequency:", avg)


# -------------------------------
# Main
# -------------------------------

def main():

    start = time.time()

    # Check folder
    if not os.path.exists(FOLDER_NAME):
        print("folder not found")
        return

    print("reading folder:", FOLDER_NAME)

    # Process
    wordcounts = process_files(FOLDER_NAME)

    # Top N (partial sort)
    top_n = wordcounts.most_common(TOP_N)

    print(f"Top {TOP_N} keywords:")

    for word, count in top_n:
        print(word, ":", count)

    # Full sort (for CSV)
    sorted_counts = sorted(
        wordcounts.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # Write outputs
    write_csv(OUTPUT_ALL, sorted_counts)
    write_csv(OUTPUT_TOP, top_n)

    # Stats
    print_statistics(wordcounts)

    # Timing
    elapsed = time.time() - start

    print(
        "Time taken:",
        round(elapsed, 3),
        "seconds"
    )

    if elapsed > 5:
        print("This script is slow. Consider parallel processing.")
    else:
        print("Good speed (optimized).")

    # Verify output
    if os.path.exists(OUTPUT_ALL) and os.path.exists(OUTPUT_TOP):
        print("Output files generated successfully.")
    else:
        print("Output generation failed.")

    print("---- END OF SCRIPT ----")


# -------------------------------
# Entry Point
# -------------------------------

if __name__ == "__main__":
    main()