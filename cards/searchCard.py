import asyncio
from math import pi

import flet as ft

from api.api import getAudiobooks, getPodcasts
from cards.detailsCard import openDetailsCard
from db.repositories import getRecentItems, saveRecentItem, searchItems
from utils.helpers import cover_image, item_id_for_recent, item_key

#==================#
#======GLOBAL======#
#==================#
searchRequestId = 0

currentQuery = ''
currentOffset = 0

localHasMore = False
apiHasMore = False

isLoadingMore = False
isSearching = False

apiResults = []
apiOffset = 0
apiLoaded = False

PAGE_SIZE = 15
DEBOUNCE_DELAY = 0.4


#================#
#======REFS======#
#================#
searchCard = ft.Ref[ft.Container]()
searchCardColumn = ft.Ref[ft.Column]()
searchCardStack = ft.Ref[ft.Stack]()

fakeSearchField = ft.Ref[ft.Container]()
fakeSearchFieldIcon = ft.Ref[ft.Icon]()
fakeSearchFieldText = ft.Ref[ft.Text]()

realSearchField = ft.Ref[ft.Container]()
cancelButton = ft.Ref[ft.Container]()

recentSearchesColumn = ft.Ref[ft.Column]()
showMoreButton = ft.Ref[ft.Container]()


#=====================#
#======FUNCTIONS======#
#=====================#


#======SEARCH CARD======#
async def openSearchCard(e: ft.ControlEvent) -> None:
    # --- Reset fake field to normal state ---
    fakeSearchField.current.top = 70
    fakeSearchField.current.right = 0
    fakeSearchField.current.height = 50
    fakeSearchField.current.border_radius = 12.5
    fakeSearchField.current.opacity = 1

    fakeSearchFieldIcon.current.visible = True

    fakeSearchFieldText.current.size = 16
    fakeSearchFieldText.current.weight = ft.FontWeight.W_800
    fakeSearchFieldText.current.color = '#f3f6ff'
    fakeSearchFieldText.current.style = ft.TextStyle(letter_spacing=0.275)
    fakeSearchFieldText.current.margin = ft.Margin.only(left=-5)

    # --- Hide real field, cancel button and recent list ---
    realSearchField.current.content.value = ''
    realSearchField.current.opacity = 0

    cancelButton.current.opacity = 0
    cancelButton.current.scale = 0

    recentSearchesColumn.current.opacity = 0
    searchCardStack.current.height = 130

    # --- Show overlay ---
    searchCard.current.opacity = 1
    searchCard.current.ignore_interactions = False
    searchCard.current.update()

    await asyncio.sleep(0.03)

    # --- Animate fake field to compact state ---
    fakeSearchField.current.top = 0
    fakeSearchField.current.right = 65
    fakeSearchField.current.height = 40
    fakeSearchField.current.border_radius = 7.5

    fakeSearchFieldIcon.current.visible = False

    fakeSearchFieldText.current.size = 14
    fakeSearchFieldText.current.weight = ft.FontWeight.BOLD
    fakeSearchFieldText.current.color = '#717f9d'
    fakeSearchFieldText.current.style = ft.TextStyle(letter_spacing=0)
    fakeSearchFieldText.current.margin = ft.Margin.only(top=-1)

    fakeSearchField.current.update()

    await asyncio.sleep(0.12)

    # --- Swap controls: hide fake field, show real field, cancel, recent ---
    fakeSearchField.current.opacity = 0
    realSearchField.current.opacity = 1

    cancelButton.current.opacity = 1
    cancelButton.current.scale = 1

    searchCardStack.current.height = 40
    recentSearchesColumn.current.opacity = 1

    fakeSearchField.current.update()
    realSearchField.current.update()
    cancelButton.current.update()
    searchCardStack.current.update()
    recentSearchesColumn.current.update()

    # --- Focus input and load recent items in the background ---
    await focusSearchField(e=e)
    e.page.run_task(startSearch, e.page, '')

