import csv
import tiktoken
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()


client = OpenAI()
gen_model = "gpt-3.5-turbo-16k"
enc = tiktoken.encoding_for_model(gen_model)  # For counting tokens when feeding the corresponding text into model


def get_embedding(text, model="text-embedding-ada-002"):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding


def process_csv_for_insert(csv_filepath, file_id):
    with open(csv_filepath, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader, None)  # Skip the header

        # 1. convert CSV file into the specific JSON format which Milvus accepts
        milvus_data = [[] for i in range(4)]

        for row in reader:
            if row:
                # Assuming each row in the CSV file is delimited by comma
                # each row is in the format of <document_title>, <reference_marker>, <content>, <page_number>
                content = row[2]

                # 2. for each row, get the embeddings via the OpenAI api
                content_embedding = get_embedding(content)

                # 3. Get the number of tokens for that chunk, in case it goes out of GPT's limit during RAG implemenetation
                num_tokens = len(enc.encode(content))

                # 4. Prepare the data in this sequence
                milvus_data[0].append(file_id)
                milvus_data[1].append(content_embedding)
                milvus_data[2].append(content)
                milvus_data[3].append(num_tokens)

        return milvus_data