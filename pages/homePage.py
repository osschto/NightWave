import flet as ft

from components.homePage.todaysPickBlock import createTodaysPickBlock, setTodaysPickItem
from components.homePage.recommendedPodcastsBlock import createRecommendedPodcastsBlock, createPodcastsCards
from components.homePage.recommendedAudiobooksBlock import createRecommendedAudiobooksBlock, createAudiobooksCards

def createHomePage(page: ft.Page) -> ft.Container:
    todaysPickBlock = createTodaysPickBlock()
    recommendedPodcastsBlock = createRecommendedPodcastsBlock()
    recommendedAudiobooksBlock = createRecommendedAudiobooksBlock()

    page.run_task(setTodaysPickItem)
    page.run_task(createPodcastsCards)
    page.run_task(createAudiobooksCards)

    return ft.Container(
        expand=True,
        content=ft.Column(
            scroll=ft.ScrollMode.HIDDEN,
            controls=[
                ft.Container(height=60),
                todaysPickBlock,
                recommendedPodcastsBlock,
                recommendedAudiobooksBlock,
                ft.Container(height=65)
            ]
        )
    )