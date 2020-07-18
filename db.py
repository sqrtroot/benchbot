import sqlalchemy
from tabulate import tabulate
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Float, Boolean, ForeignKey, and_, \
    UniqueConstraint, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session as SessionT
from contextlib import contextmanager
from typing import Optional, List, Union, Callable, Coroutine
from inspect import iscoroutinefunction

SessionT = SessionT

# string types see:
# https://mypy.readthedocs.io/en/latest/common_issues.html#using-classes-that-are-generic-in-stubs-but-not-at-runtime

meta = MetaData()
Result = sqlalchemy.engine.ResultProxy
Base = declarative_base(metadata=meta)

engine = create_engine('sqlite:///challenges.db', echo=True)
Session: sessionmaker = sessionmaker()
Session.configure(bind=engine)


def with_session(fn: Union[Callable, Coroutine]):
    def sess_func(*args, **kwargs):
        session: SessionT = Session()
        print("Hey")
        try:
            fn(session, *args, **kwargs)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    async def async_sess_func(*args, **kwargs):
        session: SessionT = Session()
        print("Hey")
        try:
            await fn(session, *args, **kwargs)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            print('closing session')
            session.close()

    if not iscoroutinefunction(fn):
        sess_func.__name__ = fn.__name__
        return sess_func
    else:
        async_sess_func.__name__ = fn.__name__
        return async_sess_func


class Contender(Base):
    __tablename__ = 'contender'
    id            = Column(Integer, primary_key=True, nullable=False)
    name          = Column(String, nullable=False)
    benchmarks    = relationship('Benchmark', back_populates='contender')


class Challenge(Base):
    __tablename__  = 'challenge'
    __table_args__ = (UniqueConstraint("name", "active"))
    id             = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name           = Column(String, nullable=False)
    active         = Column(Boolean, nullable=False)
    benchmarks     = relationship('Benchmark', back_populates='challenge')


class Benchmark(Base):
    __tablename__  = 'benchmark'
    __table_args__ = (
        UniqueConstraint("id", "hash"),
    )
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    contender_id: 'Column[ForeignKey]' = Column(ForeignKey(Contender.id),
                                                nullable=False)
    challenge_id: 'Column[ForeignKey]' = Column(ForeignKey(Challenge.id),
                                                nullable=False)
    contender = relationship('Contender', back_populates='benchmarks')
    challenge = relationship('Challenge', back_populates='benchmarks')
    hash      = Column(String(length=32))
    error     = Column(String)
    min_time  = Column(Float)
    avg_time  = Column(Float)
    max_time  = Column(Float)
    bin_size  = Column(Float)

    def result_format(self):
        if not self.error or not self.avg_time:
            return "Waiting for results"
        if self.error:
            rslt = [['error', self.error]]
        else:
            rslt = [
                ['Minimum time', self.min_time],
                ['Average time', self.avg_time],
                ['Maximum time', self.max_time],
            ]
        return tabulate([
            ['Submitted by', self.contender.name],
            ['hash', self.hash],
            ['binary_size', self.bin_size],
            *rslt])


connection: Optional[sqlalchemy.engine.Connection] = None


def init_db() -> None:
    meta.create_all(engine.engine)
    global connection
    connection = engine.connect()


def find_author(session, author_id) -> Optional[Contender]:
    result: sqlalchemy.orm.Query = session.query(
        Contender).filter(Contender.id == author_id)
    return result.first()


def get_challenge(session, name) -> Optional[Challenge]:
    result = Session().query(Challenge).filter(
        and_(Challenge.active,
             or_(Challenge.name == name, Challenge.id == name)))
    return result.first()
