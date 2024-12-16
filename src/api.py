from fastapi import FastAPI, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uvicorn
from webtoon_downloader import download_webtoon
import uuid
import json

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class DownloadRequest(BaseModel):
    url: str
    start_chapter: int = None
    end_chapter: int = None
    dest: str = None
    images_format: str = "jpg"
    download_latest_chapter: bool = False
    separate_chapters: bool = True

active_downloads = {}

async def download_manager(download_id, request, websocket):
    async def progress_callback(data):
        await websocket.send_json({
            "download_id": download_id,
            **data
        })

    await download_webtoon(
        request.url,
        request.start_chapter,
        request.end_chapter,
        request.dest,
        request.images_format,
        request.download_latest_chapter,
        separate_chapters=True,
        progress_callback=progress_callback
    )

    del active_downloads[download_id]
    await websocket.send_json({"download_id": download_id, "status": "completed"})

@app.post("/download")
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    download_id = str(uuid.uuid4())
    active_downloads[download_id] = request
    return {"download_id": download_id}

@app.get("/status")
async def get_status():
    # This is a placeholder. You'd need to implement actual status tracking.
    return {"status": "in progress", "message": "Welcome to my toon scrapper", "version": 2.0}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive_text()
            data = json.loads(data)
            if data["action"] == "start_download":
                download_id = data["download_id"]
                if download_id in active_downloads:
                    request = active_downloads[download_id]
                    asyncio.create_task(download_manager(download_id, request, websocket))
                else:
                    await websocket.send_json({"error": "Invalid download_id"})
        except Exception as e:
            await websocket.send_json({"error": str(e)})
            break

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
