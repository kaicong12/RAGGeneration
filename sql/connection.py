import aiomysql

async def get_conn_pool(database, host='localhost', port=3306, user='root', password=None):
    conn_pool = await aiomysql.create_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        db=database,
        maxsize=10  # maximum number of connections that can be opened on this pool simulatneously
    )

    return conn_pool
