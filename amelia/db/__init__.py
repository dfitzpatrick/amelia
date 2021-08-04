import asyncpg
import typing as t
import textwrap

class BaseDB:
    def __init__(self, *args, pool: asyncpg.Connection, **kwargs):
        """
        Initializes the DAL for different objects that may be extended on it.
        Parameters
        ----------
        args
        kwargs
        db - the data connection pool
        """
        self.pool = pool

    def select(self, table: str, id: t.Optional[int] = None):
        sql = f'SELECT * FROM {table}'
        if id is not None:
            sql += f' WHERE id = {id};'
        else:
            sql += ';'

    def insert(self, table: str, values: t.Dict[str, t.Any]):
        keys = ", ".join(values.keys())
        # Let the db convert the literals. Just to make it easy
        vals = ", ".join(values.values())
        sql = f"""
            INSERT INTO {table} ({keys}) 
            VALUES ({vals});
        """

    def delete(self, table: str, id: int):
        """
        Delete from the database
        Parameters
        ----------
        table
        id

        Returns
        -------

        """
        sql = f"DELETE FROM {table} WHERE id = {id};"


    def update(self, table: str, id: int, values: t.Dict[str, t.Any]):
        """
        Updates a record
        Parameters
        ----------
        table
        id

        Returns
        -------

        """
        keys = ", ".join(values.keys())
        # Let the db convert the literals. Just to make it easy
        vals = ", ".join(values.values())
        sql = f"""
                    UPDATE {table} 
                    ({keys}) 
                    VALUES ({vals});
                """