import sqlalchemy
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData
from sqlalchemy_aio import ASYNCIO_STRATEGY
from typing import Optional
import asyncio

engine = create_engine('sqlite:///challanges.db', echo=True, strategy=ASYNCIO_STRATEGY)
meta = MetaData()

Result = sqlalchemy.engine.ResultProxy

contenders = Table(
    'contender', meta,
    Column('id', Integer, primary_key=True),
    Column('name', String),
)

challenges = Table(
    'challenge', meta,
    Column('id', Integer, primary_key=True),
    Column('name', String),
)

# benchmark = Table()

connection: Optional[sqlalchemy.engine.Connection] = None

async def init_db():
    meta.create_all(engine.sync_engine)
    global connection
    connection = await engine.connect()