async def closeSearchCard(e: ft.ControlEvent) -> None:
    # --- Blur and lock the real text field ---
    realSearchField.current.content.read_only = True
    realSearchField.current.content.update()

    # --- Hide cancel, recent list and real field. Show fake field ---
    cancelButton.current.opacity = 0
    cancelButton.current.scale = 0

    recentSearchesColumn.current.opacity = 0
    searchCardStack.current.height = 130

    realSearchField.current.opacity = 0
    fakeSearchField.current.opacity = 1

    cancelButton.current.update()
    recentSearchesColumn.current.update()
    searchCardStack.current.update()
    realSearchField.current.update()
    fakeSearchField.current.update()

    await asyncio.sleep(0.12)

    # --- Animate fake field to normal state ---
    fakeSearchField.current.top = 70
    fakeSearchField.current.right = 0
    fakeSearchField.current.height = 50
    fakeSearchField.current.border_radius = 12.5

    fakeSearchFieldIcon.current.visible = True

    fakeSearchFieldText.current.size = 16
    fakeSearchFieldText.current.weight = ft.FontWeight.W_800
    fakeSearchFieldText.current.color = '#f3f6ff'
    fakeSearchFieldText.current.style = ft.TextStyle(letter_spacing=0.275)
    fakeSearchFieldText.current.margin = ft.Margin.only(left=-5)

    fakeSearchField.current.update()

    await asyncio.sleep(0.1)

    # --- Hide overlay and block interactions ---
    searchCard.current.opacity = 0
    searchCard.current.ignore_interactions = True
    searchCard.current.update()


#======FOCUS SEARCH FIELD======#
async def focusSearchField(e: ft.ControlEvent) -> None:
    realSearchField.current.content.read_only = False
    await realSearchField.current.content.focus()
    realSearchField.current.content.update()

def unfocusSearchField(e: ft.ScrollEvent) -> None:
    realSearchField.current.content.read_only = True
    realSearchField.current.content.update()


#======SEARCH======#
async def startSearch(page: ft.Page, query: str) -> None:
    global searchRequestId
    global currentQuery, currentOffset
    global localHasMore, apiHasMore
    global apiResults, apiOffset, apiLoaded
    global isLoadingMore, isSearching

    searchRequestId += 1
    requestId = searchRequestId

    currentQuery = query
    currentOffset = 0

    localHasMore = False
    apiHasMore = False

    apiResults = []
    apiOffset = 0
    apiLoaded = False

    isLoadingMore = False
    isSearching = True

    showMoreButton.current.visible = False
    showMoreButton.current.update()

    await asyncio.sleep(DEBOUNCE_DELAY)

    if requestId != searchRequestId:
        return

    if not query:
        try:
            items = await asyncio.to_thread(
                getRecentItems,
                limit=10
            )

            if requestId != searchRequestId:
                return

            renderSearchResults(
                page=page,
                items=items,
                heading='Recent searches'
            )

        except Exception as error:
            print(f'Recent searches error: {error}')

        finally:
            if requestId == searchRequestId:
                isSearching = False

        return

    try:
        items = await asyncio.to_thread(
            searchItems,
            query=query,
            limit=PAGE_SIZE + 1,
            offset=0
        )

        if requestId != searchRequestId:
            return

        localHasMore = len(items) > PAGE_SIZE
        items = items[:PAGE_SIZE]

        currentOffset = len(items)

        renderSearchResults(
            page=page,
            items=items,
            heading='Search results'
        )

        apiResults = await loadApiSearchResults(query)

        if requestId != searchRequestId:
            return

        apiLoaded = True
        apiOffset = 0
        apiHasMore = bool(apiResults)

        if not items:
            apiItems = apiResults[:PAGE_SIZE]

            apiOffset = len(apiItems)
            apiHasMore = apiOffset < len(apiResults)

            if apiItems:
                renderSearchResults(
                    page=page,
                    items=apiItems,
                    heading='Search results'
                )
            else:
                renderSearchResults(
                    page=page,
                    items=[],
                    heading='Search results'
                )

        updateShowMoreButton()

    except Exception as error:
        print(f'Search error: {error}')

        if requestId == searchRequestId and not items:
            renderSearchResults(
                page=page,
                items=[],
                heading='Search results'
            )

    finally:
        if requestId == searchRequestId:
            isSearching = False

def updateSearchResults(e: ft.ControlEvent) -> None:
    page = e.page
    query = (e.control.value or '').strip()

    page.run_task(startSearch, page, query)

