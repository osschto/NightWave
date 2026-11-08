import asyncio
from math import pi

import flet as ft
import flet_audio as fta

from utils.helpers import DEFAULT_IMAGE, resolve_image

#==================#
#======GLOBAL======#
#==================#
isPlaying = False
isSeeking = False
isCompleted = False
isLoading = False
currentAudioUrl: str | None = None

dragDistance = 0

durationMs = 0
positionMs = 0
lastDisplayedSecond = -1
pendingSeekMs: int | None = None

#================#
#======REFS======#
#================#
playerCard = ft.Ref[ft.Container]()
playerImage = ft.Ref[ft.Image]()
playerTitle = ft.Ref[ft.Text]()
playerArtist = ft.Ref[ft.Text]()
playerSlider = ft.Ref[ft.Slider]()
playerCurrentTime = ft.Ref[ft.Text]()
playerTotalTime = ft.Ref[ft.Text]()
playerPlayPauseSlot = ft.Ref[ft.Container]()
playerBackwardButton = ft.Ref[ft.Container]()
playerForwardButton = ft.Ref[ft.Container]()
audioPlayer = ft.Ref[fta.Audio]()


#=====================#
#======FUNCTIONS======#
#=====================#


#======PLAYER======#
def openPlayerCard(image: str, title: str, artist: str) -> None:
    if playerCard.current is None:
        return

    playerImage.current.src = resolve_image(image)
    playerTitle.current.value = title
    playerArtist.current.value = artist

    updatePlayPauseButton(update=False)

    playerCard.current.offset = ft.Offset(0, 0)
    playerCard.current.update()

def closePlayerCard(e: ft.ControlEvent | None = None) -> None:
    if playerCard.current is None:
        return
    
    playerCard.current.offset = ft.Offset(0, 1)
    playerCard.current.update()

def updatePlayerUI() -> None:
    if playerCard.current is not None:
        playerCard.current.update()

def setProgressUI(ms: int) -> None:
    if playerSlider.current:
        playerSlider.current.value = ms

    if playerCurrentTime.current:
        playerCurrentTime.current.value = formatTime(ms)

def setLoadingUI(loading: bool) -> None:
    global isLoading
    isLoading = loading

    if playerCurrentTime.current:
        playerCurrentTime.current.value = ('--:--' if loading else formatTime(positionMs))

    if playerTotalTime.current:
        playerTotalTime.current.value = ('--:--' if loading else formatTime(durationMs))

    if playerSlider.current:
        playerSlider.current.disabled = loading
        if loading:
            playerSlider.current.value = 0

    opacity = 0.4 if loading else 1.0
    if playerBackwardButton.current:
        playerBackwardButton.current.disabled = loading
        playerBackwardButton.current.opacity = opacity

    if playerForwardButton.current:
        playerForwardButton.current.disabled = loading
        playerForwardButton.current.opacity = opacity

    updatePlayPauseButton(update=False)
    updatePlayerUI()


#======PLAYER ANIMATION======#
def onDragStart(e: ft.DragStartEvent) -> None:
    global dragDistance

    dragDistance = 0

    playerCard.current.animate_offset = ft.Animation(duration=30, curve=ft.AnimationCurve.LINEAR)

def onDragDown(e: ft.DragUpdateEvent) -> None:
    global dragDistance

    dragDistance += e.local_delta.y
    if dragDistance > 0 and playerCard.current is not None:
        playerCard.current.offset = ft.Offset(0, dragDistance / e.page.height)
        playerCard.current.update()

def onDragEnd(e: ft.DragEndEvent) -> None:
    global dragDistance

    if playerCard.current is None:
        return

    playerCard.current.animate_offset = ft.Animation(duration=100, curve=ft.AnimationCurve.EASE_OUT_CUBIC)
    playerCard.current.offset = ft.Offset(0, 1 if dragDistance > 115 else 0)
    playerCard.current.update()


#======AUDIO======#
def resetTrackProgress() -> None:
    global durationMs, positionMs, lastDisplayedSecond
    global isSeeking, isCompleted, pendingSeekMs

    durationMs = 0
    positionMs = 0
    lastDisplayedSecond = -1
    isSeeking = False
    isCompleted = False
    pendingSeekMs = None

    if playerSlider.current:
        playerSlider.current.min = 0
        playerSlider.current.max = 1
        playerSlider.current.value = 0

    setLoadingUI(True)

