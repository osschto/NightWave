import flet as ft

from cards.genreCard import openGenreCard

#=====================#
#======FUNCTIONS======#
#=====================#
def getGenresCards() -> list[ft.Container]:
    genres = [
        {'color1': '#C2185B', 'color2': '#9C27B0', 'border': '#880E4F', 'title': 'Sports', 'description': 'Your ultimate stadium pass to the world of athletics. Tune in for passionate game analysis, expert commentary, and exclusive interviews with athletes and coaches'},
        {'color1': '#6A1B9A', 'color2': '#4527A0', 'border': '#4A148C', 'title': 'Education', 'description': 'Expand your mind with insightful audio lessons and lectures. Listen to expert discussions on science, language, self-improvement, and modern skills development'},
        {'color1': '#0A4723', 'color2': '#00897B', 'border': '#063318', 'title': 'Romance', 'description': 'Immerse yourself in captivating tales of passion, desire, and deep connection. Follow heartwarming emotional journeys, dramatic relationships, and unforgettable love stories'},
        {'color1': '#BF360C', 'color2': '#EF6C00', 'border': '#8D2A00', 'title': 'Health', 'description': 'Your audio guide to physical and mental well-being. Explore expert advice, medical insights, mindfulness practices, and actionable tips for a healthier lifestyle'},
        {'color1': '#013A63', 'color2': '#0288D1', 'border': '#012A47', 'title': 'Historical', 'description': 'Step into the past through vivid fictional narratives. Experience rich period dramas, epic sagas, and personal stories set against the backdrop of monumental historical eras'},
        {'color1': '#6A0A3C', 'color2': '#E91E63', 'border': '#4A0729', 'title': 'Biography', 'description': 'Discover the authentic, unvarnished lives of history’s most influential figures. Read incredible non-fiction accounts of personal triumphs, struggles, and lasting legacies'},
        {'color1': '#4A148C', 'color2': '#7C4DFF', 'border': '#311B92', 'title': 'Satire', 'description': "Take a sharp look at the absurdity of modern life through the lens of unfiltered wit. Tune in for biting satire, clever sarcasm, and hilarious reality checks from top comedians who aren't afraid to laugh at what everyone else is thinking"},
        {'color1': '#4A148C', 'color2': '#7B1FA2', 'border': '#311B92', 'title': 'Drama', 'description': 'Experience intense storytelling driven by deep human conflict and morality. Dive into compelling character studies, complex life dilemmas, and powerful emotional resolutions'},
        {'color1': '#8B0000', 'color2': '#E53935', 'border': '#5C0000', 'title': 'Fitness', 'description': 'Fuel your motivation and level up your training. Listen to professional workout tips, nutrition guides, and inspiring stories from elite trainers and athletes'},
        {'color1': '#8B6914', 'color2': '#D4AF37', 'border': '#5C450C', 'title': 'Arts', 'description': 'Dive into creative conversations exploring visual arts, cinema, and design. Discover deep-dive discussions with creators about their inspiration and masterworks'},
        {'color1': '#0D47A1', 'color2': '#1976D2', 'border': '#0A3375', 'title': 'Poetry', 'description': 'Explore the profound beauty of rhythm, verse, and literary metaphor. Discover classic stanzas and contemporary works that capture intense human emotions in a few brief lines'},
        {'color1': '#1A237E', 'color2': '#5C6BC0', 'border': '#0D144B', 'title': 'Lyric', 'description': 'Delve into highly expressive, melodic literature focusing on deep personal feelings. A collection of soulful, rhythmic writing that echoes the internal music of the author'},
        {'color1': '#4A0000', 'color2': '#A00000', 'border': '#2B0000', 'title': 'Comedy', 'description': 'Enjoy witty literature, brilliant parodies, and hilarious satirical masterpieces. Indulge in classic and modern humorous books designed to entertain and make you laugh out loud'},
        {'color1': "#00484D", 'color2': "#61C4AF", 'border': '#00332B', 'title': 'Leisure', 'description': 'Unwind with relaxing audio shows about hobbies, travel, and lifestyle. Perfect for casual listening, slowing down, and finding inspiration for your free time'},
        {'color1': '#311B92', 'color2': '#7B1FA2', 'border': '#1A0F5C', 'title': 'History', 'description': 'Uncover the facts, documents, and real events that shaped our modern civilization. Explore rigorous non-fiction research detailing global conflicts, empires, and cultural shifts'},
        {'color1': "#00CE56", 'color2': "#00840F", 'border': "#004D0A", 'title': 'Design', 'description': 'Explore the worlds of architecture, UX/UI, and fashion through audio. Listen to industry innovators discuss creative trends, problem-solving, and visual aesthetics'},
        {'color1': '#006064', 'color2': '#0277BD', 'border': '#004D50', 'title': 'Nature', 'description': 'Connect with the wonders of the natural world through evocative literary prose. Read captivating accounts of wildlife exploration, environmental science, and scenic landscapes'},
        {'color1': '#BF360C', 'color2': "#FFAA00", 'border': "#5E1B00", 'title': 'Philosophy', 'description': 'Challenge your perspective with timeless texts on ethics, logic, and existentialism. Contemplate profound ideas on human nature, truth, and the core meaning of existence'},
        {'color1': '#880E4F', 'color2': '#C62828', 'border': '#6A0A3C', 'title': 'Business', 'description': 'Stay ahead with sharp financial analysis, marketing strategies, and startup insights. Hear valuable advice and lessons learned from successful global entrepreneurs'},
        {'color1': '#5D4037', 'color2': '#A1887F', 'border': '#3E2723', 'title': 'Science', 'description': 'Satisfy your curiosity with discussions on breakthroughs and cosmic mysteries. Join scientists as they unpack complex research into fascinating, easy-to-understand audio stories'}
    ]

    items = []

    for i in range(0, len(genres), 2):
        row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        chunk = genres[i:i+2]

        for item in chunk:
            row.controls.append(
                ft.Container(
                    data=item,
                    expand=True,
                    height=115,
                    padding=ft.Padding.only(left=10, top=10),
                    gradient=ft.LinearGradient(colors=[item['color1'], item['color2']]),
                    border=ft.Border.all(width=0.75, color=item['border']),
                    border_radius=15,
                    ink=True,
                    on_click=onGenreCardClick,
                    content=ft.Text(
                        value=item['title'],
                        size=18,
                        font_family='SF-Pro-Bold',
                        color='#f3f6ff'
                    )
                )
            )

        items.append(row)

    return items

async def onGenreCardClick(e: ft.ControlEvent) -> None:
    title = e.control.data.get('title')
    description = e.control.data.get('description')
    gradientColor1 = e.control.data.get('color1')
    gradientColor2 = e.control.data.get('color2')

    await openGenreCard(
        title=title,
        description=description,
        gradientColor1=gradientColor1,
        gradientColor2=gradientColor2
    )


#=====================#
#======COMPONENT======#
#=====================#
def createGenresListBlock() -> ft.Container:
    return ft.Container(
        margin=ft.Margin.only(left=15, right=15),
        content=ft.Column(
            controls=getGenresCards()
        )
    )