async def loadApiSearchResults(query: str) -> list[dict]:
    podcasts, audiobooks = await asyncio.gather(
        getPodcasts(term=query, limit=100),
        getAudiobooks(title=query, limit=100, offset=0),
    )

    for item in podcasts:
        item['itemType'] = 'podcast'
    for item in audiobooks:
        item['itemType'] = 'audiobook'

    seen: set[tuple] = set()
    results: list[dict] = []

    for item in podcasts + audiobooks:
        key = (item.get('itemType'), item_key(item))
        if key in seen:
            continue
        seen.add(key)
        results.append(item)

    return results

async def loadMoreSearchResults(e: ft.ControlEvent) -> None:
    global currentOffset, localHasMore
    global apiResults, apiOffset, apiLoaded
    global isLoadingMore, apiHasMore

    if isLoadingMore or isSearching or not currentQuery:
        return

    isLoadingMore = True
    requestId = searchRequestId
    query = currentQuery
    updateShowMoreButton(loading=True)

    try:
        if localHasMore:
            items = await asyncio.to_thread(
                searchItems,
                query=query,
                limit=PAGE_SIZE + 1,
                offset=currentOffset,
            )
            if requestId != searchRequestId:
                return

            localHasMore = len(items) > PAGE_SIZE
            items = items[:PAGE_SIZE]
            if items:
                renderSearchResults(page=e.page, items=items, append=True)
                currentOffset += len(items)

            if not localHasMore and not apiLoaded:
                apiResults = await loadApiSearchResults(query)
                if requestId != searchRequestId:
                    return
                apiLoaded = True
                apiOffset = 0

                local_items = await asyncio.to_thread(
                    searchItems, query=query, limit=currentOffset, offset=0
                )
                local_keys = {
                    (item.get('itemType'), item_key(item)) for item in local_items
                }
                apiResults = [
                    item for item in apiResults
                    if (item.get('itemType'), item_key(item)) not in local_keys
                ]

            apiHasMore = apiOffset < len(apiResults)
            updateShowMoreButton()
            return

        if not apiLoaded:
            apiResults = await loadApiSearchResults(query)
            if requestId != searchRequestId:
                return
            apiLoaded = True
            apiOffset = 0

        items = apiResults[apiOffset:apiOffset + PAGE_SIZE]
        if items:
            renderSearchResults(page=e.page, items=items, append=True)
            apiOffset += len(items)

        apiHasMore = apiOffset < len(apiResults)
        updateShowMoreButton()

    except Exception as error:
        print(f'Load more error: {error}')
        if showMoreButton.current:
            showMoreButton.current.content.controls[0].value = 'Loading error'
            showMoreButton.current.content.controls[1].value = 'Please try again'
            showMoreButton.current.update()

    finally:
        if requestId == searchRequestId:
            isLoadingMore = False
            if (
                showMoreButton.current
                and showMoreButton.current.content.controls[0].value != 'Loading error'
            ):
                updateShowMoreButton()

def renderSearchResults(page: ft.Page, items: list[dict], heading: str = 'Search results', append: bool = False) -> None:
    if not append:
        recentSearchesColumn.current.controls.clear()

        recentSearchesColumn.current.controls.append(
            ft.Text(
                value=heading,
                size=22,
                font_family='SF-Pro-Semibold',
                color='#F3F6FF',
            )
        )

    if not items and not append:
        recentSearchesColumn.current.controls.append(
            ft.Text(
                value='Nothing found',
                size=16,
                font_family='SF-Pro-Regular',
                color='#717f9d',
            )
        )

    else:
        recentSearchesColumn.current.controls.extend(
            renderItems(page=page, items=items)
        )

    if showMoreButton.current:
        if showMoreButton.current in recentSearchesColumn.current.controls:
            recentSearchesColumn.current.controls.remove(
                showMoreButton.current
            )

        recentSearchesColumn.current.controls.append(
            showMoreButton.current
        )

    recentSearchesColumn.current.update()


