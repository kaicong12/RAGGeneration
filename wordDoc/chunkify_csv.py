'''
Loop through a directory and split all documents inside into smaller chunks for feeding into LLM models.
The scripts tries to fit as many whole sentences into a chunk as possible while taking note of the token limit for each chunk.
In extreme cases of badly formatted docs (eg. the whole doc is a sentence and has no sentence splitter),
the "sentence" will be broken down into words and even characters if needed.
Token limit (approx) for each chunk is set with TOKEN_LIMIT.
Don't set TOKEN_LIMIT too close to model limit, eg. if model limit is 4096, TOKEN_LIMIT should be <= 3800.
'''
import argparse
import regex as re
import tiktoken
import pandas as pd

parser = argparse.ArgumentParser(
    description="Preprocess a given file and output to a directory."
)
parser.add_argument("input_file", help="Path to the input file.")
parser.add_argument("output_file", help="Path to the output directory.")
args = parser.parse_args()

input_file = args.input_file
output_file = args.output_file
model = 'gpt-3.5-turbo'
enc = tiktoken.encoding_for_model(model)  # For counting tokens when feeding the corresponding text into model

TOKEN_LIMIT = 1000           # Max token length for each chunk
WORD_LIMIT = TOKEN_LIMIT     # For splitting single "sentence" into word units if the sentence by itself is longer than token limit (likely badly formatted document)
CHAR_LIMIT = WORD_LIMIT * 4  # For splitting single "word" into characters units if the word length is longer than word limit (likely badly formatted document)


OVERLAP_PERCENTAGE = 0.34
OVERLAP_TOKEN_LIMIT = int(TOKEN_LIMIT * OVERLAP_PERCENTAGE)
OVERLAP_WORD_LIMIT = OVERLAP_TOKEN_LIMIT
OVERLAP_CHAR_LIMIT = OVERLAP_WORD_LIMIT * 4


# Regex pattern for matching "sentence splitters", eg. '!' characters
sent_splitter = re.compile('(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!\:)\s+|\p{Cc}+|\p{Cf}+')


def split_by_sentences(text):
    sentences = []
    split_patterns = []  # Keep "sentence splitters" for later reconstruction
    last_idx = 0
    for split_pattern in sent_splitter.finditer(text):
        prev_sent = text[last_idx: split_pattern.start()]
        last_idx = split_pattern.end()
        sentences.append(prev_sent)
        split_patterns.append(split_pattern[0])
    sentences.append(text[last_idx:])
    return sentences, split_patterns


def split_by_words_limit(text, limit=WORD_LIMIT):
    words = text.split(' ')
    chunks = list(' '.join(words[i: i + limit]) for i in range(0, len(words), limit))
    return chunks, [' ' for _ in range(len(chunks) - 1)]


def split_by_chars_limit(text, limit=CHAR_LIMIT):
    chunks = list(text[i: i + limit] for i in range(0, len(text), limit))
    return chunks, ['' for _ in range(len(chunks) - 1)]


def update_chunks(chunks, curr_chunk, curr_len, texts, split_patterns=[], fallback_splitter=[]):
    for i, text in enumerate(texts):
        if i > 0:
            text = split_patterns[i - 1] + text
        text_len = len(enc.encode(text))
        if text_len + curr_len > TOKEN_LIMIT:
            if curr_chunk:
                chunks.append(''.join(curr_chunk))
            # Fallback logic if single text exceeding token limit
            if text_len > TOKEN_LIMIT and fallback_splitter:
                splitter = fallback_splitter[0]
                curr_chunk, curr_len = update_chunks(chunks, [], 0, *splitter(text), fallback_splitter[1:])
                if curr_chunk:
                    chunks.append(''.join(curr_chunk))
                    curr_chunk = []
                    curr_len = 0
            else:
                curr_chunk = [text]
                curr_len = text_len
        else:
            curr_chunk.append(text)
            curr_len += text_len
    return curr_chunk, curr_len


chunks = []
with open(input_file) as f:
    doc = f.read()
    sentences, split_patterns = split_by_sentences(doc)
    curr_chunk, curr_len = update_chunks(chunks, [], 0, sentences, split_patterns, fallback_splitter=[split_by_words_limit, split_by_chars_limit])
    if curr_chunk:  # Left over chunk not appended
        chunks.append(''.join(curr_chunk))

    if OVERLAP_PERCENTAGE > 0:
        TOKEN_LIMIT = OVERLAP_TOKEN_LIMIT
        WORD_LIMIT = OVERLAP_WORD_LIMIT
        CHAR_LIMIT = OVERLAP_CHAR_LIMIT
        for i, chunk in enumerate(chunks[:-1]):
            overlap_chunks = []
            chunk_sentences, chunk_split_patterns = split_by_sentences(chunks[i + 1])
            curr_chunk, curr_len = update_chunks(overlap_chunks, [], 0, chunk_sentences, chunk_split_patterns, fallback_splitter=[split_by_words_limit, split_by_chars_limit])
            if curr_chunk:
                overlap_chunks.append(''.join(curr_chunk))
            if overlap_chunks:
                chunks[i] = ''.join([chunk, overlap_chunks[0]])

df = pd.DataFrame(chunks, columns=['chunks'])
df.to_csv(output_file, index=False)
print(f'No. of chunks: {len(df)}')
