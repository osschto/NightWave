from __future__ import annotations

import asyncio
import hashlib
import os
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

from db.repositories import (
    getAudiobookGenreCache, getAudiobookRssUrls,
    getAudiobooksByGenre, getAudiobooksByGenrePage,
    getEpisodes, getPodcast, getPodcastGenreCache,
    getPodcastsByGenrePage, saveAudiobookGenres,
    saveAudiobooksBatch, saveEpisodes, savePodcast,
    savePodcastGenres, savePodcastsBatch,
    updateAudiobookGenreCache,
    updatePodcastGenreCache
)

from utils.helpers import DEFAULT_IMAGE, resolve_image

#==================#
#======GLOBAL======#
#==================#
ENV_PATH = Path(__file__).resolve().parent.parent / '.env'

load_dotenv(dotenv_path=ENV_PATH)

PODCAST_INDEX_KEY = os.getenv('PODCAST_INDEX_KEY')
PODCAST_INDEX_SECRET = os.getenv('PODCAST_INDEX_SECRET')

if not PODCAST_INDEX_KEY or not PODCAST_INDEX_SECRET:
    raise RuntimeError(f'Podcast Index credentials not found. Expected .env at: {ENV_PATH}')

RSS_HEADERS = {
    'User-Agent': 'NightWave/0.0.1',
    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
}

searchCache: OrderedDict[str, tuple[float, object]] = OrderedDict()

rssCache: OrderedDict[str, str] = OrderedDict()
rssTasks: dict[str, asyncio.Task] = {}

podcastGenreLocks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
audiobookGenreLocks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


#=======================#
#======HTTP CLIENT======#
#=======================#
httpClient: httpx.AsyncClient | None = None

async def getHttpClient() -> httpx.AsyncClient:
    global httpClient
    if httpClient is None or httpClient.is_closed:
        httpClient = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=10.0),
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
            ),
        )
    return httpClient

async def closeHttpClient() -> None:
    global httpClient
    if httpClient is not None and not httpClient.is_closed:
        await httpClient.aclose()
    httpClient = None

async def getJSON(url: str, params: dict | None = None, headers: dict | None = None) -> dict:
    client = await getHttpClient()
    last_error: Exception | None = None

    for attempt in range(2 + 1):
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            last_error = exc
            if isinstance(exc, httpx.HTTPStatusError):
                code = exc.response.status_code
                if code < 500 and code != 429:
                    raise
            if attempt < 2:
                await asyncio.sleep(0.4 * (attempt + 1))
                continue
            raise

    assert last_error is not None
    raise last_error

def searchCacheGet(key: str):
    item = searchCache.get(key)
    if item is None:
        return None
    expires_at, payload = item
    if time.monotonic() >= expires_at:
        searchCache.pop(key, None)
        return None
    searchCache.move_to_end(key)
    return payload

def searchCacheSet(key: str, payload) -> None:
    searchCache[key] = (time.monotonic() + 45, payload)
    searchCache.move_to_end(key)
    while len(searchCache) > 64:
        searchCache.popitem(last=False)


#==============================#
#======PODCAST INDEX AUTH======#
#==============================#
def podcastHeaders() -> dict[str, str]:
    timestamp = str(int(time.time()))
    authorization = hashlib.sha1(f'{PODCAST_INDEX_KEY}{PODCAST_INDEX_SECRET}{timestamp}'.encode()).hexdigest()

    return {
        'User-Agent': 'NightWave/0.0.1',
        'X-Auth-Key': PODCAST_INDEX_KEY,
        'X-Auth-Date': timestamp,
        'Authorization': authorization,
    }


