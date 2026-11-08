from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from db.db import getSession
from db.tables import (
    Audiobook, AudiobookGenre, AudiobookGenreCache,
    Podcast, PodcastGenre, PodcastGenreCache,
    Episode,
    RecentSearch,
    SavedItem
)

from utils.helpers import resolve_image

#==================#
#======GLOBAL======#
#==================#
audiobookRssLock = Lock()
audiobookRssUrls: set[str] | None = None


#===================#
#======HELPERS======#
#===================#
def parseDate(value: Any) -> datetime | None:
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None

def filterData(data: dict, allowed: set[str]) -> dict:
    return {k: v for k, v in data.items() if k in allowed}

def normalizeUrl(url: str | None) -> str:
    return (url or '').strip().rstrip('/').lower()

def getOrCreateCache(session: Session, model, genre: str):
    cache = session.scalars(select(model).where(model.genre == genre)).first()
    if cache is None:
        cache = model(genre=genre)
        session.add(cache)
        session.flush()
    return cache

def upsert(session: Session, model, data: dict, *, unique_fields: list[tuple[str, Any]]) -> Any:
    instance = None
    for field_name, value in unique_fields:
        if value is None:
            continue
        instance = session.scalars(
            select(model).where(getattr(model, field_name) == value)
        ).first()
        if instance is not None:
            break

    if instance is None:
        instance = model(**data)
        session.add(instance)
    else:
        for key, value in data.items():
            if value is not None:
                setattr(instance, key, value)

    return instance


#===============================#
#======AUDIOBOOK RSS CACHE======#
#===============================#
def invalidateAudiobookRssCache() -> None:
    global audiobookRssUrls
    with audiobookRssLock:
        audiobookRssUrls = None

def getAudiobookRssUrls() -> set[str]:
    global audiobookRssUrls
    with audiobookRssLock:
        if audiobookRssUrls is not None:
            return audiobookRssUrls

        with getSession() as session:
            urls = session.scalars(
                select(Audiobook.rss_url).where(Audiobook.rss_url.is_not(None))
            ).all()

        audiobookRssUrls = {
            normalizeUrl(u) for u in urls if u
        }
        return audiobookRssUrls


#====================#
#======PODCASTS======#
#====================#
def savePodcast(data: dict) -> Podcast:
    if not data.get('title'):
        raise ValueError('A podcast must have a title')

    data = filterData(dict(data), {
        'feed_id', 'title', 'author', 'description', 'image_url', 'feed_url'
    })

    with getSession() as session:
        podcast = upsert(
            session,
            Podcast,
            data,
            unique_fields=[
                ('feed_id', data.get('feed_id')),
                ('feed_url', data.get('feed_url')),
            ],
        )
        session.commit()
        session.refresh(podcast)
        return podcast

def savePodcastsBatch(items: list[dict]) -> list[Podcast]:
    if not items:
        return []

    allowed = {'feed_id', 'title', 'author', 'description', 'image_url', 'feed_url'}
    saved: list[Podcast] = []

    with getSession() as session:
        for raw in items:
            if not raw.get('title'):
                continue
            data = filterData(dict(raw), allowed)
            podcast = upsert(
                session,
                Podcast,
                data,
                unique_fields=[
                    ('feed_id', data.get('feed_id')),
                    ('feed_url', data.get('feed_url')),
                ],
            )
            saved.append(podcast)

        session.commit()
        for p in saved:
            session.refresh(p)
    return saved

def getPodcast(feed_id: int | None = None, feed_url: str | None = None, podcast_id: int | None = None) -> Podcast | None:
    with getSession() as session:
        if podcast_id is not None:
            return session.get(Podcast, podcast_id)
        if feed_id is not None:
            return session.scalars(
                select(Podcast).where(Podcast.feed_id == feed_id)
            ).first()
        if feed_url:
            return session.scalars(
                select(Podcast).where(Podcast.feed_url == feed_url)
            ).first()
        return None

def savePodcastGenres(podcast_ids: list[int], genre: str, start_position: int = 0) -> None:
    if not podcast_ids:
        return

    with getSession() as session:
        existing = set(session.scalars(
            select(PodcastGenre.podcast_id).where(
                PodcastGenre.genre == genre,
                PodcastGenre.podcast_id.in_(podcast_ids),
            )
        ).all())

        links = [
            PodcastGenre(
                podcast_id=pid,
                genre=genre,
                position=start_position + idx,
            )
            for idx, pid in enumerate(podcast_ids)
            if pid not in existing
        ]
        if links:
            session.add_all(links)
            session.commit()