async def audioplayerPlay(page: ft.Page, url: str) -> None:
    global isPlaying, isCompleted, currentAudioUrl

    if not url:
        return

    if audioPlayer.current is None or audioPlayer.current not in page.services:
        resetTrackProgress()
        page.services.append(
            fta.Audio(
                ref=audioPlayer,
                src=url,
                autoplay=True,
                balance=0,
                volume=0.5,
                release_mode=fta.ReleaseMode.STOP,
                on_duration_change=onDurationChange,
                on_position_change=onPositionChange,
                on_state_change=onStateChange,
                on_seek_complete=onSeekComplete
            )
        )
        currentAudioUrl = url
        isPlaying = True
        isCompleted = False
        updatePlayPauseButton()
        return

    if currentAudioUrl == url:
        await resumeOrRestart()
        return

    await audioPlayer.current.pause()
    resetTrackProgress()
    audioPlayer.current.src = url
    audioPlayer.current.update()
    currentAudioUrl = url
    isPlaying = True
    isCompleted = False
    updatePlayPauseButton()
    await audioPlayer.current.play()

async def resumeOrRestart() -> None:
    global isPlaying, isCompleted, positionMs, lastDisplayedSecond
    global isSeeking, pendingSeekMs

    if audioPlayer.current is None:
        return

    at_end = isCompleted or (
        durationMs > 0 and positionMs >= max(0, durationMs - 500)
    )

    if at_end:
        isSeeking = True
        pendingSeekMs = 0
        positionMs = 0
        lastDisplayedSecond = 0
        isCompleted = False
        setProgressUI(0)
        updatePlayerUI()
        await audioPlayer.current.seek(0)
        await audioPlayer.current.play()
    else:
        await audioPlayer.current.resume()

    isPlaying = True
    updatePlayPauseButton()

def formatTime(ms: int) -> str:
    total = max(0, int(ms or 0) // 1000)
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)

    if hours:
        return f'{hours}:{minutes:02}:{seconds:02}'
    return f'{minutes:02}:{seconds:02}'

def positionMsFromEvent(position) -> int:
    if hasattr(position, 'in_milliseconds'):
        position = position.in_milliseconds

    try:
        value = int(position or 0)
    except (TypeError, ValueError):
        value = 0

    if durationMs > 0:
        return max(0, min(value, durationMs))
    return max(0, value)

def onDurationChange(e: fta.AudioDurationChangeEvent) -> None:
    global durationMs, positionMs

    durationMs = max(0, int(e.duration.in_milliseconds))
    positionMs = min(max(0, positionMs), durationMs)

    if playerSlider.current:
        playerSlider.current.max = max(durationMs, 1)
        playerSlider.current.value = positionMs

    if durationMs > 0 and isLoading:
        setLoadingUI(False)
    else:
        if playerTotalTime.current:
            playerTotalTime.current.value = formatTime(durationMs)
        updatePlayerUI()

def onPositionChange(e: fta.AudioPositionChangeEvent) -> None:
    global positionMs, lastDisplayedSecond, isSeeking, pendingSeekMs

    if isLoading:
        return

    new_pos = positionMsFromEvent(e.position)

    if isSeeking:
        if pendingSeekMs is not None:
            if abs(new_pos - pendingSeekMs) <= 750:
                isSeeking = False
                pendingSeekMs = None
                positionMs = new_pos
            else:
                return
        else:
            return

    positionMs = new_pos
    current_second = positionMs // 1000

    if current_second == lastDisplayedSecond:
        return
    lastDisplayedSecond = current_second

    setProgressUI(positionMs)
    updatePlayerUI()

def onStateChange(e: fta.AudioStateChangeEvent) -> None:
    global isPlaying, isCompleted, positionMs, lastDisplayedSecond

    state = e.state
    state_value = getattr(state, 'value', state)

    if hasattr(state_value, 'lower'):
        state_value = str(state_value).lower()
    else:
        state_value = str(state).lower()

    if 'completed' in state_value:
        isCompleted = True
        isPlaying = False

        if durationMs > 0:
            positionMs = durationMs
            lastDisplayedSecond = positionMs // 1000
            setProgressUI(positionMs)

        updatePlayPauseButton(update=False)
        updatePlayerUI()

    elif 'playing' in state_value:
        isPlaying = True
        isCompleted = False
        updatePlayPauseButton()

    elif 'paused' in state_value or 'stopped' in state_value:
        isPlaying = False
        updatePlayPauseButton()

