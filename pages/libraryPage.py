import flet as ft

from components.libraryPage.audiobookBlock import createAudiobookBlock
from components.libraryPage.podcastBlock import createPodcastBlock

def createLibraryPage(page: ft.Page) -> ft.Container:
    podcastBlock = createPodcastBlock()
    audiobookBlock = createAudiobookBlock()

    return ft.Container(
        expand=True,
        content=ft.Column(
            scroll=ft.ScrollMode.HIDDEN,
            controls=[
                ft.Container(height=60),
                podcastBlock,
                audiobookBlock,
                ft.Container(height=65)
            ]
        )
    )