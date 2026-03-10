
# ================================================
# LLM Foundations & Applications – Assignment Script
# This script can be converted into a Jupyter Notebook
# by splitting sections into cells.
# ================================================

# ------------------------------------------------
# Section 1: Environment Setup
# ------------------------------------------------

# Install packages if needed (uncomment if running locally)
# !pip install transformers gensim scikit-learn numpy pandas

from transformers import pipeline, AutoTokenizer
import gensim.downloader as api
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

print("Libraries imported successfully.")

# ------------------------------------------------
# Section 2: Load Text Generation Model
# ------------------------------------------------

print("\nLoading text generation model (distilgpt2)...")
generator = pipeline("text-generation", model="distilgpt2")
print("Model loaded successfully.")

# ------------------------------------------------
# Section 3: Text Generation Example
# ------------------------------------------------

prompt = "AI is transforming industries by"

outputs = generator(
    prompt,
    max_length=50,
    num_return_sequences=3,
    do_sample=True,
    temperature=0.9,
    top_p=0.95
)

print("\nText Generation Outputs")
for i, output in enumerate(outputs):
    print(f"\nOutput {i+1}:")
    print(output['generated_text'])

# ------------------------------------------------
# Section 4: Tokenization Example
# ------------------------------------------------

tokenizer = AutoTokenizer.from_pretrained("distilgpt2")

sentence = "LLMs are powerful tools for natural language understanding."

encoding = tokenizer(sentence)

token_ids = encoding["input_ids"]
tokens = tokenizer.convert_ids_to_tokens(token_ids)
seq_length = len(token_ids)

print("\nTokenization Example")
print("Sentence:", sentence)
print("\nTokens:", tokens)
print("\nToken IDs:", token_ids)
print("\nSequence Length:", seq_length)

# ------------------------------------------------
# Section 5: Prompt Engineering Examples
# ------------------------------------------------

print("\nPrompt Engineering Demonstrations")

# Summarization Prompt
prompt_summary = '''
Summarize the following text in 30 words or less:

Large language models are trained on vast text datasets and use transformer
architectures to understand and generate human-like language across many tasks.
'''

summary_output = generator(prompt_summary, max_length=60)
print("\nSummarization Output:")
print(summary_output[0]["generated_text"])

# Q&A Prompt
prompt_qa = '''
Question: What is the capital of France?
Answer:
'''

qa_output = generator(prompt_qa, max_length=40)
print("\nQ&A Output:")
print(qa_output[0]["generated_text"])

# Creative Prompt
prompt_creative = '''
Write a four line poem about artificial intelligence.
'''

creative_output = generator(prompt_creative, max_length=80)
print("\nCreative Output:")
print(creative_output[0]["generated_text"])

# ------------------------------------------------
# Section 6: Load GloVe Word Embeddings
# ------------------------------------------------

print("\nLoading GloVe embeddings (glove-wiki-gigaword-50)...")
model = api.load("glove-wiki-gigaword-50")
print("Embeddings loaded.")

words = ["king", "queen", "diamond"]

for word in words:
    print(f"\nWord: {word}")
    print("First 10 vector values:")
    print(model[word][:10])

    print("Top 5 similar words:")
    for similar_word, score in model.most_similar(word, topn=5):
        print(similar_word, score)

# ------------------------------------------------
# Section 7: Sentence Embeddings
# ------------------------------------------------

sentences = [
    "Artificial intelligence is transforming business.",
    "Machine learning models analyse large datasets.",
    "Deep learning is widely used in image recognition.",
    "Jewellery diamonds are valued for their clarity.",
    "Gold and diamonds are popular luxury items."
]

def sentence_vector(sentence):
    words = sentence.lower().split()
    valid_words = [word for word in words if word in model]

    if len(valid_words) == 0:
        return np.zeros(50)

    return np.mean([model[word] for word in valid_words], axis=0)

sentence_vectors = np.array([sentence_vector(s) for s in sentences])

# ------------------------------------------------
# Section 8: Sentence Similarity Matrix
# ------------------------------------------------

similarity_matrix = cosine_similarity(sentence_vectors)

df = pd.DataFrame(similarity_matrix, index=sentences, columns=sentences)

print("\nSentence Similarity Matrix")
print(df)

# ------------------------------------------------
# Section 9: Transformer Application Example
# ------------------------------------------------

print("\nSentiment Analysis Example")

sentiment = pipeline("sentiment-analysis")

texts = [
    "This product is excellent and works perfectly.",
    "The service was slow and disappointing."
]

results = sentiment(texts)

for text, result in zip(texts, results):
    print("\nText:", text)
    print("Sentiment:", result)

print("\nScript execution complete.")
