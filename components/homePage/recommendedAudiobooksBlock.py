import asyncio
from random import choice, sample, shuffle

import flet as ft

from api.api import getAudiobooks, preloadRSS
from cards.detailsCard import openDetailsCard
from utils.helpers import cover_image, item_key

#==================#
#======GLOBAL======#
#==================#
shownAudiobookIds: set[str] = set()
audiobooksRow = ft.Ref[ft.Row]()
_sessionPool: list[dict] = []

_SEED_TERMS = (
    'love', 'war', 'adventure', 'mystery', 'life',
    'king', 'story', 'time', 'night', 'dream',
)

_TITLES = (
    'Next page next', 'Pick your story', 'Dive into books',
    'Listen to chapters', 'Your digital shelf', 'Stories for you',
    'Read with ears', 'Get lost in plot', 'Bestsellers for you',
    'Start a new world',
)


#=====================#
#======FUNCTIONS======#
#=====================#
async def createAudiobooksCards() -> list[ft.Container]:
    global shownAudiobookIds, _sessionPool

    if len(_sessionPool) < 8:
        terms = sample(_SEED_TERMS, k=2)
        batches = await asyncio.gather(
            *(getAudiobooks(title=term, limit=15) for term in terms),
            return_exceptions=True,
        )
        seen = {item_key(b) for b in _sessionPool}
        for batch in batches:
            if isinstance(batch, Exception):
                continue
            for book in batch:
                key = item_key(book)
                if key in seen:
                    continue
                seen.add(key)
                _sessionPool.append(book)

    fresh = [b for b in _sessionPool if item_key(b) not in shownAudiobookIds]
    if len(fresh) < 5:
        shownAudiobookIds.clear()
        fresh = list(_sessionPool)

    shuffle(fresh)
    selected = fresh[:5]

    for book in selected:
        shownAudiobookIds.add(item_key(book))
        rss = book.get('rss')
        if rss:
            asyncio.create_task(preloadRSS(rss))

    items = [buildCard(book) for book in selected]

    if audiobooksRow.current is not None:
        audiobooksRow.current.controls = items
        audiobooksRow.current.update()

    return items

def buildCard(book: dict) -> ft.Container:
    return ft.Container(
        data=book,
        content=ft.Column(
            controls=[
                ft.GestureDetector(
                    on_pan_down=onPanDown,
                    on_tap=onTap,
                    animate_scale=150,
                    content=cover_image(
                        book.get('image'),
                        width=150, height=150,
                        border_radius=7.5
                    )
                ),
                ft.Text(
                    value=book.get('title') or 'Untitled',
                    width=150,
                    size=16,
                    font_family='SF-Pro-Semibold',
                    color='#f3f6ff',
                    overflow=ft.TextOverflow.ELLIPSIS,
                    margin=ft.Margin.only(bottom=-8.5),
                ),
                ft.Text(
                    value=book.get('artist') or '-',
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
def createRecommendedAudiobooksBlock() -> ft.Container:
    return ft.Container(
        margin=ft.Margin.only(left=15, right=15),
        content=ft.Column(
            controls=[
                ft.Text(
                    value=choice(_TITLES),
                    size=22,
                    font_family='SF-Pro-Bold',
                    color='#f3f6ff',
                ),
                ft.Row(
                    ref=audiobooksRow,
                    height=225,
                    scroll=ft.ScrollMode.HIDDEN,
                    controls=[],
                ),
            ]
        ),
    )
