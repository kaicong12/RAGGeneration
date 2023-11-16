from fastapi import FastAPI, HTTPException
from sql.payload import SQLQueryPayload
from sql.handler import handler
from sql.connection import get_conn_pool

from contextlib import asynccontextmanager

import os
from dotenv import load_dotenv
load_dotenv()


db_pool = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    # connect to SQL DB on app startup
    db_pool = await get_conn_pool("employees", password=os.getenv("SQL_PASSWORD"))
    yield
    # close sql connection on app shutdown
    db_pool.close()
    await db_pool.wait_closed()
    db_pool = None

app = FastAPI(lifespan=lifespan)


@app.post("/sql_insights")
async def get_sql_insights(payload: SQLQueryPayload):
    # table_name and question validation performed by FastAPI through the Pydantic library
    question, table_name = payload.question, payload.table_name
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database connection is not available")
    
    return handler(question, table_name)
    