import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.handlers import SessionHandler

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()

    async def send_json(msg: dict) -> None:
        await websocket.send_json(msg)

    handler = SessionHandler(send_json=send_json)
    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                await handler.handle_binary(message["bytes"])
            elif "text" in message and message["text"]:
                await handler.handle_text(message["text"])
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception:
        logger.exception("WebSocket error")
    finally:
        handler.cleanup()
