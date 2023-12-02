from openai import OpenAI
from pymilvus import connections

from fastapi import FastAPI, HTTPException, File, UploadFile, status
from sql.payload import SQLQueryPayload, SplitDocQueryPayload
from sql.handler import handler
from sql.connection import get_conn_pool
from contextlib import asynccontextmanager
from firebase.connection import bucket, db_ref
from wordDoc.chunking.semantic.word import split_handler
from wordDoc.utils.process_data import process_csv_for_insert
from wordDoc.milvus.insert import insert_data

import os
import uuid
import json
import tempfile
from dotenv import load_dotenv
load_dotenv()


global db_pool 
global openai_client
openai_client = None
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # connect to SQL DB on app startup
    global db_pool
    db_pool = await get_conn_pool("employees", password=os.getenv("SQL_PASSWORD"))

    global openai_client
    openai_client = OpenAI()

    connections.connect(
        host=os.getenv("MILVUS_HOST"),
        port=os.getenv("MILVUS_PORT")
    )

    yield
    # close sql connection on app shutdown

    db_pool.close()
    await db_pool.wait_closed()
    db_pool = None

app = FastAPI(lifespan=lifespan)


@app.post("/api/upload_doc")
async def upload_doc(file: UploadFile = File(...)):
    if not file.filename.endswith('.docx'):
        return {"error": "File is not a Word document"}

    try:
        # Generate a unique filename
        unique_filename = str(uuid.uuid4()) + ".docx"

        blob = bucket.blob(f'wordDoc/{unique_filename}')
        blob.upload_from_string(await file.read(), content_type=file.content_type)

        # Get the URL of the uploaded file
        blob.make_public()
        file_url = blob.public_url

        db_ref.child('uploaded_docs').push({
            'filename': unique_filename,
            'storage_path': file_url
        })

        return { "storage_path": file_url }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/split_doc", status_code=status.HTTP_201_CREATED)
async def split_docs(payload: SplitDocQueryPayload):
    
    # download document from cloud storage into a tmp dir
    with tempfile.TemporaryDirectory() as tmp_dir:
        blob = bucket.blob(payload.doc_path)
        # Use the filename as the uuid
        file_name_with_ext = os.path.basename(payload.doc_path)
        file_uuid, _ = os.path.splitext(file_name_with_ext)

        local_file_path = os.path.join(tmp_dir, "temp_doc.docx")
        blob.download_to_filename(local_file_path)

        # split the word doc and produce a dataframe
        await split_handler(tmp_dir, f"{tmp_dir}_out")

        # insert the dataframe into milvus
        milvus_data = process_csv_for_insert(os.path.join(f"{tmp_dir}_out", "combined.csv"), file_uuid)
        await insert_data(milvus_data, payload.collection_name)

    return {
        'message': 'Records have been inserted'
    }

@app.post("/api/sql_insights")
async def get_sql_insights(payload: SQLQueryPayload):
    # table_name and question validation performed by FastAPI through the Pydantic library
    global db_pool, openai_client
    table_name = payload.table_name
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database connection is not available")
    
    return await handler(table_name, db_pool, openai_client)
    