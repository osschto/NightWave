from __future__ import annotations

import flet as ft

DEFAULT_IMAGE = 'images/default-image.jpg'

def item_key(item: dict) -> str:
    return str(
        item.get('feedId')
        or item.get('librivoxId')
        or item.get('rss')
        or f"{item.get('title', '')}|{item.get('artist', '')}"
    )

def item_id_for_recent(item: dict) -> str | int | None:
    item_type = item.get('itemType')

    if item_type == 'podcast':
        return item.get('feedId') or item.get('rss') or item.get('id')
    
    if item_type == 'audiobook':
        return item.get('librivoxId') or item.get('rss') or item.get('id')
    
    return (
        item.get('feedId')
        or item.get('librivoxId')
        or item.get('rss')
        or item.get('id')
    )

def resolve_image(url: str | None) -> str:
    if url is None:
        return DEFAULT_IMAGE

    text = str(url).strip()
    if not text or text.lower() in ('none', 'null', 'undefined'):
        return DEFAULT_IMAGE

    if text.startswith('//'):
        text = 'https:' + text

    return text

def cover_image(
    src: str | None,
    *,
    width: int | float,
    height: int | float,
    border_radius: int | float = 7.5,
    ref: ft.Ref[ft.Image] | None = None,
    fit: ft.BoxFit = ft.BoxFit.COVER) -> ft.Image:
    resolved = resolve_image(src)

    return ft.Image(
        ref=ref,
        src=resolved,
        width=width, height=height,
        fit=fit,
        border_radius=border_radius,
        error_content=ft.Image(
            src=DEFAULT_IMAGE,
            width=width, height=height,
            fit=fit,
            border_radius=border_radius,
        ),
    )