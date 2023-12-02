from fastapi import FastAPI
from wordDoc.routes import router as document_router
from sql.routes import router as sql_router

app = FastAPI()

app.include_router(document_router)
app.include_router(sql_router)