#========================#
#======DATE HELPERS======#
#========================#
async def db(func, /, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

def getDateFromTimestamp(value) -> str:
    if not value:
        return ''
    try:
        return time.strftime('%d.%m.%Y', time.localtime(int(value)))
    except (ValueError, TypeError, OverflowError):
        return ''

def timestampToDatetime(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None

def parseRSSDatetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date
    except (ValueError, TypeError, OverflowError):
        return None

def formatDate(value: datetime | None) -> str:
    if value is None:
        return ''
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime('%d.%m.%Y')


#======================#
#======FORMATTERS======#
#======================#
def formatPodcast(podcast) -> dict:
    return {
        'title': podcast.title or 'Untitled',
        'artist': podcast.author or '-',
        'description': podcast.description or 'Description is missing',
        'image': resolve_image(podcast.image_url),
        'rss': podcast.feed_url or '',
        'feedId': podcast.feed_id,
        'genres': [g.genre for g in podcast.genres],
        'itemType': 'podcast',
    }

def formatAudiobook(audiobook, genre: str | None = None) -> dict:
    author = (audiobook.author or '').strip()
    if author.lower() in ('librivox', '-'):
        author = '-'
    return {
        'title': audiobook.title or 'Untitled',
        'artist': author or '-',
        'description': audiobook.description or 'Description is missing',
        'image': resolve_image(audiobook.image_url),
        'rss': audiobook.rss_url or '',
        'genres': [genre] if genre else [],
        'itemType': 'audiobook',
        'librivoxId': getattr(audiobook, 'librivox_id', None),
    }

def formatEpisodes(episode) -> dict:
    return {
        'id': episode.guid or episode.audio_url,
        'title': episode.title or 'Untitled',
        'date': formatDate(episode.published_at),
        'duration': episode.duration or 0,
        'audio': episode.audio_url or '',
    }


#==========================#
#======PODCAST SEARCH======#
#==========================#
async def getPodcasts(term: str = 'Technology', limit: int = 5) -> list[dict]:
    limit = min(max(limit, 1), 1000)
    term = (term or '').strip()
    if not term:
        return []

    cache_key = f'podcasts|{term.lower()}|{limit}'
    cached = searchCacheGet(cache_key)
    if cached is not None:
        return cached

    audiobook_rss = await db(getAudiobookRssUrls)

    data = await getJSON(
        url='https://api.podcastindex.org/api/1.0/search/byterm',
        params={'q': term, 'max': limit},
        headers=podcastHeaders(),
    )

    podcasts: list[dict] = []
    to_save: list[dict] = []
    seen: set = set()

    for feed in data.get('feeds', []):
        if isAudiobookFeed(feed, audiobook_rss):
            continue

        feed_id = feed.get('id')
        feed_url = feed.get('url')
        if not feed_id and not feed_url:
            continue

        podcast = {
            'title': feed.get('title') or 'Untitled',
            'artist': feed.get('author') or '-',
            'description': feed.get('description') or 'Description is missing',
            'image': resolve_image(feed.get('artwork') or feed.get('image')),
            'rss': feed_url or '',
            'feedId': feed_id,
            'itemType': 'podcast',
            'genres': getFeedGenres(feed),
        }

        key = podcast['feedId'] or podcast['rss'] or (
            podcast['title'], podcast['artist']
        )
        if key in seen:
            continue
        seen.add(key)

        to_save.append({
            'feed_id': feed_id,
            'title': podcast['title'],
            'author': feed.get('author'),
            'description': feed.get('description'),
            'image_url': resolve_image(feed.get('artwork') or feed.get('image')),
            'feed_url': feed_url,
        })
        podcasts.append(podcast)

        if len(podcasts) >= limit:
            break

    if to_save:
        await db(savePodcastsBatch, to_save)

    searchCacheSet(cache_key, podcasts)
    return podcasts


#==========================#
#======PODCAST GENRES======#
#==========================#
async def loadPodcastGenre(genre: str) -> None:
    async with podcastGenreLocks[genre]:
        cache = await db(getPodcastGenreCache, genre)
        if cache.is_loaded:
            return

        audiobook_rss = await db(getAudiobookRssUrls)

        data = await getJSON(
            url='https://api.podcastindex.org/api/1.0/podcasts/trending',
            params={
                'cat': genre,
                'max': 500,
            },
            headers=podcastHeaders(),
        )

        feeds = data.get('feeds') or []
        seen: set = set()
        to_save: list[dict] = []

        for feed in feeds:
            key = getPodcastKey(feed)
            if not key or key in seen:
                continue
            seen.add(key)

            if isAudiobookFeed(feed, audiobook_rss):
                continue

            feed_id = feed.get('id')
            feed_url = feed.get('url')
            if not feed_id and not feed_url:
                continue

            to_save.append({
                'feed_id': feed_id,
                'title': feed.get('title') or 'Untitled',
                'author': feed.get('author'),
                'description': feed.get('description'),
                'image_url': resolve_image(feed.get('artwork') or feed.get('image')),
                'feed_url': feed_url,
            })

        saved = []
        if to_save:
            saved = await db(savePodcastsBatch, to_save)

        podcast_ids = [p.id for p in saved]
        await db(
            savePodcastGenres,
            podcast_ids=podcast_ids,
            genre=genre,
            start_position=0,
        )
        await db(
            updatePodcastGenreCache,
            genre=genre,
            next_start_at=len(podcast_ids),
            has_more=False,
            is_loaded=True,
        )

async def getPodcastGenrePage(genre: str, offset: int = 0, limit: int = 15) -> dict:
    genre = (genre or '').strip()
    offset = max(0, offset)
    limit = min(max(1, limit), 100)

    if not genre:
        return {'results': [], 'hasMore': False}

    cache = await db(getPodcastGenreCache, genre)
    if not cache.is_loaded:
        await loadPodcastGenre(genre)

    page, has_more = await db(getPodcastsByGenrePage, genre, offset, limit)

    return {
        'results': [formatPodcast(p) for p in page],
        'hasMore': has_more,
    }


#===========================#
#======PODCAST HELPERS======#
#===========================#
def normalizeFeedUrl(url: str | None) -> str:
    return (url or '').strip().rstrip('/').lower()

def isAudiobookFeed(feed: dict | object, audiobook_rss: set[str]) -> bool:
    if isinstance(feed, dict):
        url = (
            feed.get('url')
            or feed.get('feed_url')
            or feed.get('rss')
            or feed.get('rss_url')
            or ''
        )
        title = feed.get('title') or ''
    else:
        url = getattr(feed, 'feed_url', '') or ''
        title = getattr(feed, 'title', '') or ''

    normalized_url = normalizeFeedUrl(url)
    normalized_title = title.strip().lower()

    if normalized_url in audiobook_rss:
        return True
    if 'librivox.org' in normalized_url:
        return True
    if normalized_title.startswith('librivox:'):
        return True
    return False

def getPodcastKey(podcast: dict):
    return podcast.get('id') or podcast.get('url')

def getFeedGenres(feed: dict) -> list[str]:
    categories = feed.get('categories') or []
    if isinstance(categories, dict):
        genres = list(categories.keys())
    elif isinstance(categories, list):
        genres = categories
    else:
        genres = []
    return list(dict.fromkeys(
        str(g).strip() for g in genres if g and str(g).strip()
    ))


#============================#
#======AUDIOBOOK SEARCH======#
#============================#
async def getAudiobooks(title: str = 'Alice in wonderland', limit: int = 15, offset: int = 0) -> list[dict]:
    limit = min(max(limit, 1), 100)
    offset = max(0, offset)
    title = (title or '').strip()
    if not title:
        return []

    cache_key = f'audiobooks|{title.lower()}|{limit}|{offset}'
    cached = searchCacheGet(cache_key)
    if cached is not None:
        return cached

    data = await getJSON(
        'https://librivox.org/api/feed/audiobooks/',
        params={
            'fields': (
                'id,title,authors,coverart_jpg,url_rss,'
                'url_librivox,description'
            ),
            'title': f'^{title}',
            'format': 'json',
            'limit': limit,
            'offset': offset,
            'coverart': 1,
        },
    )

    audiobooks: list[dict] = []
    to_save: list[dict] = []
    seen: set = set()

    for book in data.get('books', []):
        author = getBookAuthor(book)
        rss_url = book.get('url_rss') or ''

        item = {
            'title': book.get('title') or 'Untitled',
            'artist': author,
            'description': book.get('description') or 'Description is missing',
            'image': resolve_image(book.get('coverart_jpg')),
            'rss': rss_url,
            'genres': [],
            'itemType': 'audiobook',
            'librivoxId': book.get('id'),
        }

        key = book.get('id') or normalizeFeedUrl(rss_url) or (
            item['title'], item['artist']
        )
        if key in seen:
            continue
        seen.add(key)

        if book.get('id') or rss_url:
            to_save.append({
                'librivox_id': book.get('id'),
                'title': item['title'],
                'author': author,
                'description': book.get('description'),
                'image_url': book.get('coverart_jpg'),
                'rss_url': rss_url,
            })

        audiobooks.append(item)

    if to_save:
        await db(saveAudiobooksBatch, to_save)

    searchCacheSet(cache_key, audiobooks)
    return audiobooks


#============================#
#======AUDIOBOOK GENRES======#
#============================#
async def getAudiobookGenrePage(genre: str, offset: int = 0, limit: int = 15) -> dict:
    genre = (genre or '').strip()
    offset = max(0, offset)
    limit = min(max(1, limit), 100)

    if not genre:
        return {'results': [], 'hasMore': False}

    async with audiobookGenreLocks[genre]:
        cache = await db(getAudiobookGenreCache, genre)
        page_books, page_has_more = await db(
            getAudiobooksByGenrePage, genre, offset, limit
        )

        if page_books:
            return {
                'results': [formatAudiobook(b, genre) for b in page_books],
                'hasMore': page_has_more or cache.has_more,
            }

        if not cache.has_more:
            return {'results': [], 'hasMore': False}

        saved_books = await db(getAudiobooksByGenre, genre)
        seen = {
            b.librivox_id or normalizeFeedUrl(b.rss_url)
            for b in saved_books
        }
        added = []
        next_offset = cache.next_offset
        has_more = cache.has_more

        while len(added) < limit and has_more:
            books = await requestAudiobookGenrePage(
                genre=genre,
                offset=next_offset,
                limit=limit,
            )
            if not books:
                has_more = False
                break

            next_offset += len(books)
            has_more = len(books) == limit

            batch: list[dict] = []
            for book in books:
                key = getAudiobookKey(book)
                if not key or key in seen:
                    continue
                seen.add(key)

                author = getBookAuthor(book)
                rss_url = book.get('url_rss') or ''
                batch.append({
                    'librivox_id': book.get('id'),
                    'title': book.get('title') or 'Untitled',
                    'author': author,
                    'description': book.get('description'),
                    'image_url': book.get('coverart_jpg'),
                    'rss_url': rss_url,
                })

            if batch:
                saved_batch = await db(saveAudiobooksBatch, batch)
                added.extend(saved_batch)

            if len(books) < limit:
                has_more = False

        start_position = len(saved_books)
        if added:
            await db(
                saveAudiobookGenres,
                audiobook_ids=[b.id for b in added],
                genre=genre,
                start_position=start_position,
            )
        await db(
            updateAudiobookGenreCache,
            genre=genre,
            next_offset=next_offset,
            has_more=has_more,
        )

        return {
            'results': [
                formatAudiobook(b, genre) for b in added[:limit]
            ],
            'hasMore': has_more,
        }


#=============================#
#======AUDIOBOOK HELPERS======#
#=============================#
def getBookAuthor(book: dict) -> str:
    authors = book.get('authors') or []
    if isinstance(authors, dict):
        authors = [authors]
    for author in authors:
        if not isinstance(author, dict):
            continue
        first = (author.get('first_name') or '').strip()
        last = (author.get('last_name') or '').strip()
        name = f'{first} {last}'.strip()
        if name and name.lower() not in ('librivox', 'unknown'):
            return name
    return '-'

def getAudiobookKey(book: dict):
    book_id = book.get('id')
    rss_url = normalizeFeedUrl(book.get('url_rss'))
    return book_id or rss_url or None

async def requestAudiobookGenrePage(genre: str, offset: int, limit: int) -> list[dict]:
    data = await getJSON(
        url='https://librivox.org/api/feed/audiobooks/',
        params={
            'fields': (
                'id,title,authors,coverart_jpg,url_rss,'
                'url_librivox,description'
            ),
            'genre': genre,
            'format': 'json',
            'limit': limit,
            'offset': offset,
            'coverart': 1,
        },
    )
    return data.get('books') or []


#============================#
#======PODCAST EPISODES======#
#============================#
async def getPodcastEpisodes(feedId: int | str, limit: int = 20) -> list[dict]:
    if not feedId:
        return []

    limit = min(max(limit, 1), 1000)

    try:
        podcast = await db(getPodcast, feed_id=int(feedId))
    except (ValueError, TypeError):
        podcast = None

    if podcast is not None:
        cached = await db(getEpisodes, podcast.id, limit=limit)
        if len(cached) >= limit:
            return [formatEpisodes(ep) for ep in cached]

    data = await getJSON(
        url='https://api.podcastindex.org/api/1.0/episodes/byfeedid',
        params={'id': str(feedId), 'max': limit},
        headers=podcastHeaders(),
    )

    items = data.get('items', [])
    episodes: list[dict] = []

    for item in items:
        audio_url = item.get('enclosureUrl')
        if not audio_url:
            continue
        guid = item.get('guid') or str(item.get('id') or audio_url)
        episodes.append({
            'id': item.get('id') or guid or audio_url,
            'title': item.get('title') or 'Untitled',
            'date': (
                item.get('datePublishedPretty')
                or getDateFromTimestamp(item.get('datePublished'))
            ),
            'duration': item.get('duration') or 0,
            'audio': audio_url,
        })

    if podcast is not None and items:
        episodes_data = []
        for item in items:
            audio_url = item.get('enclosureUrl')
            if not audio_url:
                continue
            episodes_data.append({
                'guid': str(item.get('guid') or item.get('id') or audio_url),
                'title': item.get('title') or 'Untitled',
                'audio_url': audio_url,
                'duration': item.get('duration') or 0,
                'published_at': timestampToDatetime(item.get('datePublished')),
            })
        if episodes_data:
            await db(saveEpisodes, podcast_id=podcast.id, episodes_data=episodes_data)

    return episodes


#=======================#
#======RSS HELPERS======#
#=======================#
def localName(tag: str) -> str:
    return tag.split('}')[-1].split(':')[-1]

def findChild(element: ET.Element, name: str) -> ET.Element | None:
    return next(
        (child for child in element if localName(child.tag) == name),
        None,
    )

def findText(element: ET.Element, name: str) -> str:
    for child in element.iter():
        if localName(child.tag) == name and child.text:
            return child.text.strip()
    return ''

def findImage(channel: ET.Element) -> str:
    for element in channel.iter():
        if localName(element.tag) not in ('image', 'thumbnail'):
            continue
        url = element.get('href') or element.get('url')
        if url:
            return url
        if localName(element.tag) == 'image':
            image_url = findText(element, 'url')
            if image_url:
                return image_url
    return DEFAULT_IMAGE

def getDuration(value: str) -> int:
    if not value:
        return 0
    try:
        seconds = 0
        for part in value.strip().split(':'):
            seconds = seconds * 60 + int(part)
        return seconds
    except (ValueError, TypeError):
        return 0

async def getRSSRoot(url: str) -> ET.Element:
    client = await getHttpClient()
    last_error: Exception | None = None

    for attempt in range(2 + 1):
        try:
            response = await client.get(url, headers=RSS_HEADERS)
            response.raise_for_status()
            try:
                return ET.fromstring(response.content)
            except ET.ParseError as error:
                raise ValueError(f'Invalid RSS/XML: {url}') from error
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            last_error = exc
            if isinstance(exc, httpx.HTTPStatusError):
                code = exc.response.status_code
                if code < 500 and code != 429:
                    raise
            if attempt < 2:
                await asyncio.sleep(0.4 * (attempt + 1))
                continue
            raise

    assert last_error is not None
    raise last_error


#============================#
#======RSS FEED DETAILS======#
#============================#
def parseRSSDetails(root: ET.Element) -> dict:
    channel = findChild(root, 'channel')
    if channel is None:
        return {}

    episodes = []
    for index, item in enumerate(channel, start=1):
        if localName(item.tag) != 'item':
            continue
        enclosure = findChild(item, 'enclosure')
        if enclosure is None:
            continue
        audio_url = enclosure.get('url')
        if not audio_url:
            continue

        published_at = parseRSSDatetime(findText(item, 'pubDate'))
        episodes.append({
            'id': findText(item, 'guid') or audio_url,
            'title': findText(item, 'title') or f'Episode {index}',
            'date': formatDate(published_at),
            'duration': getDuration(findText(item, 'duration')),
            'audio': audio_url,
            '_publishedAt': published_at,
        })

    return {
        'title': findText(channel, 'title') or 'Untitled',
        'artist': (
            findText(channel, 'author')
            or findText(channel, 'managingEditor')
            or '-'
        ),
        'description': (
            findText(channel, 'summary')
            or findText(channel, 'description')
            or findText(channel, 'subtitle')
            or 'Description is missing'
        ),
        'image': findImage(channel),
        'episodes': episodes,
    }

async def getFeedDetails(rssUrl: str) -> dict:
    if not rssUrl:
        return {}

    podcast = await db(getPodcast, feed_url=rssUrl)
    if podcast is not None:
        cached_episodes = await db(getEpisodes, podcast.id, limit=1000)
        if cached_episodes:
            return {
                'title': podcast.title or 'Untitled',
                'artist': podcast.author or '-',
                'description': podcast.description or 'Description is missing',
                'image': resolve_image(podcast.image_url),
                'episodes': [formatEpisodes(ep) for ep in cached_episodes],
            }

    root = await getRSSRoot(rssUrl)
    details = parseRSSDetails(root)
    if not details:
        return {}

    saved = await db(savePodcast, {
        'title': details['title'],
        'author': details['artist'],
        'description': details['description'],
        'image_url': details['image'],
        'feed_url': rssUrl,
    })

    episodes_data = [
        {
            'guid': str(ep['id']),
            'title': ep['title'],
            'audio_url': ep['audio'],
            'duration': ep['duration'],
            'published_at': ep['_publishedAt'],
        }
        for ep in details['episodes']
    ]
    if episodes_data:
        await db(saveEpisodes, saved.id, episodes_data)

    for ep in details['episodes']:
        ep.pop('_publishedAt', None)

    return details


#============================#
#======RSS AUDIO LOOKUP======#
#============================#
async def fetchRSSAudio(url: str) -> str:
    root = await getRSSRoot(url)
    channel = findChild(root, 'channel')

    if channel is None:
        return ''

    for item in channel:
        if localName(item.tag) != 'item':
            continue

        enclosure = findChild(item, 'enclosure')
        if enclosure is not None and enclosure.get('url'):
            return enclosure.get('url')

    return ''

def RSSCacheSet(url: str, audio_url: str) -> None:
    rssCache[url] = audio_url
    rssCache.move_to_end(url)

    while len(rssCache) > 256:
        rssCache.popitem(last=False)

async def parseRSS(url: str) -> str:
    if not url:
        return ''

    if url in rssCache:
        rssCache.move_to_end(url)
        return rssCache[url]

    task = rssTasks.get(url)

    if task is None:
        task = asyncio.create_task(fetchRSSAudio(url))
        rssTasks[url] = task

    try:
        audio_url = await task

        if audio_url:
            RSSCacheSet(url, audio_url)

        return audio_url

    finally:
        if rssTasks.get(url) is task and task.done():
            del rssTasks[url]

async def preloadRSS(url: str) -> None:
    if not url or url in rssCache:
        return

    try:
        await parseRSS(url)
    except (httpx.HTTPError, ValueError, ET.ParseError):
        pass