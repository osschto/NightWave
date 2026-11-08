import asyncio
from math import pi

import flet as ft

from api.api import getAudiobookGenrePage, getPodcastGenrePage
from cards.detailsCard import openDetailsCard
from utils.helpers import cover_image, resolve_image

#==================#
#======GLOBAL======#
#==================#
dragDistance = 0

currentGenre = ''
currentGenreType = ''

currentOffset = 0
currentHasMore = False
isLoadingMore = False

requestId = 0


PODCAST_GENRES = [
    'Sports', 'Education', 'Health', 'Fitness', 'Arts',
    'Comedy', 'Leisure', 'Design', 'Business', 'Science',
]

AUDIOBOOK_GENRES = [
    'Romance', 'Historical', 'Biography', 'Satire', 'Drama',
    'Poetry', 'Lyric', 'History', 'Nature', 'Philosophy',
]


#================#
#======REFS======#
#================#
genreCard = ft.Ref[ft.Container]()
genreTitle = ft.Ref[ft.ShaderMask]()
genreDescription = ft.Ref[ft.ShaderMask]()
backButton = ft.Ref[ft.ShaderMask]()
genresList = ft.Ref[ft.Column]()
showMoreButton = ft.Ref[ft.Container]()


#=====================#
#======FUNCTIONS======#
#=====================#


#======GENRE CARD======#
async def openGenreCard(title: str, description: str, gradientColor1: str, gradientColor2: str) -> None:
    if genreCard.current is None:
        return

    genreTitle.current.content.value = title
    genreTitle.current.shader.colors = [gradientColor1, gradientColor2]
    genreDescription.current.content.value = description
    genreDescription.current.shader.colors = [gradientColor1, gradientColor2]
    backButton.current.shader.colors = [gradientColor1, gradientColor2]

    genresList.current.controls.clear()
    genresList.current.controls.append(
        ft.Text(
            align=ft.Alignment.CENTER,
            value='Loading...',
            weight=ft.FontWeight.BOLD,
            size=24,
            font_family='SF-Pro-Bold',
            color='#717f9d',
            margin=ft.Margin.only(top=125),
        )
    )

    genreCard.current.offset = ft.Offset(0, 0)
    genreCard.current.update()

    await asyncio.sleep(0.175)
    await loadGenres(genre=title)

def closeGenreCard() -> None:
    if genreCard.current is None:
            return
    
    genreCard.current.offset = ft.Offset(1, 0)
    genreCard.current.update()


#======GENRE CARD ANIMATION======#
def onDragStart(e: ft.DragStartEvent) -> None:
    global dragDistance

    dragDistance = 0

    genreCard.current.animate_offset = ft.Animation(duration=30, curve=ft.AnimationCurve.LINEAR)

def onDragRight(e: ft.DragUpdateEvent) -> None:
    global dragDistance

    dragDistance += e.local_delta.x

    if dragDistance > 0:
        genreCard.current.offset = ft.Offset(dragDistance / e.page.width, 0)
        genreCard.current.update()

def onDragEnd(e: ft.DragEndEvent) -> None:
    global dragDistance

    isClose = dragDistance > 115

    genreCard.current.animate_offset = ft.Animation(duration=150, curve=ft.AnimationCurve.EASE_IN_OUT)
    genreCard.current.offset = ft.Offset(1 if isClose else 0, 0)
    genreCard.current.update()

