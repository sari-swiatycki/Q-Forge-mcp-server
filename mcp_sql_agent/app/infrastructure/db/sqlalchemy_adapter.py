from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


class SQLAlchemyAdapter:
    def __init__(self, connection_string: str):
        self.engine: Engine = create_engine(connection_string, future=True)

    def query(self, sql: str) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql)).mappings().all()
            return [dict(r) for r in rows]

    def execute_write(self, sql: str) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(text(sql))
            return int(result.rowcount or 0)

    def get_schema(self) -> dict:
        insp = inspect(self.engine)
        schema = {}
        foreign_keys = []
        for table in insp.get_table_names():
            cols = insp.get_columns(table)
            schema[table] = [{"name": c["name"], "type": str(c["type"])} for c in cols]
            for fk in insp.get_foreign_keys(table):
                if not fk.get("referred_table") or not fk.get("constrained_columns"):
                    continue
                foreign_keys.append(
                    {
                        "table": table,
                        "columns": fk.get("constrained_columns", []),
                        "referred_table": fk.get("referred_table"),
                        "referred_columns": fk.get("referred_columns", []),
                    }
                )
        return {
            "dialect": self.engine.dialect.name,
            "tables": schema,
            "foreign_keys": foreign_keys,
        }

    def get_dialect(self) -> str:
        return self.engine.dialect.name



