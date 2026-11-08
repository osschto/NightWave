from datetime import datetime
from random import choice

import flet as ft

#=====================#
#======FUNCTIONS======#
#=====================#
def setGreetingTitle() -> str:
    timeNow = datetime.now().astimezone().time()

    match timeNow.hour:
        case hourNow if 6 <= hourNow < 12: return 'GOOD MORNING'
        case hourNow if 12 <= hourNow < 18: return 'GOOD DAY'
        case hourNow if 18 <= hourNow < 24: return 'GOOD EVENING'
        case _: return 'GOOD NIGHT'

def setGreetingSubtitle() -> str:
    greetings = [
        'Find your voice.', 'Hear the stories.', 'Tune into ideas.', 'Listen and learn.', 'Voice your mind.',
        'Open your ears.', 'Read with ears.', 'Get lost in words.', 'Stories start here.', 'Dive into chapters.',
        'Feed your mind.', 'Press play, grow.', 'Think out loud.', 'Your daily insight.', 'Escape in audio.'
    ]

    return choice(greetings)


#=====================#
#======COMPONENT======#
#=====================#
def createHeader() -> ft.Container:
    return ft.Container(
        bgcolor='#070B19',
        border=ft.Border(bottom=ft.BorderSide(width=1, color=ft.Colors.with_opacity(opacity=0.1, color='#ffffff'))),
        padding=ft.Padding(left=15, top=5, right=15, bottom=5),
        content=ft.Column(
            controls=[
                ft.Text(value=setGreetingTitle(), size=18, font_family='SF-Pro-Regular', color='#717f9d', margin=ft.Margin.only(bottom=-10)),
                ft.Text(value=setGreetingSubtitle(), size=22, font_family='SF-Pro-Semibold', color='#f3f6ff', margin=ft.Margin.only(left=2.5))
            ]
        )
    )