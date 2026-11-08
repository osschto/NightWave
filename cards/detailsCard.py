import asyncio
import html
import re
from math import pi

import flet as ft

from api.api import getFeedDetails, getPodcastEpisodes
from cards.playerCard import audioplayerPlay, openPlayerCard
from db.repositories import isLibraryItemSaved, removeLibraryItem, saveLibraryItem
from utils.helpers import DEFAULT_IMAGE, resolve_image

#==================#
#======GLOBAL======#
#==================#
currentDetailsItem: dict | None = None

allEpisodes: list[dict] = []
visibleEpisodes = 0

saveToggleBusy = False

dragDistance = 0


#================#
#======REFS======#
#================#
detailsCard = ft.Ref[ft.Container]()
detailsCardImage = ft.Ref[ft.Image]()
detailsCardTitle = ft.Ref[ft.Text]()
detailsCardArtist = ft.Ref[ft.Text]()
detailsCardDescription = ft.Ref[ft.Text]()
detailsCardEpisodesList = ft.Ref[ft.Column]()
showMoreButton = ft.Ref[ft.Container]()
detailsSaveButton = ft.Ref[ft.IconButton]()

#=====================#
#======FUNCTIONS======#
#=====================#


#======DETAILS CARD======#
async def openDetailsCard(page: ft.Page, item: dict) -> None:
    global currentDetailsItem
    currentDetailsItem = item

    if detailsCard.current is None:
        return

    detailsCardTitle.current.value = ''
    detailsCardArtist.current.value = ''
    detailsCardImage.current.src = resolve_image(item.get('image'))
    detailsCardDescription.current.value = 'Loading description...'
    detailsCardEpisodesList.current.controls = [
        ft.Text(
            value='Loading episodes...',
            size=14,
            font_family='SF-Pro-Regular',
            color='#717f9d',
        )
    ]

    detailsCard.current.offset = ft.Offset(0, 0)
    detailsCard.current.update()

    await asyncio.sleep(0.175)
    await setAllDetailsValues(item=item)
    await refreshDetailsSaveButton(item=item)

def closeDetailsCard() -> None:
    if detailsCard.current is None:
            return

    detailsCard.current.offset = ft.Offset(1, 0)
    detailsCard.current.update()

async def setAllDetailsValues(item: dict) -> None:
    if item.get('feedId'):
        episodes = await getPodcastEpisodes(feedId=item['feedId'], limit=50)

        details = {
            'title': item.get('title'),
            'artist': item.get('artist'),
            'description': item.get('description'),
            'image': item.get('image'),
            'episodes': episodes,
        }
    else:
        details = await getFeedDetails(item.get('rss'))

    detailsCardTitle.current.value = details.get('title') or item.get('title')
    detailsCardArtist.current.value = getDisplayArtist(
        apiArtist=details.get('artist'),
        itemArtist=item.get('artist'),
    )
    detailsCardImage.current.src = (
        resolve_image(details.get('image') or item.get('image'))
    )
    description = details.get('description') or item.get('description')
    detailsCardDescription.current.value = cleanDescription(description=description)

    episodes = details.get('episodes', [])
    renderEpisodes(item=item, episodes=episodes, update=False)

    detailsCard.current.update()


#======DETAILS CARD ANIMATION======#
def onDragStart(e: ft.DragStartEvent) -> None:
    global dragDistance
    
    dragDistance = 0

    detailsCard.current.animate_offset = ft.Animation(duration=30, curve=ft.AnimationCurve.LINEAR)

def onDragRight(e: ft.DragUpdateEvent) -> None:
    global dragDistance

    dragDistance += e.local_delta.x

    if dragDistance > 0:
        detailsCard.current.offset = ft.Offset(dragDistance / e.page.width, 0)
        detailsCard.current.update()

