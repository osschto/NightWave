import flet as ft

from db.db import createDB
createDB()

from cards.detailsCard import createDetailsCard
from cards.genreCard import createGenreCard
from cards.playerCard import createPlayerCard
from cards.searchCard import createSearchCard
from cards.libraryCard import createLibraryCard

from pages.mainPage import createMainPage

async def main(page: ft.Page) -> None:
    page.title = 'NightWave'
    page.adaptive = True

    page.bgcolor = '#070B19'
    page.padding = 0

    page.theme = ft.Theme(
        system_overlay_style=ft.SystemOverlayStyle(
            system_navigation_bar_color='#070819',
            system_navigation_bar_divider_color='#070819',
            system_navigation_bar_icon_brightness=ft.Brightness.LIGHT,
            
            status_bar_color='#070819',
            status_bar_icon_brightness=ft.Brightness.LIGHT,
            
            enforce_system_navigation_bar_contrast=False,
            enforce_system_status_bar_contrast=False,
        )
    )

    page.fonts = {
    'SF-Pro-Black': 'fonts/SF-Pro-Black.ttf',
    'SF-Pro-Bold': 'fonts/SF-Pro-Bold.ttf',
    'SF-Pro-Regular': 'fonts/SF-Pro-Regular.ttf',
    'SF-Pro-Semibold': 'fonts/SF-Pro-Semibold.ttf',
    }
    
    genreCard = createGenreCard(page=page)
    searchCard = createSearchCard(page=page)
    libraryCard = createLibraryCard(page=page)
    detailsCard = createDetailsCard(page=page)
    playerCard = createPlayerCard(page=page)

    page.overlay.extend([
        genreCard,
        searchCard,
        libraryCard,
        detailsCard,
        playerCard
    ])

    mainPage = createMainPage(page=page)
    page.add(mainPage)

ft.run(main=main, assets_dir='assets')