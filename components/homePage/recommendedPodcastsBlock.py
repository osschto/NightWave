import asyncio
from random import choice, sample, shuffle

import flet as ft

from api.api import getPodcasts, preloadRSS
from cards.detailsCard import openDetailsCard
from utils.helpers import cover_image, item_key

#==================#
#======GLOBAL======#
#==================#
shownPodcastIds: set[str] = set()
podcastsRow = ft.Ref[ft.Row]()

_sessionPool: list[dict] = []

_SEED_TERMS = (
    'technology', 'science', 'history', 'music', 'comedy',
    'news', 'health', 'business', 'story', 'culture',
)

_TITLES = (
    'Curated for you', "What's new today?", 'Fresh talks inside',
    'Listen to this', 'Tap into ideas', 'Your daily feed',
    'Top picks today', 'Hear the trends', 'Voices that matter',
    'Stay in the loop',
)


#=====================#
#======FUNCTIONS======#
#=====================#
async def createPodcastsCards() -> list[ft.Container]:
    global shownPodcastIds, _sessionPool

    if len(_sessionPool) < 8:
        terms = sample(_SEED_TERMS, k=2)
        batches = await asyncio.gather(
            *(getPodcasts(term=term, limit=15) for term in terms),
            return_exceptions=True,
        )
        seen = {item_key(p) for p in _sessionPool}
        for batch in batches:
            if isinstance(batch, Exception):
                continue
            for podcast in batch:
                key = item_key(podcast)
                if key in seen:
                    continue
                seen.add(key)
                _sessionPool.append(podcast)

    fresh = [p for p in _sessionPool if item_key(p) not in shownPodcastIds]
    if len(fresh) < 5:
        shownPodcastIds.clear()
        fresh = list(_sessionPool)

    shuffle(fresh)
    selected = fresh[:5]

    for podcast in selected:
        shownPodcastIds.add(item_key(podcast))
        if podcast.get('rss') and not podcast.get('feedId'):
            asyncio.create_task(preloadRSS(podcast['rss']))

    items = [buildCard(podcast) for podcast in selected]

    if podcastsRow.current is not None:
        podcastsRow.current.controls = items
        podcastsRow.current.update()

    return items

def buildCard(podcast: dict) -> ft.Container:
    return ft.Container(
        data=podcast,
        content=ft.Column(
            controls=[
                ft.GestureDetector(
                    on_pan_down=onPanDown,
                    on_tap=onTap,
                    animate_scale=200,
                    content=cover_image(
                        podcast.get('image'),
                        width=150, height=150,
                        border_radius=7.5
                    )
                ),
                ft.Text(
                    value=podcast.get('title') or 'Untitled',
                    width=150,
                    size=16,
                    font_family='SF-Pro-Semibold',
                    color='#f3f6ff',
                    overflow=ft.TextOverflow.ELLIPSIS,
                    margin=ft.Margin.only(bottom=-8.5),
                ),
                ft.Text(
                    value=podcast.get('artist') or '-',
                    width=125,
                    size=14,
                    font_family='SF-Pro-Regular',
                    color='#717f9d',
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ]
        ),
    )

async def onTap(e: ft.TapEvent) -> None:
    item = e.control.parent.parent.data
    await openDetailsCard(page=e.page, item=item)

async def onPanDown(e: ft.ControlEvent) -> None:
    image = e.control.content
    image.scale = 0.95
    image.update()

    await asyncio.sleep(0.1)

    image.scale = 1
    image.update()


#=====================#
#======COMPONENT======#
#=====================#
def createRecommendedPodcastsBlock() -> ft.Container:
    return ft.Container(
        margin=ft.Margin.only(left=15, top=15, right=15),
        content=ft.Column(
            controls=[
                ft.Text(
                    value=choice(_TITLES),
                    size=22,
                    font_family='SF-Pro-Bold',
                    color='#f3f6ff',
                ),
                ft.Row(
                    ref=podcastsRow,
                    height=225,
                    scroll=ft.ScrollMode.HIDDEN,
                    controls=[],
                ),
            ]
        ),
    )