def onSeekComplete(e: ft.ControlEvent) -> None:
    global isSeeking, pendingSeekMs, positionMs, lastDisplayedSecond

    if pendingSeekMs is not None:
        positionMs = pendingSeekMs
        lastDisplayedSecond = positionMs // 1000
        setProgressUI(positionMs)
        updatePlayerUI()

    isSeeking = False
    pendingSeekMs = None


#======SLIDER======#
def onSliderChange(e: ft.ControlEvent) -> None:
    if isLoading:
        return

    global positionMs, lastDisplayedSecond, isSeeking, pendingSeekMs

    isSeeking = True
    positionMs = max(0, min(int(e.control.value or 0), durationMs or 0))
    pendingSeekMs = positionMs
    lastDisplayedSecond = positionMs // 1000

    if playerCurrentTime.current:
        playerCurrentTime.current.value = formatTime(positionMs)
        playerCurrentTime.current.update()

async def onSliderChangeEnd(e: ft.ControlEvent) -> None:
    if isLoading:
        return

    global positionMs, lastDisplayedSecond, isSeeking, pendingSeekMs, isCompleted

    positionMs = max(0, min(int(e.control.value or 0), durationMs or 0))
    pendingSeekMs = positionMs
    lastDisplayedSecond = positionMs // 1000
    isSeeking = True
    isCompleted = False

    setProgressUI(positionMs)
    updatePlayerUI()

    if audioPlayer.current is None:
        isSeeking = False
        pendingSeekMs = None
        return

    try:
        await audioPlayer.current.seek(positionMs)
    except Exception:
        isSeeking = False
        pendingSeekMs = None

async def seekBy(delta_ms: int) -> None:
    if isLoading or audioPlayer.current is None:
        return

    global positionMs, lastDisplayedSecond, isSeeking, pendingSeekMs, isCompleted

    target = max(0, min(positionMs + delta_ms, durationMs or 0))
    isSeeking = True
    pendingSeekMs = target
    positionMs = target
    lastDisplayedSecond = target // 1000
    isCompleted = False

    setProgressUI(target)
    updatePlayerUI()

    try:
        await audioPlayer.current.seek(target)
    except Exception:
        isSeeking = False
        pendingSeekMs = None

async def seekBackward(e: ft.ControlEvent) -> None:
    await seekBy(-15000)

async def seekForward(e: ft.ControlEvent) -> None:
    await seekBy(15000)


#======PLAY/PAUSE BUTTON======#
def centerContent() -> ft.Control:
    if isLoading:
        return ft.Container(
            width=65, height=65,
            alignment=ft.Alignment.CENTER,
            content=ft.ProgressRing(
                width=50, height=50,
                stroke_width=3,
                color='#8eaeff'
            )
        )
    
    return ft.Image(
        src=('images/pause-button.png' if isPlaying else 'images/play-button.png'),
        width=65, height=65,
        fit=ft.BoxFit.CONTAIN
    )

def updatePlayPauseButton(update: bool = True) -> None:
    if playerPlayPauseSlot.current is None:
        return

    playerPlayPauseSlot.current.content = centerContent()

    if update:
        playerPlayPauseSlot.current.update()

async def togglePlayPause(e: ft.ControlEvent) -> None:
    global isPlaying

    if isLoading or audioPlayer.current is None:
        return

    if isPlaying:
        await audioPlayer.current.pause()
        isPlaying = False
        updatePlayPauseButton()
        return

    await resumeOrRestart()

def makeSideButton(ref: ft.Ref[ft.Container], image_src: str, on_click) -> ft.GestureDetector:
    return ft.GestureDetector(
            on_tap=on_click,
            on_tap_down=onSidePress,
            content=ft.Container(
            ref=ref,
            alignment=ft.Alignment.CENTER,
            width=50, height=50,
            opacity=0.4,
            disabled=True,
            animate_scale=ft.Animation(100, ft.AnimationCurve.EASE_OUT),
            content=ft.Image(
                src=image_src,
                width=50, height=50,
                fit=ft.BoxFit.CONTAIN
            )
        )
    )

def makeCenterButton() -> ft.GestureDetector:
    return ft.GestureDetector(
            on_tap=togglePlayPause,
            on_tap_down=onCenterPress,
            content=ft.Container(
            ref=playerPlayPauseSlot,
            alignment=ft.Alignment.CENTER,
            width=65, height=65,
            animate_scale=ft.Animation(100, ft.AnimationCurve.EASE_OUT),
            content=centerContent()
        )
    )

