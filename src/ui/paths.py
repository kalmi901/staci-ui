from src.config import APP_URL_PREFIX


def app_path(path: str) -> str:
    return APP_URL_PREFIX + path.lstrip("/")


def local_path(pathname: str | None) -> str | None:
    if pathname is None:
        return None
    if not pathname.startswith(APP_URL_PREFIX):
        return None
    return "/" + pathname[len(APP_URL_PREFIX):]