#======RENDER/OPEN ITEMS======#
def renderItems(page: ft.Page, items: list[dict]) -> list:
    cards = []

    for item in items:
        card = ft.Container(
            data=item,
            padding=ft.Padding.all(10),
            bgcolor='#111d39',
            border=ft.Border.all(width=1.5, color='#26385B'),
            border_radius=15,
            ink=True,
            ink_color='#1c2a4e',
            on_click=openSearchItem,
            content=ft.Row(
                controls=[
                    cover_image(
                        item.get('image'),
                        width=50, height=50,
                        border_radius=7.5,
                    ),
                    ft.Column(
                        expand=True,
                        controls=[
                            ft.Text(
                                value=item.get('title'),
                                weight=ft.FontWeight.BOLD,
                                size=14,
                                font_family='SF-Pro-Bold',
                                color='#f3f6ff',
                                overflow=ft.TextOverflow.ELLIPSIS,
                                max_lines=1,
                                margin=ft.Margin.only(bottom=-7.5),
                            ),
                            ft.Text(
                                value=f"{item.get('itemType').capitalize()} • {item.get('artist')}",
                                weight=ft.FontWeight.BOLD,
                                size=12,
                                font_family='SF-Pro-Semibold',
                                color='#717f9d',
                                overflow=ft.TextOverflow.ELLIPSIS,
                                max_lines=1
                            )
                        ]
                    )
                ]
            )
        )

        cards.append(card)

    return cards

async def openSearchItem(e: ft.ControlEvent) -> None:
    item = e.control.data
    item_type = item.get('itemType')
    item_id = item_id_for_recent(item)

    unfocusSearchField(e=e)
    await openDetailsCard(page=e.page, item=item)

    try:
        await asyncio.to_thread(
            saveRecentItem,
            item=item,
            item_id=item_id,
            item_type=item_type,
        )
    except Exception as error:
        print(f'Recent item error: {error}')


#======SHOW MORE BUTTON======#
def updateShowMoreButton(loading: bool = False) -> None:
    if not showMoreButton.current:
        return

    if loading:
        showMoreButton.current.content.controls[0].value = 'Loading...'
        showMoreButton.current.content.controls[1].value = 'Please wait'
    else:
        showMoreButton.current.content.controls[0].value = 'Load more'
        showMoreButton.current.content.controls[1].value = 'Show next 15 results'

    hasMore = localHasMore or apiHasMore

    showMoreButton.current.visible = bool(currentQuery) and hasMore
    showMoreButton.current.update()


