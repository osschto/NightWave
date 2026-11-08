from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

engine = create_engine(
    url='sqlite:///nightwave.db',
    connect_args={'check_same_thread': False, 'timeout': 30},
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

@event.listens_for(engine, 'connect')
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA journal_mode=WAL')
    cursor.execute('PRAGMA synchronous=NORMAL')
    cursor.execute('PRAGMA temp_store=MEMORY')
    cursor.execute('PRAGMA mmap_size=268435456')
    cursor.execute('PRAGMA cache_size=-64000')
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

def createDB() -> None:
    from db.tables import (
        Audiobook, AudiobookGenre, AudiobookGenreCache,
        Podcast, PodcastGenre, PodcastGenreCache,
        Episode,
        RecentSearch,
        SavedItem,
    )
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS ix_podcast_title_lower '
            'ON podcast (lower(title))'
        ))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS ix_podcast_author_lower '
            'ON podcast (lower(author))'
        ))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS ix_audiobook_title_lower '
            'ON audiobook (lower(title))'
        ))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS ix_audiobook_author_lower '
            'ON audiobook (lower(author))'
        ))

def getSession() -> Session:
    return SessionLocal()