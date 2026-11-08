import asyncio

import flet as ft

#==================#
#======GLOBAL======#
#==================#
currentPage = 'home'


#================#
#======REFS======#
#================#
navigationBar = ft.Ref[ft.Row]()


#=====================#
#======FUNCTIONS======#
#=====================#
def createNavigationBarItems() -> list[ft.Container]:
    values = {
        'home': (
            ft.Icon(icon=ft.Icons.HOME, color='#8eaeff', animate_scale=125, margin=ft.Margin.only(top=7.5, bottom=-7.5)),
            ft.Text(value='Home', font_family='SF-Pro-Bold', color='#8eaeff', animate_scale=125)
        ),
        'search': (
            ft.Icon(icon=ft.Icons.SEARCH, color='#7787a8', animate_scale=125, margin=ft.Margin.only(top=7.5, bottom=-7.5)),
            ft.Text(value='Search', font_family='SF-Pro-Bold', color='#7787a8', animate_scale=125)
        ),
        'library': (
            ft.Icon(icon=ft.Icons.LIBRARY_MUSIC_OUTLINED, color='#7787a8', animate_scale=125, margin=ft.Margin.only(top=7.5, bottom=-7.5)),
            ft.Text(value='Library', font_family='SF-Pro-Bold', color='#7787a8', animate_scale=125)
        )
    }

    items = []
    for page_name, (icon, label) in values.items():
        items.append(
            ft.Container(
                on_click=onSelectItem,
                content=ft.Column(
                    data=page_name,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[icon, label]
                )
            )
        )
    return items

async def onSelectItem(e: ft.ControlEvent) -> None:
    global currentPage
    page_name = e.control.content.data

    # --- update library information --- #
    if page_name == 'library':
        from components.libraryPage.podcastBlock import loadPodcastsBlock
        from components.libraryPage.audiobookBlock import loadAudiobooksBlock
        
        e.page.run_task(loadPodcastsBlock)
        e.page.run_task(loadAudiobooksBlock)

    # --- set page --- #
    from pages.mainPage import setPage
    
    if currentPage == page_name:
        return

    currentPage = page_name
    setPage(pageName=page_name, page=e.page)

    if navigationBar.current is None:
        return

    # --- navigation item animation --- #
    for item in navigationBar.current.controls:
        item.content.controls[0].color = '#7787a8'
        item.content.controls[1].color = '#7787a8'

    clicked_icon = e.control.content.controls[0]
    clicked_label = e.control.content.controls[1]
    clicked_icon.scale = 0.85
    clicked_label.scale = 0.85
    clicked_icon.color = '#8eaeff'
    clicked_label.color = '#8eaeff'
    navigationBar.current.update()

    await asyncio.sleep(0.1)

    clicked_icon.scale = 1
    clicked_label.scale = 1
    navigationBar.current.update()


#=====================#
#======COMPONENT======#
#=====================#
def createNavigationBar() -> ft.Container:
    return ft.Container(
        bgcolor='#070B19',
        border=ft.Border(top=ft.BorderSide(width=1, color=ft.Colors.with_opacity(opacity=0.1, color='#ffffff'))),
        padding=ft.Padding.only(left=75, right=75),
        content=ft.Row(
            ref=navigationBar,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=createNavigationBarItems(),
        ),
    )
