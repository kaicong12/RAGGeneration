from fastapi import HTTPException
import aiomysql
import os
import json


async def get_column_descriptions(rows, column_names, table_name, openai_client):
    filepath = "sql/db_configs/employees.json"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=401, detail="Table file cannot be found")

    f = open(filepath)
    table_data = json.load(f)
    if table_name not in table_data:
        raise HTTPException(status_code=401, detail="Table cannot be found in the database")

    table_description = table_data[table_name].get("description", "This table has no description.")
    
    prompt = f""" you are given the following table named: {table_name}. The table has the following description: {table_description}.
    The table "{table_name}" has the following columns: {column_names}. And here are some of the example data each column has: {rows}.
    Based on the given data from the table, could you generate a description for each of the column on what the column is about.
    """

    completion = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert data analyst, skilled in explaining complex SQL tables to non-business users on what the table data is about."},
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content


async def handler(question, table_name, db_pool, openai_client):
    # db_pool variable has been set in main.py as global variable
    if db_pool is None:
        raise HTTPException(status_code=401, detail="Database connection pool is not available")
    if openai_client is None:
        raise HTTPException(status_code=401, detail="OpenAI connection is not available")

    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            try:
                # Get all column names
                await cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            except:
                raise Exception(f"Table {table_name} does not exist")
            
            columns = await cursor.fetchall()
            column_names = [column["Field"] for column in columns]

            # Get the top 100 rows of the table
            await cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
            rows = await cursor.fetchall()

            # # Feed the data to ChatGPT and get descriptions for each column
            column_descriptions = await get_column_descriptions(rows, column_names, table_name, openai_client)

    return {
        "code": 200,
        "message": column_descriptions
    }