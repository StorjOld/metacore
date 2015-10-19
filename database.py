import os.path

from sqlalchemy import create_engine, Column, Integer, MetaData, String, Table

__author__ = 'karatel'


engine = create_engine(
    'sqlite:///' + os.path.join(os.path.dirname(__file__), 'storj.db'),
    convert_unicode=True
)
metadata = MetaData(bind=engine)


files = Table(
    'files', metadata,
    Column('id', Integer, primary_key=True),
    Column('hash', String(64), nullable=False, unique=True),
    Column('role', String(3), nullable=False),
    Column('size', Integer, nullable=False),
)


metadata.create_all()
