from fastapi import Request


def current_user(request: Request) -> str | None:
    return request.session.get("username")


def is_authenticated(request: Request) -> bool:
    return current_user(request) is not None
