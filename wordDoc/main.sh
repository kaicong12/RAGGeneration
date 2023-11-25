#!/bin/bash

# Check for input arguments
if [ "$#" -ne 5 ]; then
    echo "Usage: $0 <path-to-word-doc> <word2CSV-output-path> <chunkified-csv-path> <csv-with-embeddings-output-path> <collectionName>"
    exit 1
fi

input_file="$1"
word2CSV_path="$2"
chunkifiedCSV_path="$3"
csvWithEmbedding_path="$4"
collection_name="$5"

# Check if the the input word doc exists
if [ ! -f "$input_file" ]; then
    echo "File not found: $input_file"
    exit 1
fi

python3 word2CSV.py "$input_file" "$word2CSV_path"
python3 csv_bruteforce_chunking.py "$word2CSV_path" "$chunkifiedCSV_path"
python3 get_embeddings.py "$chunkifiedCSV_path" "$csvWithEmbedding_path"
node insert.mjs "${csvWithEmbedding_path}" "${collection_name}"