#======GENRES LIST======#
async def loadGenres(genre: str) -> None:
    global currentGenre, currentGenreType
    global currentOffset, currentHasMore, isLoadingMore, requestId

    requestId += 1
    currentRequestId = requestId

    if genre in PODCAST_GENRES:
        currentGenreType = 'Podcast'
    elif genre in AUDIOBOOK_GENRES:
        currentGenreType = 'Audiobook'

    currentGenre = genre
    currentOffset = 0
    currentHasMore = False
    isLoadingMore = False

    if showMoreButton.current is not None:
        showMoreButton.current.visible = False
        showMoreButton.current.update()

    try:
        if currentGenreType == 'Podcast':
            data = await getPodcastGenrePage(genre=genre, limit=15, offset=0)
        else:
            data = await getAudiobookGenrePage(genre=genre, limit=15, offset=0)

        if currentRequestId != requestId:
            return

        results = data['results']

        currentOffset = len(results)
        currentHasMore = data['hasMore']

        renderGenresCards(data=results, genreType=currentGenreType, append=False)

        if showMoreButton.current is not None:
            showMoreButton.current.visible = currentHasMore
            showMoreButton.current.update()

    except Exception:

        if currentRequestId != requestId:
            return

        genresList.current.controls.clear()
        genresList.current.controls.append(
            ft.Text(
                align=ft.Alignment.CENTER,
                value='Something went wrong',
                weight=ft.FontWeight.BOLD,
                size=24,
                font_family='SF-Pro-Bold',
                color='#717f9d',
                margin=ft.Margin.only(top=125)
            )
        )

        genresList.current.update()

async def loadMoreGenres(e: ft.ControlEvent) -> None:
    global currentOffset, currentHasMore
    global isLoadingMore

    if isLoadingMore or not currentHasMore:
        return

    isLoadingMore = True

    currentRequestId = requestId
    genre = currentGenre
    genreType = currentGenreType
    offset = currentOffset

    showMoreButton.current.content.controls[0].value = 'Loading...'
    showMoreButton.current.content.controls[1].value = 'Please wait'
    showMoreButton.current.update()

    try:
        if genreType == 'Podcast':
            data = await getPodcastGenrePage(genre=genre, offset=offset, limit=15)
        else:
            data = await getAudiobookGenrePage(genre=genre, offset=offset, limit=15)

        if currentRequestId != requestId:
            return

        results = data['results']

        if not results:
            currentHasMore = False
            return

        renderGenresCards(data=results, genreType=genreType, append=True)

        currentOffset += len(results)
        currentHasMore = data['hasMore']

    except Exception:
        if currentRequestId != requestId:
            return

        showMoreButton.current.content.controls[0].value = 'Loading error'
        showMoreButton.current.content.controls[1].value = 'Please try again'
        showMoreButton.current.update()

    finally:
        if currentRequestId == requestId:
            isLoadingMore = False

            showMoreButton.current.content.controls[0].value = 'Load more'
            showMoreButton.current.content.controls[1].value = 'Show next 15 results'
            showMoreButton.current.visible = currentHasMore
            showMoreButton.current.update()

def renderGenresCards(data: list[dict], genreType: str, append: bool) -> None:
    if not append:
        genresList.current.controls.clear()

    if not data and not append:
        genresList.current.controls.append(
            ft.Text(
                align=ft.Alignment.CENTER,
                value='Nothing found',
                weight=ft.FontWeight.BOLD,
                size=22,
                font_family='SF-Pro-Bold',
                color='#717f9d',
                margin=ft.Margin.only(top=125)
            )
        )

        genresList.current.update()
        return

    for item in data:
        itemImage = resolve_image(item.get('image'))
        itemTitle = item.get('title') or 'Untitled'
        itemArtist = item.get('artist') or '-'
        
        card = ft.Container(
            data=item,
            padding=ft.Padding.all(10),
            bgcolor='#111d39',
            border=ft.Border.all(width=1.5, color='#26385B'),
            border_radius=15,
            ink=True,
            ink_color='#1c2a4e',
            on_click=openItemDetails,
            content=ft.Row(
                controls=[
                    cover_image(
                        itemImage,
                        width=50, height=50,
                        border_radius=7.5
                    ),
                    ft.Column(
                        expand=True,
                        controls=[
                            ft.Text(
                                value=itemTitle,
                                weight=ft.FontWeight.BOLD,
                                size=14,
                                font_family='SF-Pro-Bold',
                                color='#f3f6ff',
                                overflow=ft.TextOverflow.ELLIPSIS,
                                margin=ft.Margin.only(bottom=-7.5)
                            ),
                            ft.Text(
                                value=f'{genreType} • {itemArtist}',
                                weight=ft.FontWeight.BOLD,
                                size=12,
                                font_family='SF-Pro-Semibold',
                                color='#717f9d',
                                overflow=ft.TextOverflow.ELLIPSIS
                            )
                        ]
                    )
                ]
            )
        )

        genresList.current.controls.append(card)

    genresList.current.update()

