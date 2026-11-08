import flet as ft

from pages.homePage import createHomePage
from pages.libraryPage import createLibraryPage
from pages.searchPage import createSearchPage

from utils.navigationBar import createNavigationBar
from utils.header import createHeader

pages: dict[str, ft.Control] = {}
mainPage = ft.Ref[ft.Container]()

def setPage(pageName: str, page: ft.Page) -> None:
    if pageName not in pages or mainPage.current is None:
        return
    mainPage.current.content = pages[pageName]
    mainPage.current.update()

def createMainPage(page: ft.Page) -> ft.SafeArea:
    pages.update({
        'home': createHomePage(page=page),
        'search': createSearchPage(page=page),
        'library': createLibraryPage(page=page)
    })

    return ft.SafeArea(
        avoid_intrusions_bottom=True,
        avoid_intrusions_top=True,
        expand=True,
        content=ft.Stack(
            expand=True,
            controls=[
                ft.Container(
                    ref=mainPage,
                    expand=True,
                    content=pages['home'],
                ),
                ft.Container(
                    left=0,
                    top=0,
                    right=0,
                    content=createHeader(),
                ),
                ft.Container(
                    left=0,
                    right=0,
                    bottom=0,
                    content=createNavigationBar(),
                ),
            ],
        ),
    )
