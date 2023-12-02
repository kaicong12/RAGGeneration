from fastapi import APIRouter, HTTPException
from payload import SQLQueryPayload
from sql.handler import sql_handler


router = APIRouter()


@router.post("/api/sql_insights")
async def get_sql_insights(payload: SQLQueryPayload):
    # table_name and question validation performed by FastAPI through the Pydantic library
    global db_pool, openai_client
    table_name = payload.table_name
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database connection is not available")
    
    return await sql_handler(table_name, db_pool, openai_client)