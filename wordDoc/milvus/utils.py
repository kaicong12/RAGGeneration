import os
import asyncio
from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility
)
from process_data import process_csv_for_insert
from dotenv import load_dotenv
load_dotenv()

    

host = os.getenv('MILVUS_HOST', 'localhost')
port = os.getenv('MILVUS_PORT', '19530')
connections.connect("default", host=host, port=port)


def sanitise_collection_name(collection_name):
    return ''.join(e for e in collection_name if e.isalnum() or e == '_')


async def create_collection_if_missing(collection_name):
    fields = [
        # record ID
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        # file ID, used to retrieve all the records which belong to one file
        FieldSchema(name="file_id", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=30000),
        FieldSchema(name="num_tokens", dtype=DataType.INT64, max_length=2000)
    ]

    schema = CollectionSchema(fields, description="Job Handlers")

    if not utility.has_collection(collection_name):
        collection = Collection(name=collection_name, schema=schema)
        print(f"Collection {collection_name} has been created")

        # Create index for vector column
        collection.create_index(field_name="embedding", index_params={
            "index_type": "HNSW", 
            "params": {"M": 16, "efConstruction": 100}, 
            "metric_type": "L2"
        })

        # Load collection into memory so that we can query data later
        collection.load()


async def insert_data(data, collection_name):
    await create_collection_if_missing(collection_name)
    collection = Collection(collection_name)
    collection.insert(data) # Milvus will automatically create an index for the newly inserted data

    print("Done insertion and indexing")


if __name__ == "__main__":
    data = process_csv_for_insert("../test_data/pdfs_out/combined.csv", "-Nkjdhasi212dA")
    asyncio.run(insert_data(data, "tmpKC"))