#=====================#
#======COMPONENT======#
#=====================#
def createSearchCard(page: ft.Page) -> ft.Container:
    return ft.Container(
        ref=searchCard,
        left=0,
        top=0,
        width=page.width,
        height=page.height,
        padding=ft.Padding.all(15),
        margin=ft.Margin.only(bottom=15),
        bgcolor='#070B19',
        opacity=0,
        ignore_interactions=True,
        animate_opacity=ft.Animation(duration=100, curve=ft.AnimationCurve.EASE_IN_OUT),
        content=ft.SafeArea(
            avoid_intrusions_bottom=True,
            avoid_intrusions_top=True,
            expand=True,
            content=ft.Column(
                ref=searchCardColumn,
                controls=[
                    ft.Stack(
                        ref=searchCardStack,
                        height=130,
                        controls=[
                            ft.Container(
                                ref=fakeSearchField,
                                left=0,
                                top=70,
                                right=0,
                                height=50,
                                padding=ft.Padding.only(left=15),
                                bgcolor='#10162A',
                                border=ft.Border.all(width=1.25, color='#29304A'),
                                border_radius=12.5,
                                opacity=1,
                                animate_position=ft.Animation(duration=100, curve=ft.AnimationCurve.EASE_IN_OUT),
                                animate_size=ft.Animation(duration=100, curve=ft.AnimationCurve.EASE_IN_OUT),
                                animate_opacity=ft.Animation(duration=100, curve=ft.AnimationCurve.EASE_IN_OUT),
                                on_click=openSearchCard,
                                content=ft.Row(
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Icon(
                                            ref=fakeSearchFieldIcon,
                                            icon=ft.CupertinoIcons.SEARCH,
                                            color='#8eaeff'
                                        ),
                                        ft.Text(
                                            ref=fakeSearchFieldText,
                                            value="What're we searching for today?",
                                            weight=ft.FontWeight.W_800,
                                            size=16,
                                            font_family='SF-Pro-Regular',
                                            color='#f3f6ff',
                                            margin=ft.Margin.only(left=-5)
                                        )
                                    ]
                                )
                            ),
                            ft.Container(
                                ref=realSearchField,
                                left=0,
                                top=0,
                                right=65,
                                height=40,
                                bgcolor='#10162A',
                                border=ft.Border.all(width=1.25, color='#29304A'),
                                border_radius=7.5,
                                opacity=0,
                                animate_position=ft.Animation(duration=200, curve=ft.AnimationCurve.FAST_OUT_SLOWIN),
                                animate_size=ft.Animation(duration=200, curve=ft.AnimationCurve.FAST_OUT_SLOWIN),
                                animate_opacity=ft.Animation(duration=100, curve=ft.AnimationCurve.EASE_IN_OUT),
                                content=ft.TextField(
                                    dense=True,
                                    text_vertical_align=ft.VerticalAlignment.CENTER,
                                    hint_text="What're we searching for today?",
                                    hint_style=ft.TextStyle(size=14, weight=ft.FontWeight.BOLD, font_family='SF-Pro-Regular', color='#717f9d', letter_spacing=0),
                                    text_style=ft.TextStyle(size=14, weight=ft.FontWeight.BOLD, font_family='SF-Pro-Regular', color='#f3f6ff', letter_spacing=0),
                                    cursor_color='#8eaeff',
                                    bgcolor='transparent',
                                    hover_color='transparent',
                                    focused_bgcolor='transparent',
                                    border={
                                        ft.ControlState.DEFAULT: ft.OutlineInputBorder(side=ft.BorderSide(width=0, color='transparent')),
                                        ft.ControlState.FOCUSED: ft.OutlineInputBorder(side=ft.BorderSide(width=0, color='transparent'))
                                    },
                                    on_click=lambda e: page.run_task(focusSearchField, e=e),
                                    on_change=updateSearchResults
                                )
                            ),
                            ft.Container(
                                ref=cancelButton,
                                alignment=ft.Alignment.CENTER,
                                top=5,
                                right=0,
                                height=30,
                                padding=ft.Padding.only(left=5, right=5),
                                bgcolor='#1a2b4f',
                                border=ft.Border.all(width=1, color='#3D5684'),
                                border_radius=10,
                                ink=True,
                                ink_color='#344C7B',
                                opacity=0,
                                scale=0,
                                animate_opacity=ft.Animation(duration=125, curve=ft.AnimationCurve.EASE_IN_OUT),
                                animate_scale=ft.Animation(duration=125, curve=ft.AnimationCurve.EASE_IN_OUT_BACK),
                                on_click=lambda e: page.run_task(closeSearchCard, e=e),
                                content=ft.Text(
                                    value='Cancel',
                                    weight=ft.FontWeight.BOLD,
                                    size=12,
                                    font_family='SF-Pro-Bold',
                                    color='#f3f6ff'
                                )
                            )
                        ]
                    ),
                    ft.Column(
                        ref=recentSearchesColumn,
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                        opacity=0,
                        spacing=10,
                        animate_opacity=ft.Animation(duration=75, curve=ft.AnimationCurve.EASE_IN_OUT),
                        on_scroll=unfocusSearchField,
                        controls=[
                            ft.Text(
                                value='Recent searches',
                                size=22,
                                font_family='SF-Pro-Semibold',
                                color='#F3F6FF'
                            ),
                            ft.Container(
                                ref=showMoreButton,
                                align=ft.Alignment.CENTER,
                                alignment=ft.Alignment.CENTER,
                                width=page.width * 0.45,
                                padding=ft.Padding.all(7.5),
                                bgcolor='#1a2b4f',
                                ink=True,
                                ink_color='#344C7B',
                                border=ft.Border.all(width=0.75, color='#3D5684'),
                                border_radius=10,
                                visible=False,
                                on_click=loadMoreSearchResults,
                                content=ft.Column(
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=0,
                                    controls=[
                                        ft.Text(
                                            align=ft.Alignment.CENTER,
                                            value='Load more',
                                            weight=ft.FontWeight.BOLD,
                                            size=16,
                                            font_family='SF-Pro-Bold',
                                            color='#f3f6ff'
                                        ),
                                        ft.Text(
                                            align=ft.Alignment.CENTER,
                                            value='Show next 15 results',
                                            weight=ft.FontWeight.BOLD,
                                            size=14,
                                            font_family='SF-Pro-Regular',
                                            color='#717f9d',
                                            margin=ft.Margin.only(top=-7.5)
                                        )
                                    ]
                                )
                            )
                        ]
                    )
                ]
            )
        )
    )