import flet as ft

from cards.searchCard import openSearchCard

#================#
#======REFS======#
#================#
searchField = ft.Ref[ft.Container]()


#=====================#
#======COMPONENT======#
#=====================#
def createSearchFieldBlock(page: ft.Page) -> ft.Container:
    return ft.Container(
        ref=searchField,
        height=50,
        padding=ft.Padding.only(left=15),
        margin=ft.Margin(left=15, top=15, right=15, bottom=7.5),
        bgcolor='#10162A',
        border=ft.Border.all(width=1.25, color='#29304A'),
        border_radius=12.5,
        on_click=lambda e: page.run_task(openSearchCard, e=e),
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(
                    icon=ft.CupertinoIcons.SEARCH,
                    color='#8eaeff'
                ),
                ft.Text(
                    value="What're we searching for today?",
                    weight=ft.FontWeight.W_800,
                    size=16,
                    font_family='SF-Pro-Regular',
                    color='#f3f6ff',
                    margin=ft.Margin.only(left=-5)
                )
            ]
        )
    )