def getPodcastsByGenrePage(genre: str, offset: int = 0, limit: int = 15) -> tuple[list[Podcast], bool]:
    offset = max(0, offset)
    limit = max(0, limit)
    if limit == 0:
        return [], False

    with getSession() as session:
        stmt = (
            select(Podcast)
            .options(selectinload(Podcast.genres))
            .join(PodcastGenre)
            .where(PodcastGenre.genre == genre)
            .order_by(PodcastGenre.position, PodcastGenre.id)
            .offset(offset)
            .limit(limit + 1)
        )
        rows = list(session.scalars(stmt).unique().all())
        has_more = len(rows) > limit
        return rows[:limit], has_more

def getAudiobooksByGenrePage(genre: str, offset: int = 0, limit: int = 15) -> tuple[list[Audiobook], bool]:
    offset = max(0, offset)
    limit = max(0, limit)
    if limit == 0:
        return [], False

    with getSession() as session:
        stmt = (
            select(Audiobook)
            .join(AudiobookGenre)
            .where(AudiobookGenre.genre == genre)
            .order_by(AudiobookGenre.position, AudiobookGenre.id)
            .offset(offset)
            .limit(limit + 1)
        )
        rows = list(session.scalars(stmt).all())
        has_more = len(rows) > limit
        return rows[:limit], has_more


#=====================#
#======AUDIOBOOK======#
#=====================#
def getAudiobooks(limit: int = 100) -> list[Audiobook]:
    with getSession() as session:
        return list(
            session.scalars(
                select(Audiobook)
                .order_by(Audiobook.title)
                .limit(max(0, limit))
            ).all()
        )

def saveAudiobooksBatch(items: list[dict]) -> list[Audiobook]:
    if not items:
        return []

    allowed = {
        'librivox_id', 'title', 'author', 'description', 'image_url', 'rss_url',
    }
    saved: list[Audiobook] = []

    with getSession() as session:
        for raw in items:
            if not raw.get('title'):
                continue
            data = filterData(dict(raw), allowed)
            book = upsert(
                session,
                Audiobook,
                data,
                unique_fields=[
                    ('librivox_id', data.get('librivox_id')),
                    ('rss_url', data.get('rss_url')),
                ],
            )
            saved.append(book)

        session.commit()
        for b in saved:
            session.refresh(b)

    invalidateAudiobookRssCache()
    return saved

def saveAudiobookGenres(audiobook_ids: list[int], genre: str, start_position: int = 0) -> None:
    if not audiobook_ids:
        return

    with getSession() as session:
        existing = set(session.scalars(
            select(AudiobookGenre.audiobook_id).where(
                AudiobookGenre.genre == genre,
                AudiobookGenre.audiobook_id.in_(audiobook_ids),
            )
        ).all())

        links = [
            AudiobookGenre(
                audiobook_id=aid,
                genre=genre,
                position=start_position + idx,
            )
            for idx, aid in enumerate(audiobook_ids)
            if aid not in existing
        ]
        if links:
            session.add_all(links)
            session.commit()

def getAudiobooksByGenre(genre: str) -> list[Audiobook]:
    with getSession() as session:
        stmt = (
            select(Audiobook)
            .join(AudiobookGenre)
            .where(AudiobookGenre.genre == genre)
            .order_by(AudiobookGenre.position, AudiobookGenre.id)
        )
        return list(session.scalars(stmt).all())


#====================#
#======EPISODES======#
#====================#
def saveEpisodes(podcast_id: int, episodes_data: list[dict]) -> list[Episode]:
    allowed = {'guid', 'title', 'audio_url', 'duration', 'published_at'}

    with getSession() as session:
        if session.get(Podcast, podcast_id) is None:
            raise ValueError(f'Podcast with ID {podcast_id} not found')

        saved: list[Episode] = []
        for raw in episodes_data:
            data = filterData(dict(raw), allowed)
            if not data.get('title'):
                continue

            data['published_at'] = parseDate(data.get('published_at'))
            episode = None

            if data.get('guid'):
                episode = session.scalars(
                    select(Episode).where(
                        Episode.podcast_id == podcast_id,
                        Episode.guid == data['guid'],
                    )
                ).first()

            if episode is None and data.get('audio_url'):
                episode = session.scalars(
                    select(Episode).where(
                        Episode.podcast_id == podcast_id,
                        Episode.audio_url == data['audio_url'],
                    )
                ).first()

            if episode is None:
                episode = Episode(podcast_id=podcast_id, **data)
                session.add(episode)
            else:
                for key, value in data.items():
                    if value is not None:
                        setattr(episode, key, value)

            saved.append(episode)

        session.commit()
        for ep in saved:
            session.refresh(ep)
        return saved

