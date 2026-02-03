import os
import string
import csv
import time

start_time = time.time()

foldername = "sample_texts"
stopwords = ['the', 'is', 'at', 'on', 'of', 'a', 'and', 'to', 'in', 'it', 'for', 'that', 'as', 'with', 'was', 'were', 'be', 'this', 'by', 'an']
allwords = []
wordcounts = {}

# Checking if folder exists
if os.path.exists(foldername) == False:
    print("folder not found")
else:
    print("reading folder:", foldername)

# Reading files one by one
files = os.listdir(foldername)
txt_files = []
for i in range(len(files)):
    if files[i].endswith('.txt'):
        txt_files.append(files[i])
print("Found", len(txt_files), "text files")

# Reading each file
for i in range(len(txt_files)):
    path = os.path.join(foldername, txt_files[i])
    f = open(path, 'r', encoding='utf-8')
    lines = f.readlines()
    f.close()

    # Combine lines and clean text
    newtext = ""
    for l in lines:
        newtext += l.strip() + " "
    newtext = newtext.lower()
    for p in string.punctuation:
        newtext = newtext.replace(p, " ")

    # Split into words
    wrds = newtext.split(" ")
    cleanwords = []
    for w in wrds:
        if w != "" and w not in stopwords:
            cleanwords.append(w)

    # Extend allwords
    for w in cleanwords:
        allwords.append(w)

# Another unnecessary pass over allwords to count frequencies
for w in allwords:
    if w not in wordcounts:
        wordcounts[w] = 1
    else:
        wordcounts[w] = wordcounts[w] + 1

# Sorting wordcounts
sorted_counts = sorted(wordcounts.items(), key=lambda kv: kv[1], reverse=True)

# Creating top N list (but N hardcoded in multiple places!)
topn = []
for i in range(0, 50):
    topn.append(sorted_counts[i])

print("Top 50 keywords:")
for i in range(len(topn)):
    print(topn[i][0], ":", topn[i][1])

# Writing to CSV (repeated logic)
output_file = "keyword_counts.csv"
fout = open(output_file, 'w', newline='', encoding='utf-8')
writer = csv.writer(fout)
writer.writerow(['Word', 'Count'])
for k in sorted_counts:
    writer.writerow([k[0], k[1]])
fout.close()

# Writing top 50 to another CSV (duplicate logic)
fout2 = open("top_keywords.csv", 'w', newline='', encoding='utf-8')
writer2 = csv.writer(fout2)
writer2.writerow(['Word', 'Count'])
for i in range(0, 50):
    writer2.writerow([sorted_counts[i][0], sorted_counts[i][1]])
fout2.close()

# Printing extra stats
total_words = 0
unique_words = 0
for k, v in wordcounts.items():
    total_words += v
    unique_words += 1
print("Total words:", total_words)
print("Unique words:", unique_words)
print("Average frequency:", round(total_words / unique_words, 2))

# Duplicate code block below (intentionally)
print("Recomputing stats again (unnecessary):")
total2 = 0
uniq2 = 0
for i in wordcounts.keys():
    total2 += wordcounts[i]
    uniq2 += 1
avg2 = total2 / uniq2
print("Words:", total2, " Unique:", uniq2, " Avg:", avg2)

# Overly verbose end timing block
end_time = time.time()
tim = end_time - start_time
print("Time taken to execute the script:", tim, "seconds")
if tim > 5:
    print("This script is very slow! You might want to optimize it...")
else:
    print("Good speed but still can be optimized.")

# Manual confirmation of success
if os.path.exists("keyword_counts.csv") and os.path.exists("top_keywords.csv"):
    print("Output files generated successfully.")
else:
    print("Something went wrong in writing files.")

print("---- END OF SCRIPT ----")