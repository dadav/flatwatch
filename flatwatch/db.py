import logging
import sqlite3
from multiprocessing import Manager
from typing import Optional, List, Tuple

log = logging.getLogger('rich')


class SqlBackend:
    """\
    Manages persistent data
    """
    def __init__(self, db):
        self._lock = Manager().Lock()
        self._connection = sqlite3.connect(db, check_same_thread=False)

        self._cursor = self._connection.cursor()

        with self._lock:
            self._cursor.execute('create table if not exists data (\
                                 id integer primary key not null,\
                                 chatid integer not null,\
                                 location text not null,\
                                 locationid integer not null,\
                                 price integer,\
                                 rooms integer,\
                                 area integer,\
                                 radius integer,\
                                 count integer)')
            self._connection.commit()

    def save(self, chatid: int, location: str, locationid: int, price: Optional[int] = None, rooms: Optional[int] = None, area: Optional[int] = None, radius: Optional[int] = None) -> bool:
        try:
            with self._lock:
                self._cursor.execute("insert into data values (null,?,?,?,?,?,?,?,-1)", (chatid, location, locationid, price, rooms, area, radius))
                self._connection.commit()
            return True
        except sqlite3.Error as sql_err:
            log.debug(sql_err)
        return False

    def load(self, chatid: Optional[int] = None) -> List[Tuple]:
        try:
            with self._lock:
                if chatid:
                    result = self._cursor.execute('select * from data where chatid=?', (chatid,))
                else:
                    result = self._cursor.execute('select * from data')
                return result.fetchall()
        except sqlite3.Error as sql_err:
            log.debug(sql_err)
        return list()

    def set_count(self, entry: int, value: int) -> bool:
        try:
            with self._lock:
                self._cursor.execute('update data set count=? where id=?', (entry, value,))
                self._connection.commit()
            return True
        except sqlite3.Error as sql_err:
            log.debug(sql_err)
        return False

    def delete(self, chatid: int, entry: Optional[int] = None) -> bool:
        try:
            with self._lock:
                if entry:
                    self._cursor.execute('delete from data where chatid=? and id=?', (chatid, entry,))
                else:
                    self._cursor.execute('delete from data where chatid=?', (chatid,))
                self._connection.commit()
            return True
        except sqlite3.Error as sql_err:
            log.debug(sql_err)
        return False