def getEpisodes(podcast_id: int, limit: int = 100, offset: int = 0) -> list[Episode]:
    with getSession() as session:
        stmt = (
            select(Episode)
            .where(Episode.podcast_id == podcast_id)
            .order_by(Episode.published_at.desc())
            .offset(max(0, offset))
            .limit(max(0, limit))
        )
        return list(session.scalars(stmt).all())


#=======================#
#======GENRE CACHE======#
#=======================#
def getPodcastGenreCache(genre: str) -> PodcastGenreCache:
    with getSession() as session:
        cache = getOrCreateCache(session, PodcastGenreCache, genre)
        session.commit()
        session.refresh(cache)
        return cache

def updatePodcastGenreCache(genre: str, next_start_at: int, has_more: bool, is_loaded: bool = True) -> PodcastGenreCache:
    with getSession() as session:
        cache = getOrCreateCache(session, PodcastGenreCache, genre)
        cache.next_start_at = max(0, next_start_at)
        cache.has_more = has_more
        cache.is_loaded = is_loaded
        session.commit()
        session.refresh(cache)
        return cache

def getAudiobookGenreCache(genre: str) -> AudiobookGenreCache:
    with getSession() as session:
        cache = getOrCreateCache(session, AudiobookGenreCache, genre)
        session.commit()
        session.refresh(cache)
        return cache

def updateAudiobookGenreCache(genre: str, next_offset: int, has_more: bool) -> AudiobookGenreCache:
    with getSession() as session:
        cache = getOrCreateCache(session, AudiobookGenreCache, genre)
        cache.next_offset = max(0, next_offset)
        cache.has_more = has_more
        session.commit()
        session.refresh(cache)
        return cache


#==================#
#======SEARCH======#
#==================#
def searchItems(query: str, limit: int = 15, offset: int = 0) -> list[dict]:
    query = (query or '').strip()
    if not query or limit <= 0:
        return []

    limit = max(0, limit)
    offset = max(0, offset)
    fetch_limit = offset + limit

    with getSession() as session:
        q_lower = query.lower()

        podcasts = session.scalars(
            select(Podcast)
            .where(
                or_(
                    func.lower(Podcast.title).startswith(q_lower),
                    func.lower(Podcast.author).startswith(q_lower),
                )
            )
            .order_by(func.lower(Podcast.title), Podcast.id)
            .limit(fetch_limit)
        ).all()

        audiobooks = session.scalars(
            select(Audiobook)
            .where(
                or_(
                    func.lower(Audiobook.title).startswith(q_lower),
                    func.lower(Audiobook.author).startswith(q_lower),
                )
            )
            .order_by(func.lower(Audiobook.title), Audiobook.id)
            .limit(fetch_limit)
        ).all()

        results: list[dict] = []

        for p in podcasts:
            results.append({
                'id': p.id,
                'itemType': 'podcast',
                'title': p.title,
                'artist': p.author or '-',
                'description': p.description or '',
                'image': resolve_image(p.image_url),
                'rss': p.feed_url or '',
                'feedId': p.feed_id,
            })

        for a in audiobooks:
            results.append({
                'id': a.id,
                'itemType': 'audiobook',
                'title': a.title,
                'artist': a.author or '-',
                'description': a.description or '',
                'image': resolve_image(a.image_url),
                'rss': a.rss_url or '',
                'librivoxId': a.librivox_id,
            })

    results.sort(
        key=lambda item: (
            item['title'].casefold(),
            item['itemType'],
            item['id'],
        )
    )
    return results[offset:offset + limit]


#===========================#
#======RECENT SEARCHES======#
#===========================#
def saveRecentItem(item: dict, item_id: int | str, item_type: str) -> None:
    if item_type not in ('podcast', 'audiobook'):
        raise ValueError('Invalid item type')
    if item_id is None:
        raise ValueError('Item ID cannot be None')
    if not item.get('title'):
        raise ValueError('Item must have a title')

    with getSession() as session:
        recent = session.scalars(
            select(RecentSearch).where(
                RecentSearch.item_id == str(item_id),
                RecentSearch.item_type == item_type,
            )
        ).first()

        if recent is None:
            recent = RecentSearch(
                item_id=str(item_id),
                item_type=item_type,
                title=item['title'],
                artist=item.get('artist'),
                description=item.get('description'),
                image=resolve_image(item.get('image')),
                rss_url=item.get('rss') or item.get('rss_url'),
            )
            session.add(recent)
        else:
            recent.title = item['title']
            recent.artist = item.get('artist')
            recent.description = item.get('description')
            recent.image = resolve_image(item.get('image'))
            recent.rss_url = item.get('rss') or item.get('rss_url')

        recent.created_at = datetime.now(timezone.utc)
        session.flush()

        old_items = session.scalars(
            select(RecentSearch)
            .order_by(RecentSearch.created_at.desc(), RecentSearch.id.desc())
            .offset(10)
        ).all()
        for old in old_items:
            session.delete(old)

        session.commit()

