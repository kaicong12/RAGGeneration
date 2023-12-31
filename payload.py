from pydantic import BaseModel


class SplitDocQueryPayload(BaseModel):
    collection_name: str
    doc_path: str

class SQLQueryPayload(BaseModel):
    table_name: str

class ChatWithPDFPayload(BaseModel):
    user_id: str
    pdf_id: str
    user_question: str