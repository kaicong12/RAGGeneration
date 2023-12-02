from openai import OpenAI
from pymilvus import connections
from firebase.connection import bucket, db_ref


from fastapi import APIRouter, File, UploadFile, HTTPException
from payload import SplitDocQueryPayload, ChatWithPDFPayload
from wordDoc.chunking.semantic.word import split_handler
from wordDoc.utils.process_data import process_csv_for_insert, get_embedding
from wordDoc.milvus.insert import insert_data
from wordDoc.milvus.query import get_top_n_chunks

import os
import uuid
import tempfile
from dotenv import load_dotenv
load_dotenv()


# Milvus Connection
connections.connect(
    host=os.getenv("MILVUS_HOST"),
    port=os.getenv("MILVUS_PORT")
)
openai_client = OpenAI()
router = APIRouter()


@router.post("/api/upload_doc")
async def upload_doc(file: UploadFile = File(...)):
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=401, detail="File is not a Word document")

    try:
        # Generate a unique filename
        file_uuid = str(uuid.uuid4())
        unique_filename = file_uuid + ".docx"

        blob = bucket.blob(f'wordDoc/{unique_filename}')
        blob.upload_from_string(await file.read(), content_type=file.content_type)

        # Get the URL of the uploaded file
        blob.make_public()
        file_url = blob.public_url

        db_ref.child('uploaded_docs').push({
            'filename': unique_filename,
            'storage_path': file_url
        })

        return { "file_uuid": file_uuid, "storage_path": file_url }
    except Exception as e:
        return {"error": str(e)}


@router.post("/api/split_doc")
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


@router.post("/api/chat_with_pdf")
async def chat_with_pdf(payload: ChatWithPDFPayload):
    if not payload.user_question:
        raise HTTPException(status_code=401, detail="Please provide a user question")
    if not payload.user_id:
        raise HTTPException(status_code=401, detail="User id not found")
    if not payload.pdf_id:
        raise HTTPException(status_code=401, detail="File id not found")
    
    # 1. Convert user's query to embeddings
    search_vector = get_embedding(payload.user_question)

    # 2. look up the top 10 relevant chunks
    top_10_chunks = get_top_n_chunks(
        payload.user_id, search_vector, f"file_id == '{payload.pdf_id}'", ["file_id", "content", "num_tokens"], 10
    )

    # 3. Feed these relevant chunks to ChatGPT
    context_for_gpt = ''
    token_count, token_thresh = 0, 10000
    for chunk in top_10_chunks:
        entity = chunk.entity
        token_count += int(entity.get('num_tokens'))
        if token_count >= token_thresh:
            break
        
        context_for_gpt += entity.get('content')
        context_for_gpt += "\n"

    # 4. Collate the information from each individual API calls
    completion = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a super intelligent agent, who knows the following information: \n\n" + context_for_gpt + "\n\n You will only answer user's question based on these information, and if user's question are unrelated or the answers cannot be found in the context, you will refuse to answer user's question"},
            {"role": "user", "content": "I want to know: " + payload.user_question}
        ]
    )

    return {
        'code': 200,
        'message': completion.choices[0].message.content
    }