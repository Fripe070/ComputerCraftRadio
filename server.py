import random
import json

import ffmpeg
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from yt_dlp import YoutubeDL

PLAYLIST_URL = "https://www.youtube.com/playlist?list=<PLAYLIST_ID>"
CHUNK_SIZE = 16 * 1024

app = FastAPI()
active_connections = []


@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket_handler(websocket)
    except WebSocketDisconnect:
        active_connections.remove(websocket)


class CacheData:
    def __init__(self):
        self.data: list[int] | None = None  # ints are -128 to 127 inclusive

    def pop_chunk(self) -> list[int]:
        if self.data is None:
            raise ValueError("No data in cache")

        chunk = self.data[:CHUNK_SIZE]
        self.data = self.data[CHUNK_SIZE:]

        return chunk


cache = CacheData()
playlist_videos = []


def video_to_best_audio_url(video: dict) -> str:
    formats = video["formats"]
    for format in formats:
        if format["format_id"] == "251":
            return format["url"]


with YoutubeDL(dict(
    format="bestaudio/best",
)) as ydl:
    playlist = ydl.extract_info(PLAYLIST_URL, download=False)
    playlist_videos = list(map(
        video_to_best_audio_url,
        playlist["entries"]
    ))

print(json.dumps(playlist_videos, indent=4))

async def get_next_chunk() -> list[int]:
    if cache.data:
        return cache.pop_chunk()
    
    video = random.choice(playlist["entries"])
    print(video)
    stream = (
        ffmpeg
        .input(video["url"])
        .output(
            "pipe:",
            format="dfpwm",
            ac=1,  # 1 channel
            ar=48000,  # 48kHz
            sample_fmt="u8"  # 8 bit
        )
        .run_async(pipe_stdout=True)
    )

    cache.data = []
    cache.data.extend(stream.stdout.read())

    return cache.pop_chunk()


async def websocket_handler(websocket: WebSocket):
    command = await websocket.receive_text()
    match command:
        case "more":
            chunk = await get_next_chunk()
            print(f"Sending chunk of size {len(chunk)} to {websocket.client.host}")
            await websocket.send_bytes(bytes(chunk))