def onDragEnd(e: ft.DragEndEvent) -> None:
    global dragDistance

    isClose = dragDistance > 115

    detailsCard.current.animate_offset = ft.Animation(duration=150, curve=ft.AnimationCurve.EASE_OUT_CUBIC)
    detailsCard.current.offset = ft.Offset(1 if isClose else 0, 0)
    detailsCard.current.update()


#======FAVORITE BUTTON======#
async def refreshDetailsSaveButton(item: dict | None = None, saved: bool | None = None) -> None:
    if detailsSaveButton.current is None:
        return

    item = item if item is not None else currentDetailsItem
    item_id, item_type = detailLibraryIds(item)

    if item_id is None or item_type is None:
        detailsSaveButton.current.icon = ft.Icons.FAVORITE_BORDER
        detailsSaveButton.current.icon_color = '#8eaeff'
        detailsSaveButton.current.update()
        return

    if saved is None:
        saved = await asyncio.to_thread(isLibraryItemSaved, item_id, item_type)

    detailsSaveButton.current.icon = ft.Icons.FAVORITE if saved else ft.Icons.FAVORITE_BORDER
    detailsSaveButton.current.icon_color = '#8eaeff'
    detailsSaveButton.current.update()

async def toggleDetailsSave(e: ft.ControlEvent) -> None:
    global saveToggleBusy

    if saveToggleBusy:
        return

    item = currentDetailsItem
    item_id, item_type = detailLibraryIds(item)

    if item is None or item_id is None or item_type is None:
        return

    saveToggleBusy = True
    try:
        was_saved = await asyncio.to_thread(isLibraryItemSaved, item_id, item_type)

        if was_saved:
            await asyncio.to_thread(removeLibraryItem, item_id, item_type)
            await refreshDetailsSaveButton(item=item, saved=False)
        else:
            payload = dict(item)
            if not payload.get('title'):
                payload['title'] = (
                    detailsCardTitle.current.value
                    if detailsCardTitle.current and detailsCardTitle.current.value
                    else 'Untitled'
                )

            if not payload.get('itemType'):
                payload['itemType'] = item_type

            await asyncio.to_thread(saveLibraryItem, item=payload, item_id=item_id, item_type=item_type)
            await refreshDetailsSaveButton(item=item, saved=True)

        await syncLibraryUi(item_type)

    except Exception:
        await refreshDetailsSaveButton(item=item, saved=None)

    finally:
        saveToggleBusy = False


#======HELPING FUNCTIONS======#
def cleanDescription(description: str) -> str:
    if not description:
        return ''

    text = re.sub(
        r'<\s*(br|/p|/div|/li|/h[1-6])\b[^>]*>',
        '\n',
        description,
        flags=re.IGNORECASE,
    )
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)

    lines = [
        re.sub(r'[ \t]+', ' ', line).strip()
        for line in text.splitlines()
    ]
    return '\n'.join(line for line in lines if line)

def formatDuration(seconds: int) -> str:
    if not seconds:
        return ''

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes}:{seconds:02}'

def setImage(imageRef: ft.Ref[ft.Image], imageUrl: str | None) -> None:
    image = imageRef.current
    image.src = resolve_image(imageUrl)
    image.update()

def getDisplayArtist(apiArtist: str | None, itemArtist: str | None) -> str:
    for artist in (apiArtist, itemArtist):
        if artist and artist.strip().lower() not in ('librivox', '-'):
            return artist.strip()

    return 'Unknown author'

def detailLibraryIds(item: dict | None) -> tuple[str | int | None, str | None]:
    if not item:
        return None, None

    item_type = item.get('itemType')
    if item_type not in ('podcast', 'audiobook'):
        if item.get('feedId') is not None:
            item_type = 'podcast'
        elif item.get('librivoxId') is not None:
            item_type = 'audiobook'
        else:
            return None, None

    if item_type == 'podcast':
        item_id = item.get('feedId') or item.get('id') or item.get('rss')
    else:
        item_id = item.get('librivoxId') or item.get('id') or item.get('rss')

    if not item_id:
        return None, None

    return item_id, item_type

