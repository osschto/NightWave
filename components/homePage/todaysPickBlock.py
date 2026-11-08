import asyncio
from random import choice, randint
from string import ascii_lowercase

import flet as ft

from api.api import getAudiobooks, getPodcastEpisodes, getPodcasts, parseRSS, preloadRSS
from cards.playerCard import audioplayerPlay, openPlayerCard
from utils.helpers import DEFAULT_IMAGE, item_key, resolve_image

#==================#
#======GLOBAL======#
#==================#
shownTodaysPickIds: set[str] = set()


#================#
#======REFS======#
#================#
card = ft.Ref[ft.Container]()
image = ft.Ref[ft.Image]()
title = ft.Ref[ft.Text]()
artist = ft.Ref[ft.Text]()


#=====================#
#======FUNCTIONS======#
#=====================#
async def setTodaysPickItem() -> None:
    global shownTodaysPickIds

    is_podcast = randint(1, 2) == 1
    terms = [choice(ascii_lowercase) for _ in range(2)]

    if is_podcast:
        batches = await asyncio.gather(
            *(getPodcasts(term=t, limit=10) for t in terms),
            return_exceptions=True,
        )
    else:
        batches = await asyncio.gather(
            *(getAudiobooks(title=t, limit=10) for t in terms),
            return_exceptions=True,
        )

    items: list[dict] = []
    seen: set[str] = set()

    for batch in batches:
        if isinstance(batch, Exception):
            continue
        for result in batch:
            key = item_key(result)
            if key in seen:
                continue
            seen.add(key)
            items.append(result)

    fresh = [i for i in items if item_key(i) not in shownTodaysPickIds]
    if not fresh:
        shownTodaysPickIds.clear()
        fresh = items

    item = choice(fresh) if fresh else None
    if item:
        shownTodaysPickIds.add(item_key(item))

    if card.current is None:
        return

    card.current.data = item
    image.current.src = (
        resolve_image(item.get('image') if item else None)
    )
    title.current.value = (
        (item.get('title') if item else None) or 'Content is unavailable'
    )
    artist.current.value = (
        (item.get('artist') if item else None) or 'Content is unavailable'
    )
    card.current.update()

    if item and not item.get('feedId') and item.get('rss'):
        asyncio.create_task(preloadRSS(item['rss']))

async def onClickListenButton(e: ft.ControlEvent) -> None:
    item = card.current.data if card.current else None
    if not item:
        return

    if item.get('feedId'):
        episodes = await getPodcastEpisodes(feedId=item['feedId'], limit=1)
        if not episodes:
            return
        audio_url = episodes[0].get('audio')
        ep_title = episodes[0].get('title') or item.get('title') or 'Episode'
    else:
        audio_url = await parseRSS(item.get('rss', ''))
        ep_title = item.get('title') or 'Episode'

    if not audio_url:
        return

    openPlayerCard(
        image=resolve_image(item.get('image')),
        title=ep_title,
        artist=item.get('artist') or '',
    )
    await audioplayerPlay(page=e.page, url=audio_url)


#=====================#
#======COMPONENT======#
#=====================#
def createTodaysPickBlock() -> ft.Container:
    return ft.Container(
        ref=card,
        data='',
        margin=ft.Margin.only(left=15, top=15, right=15),
        padding=ft.Padding.all(15),
        bgcolor='#111d39',
        border=ft.Border.all(width=1.5, color='#26385B'),
        border_radius=15,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Image(
                            ref=image,
                            src=DEFAULT_IMAGE,
                            width=75,
                            height=75,
                            border_radius=7.5,
                        ),
                        ft.Column(
                            width=265,
                            controls=[
                                ft.Text(
                                    value="Today's pick",
                                    size=18,
                                    font_family='SF-Pro-Bold',
                                    color='#8eaeff',
                                    margin=ft.Margin.only(bottom=-7.5),
                                ),
                                ft.Text(
                                    ref=title,
                                    value='',
                                    size=16,
                                    font_family='SF-Pro-Semibold',
                                    color='#f3f6ff',
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    margin=ft.Margin.only(bottom=-10),
                                ),
                                ft.Text(
                                    ref=artist,
                                    value='',
                                    size=14,
                                    font_family='SF-Pro-Regular',
                                    color='#717f9d',
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                        ),
                    ]
                ),
                ft.Container(
                    padding=7.5,
                    bgcolor='#1a2b4f',
                    ink=True,
                    ink_color='#344C7B',
                    border=ft.Border.all(width=0.75, color='#3D5684'),
                    border_radius=10,
                    on_click=onClickListenButton,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(icon=ft.Icons.PLAY_CIRCLE, color='#8eaeff'),
                                    ft.Text(
                                        value='Listen now',
                                        weight=ft.FontWeight.BOLD,
                                        size=16,
                                        font_family='SF-Pro-Black',
                                        color='#f3f6ff',
                                    ),
                                ]
                            ),
                            ft.Icon(icon=ft.Icons.HEADPHONES_OUTLINED, color='#8eaeff'),
                        ],
                    ),
                ),
            ]
        ),
    )
