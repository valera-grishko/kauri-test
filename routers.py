import asyncio

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from manager import manager
from exchanges import EXCHANGE_INTEGRATORS

app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/display-prices", response_class=HTMLResponse)
def display_prices(request: Request, pair: str | None = None, exchange: str | None = None):
    return templates.TemplateResponse(
        "interface.html",
        context={
            "request": request,
            "pair": pair,
            "exchange": exchange
        }
    )


@app.on_event("startup")
async def exchanges_starting_event():
    for integrator in EXCHANGE_INTEGRATORS:
        asyncio.create_task(integrator.connect())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    while True:
        await manager.broadcast_with_disconnect_checker()
        await asyncio.sleep(2)