async def syncLibraryUi(item_type: str) -> None:
    try:
        from cards.libraryCard import currentLibraryType, loadLibraryItems

        if currentLibraryType == item_type:
            await loadLibraryItems(item_type)

    except Exception as error:
        print(f'Library list sync error: {error}')

    try:
        if item_type == 'podcast':
            from components.libraryPage.podcastBlock import loadPodcastsBlock
            await loadPodcastsBlock()
        elif item_type == 'audiobook':
            from components.libraryPage.audiobookBlock import loadAudiobooksBlock
            await loadAudiobooksBlock()

    except Exception as error:
        print(f'Library preview sync error: {error}')


#======EPISODE CARD + PLAY EPISODE FUNCTION======#
def createEpisodeCard(item: dict, episode: dict) -> None:
    duration = formatDuration(episode.get('duration', 0))
    date = episode.get('date', '')
    metadata = ' · '.join(v for v in (date, duration) if v)

    return ft.Container(
        padding=ft.Padding.all(10),
        bgcolor='#111d39',
        border=ft.Border.all(width=1.5, color='#26385B'),
        border_radius=15,
        ink=True,
        ink_color='#1c2a4e',
        on_click=lambda e: e.page.run_task(playEpisode, page=e.page, item=item, episode=episode),
        content=ft.Row(
            controls=[
                ft.Container(
                    width=50,
                    height=50,
                    border_radius=10,
                    bgcolor='#202B45',
                    content=ft.Icon(
                        icon=ft.Icons.PLAY_ARROW_OUTLINED,
                        color='#8eaeff'
                    )
                ),
                ft.Column(
                    expand=True,
                    controls=[
                        ft.Text(
                            value=episode.get('title') or 'Episode',
                            size=14,
                            font_family='SF-Pro-Semibold',
                            color='#F3F6FF',
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            margin=ft.Margin.only(bottom=-10)
                        ),
                        ft.Text(
                            value=metadata or 'Episode',
                            size=12,
                            font_family='SF-Pro-Regular',
                            color='#717f9d'
                        )
                    ]
                )
            ]
        )
    )

def renderEpisodes(item: dict, episodes: list[dict], update: bool = True) -> None:
    global allEpisodes, visibleEpisodes

    allEpisodes = episodes
    visibleEpisodes = min(5, len(allEpisodes))

    detailsCardEpisodesList.current.controls = [
        createEpisodeCard(item=item, episode=episode)
        for episode in allEpisodes[:visibleEpisodes]
    ]
    showMoreButton.current.visible = visibleEpisodes < len(allEpisodes)

    if update:
        detailsCardEpisodesList.current.update()
        showMoreButton.current.update()

def showMoreEpisodes(item: dict) -> None:
    global visibleEpisodes

    nextIndex = min(visibleEpisodes + 5, len(allEpisodes))

    detailsCardEpisodesList.current.controls.extend(
        createEpisodeCard(item=item, episode=episode)
        for episode in allEpisodes[visibleEpisodes:nextIndex]
    )

    visibleEpisodes = nextIndex

    showMoreButton.current.visible = visibleEpisodes < len(allEpisodes)

    detailsCardEpisodesList.current.update()
    showMoreButton.current.update()

async def playEpisode(page: ft.Page, item: dict, episode: dict) -> None:
    audioUrl = episode.get('audio')

    if not audioUrl:
        return

    openPlayerCard(
        image=resolve_image(detailsCardImage.current.src or item.get('image')),
        title=episode.get('title') or 'Episode',
        artist=detailsCardArtist.current.value or item.get('artist') or '',
    )

    await audioplayerPlay(page=page, url=audioUrl)


