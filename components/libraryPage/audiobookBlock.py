import asyncio

import flet as ft
import flet.canvas as cv

from cards.libraryCard import openLibraryCard
from db.repositories import countLibraryItems, getLibraryItems
from utils.helpers import cover_image

#================#
#======REFS======#
#================#
audiobooksBlock = ft.Ref[ft.Container]()
audiobooksCountText = ft.Ref[ft.Text]()
audiobooksPreview = ft.Ref[ft.Row]()


#=====================#
#======FUNCTIONS======#
#=====================#
def applyAudiobooksPreview(total: int, items: list[dict]) -> None:
    if audiobooksCountText.current is not None:
        audiobooksCountText.current.value = str(total)

    if audiobooksPreview.current is not None:
        if total <= 0:
            audiobooksPreview.current.controls = emptyPreview()
        else:
            audiobooksPreview.current.controls = coversPreview(items, total)

    if audiobooksBlock.current is not None:
        audiobooksBlock.current.update()
    elif audiobooksPreview.current is not None:
        audiobooksPreview.current.update()

        if audiobooksCountText.current is not None:
            audiobooksCountText.current.update()

def emptyPreview() -> list[ft.Control]:
    return [
        cv.Canvas(
            width=50, height=50,
            content=ft.Icon(icon=ft.Icons.ADD, color='#8eaeff'),
            shapes=[
                cv.Rect(
                    x=1,
                    y=1,
                    width=48, height=48,
                    border_radius=7.5,
                    paint=ft.Paint(
                        color='#26385B',
                        stroke_width=1.5,
                        style=ft.PaintingStyle.STROKE,
                        stroke_dash_pattern=[6, 5]
                    )
                )
            ]
        ),
        ft.Column(
            controls=[
                ft.Text(
                    value='Nothing saved yet',
                    weight=ft.FontWeight.BOLD,
                    size=16,
                    font_family='SF-Pro-Regular',
                    color='#A0ADC8',
                    margin=ft.Margin.only(bottom=-10)
                ),
                ft.Text(
                    value='Save from details',
                    size=14,
                    font_family='SF-Pro-Regular',
                    color='#717F9D'
                )
            ]
        )
    ]

def coversPreview(items: list[dict], total: int) -> list[ft.Control]:
    controls: list[ft.Control] = [
        cover_image(
            item.get('image'),
            width=50, height=50,
            border_radius=7.5
        ) for item in items[:3]
    ]

    if total > 3:
        controls.append(
            ft.Text(
                value=f'+{total - 3} more',
                weight=ft.FontWeight.BOLD,
                size=14,
                font_family='SF-Pro-Semibold',
                color='#8E9BB8'
            )
        )

    return controls

async def loadAudiobooksBlock() -> None:
    total, items = await asyncio.gather(
        asyncio.to_thread(countLibraryItems, 'audiobook'),
        asyncio.to_thread(getLibraryItems, 'audiobook', 3, 0),
    )

    applyAudiobooksPreview(total=total, items=items)


#=====================#
#======COMPONENT======#
#=====================#
def createAudiobookBlock() -> ft.Container:
    return ft.Container(
        ref=audiobooksBlock,
        margin=ft.Margin.only(left=15, top=15, right=15),
        padding=ft.Padding.all(15),
        bgcolor='#111d39',
        border=ft.Border.all(width=1.5, color='#26385B'),
        border_radius=15,
        ink=True,
        ink_color='#1c2a4e',
        on_click=lambda e: e.page.run_task(openLibraryCard, e.page, 'audiobook'),
        content=ft.Column(
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    margin=ft.Margin.only(bottom=-10),
                    controls=[
                        ft.Text(
                            value='READ BY LISTENING',
                            weight=ft.FontWeight.BOLD,
                            size=14,
                            font_family='SF-Pro-Bold',
                            color='#8eaeff'
                        ),
                        ft.Container(
                            padding=ft.Padding.all(5),
                            bgcolor='#1B2B4A',
                            border_radius=50,
                            content=ft.Icon(
                                icon=ft.Icons.ARROW_OUTWARD,
                                color='#8eaeff'
                            )
                        )
                    ]
                ),
                ft.Text(
                    value='Audiobooks',
                    size=20,
                    font_family='SF-Pro-Semibold',
                    color='#f3f6ff',
                    margin=ft.Margin.only(bottom=-7.5)
                ),
                ft.Row(
                    controls=[
                        ft.Text(
                            ref=audiobooksCountText,
                            value='0',
                            weight=ft.FontWeight.BOLD,
                            size=22,
                            font_family='SF-Pro-Bold',
                            color='#F3F6FF',
                            margin=ft.Margin.only(top=-4, right=-5)
                        ),
                        ft.Text(
                            value='saved',
                            weight=ft.FontWeight.BOLD,
                            size=16,
                            font_family='SF-Pro-Semibold',
                            color='#8E9BB8'
                        )
                    ]
                ),
                ft.Row(
                    ref=audiobooksPreview,
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=emptyPreview()
                )
            ]
        )
    )