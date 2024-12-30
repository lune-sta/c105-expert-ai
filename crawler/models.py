from pathlib import Path

from peewee import *


db = SqliteDatabase(Path(__file__).resolve().parent.parent / "sqlite.db")


class Page(Model):
    host = CharField()
    url = CharField()
    is_scraped = BooleanField(default=False)

    class Meta:
        database = db


db.create_tables([Page])