async def openItemDetails(e: ft.ControlEvent) -> None:
    item = e.control.data
    await openDetailsCard(page=e.page, item=item)


#=====================#
#======COMPONENT======#
#=====================#
def createGenreCard(page: ft.Page) -> ft.Container:
    return ft.Container(
        ref=genreCard,
        left=0,
        top=0,
        width=page.width,
        height=page.height,
        margin=ft.Margin.only(bottom=15),
        padding=ft.Padding.all(15),
        bgcolor='#070B19',
        offset=ft.Offset(1, 0),
        animate_offset=ft.Animation(duration=150, curve=ft.AnimationCurve.EASE_IN_OUT),
        content=ft.SafeArea(
            avoid_intrusions_bottom=True,
            avoid_intrusions_top=True,
            expand=True,
            content=ft.GestureDetector(
                drag_interval=8,
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
                                ft.ShaderMask(
                                    ref=backButton,
                                    blend_mode=ft.BlendMode.SRC_IN,
                                    shader=ft.LinearGradient(colors=['#ffffff', '#ffffff']),
                                    content=ft.IconButton(
                                        icon=ft.Icons.ARROW_BACK_IOS_NEW,
                                        rotate=pi,
                                        on_click=closeGenreCard
                                    )
                                ),
                                ft.ShaderMask(
                                    ref=genreTitle,
                                    blend_mode=ft.BlendMode.SRC_IN,
                                    shader=ft.LinearGradient(colors=['#ffffff', '#ffffff']),
                                    content=ft.Text(
                                        align=ft.Alignment.CENTER,
                                            value='',
                                            size=32,
                                            font_family='SF-Pro-Bold'
                                    )
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                                    icon_color='#070B19',
                                    disabled=True
                                ),
                            ]
                        ),
                        ft.ShaderMask(
                            ref=genreDescription,
                            blend_mode=ft.BlendMode.SRC_IN,
                            shader=ft.LinearGradient(colors=['#ffffff', '#ffffff']),
                            content=ft.Text(
                                    align=ft.Alignment.CENTER,
                                    text_align=ft.TextAlign.CENTER,
                                    width=page.width,
                                    value='',
                                    size=16,
                                    font_family='SF-Pro-Bold',
                            )
                        ),
                        ft.Column(
                            ref=genresList,
                            margin=ft.Margin.only(top=15),
                            controls=[

                            ]
                        ),
                        ft.Container(
                            ref=showMoreButton,
                            align=ft.Alignment.CENTER,
                            width = page.width * 0.45,
                            padding=ft.Padding.all(7.5),
                            bgcolor='#1a2b4f',
                            ink=True,
                            ink_color='#344C7B',
                            border=ft.Border.all(width=0.75, color='#3D5684'),
                            border_radius=10,
                            visible=False,
                            on_click=loadMoreGenres,
                            content=ft.Column(
                                alignment=ft.MainAxisAlignment.CENTER,
                                controls=[
                                    ft.Text(
                                        align=ft.Alignment.CENTER,
                                        value='Load more',
                                        weight=ft.FontWeight.BOLD,
                                        size=16,
                                        font_family='SF-Pro-Bold',
                                        color='#f3f6ff'
                                    ),
                                    ft.Text(
                                        align=ft.Alignment.CENTER,
                                        value='Show next 15 results',
                                        weight=ft.FontWeight.BOLD,
                                        size=14,
                                        font_family='SF-Pro-Regular',
                                        color='#717f9d',
                                        margin=ft.Margin.only(top=-7.5)
                                    )
                                ]
                            )
                        )
                    ]
                )
            ) 
        )
    )