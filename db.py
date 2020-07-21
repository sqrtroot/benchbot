import sqlalchemy
from tabulate import tabulate
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Float, Boolean, ForeignKey, and_, \
    UniqueConstraint, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session as SessionT
from contextlib import contextmanager
from typing import Optional, List, Union, Callable, Coroutine
from inspect import iscoroutinefunction, signature
from consts import ECHO_SQL

SessionT = SessionT

# string types see:
# https://mypy.readthedocs.io/en/latest/common_issues.html#using-classes-that-are-generic-in-stubs-but-not-at-runtime

meta = MetaData()
Result = sqlalchemy.engine.ResultProxy
Base = declarative_base(metadata=meta)

engine = create_engine('sqlite:///challenges.db', echo=ECHO_SQL)
Session: sessionmaker = sessionmaker()
Session.configure(bind=engine)


def with_session(fn: Union[Callable, Coroutine]):
    def sess_func(*args, **kwargs):
        session: SessionT = Session()
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
        retfunc = sess_func
    else:
        retfunc = async_sess_func
    # keep original name and signature (for discord bot)
    retfunc.__name__ = getattr(fn, '__name__', retfunc.__name__)
    sig = signature(fn)
    sig = sig.replace(parameters=tuple(sig.parameters.values())[1:])
    retfunc.__signature__ = sig
    return retfunc


class Contender(Base):
    __tablename__ = 'contender'
    id            = Column(Integer, primary_key=True, nullable=False)
    name          = Column(String, nullable=False)
    benchmarks    = relationship('Benchmark', back_populates='contender')


class Challenge(Base):
    __tablename__  = 'challenge'
    __table_args__ = (UniqueConstraint("name", "active"),)
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
        if not self.error and not self.avg_time:
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
            ['Challenge', self.challenge.name],
            ['hash', self.hash],
            ['binary_size', self.bin_size],
            *rslt], tablefmt='fancy_grid')


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
