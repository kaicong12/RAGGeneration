from pydantic import BaseModel

class SQLQueryPayload(BaseModel):
    question: str
    table_name: str
