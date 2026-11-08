import asyncio
from math import pi

import flet as ft

from cards.detailsCard import openDetailsCard
from db.repositories import getLibraryItems
from utils.helpers import cover_image

#==================#
#======GLOBAL======#
#==================#
currentLibraryType = ''

dragDistance = 0


#================#
#======REFS======#
#================#
libraryCard = ft.Ref[ft.Container]()
libraryTitle = ft.Ref[ft.Text]()
libraryList = ft.Ref[ft.Column]()


#=====================#
#======FUNCTIONS======#
#=====================#


#======LIBRARY CARD======#
async def openLibraryCard(page: ft.Page, item_type: str) -> None:
    global currentLibraryType
    currentLibraryType = item_type

    if libraryCard.current is None:
        return

    if item_type == 'podcast':
        libraryTitle.current.value = 'Podcasts'
    else:
        libraryTitle.current.value = 'Audiobooks'

    libraryList.current.controls = [
        ft.Text(
            value='Loading...',
            size=16,
            font_family='SF-Pro-Regular',
            color='#717f9d',
        )
    ]

    libraryCard.current.offset = ft.Offset(0, 0)
    libraryCard.current.update()

    await asyncio.sleep(0.175)
    await loadLibraryItems(item_type=item_type)

def closeLibraryCard(e: ft.ControlEvent | None = None) -> None:
    if libraryCard.current is None:
        return

    libraryCard.current.offset = ft.Offset(1, 0)
    libraryCard.current.update()


#======LIBRARY CARD ANIMATION======#
def onDragStart(e: ft.DragStartEvent) -> None:
    global dragDistance

    dragDistance = 0
    libraryCard.current.animate_offset = ft.Animation(duration=30, curve=ft.AnimationCurve.LINEAR)

def onDragRight(e: ft.DragUpdateEvent) -> None:
    global dragDistance

    dragDistance += e.local_delta.x

    if dragDistance > 0:
        libraryCard.current.offset = ft.Offset(dragDistance / e.page.width, 0)
        libraryCard.current.update()

def onDragEnd(e: ft.DragEndEvent) -> None:
    global dragDistance

    isClose = dragDistance > 115

    libraryCard.current.animate_offset = ft.Animation(duration=150, curve=ft.AnimationCurve.EASE_OUT_CUBIC)
    libraryCard.current.offset = ft.Offset(1 if isClose else 0, 0)
    libraryCard.current.update()


#======LIBRARY LIST======#
async def loadLibraryItems(item_type: str) -> None:
    try:
        items = await asyncio.to_thread(getLibraryItems, item_type)
        renderLibraryItems(items)

    except Exception:
        if libraryList.current is None:
            return

        libraryList.current.controls = [
            ft.Text(
                value='Something went wrong',
                size=16,
                font_family='SF-Pro-Regular',
                color='#717f9d',
            )
        ]
        libraryList.current.update()

def renderLibraryItems(items: list[dict]) -> None:
    if libraryList.current is None:
        return

    if not items:
        libraryList.current.controls = [
            ft.Text(
                value='Nothing saved yet',
                size=16,
                font_family='SF-Pro-Regular',
                color='#717f9d',
            )
        ]
    else:
        cards = []
        for item in items:
            cards.append(
                ft.Container(
                    data=item,
                    padding=ft.Padding.all(10),
                    bgcolor='#111d39',
                    border=ft.Border.all(width=1.5, color='#26385B'),
                    border_radius=15,
                    ink=True,
                    ink_color='#1c2a4e',
                    on_click=lambda e: e.page.run_task(openLibraryItem, e),
                    content=ft.Row(
                        controls=[
                            cover_image(
                                item.get('image'),
                                width=50,
                                height=50,
                                border_radius=7.5,
                            ),
                            ft.Column(
                                expand=True,
                                controls=[
                                    ft.Text(
                                        value=item.get('title') or 'Untitled',
                                        weight=ft.FontWeight.BOLD,
                                        size=14,
                                        font_family='SF-Pro-Bold',
                                        color='#f3f6ff',
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        max_lines=1,
                                        margin=ft.Margin.only(bottom=-7.5),
                                    ),
                                    ft.Text(
                                        value=item.get('artist') or '-',
                                        weight=ft.FontWeight.BOLD,
                                        size=12,
                                        font_family='SF-Pro-Semibold',
                                        color='#717f9d',
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        max_lines=1,
                                    ),
                                ],
                            ),
                        ]
                    ),
                )
            )
        libraryList.current.controls = cards

    libraryList.current.update()

async def openLibraryItem(e: ft.ControlEvent) -> None:
    item = e.control.data
    if not item:
        return
    await openDetailsCard(page=e.page, item=item)


#=====================#
#======COMPONENT======#
#=====================#
def createLibraryCard(page: ft.Page) -> ft.Container:
    return ft.Container(
        ref=libraryCard,
        left=0,
        top=0,
        width=page.width, height=page.height,
        margin=ft.Margin.only(bottom=15),
        padding=ft.Padding.all(15),
        bgcolor='#070B19',
        offset=ft.Offset(1, 0),
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
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                                    icon_color='#8eaeff',
                                    rotate=pi,
                                    on_click=closeLibraryCard
                                ),
                                ft.Text(
                                    ref=libraryTitle,
                                    value='',
                                    size=22,
                                    font_family='SF-Pro-Bold',
                                    color='#f3f6ff'
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                                    icon_color='#070B19',
                                    disabled=True
                                )
                            ]
                        ),
                        ft.Column(
                            ref=libraryList,
                            expand=True,
                            scroll=ft.ScrollMode.AUTO,
                            spacing=10,
                            controls=[

                            ]
                        )
                    ]
                )
            )
        )
    )