def getRecentItems(limit: int = 10) -> list[dict]:
    with getSession() as session:
        items = session.scalars(
            select(RecentSearch)
            .order_by(
                RecentSearch.created_at.desc(),
                RecentSearch.id.desc(),
            )
            .limit(max(0, limit))
        ).all()

        results = []
        for item in items:
            result = {
                'id': item.item_id,
                'itemType': item.item_type,
                'title': item.title,
                'artist': item.artist or '-',
                'description': item.description or 'Description is missing',
                'image': resolve_image(item.image),
                'rss': item.rss_url or '',
            }
            if item.item_type == 'podcast':
                result['feedId'] = item.item_id
            elif item.item_type == 'audiobook':
                result['librivoxId'] = item.item_id
            results.append(result)
        return results


#===================#
#======LIBRARY======#
#===================#
def savedItemToDict(item: SavedItem) -> dict:
    result = {
        'id': item.item_id,
        'itemType': item.item_type,
        'title': item.title,
        'artist': item.artist or '-',
        'description': item.description or 'Description is missing',
        'image': resolve_image(item.image),
        'rss': item.rss_url or '',
    }

    if item.item_type == 'podcast':
        result['feedId'] = item.item_id
    elif item.item_type == 'audiobook':
        result['librivoxId'] = item.item_id
    return result

def saveLibraryItem(item: dict, item_id: int | str, item_type: str) -> dict:
    if item_type not in ('podcast', 'audiobook'):
        raise ValueError('Invalid item type')
    
    if item_id is None:
        raise ValueError('Item ID cannot be None')
    
    if not item.get('title'):
        raise ValueError('Item must have a title')

    with getSession() as session:
        row = session.scalars(
            select(SavedItem).where(SavedItem.item_id == str(item_id), SavedItem.item_type == item_type)
        ).first()

        if row is None:
            row = SavedItem(
                item_id=str(item_id),
                item_type=item_type,
                title=item['title'],
                artist=item.get('artist'),
                description=item.get('description'),
                image=resolve_image(item.get('image')),
                rss_url=item.get('rss') or item.get('rss_url'),
            )
            session.add(row)
        else:
            row.title = item['title']
            row.artist = item.get('artist')
            row.description = item.get('description')
            row.image = resolve_image(item.get('image'))
            row.rss_url = item.get('rss') or item.get('rss_url')
            row.created_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(row)

        return savedItemToDict(row)

def removeLibraryItem(item_id: int | str, item_type: str) -> bool:
    if item_type not in ('podcast', 'audiobook'):
        raise ValueError('Invalid item type')
    
    if item_id is None:
        raise ValueError('Item ID cannot be None')

    with getSession() as session:
        row = session.scalars(
            select(SavedItem).where(SavedItem.item_id == str(item_id), SavedItem.item_type == item_type)
        ).first()

        if row is None:
            return False
        
        session.delete(row)
        session.commit()

        return True

def isLibraryItemSaved(item_id: int | str, item_type: str) -> bool:
    if item_type not in ('podcast', 'audiobook') or item_id is None:
        return False

    with getSession() as session:
        return session.scalars(
            select(SavedItem.id).where(SavedItem.item_id == str(item_id), SavedItem.item_type == item_type)
        ).first() is not None

def getLibraryItems(item_type: str | None = None, limit: int | None = None, offset: int = 0) -> list[dict]:
    if item_type is not None and item_type not in ('podcast', 'audiobook'):
        raise ValueError('Invalid item type')

    with getSession() as session:
        stmt = select(SavedItem).order_by(
            SavedItem.created_at.desc(),
            SavedItem.id.desc(),
        )

        if item_type is not None:
            stmt = stmt.where(SavedItem.item_type == item_type)

        if offset:
            stmt = stmt.offset(max(0, offset))

        if limit is not None:
            stmt = stmt.limit(max(0, limit))

        rows = session.scalars(stmt).all()

        return [savedItemToDict(row) for row in rows]

def countLibraryItems(item_type: str | None = None) -> int:
    if item_type is not None and item_type not in ('podcast', 'audiobook'):
        raise ValueError('Invalid item type')

    with getSession() as session:
        stmt = select(func.count()).select_from(SavedItem)

        if item_type is not None:
            stmt = stmt.where(SavedItem.item_type == item_type)

        return int(session.scalar(stmt) or 0)