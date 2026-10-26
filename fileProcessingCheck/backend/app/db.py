import oracledb

from app.config import get_settings

oracledb.defaults.fetch_lobs = False


def connect(env: str) -> oracledb.Connection:
    s = get_settings()
    user, password, dsn = (
        (s.dev_db_user, s.dev_db_password, s.dev_db_dsn) if env == "dev" else (s.test_db_user, s.test_db_password, s.test_db_dsn)
    )
    try:
        return oracledb.connect(user=user, password=password, dsn=dsn)
    except oracledb.Error as e:
        raise RuntimeError(f"{env.upper()} database login failed ({user}@{dsn}): {e}") from e


def select(conn: oracledb.Connection, table: str, where: str, binds: dict) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(f"select * from {table} where {where}", binds)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur]


def delete(conn: oracledb.Connection, table: str, where: str, binds: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(f"delete from {table} where {where}", binds)
        return cur.rowcount


def insert(conn: oracledb.Connection, table: str, rows: list[dict]) -> None:
    cols = list(rows[0])
    sql = f"insert into {table} ({', '.join(cols)}) values ({', '.join(f':{i + 1}' for i in range(len(cols)))})"
    with conn.cursor() as cur:
        cur.executemany(sql, [[r[c] for c in cols] for r in rows])


def column_names(conn: oracledb.Connection, sql: str, table: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(sql, t=table)
        return [r[0] for r in cur]


def virtual_columns(conn: oracledb.Connection, table: str) -> list[str]:
    return column_names(conn, "select column_name from user_tab_cols where table_name = :t and virtual_column = 'YES'", table)


def unique_number_columns(conn: oracledb.Connection, table: str) -> list[str]:
    """Number columns that alone make up a unique index (e.g. SEQNO)."""
    return column_names(
        conn,
        """select ic.column_name from user_indexes i
           join user_ind_columns ic on ic.index_name = i.index_name
           join user_tab_cols tc on tc.table_name = ic.table_name and tc.column_name = ic.column_name
           where i.table_name = :t and i.uniqueness = 'UNIQUE' and tc.data_type = 'NUMBER'
             and (select count(*) from user_ind_columns x where x.index_name = i.index_name) = 1""",
        table,
    )


def used_values(conn: oracledb.Connection, table: str, column: str, values: list) -> tuple[set, int]:
    """Which of values already exist in column, and the current max of column."""
    with conn.cursor() as cur:
        cur.execute(f"select max({column}) from {table}")
        top = cur.fetchone()[0] or 0
        cur.execute(f"select {column} from {table} where {column} in (select column_value from table(:v))", v=conn.gettype("SYS.ODCINUMBERLIST").newobject(values))
        return {r[0] for r in cur}, top
