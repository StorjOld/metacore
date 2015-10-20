import datetime
import os.path

from sqlalchemy import create_engine, Column, ForeignKey, MetaData, Table
from sqlalchemy import Boolean, DateTime, Integer, String

__author__ = 'karatel'


engine = create_engine(
    'sqlite:///' + os.path.join(os.path.dirname(__file__), 'storj.db'),
    convert_unicode=True
)
metadata = MetaData(bind=engine)


files = Table(
    'files', metadata,
    Column('hash', String(64), nullable=False, primary_key=True),
    Column('role', String(3), nullable=False),
    Column('size', Integer, nullable=False),
    Column('owner', String(35), nullable=False),
)


audit = Table(
    'audit', metadata,
    Column('file_hash', Integer, ForeignKey('files.hash'), nullable=False),
    Column('is_owners', Boolean, default=False, nullable=False),
    Column('made_at', DateTime, default=datetime.datetime.now, nullable=False)
)

metadata.create_all()
