import flet as ft

from components.searchPage.searchFieldBlock import createSearchFieldBlock
from components.searchPage.genresListBlock import createGenresListBlock

def createSearchPage(page: ft.Page) -> ft.Container:
    searchFieldBlock = createSearchFieldBlock(page=page)
    genresListBlock = createGenresListBlock()

    return ft.Container(
        expand=True,
        content=ft.Column(
            scroll=ft.ScrollMode.HIDDEN,
            controls=[
                ft.Container(height=60),
                searchFieldBlock,
                genresListBlock,
                ft.Container(height=65)
            ]
        )
    )