async def pressScale(control: ft.Control) -> None:
    if control is None:
        return
    
    control.scale = 0.85
    control.update()

    await asyncio.sleep(0.1)

    control.scale = 1
    control.update()

async def onSidePress(e: ft.ControlEvent) -> None:
    target = e.control.content

    if target is None or getattr(target, 'disabled', False):
        return
    await pressScale(target)

async def onCenterPress(e: ft.ControlEvent) -> None:
    target = e.control.content

    if isLoading or target is None:
        return
    
    await pressScale(target)


#=====================#
#======COMPONENT======#
#=====================#
def createPlayerCard(page: ft.Page) -> ft.Container:
    return ft.Container(
        ref=playerCard,
        left=0,
        top=0,
        width=page.width, height=page.height,
        offset=ft.Offset(0, 1),
        padding=ft.Padding.all(15),
        bgcolor='#070B19',
        animate_offset=ft.Animation(duration=100, curve=ft.AnimationCurve.EASE_OUT_CUBIC),
        content=ft.SafeArea(
            avoid_intrusions_bottom=True,
            avoid_intrusions_top=True,
            expand=True,
            content=ft.GestureDetector(
                drag_interval=8,
                on_vertical_drag_start=onDragStart,
                on_vertical_drag_update=onDragDown,
                on_vertical_drag_end=onDragEnd,
                content=ft.Column(
                    expand=True,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                                    icon_color='#8eaeff',
                                    rotate=-(pi / 2),
                                    on_click=closePlayerCard
                                ),
                                ft.Container(
                                    width=50, height=5,
                                    bgcolor='#263452',
                                    border_radius=50
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                                    icon_color='#070B19'
                                )
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    value='NOW PLAYING',
                                    weight=ft.FontWeight.BOLD,
                                    size=12,
                                    font_family='SF-Pro-Bold',
                                    color='#717f9d',
                                    margin=ft.Margin.only(top=-10)
                                )
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Image(
                                    ref=playerImage,
                                    width=page.width * 0.85, height=page.width * 0.85,
                                    src=DEFAULT_IMAGE,
                                    fit=ft.BoxFit.COVER,
                                    border_radius=7.5,
                                    error_content=ft.Image(
                                        width=page.width * 0.85, height=page.width * 0.85,
                                        src=DEFAULT_IMAGE,
                                        fit=ft.BoxFit.COVER,
                                        border_radius=7.5
                                    )
                                )
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.START,
                            controls=[
                                ft.Text(
                                    ref=playerTitle,
                                    expand=True,
                                    value='',
                                    weight=ft.FontWeight.BOLD,
                                    size=18,
                                    font_family='SF-Pro-Semibold',
                                    color='#f3f6ff',
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    margin=ft.Margin.only(top=10, bottom=-10)
                                )
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.START,
                            controls=[
                                ft.Text(
                                    ref=playerArtist,
                                    value='',
                                    weight=ft.FontWeight.BOLD,
                                    size=16,
                                    font_family='SF-Pro-Regular',
                                    color='#717f9d'
                                )
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Slider(
                                    ref=playerSlider,
                                    expand=True,
                                    min=0,
                                    max=1,
                                    value=0,
                                    active_color='#8eaeff',
                                    thumb_color='#ffffff',
                                    on_change=onSliderChange,
                                    on_change_end=onSliderChangeEnd,
                                    margin=ft.Margin.only(left=-7.5, right=-7.5),
                                    disabled=True
                                )
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    ref=playerCurrentTime,
                                    value='--:--',
                                    weight=ft.FontWeight.BOLD,
                                    size=12,
                                    font_family='SF-Pro-Regular',
                                    color='#717f9d',
                                    margin=ft.Margin.only(left=10, top=-15, bottom=-15)
                                ),
                                ft.Text(
                                    ref=playerTotalTime,
                                    value='--:--',
                                    weight=ft.FontWeight.BOLD,
                                    size=12,
                                    font_family='SF-Pro-Regular',
                                    color='#717f9d',
                                    margin=ft.Margin.only(top=-15, right=10, bottom=-15)
                                )
                            ]
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=24,
                            controls=[
                                makeSideButton(ref=playerBackwardButton, image_src='images/backward15.png', on_click=seekBackward),
                                makeCenterButton(),
                                makeSideButton(ref=playerForwardButton, image_src='images/forward15.png', on_click=seekForward)
                            ]
                        )
                    ]
                )
            )
        )
    )
