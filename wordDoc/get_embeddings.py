import os
import argparse
import openai
from openai.embeddings_utils import get_embedding
import tiktoken
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

parser = argparse.ArgumentParser(
    description="Preprocess a given file and output to a directory."
)
parser.add_argument("input_file", help="Path to the input file.")
parser.add_argument("output_file", help="Path to the output directory.")
args = parser.parse_args()

input_file = args.input_file
output_file = args.output_file


openai.api_key = os.getenv("OPENAI_API_KEY")
embedding_model = "text-embedding-ada-002"
max_tokens = 8000  # the maximum for text-embedding-ada-002 is 8191

# For counting tokens when feeding the corresponding text into model
gen_model = "gpt-3.5-turbo-16k"
enc = tiktoken.encoding_for_model(gen_model)


# Getting Embeddings from OpenAI
cur_df = pd.read_csv(input_file)
cur_df = cur_df.dropna()
cur_df["num_tokens"] = cur_df.chunks.apply(lambda x: len(enc.encode(x)))
cur_df["embedding"] = cur_df.chunks.apply(
    lambda x: get_embedding(x, engine=embedding_model)
)
cur_df = cur_df.dropna()
cur_df.to_csv(output_file, index=False)
