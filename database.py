import os
from urllib.parse import quote_plus

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def get_database_url():
    """
    Resuelve la URI de PostgreSQL desde .env.
    Prioridad: DATABASE_URL completa, o variables PG_* por separado.
    """
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        user = os.getenv('PG_USER')
        password = os.getenv('PG_PASSWORD')
        host = os.getenv('PG_HOST', 'localhost')
        port = os.getenv('PG_PORT', '5432')
        name = os.getenv('PG_DATABASE') or os.getenv('PG_NAME')
        if user and password and name:
            db_url = (
                f'postgresql://{quote_plus(user)}:{quote_plus(password)}'
                f'@{host}:{port}/{name}'
            )

    if not db_url:
        raise RuntimeError(
            'Configure PostgreSQL en .env: DATABASE_URL '
            'o PG_USER, PG_PASSWORD, PG_DATABASE (y opcional PG_HOST, PG_PORT).'
        )

    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql+pg8000://', 1)
    elif db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+pg8000://', 1)

    if not db_url.startswith('postgresql+pg8000://'):
        raise RuntimeError('Audit solo soporta PostgreSQL (postgresql:// o postgres://).')

    return db_url


def configure_database(app: Flask):
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