#=====================#
#======COMPONENT======#
#=====================#
def createDetailsCard(page: ft.Page) -> ft.Container:
    return ft.Container(
        ref=detailsCard,
        left=0,
        top=0,
        width=page.width,
        height=page.height,
        offset=ft.Offset(1, 0),
        margin=ft.Margin.only(bottom=15),
        padding=ft.Padding.all(15),
        bgcolor='#070B19',
        animate_offset=ft.Animation(duration=150, curve=ft.AnimationCurve.EASE_OUT_CUBIC),
        content=ft.SafeArea(
            avoid_intrusions_bottom=True,
            avoid_intrusions_top=True,
            expand=True,
            content=ft.GestureDetector(
                on_horizontal_drag_start=onDragStart,
                on_horizontal_drag_update=onDragRight,
                on_horizontal_drag_end=onDragEnd,
                content=ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                                    icon_color='#8eaeff',
                                    rotate=pi,
                                    on_click=closeDetailsCard
                                ),
                                ft.IconButton(
                                    ref=detailsSaveButton,
                                    icon=ft.Icons.FAVORITE_BORDER,
                                    icon_color='#8eaeff',
                                    on_click=toggleDetailsSave
                                )
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Image(
                                    ref=detailsCardImage,
                                    width=page.width * 0.55, height=page.width * 0.55,
                                    src=DEFAULT_IMAGE,
                                    fit=ft.BoxFit.COVER,
                                    border_radius=7.5,
                                    error_content=ft.Image(
                                        width=page.width * 0.55, height=page.width * 0.55,
                                        src=DEFAULT_IMAGE,
                                        fit=ft.BoxFit.COVER,
                                        border_radius=7.5
                                    )
                                )
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    ref=detailsCardTitle,
                                    expand=True,
                                    value='',
                                    size=22,
                                    font_family='SF-Pro-Bold',
                                    color='#f3f6ff',
                                    text_align=ft.TextAlign.CENTER,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    margin=ft.Margin.only(bottom=-7.5)
                                )
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    ref=detailsCardArtist,
                                    expand=True,
                                    value='',
                                    size=18,
                                    font_family='SF-Pro-Semibold',
                                    color='#717f9d',
                                    text_align=ft.TextAlign.CENTER,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS
                                )
                            ]
                        ),
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            value ='Description',
                                            size=22,
                                            font_family='SF-Pro-Semibold',
                                            color='#F3F6FF',
                                            margin=ft.Margin.only(bottom=-5)
                                        )
                                    ]
                                ),
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            ref=detailsCardDescription,
                                            expand=True,
                                            value='',
                                            size=14,
                                            font_family='SF-Pro-Regular',
                                            color='#717f9d',
                                            overflow=ft.TextOverflow.CLIP
                                        )
                                    ]
                                )
                            ]
                        ),
                        ft.Row(
                            controls=[
                                ft.Text(
                                    value ='Episodes',
                                    size=22,
                                    font_family='SF-Pro-Semibold',
                                    color='#F3F6FF'
                                )
                            ]
                        ),
                        ft.Column(
                            ref=detailsCardEpisodesList,
                            controls=[
                                ft.Text(
                                    value='',
                                    size=14,
                                    font_family='SF-Pro-Regular',
                                    color='#717f9d'
                                )
                            ]
                        ),
                        ft.Container(
                            ref=showMoreButton,
                            align=ft.Alignment.CENTER,
                            width = page.width * 0.40,
                            padding=ft.Padding.all(15),
                            bgcolor='#1a2b4f',
                            ink=True,
                            ink_color='#344C7B',
                            border=ft.Border.all(width=0.75, color='#3D5684'),
                            border_radius=10,
                            on_click=showMoreEpisodes,
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.CENTER,
                                controls=[
                                    ft.Text(value='Show more', weight=ft.FontWeight.BOLD, size=16, font_family='SF-Pro-Black', color='#f3f6ff'),
                                    ft.Icon(icon=ft.Icons.KEYBOARD_ARROW_DOWN, color='#8eaeff')
                                ]
                            )
                        )
                    ]
                )
            )
        )
    )