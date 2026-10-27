# ShelfReady online version: the same web page as shelfready_app.py, with one extra check in front.
# Streamlit has a public /_stcore/metrics page (visitor counts) that cannot be switched off in its settings,
# so a small "middleware" looks at every request first and answers "not found" for that page.
# Used by the Dockerfile (Render). Locally, streamlit run shelfready_app.py still works as before.

import streamlit as st
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse

HIDDEN_PATHS: list[str] = ["/_stcore/metrics"]


class HidePaths:
    # runs before streamlit for every request
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # "/_stcore/metrics/" with a slash at the end is the same page, so it is hidden too
        path: str = scope.get("path", "").rstrip("/")
        if scope["type"] == "http" and path in HIDDEN_PATHS:
            response = PlainTextResponse("Not found", status_code=404)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


app = st.App("shelfready_app.py", middleware=[Middleware(HidePaths)])
