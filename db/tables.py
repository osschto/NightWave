from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db import Base

class Podcast(Base):
    __tablename__ = 'podcast'

    id: Mapped[int] = mapped_column(primary_key=True)
    feed_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True, default=None)
    title: Mapped[str] = mapped_column(String, index=True)
    author: Mapped[Optional[str]] = mapped_column(String, default=None)
    description: Mapped[Optional[str]] = mapped_column(String, default=None)
    image_url: Mapped[Optional[str]] = mapped_column(String, default=None)
    feed_url: Mapped[Optional[str]] = mapped_column(String, unique=True, default=None)

    episodes: Mapped[List['Episode']] = relationship(back_populates='podcast', cascade='all, delete-orphan')
    genres: Mapped[List['PodcastGenre']] = relationship(back_populates='podcast', cascade='all, delete-orphan')


class Audiobook(Base):
    __tablename__ = 'audiobook'

    id: Mapped[int] = mapped_column(primary_key=True)
    librivox_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True, default=None)
    title: Mapped[str] = mapped_column(String, index=True)
    author: Mapped[Optional[str]] = mapped_column(String, default=None)
    description: Mapped[Optional[str]] = mapped_column(String, default=None)
    image_url: Mapped[Optional[str]] = mapped_column(String, default=None)
    rss_url: Mapped[Optional[str]] = mapped_column(String, unique=True, default=None)

    genres: Mapped[List['AudiobookGenre']] = relationship(back_populates='audiobook', cascade='all, delete-orphan')


class Episode(Base):
    __tablename__ = 'episode'

    id: Mapped[int] = mapped_column(primary_key=True)
    podcast_id: Mapped[int] = mapped_column(ForeignKey('podcast.id'), index=True)
    guid: Mapped[Optional[str]] = mapped_column(String, default=None)
    title: Mapped[str] = mapped_column(String)
    audio_url: Mapped[Optional[str]] = mapped_column(String, default=None)
    duration: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    podcast: Mapped[Optional['Podcast']] = relationship(back_populates='episodes')


class PodcastGenre(Base):
    __tablename__ = 'podcast_genre'
    __table_args__ = (UniqueConstraint('podcast_id', 'genre', name='uq_podcast_genre'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    podcast_id: Mapped[int] = mapped_column(ForeignKey('podcast.id'), index=True)
    genre: Mapped[str] = mapped_column(String, index=True)
    position: Mapped[int] = mapped_column(Integer)
    podcast: Mapped['Podcast'] = relationship(back_populates='genres')


class AudiobookGenre(Base):
    __tablename__ = 'audiobook_genre'
    __table_args__ = (UniqueConstraint('audiobook_id', 'genre', name='uq_audiobook_genre'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    audiobook_id: Mapped[int] = mapped_column(ForeignKey('audiobook.id'), index=True)
    genre: Mapped[str] = mapped_column(String, index=True)
    position: Mapped[int] = mapped_column(Integer)
    audiobook: Mapped['Audiobook'] = relationship(back_populates='genres')


class PodcastGenreCache(Base):
    __tablename__ = 'podcast_genre_cache'

    id: Mapped[int] = mapped_column(primary_key=True)
    genre: Mapped[str] = mapped_column(String, unique=True, index=True)
    next_start_at: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    has_more: Mapped[bool] = mapped_column(Boolean, default=True)
    is_loaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AudiobookGenreCache(Base):
    __tablename__ = 'audiobook_genre_cache'

    id: Mapped[int] = mapped_column(primary_key=True)
    genre: Mapped[str] = mapped_column(String, unique=True, index=True)
    next_offset: Mapped[int] = mapped_column(Integer, default=0)
    has_more: Mapped[bool] = mapped_column(Boolean, default=True)


class RecentSearch(Base):
    __tablename__ = 'recent_search'
    __table_args__ = (UniqueConstraint('item_id', 'item_type', name='uq_recent_search_item'),)

    id: Mapped[int] = mapped_column(primary_key=True)

    item_id: Mapped[str] = mapped_column(String, index=True)
    item_type: Mapped[str] = mapped_column(String, index=True)

    title: Mapped[str] = mapped_column(String)
    artist: Mapped[Optional[str]] = mapped_column(String, default=None)
    description: Mapped[Optional[str]] = mapped_column(String, default=None)
    image: Mapped[Optional[str]] = mapped_column(String, default=None)
    rss_url: Mapped[Optional[str]] = mapped_column(String, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

class SavedItem(Base):
    __tablename__ = 'saved_item'
    __table_args__ = (UniqueConstraint('item_id', 'item_type', name='uq_saved_item'),)

    id: Mapped[int] = mapped_column(primary_key=True)

    item_id: Mapped[str] = mapped_column(String, index=True)
    item_type: Mapped[str] = mapped_column(String, index=True)

    title: Mapped[str] = mapped_column(String)
    artist: Mapped[Optional[str]] = mapped_column(String, default=None)
    description: Mapped[Optional[str]] = mapped_column(String, default=None)
    image: Mapped[Optional[str]] = mapped_column(String, default=None)
    rss_url: Mapped[Optional[str]] = mapped_column(String, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)