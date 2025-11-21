import asyncio
import os
import uuid
from pathlib import Path
from typing import List
from zipfile import ZipFile

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PyPDF2 import PdfReader, PdfWriter

STATIC_DIR = Path(__file__).resolve().parent / "static"
STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)

app = FastAPI(title="PDF Splitter API")
app.mount("/files", StaticFiles(directory=STORAGE_DIR), name="files")


async def download_pdf(url: str, destination: Path) -> None:
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=400, detail=f"Failed to download PDF: {exc}") from exc

    destination.write_bytes(response.content)


async def save_pdf_from_request(request: Request, session_dir: Path) -> Path:
    temp_file = session_dir / "source.pdf"
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception as exc:  # pylint: disable=broad-except
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

        pdf_url = payload.get("pdf-url")
        if not pdf_url:
            raise HTTPException(status_code=400, detail="'pdf-url' is required")

        await download_pdf(pdf_url, temp_file)
        return temp_file

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="PDF binary data is required in the request body")

    temp_file.write_bytes(body)
    return temp_file


def split_pdf(source: Path, output_dir: Path, prefix: str) -> List[Path]:
    try:
        reader = PdfReader(str(source))
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail="Unable to read PDF file") from exc

    if len(reader.pages) == 0:
        raise HTTPException(status_code=400, detail="PDF contains no pages")

    paths: List[Path] = []
    for index, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        output_path = output_dir / f"{prefix}_page_{index}.pdf"
        with output_path.open("wb") as output_file:
            writer.write(output_file)
        paths.append(output_path)
    return paths


async def delete_folder_later(folder: Path, delay_seconds: int) -> None:
    await asyncio.sleep(delay_seconds)
    for file_path in folder.glob("*"):
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass
    try:
        folder.rmdir()
    except OSError:
        pass


@app.get("/")
async def serve_index() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail="Index file not found")
    return FileResponse(index_path)


@app.get("/health")
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/pdf-split")
async def pdf_split(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    unique_id = uuid.uuid4().hex
    session_dir = STORAGE_DIR / unique_id
    session_dir.mkdir(exist_ok=True)

    temp_file = await save_pdf_from_request(request, session_dir)

    prefix = temp_file.stem + f"_{unique_id}"
    split_paths = split_pdf(temp_file, session_dir, prefix)

    delete_delay = int(os.environ.get("PDF_CLEANUP_SECONDS", "3600"))
    background_tasks.add_task(delete_folder_later, session_dir, delete_delay)

    base_url = str(request.base_url).rstrip("/")
    urls = [f"{base_url}/files/{unique_id}/{path.name}" for path in split_paths]

    return JSONResponse({"files": urls})


@app.post("/pdf-split-zip")
async def pdf_split_zip(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    unique_id = uuid.uuid4().hex
    session_dir = STORAGE_DIR / unique_id
    session_dir.mkdir(exist_ok=True)

    temp_file = await save_pdf_from_request(request, session_dir)

    prefix = temp_file.stem + f"_{unique_id}"
    split_paths = split_pdf(temp_file, session_dir, prefix)

    zip_path = session_dir / f"{prefix}.zip"
    with ZipFile(zip_path, "w") as archive:
        for page_path in split_paths:
            archive.write(page_path, arcname=page_path.name)

    delete_delay = int(os.environ.get("PDF_CLEANUP_SECONDS", "3600"))
    background_tasks.add_task(delete_folder_later, session_dir, delete_delay)

    base_url = str(request.base_url).rstrip("/")
    zip_url = f"{base_url}/files/{unique_id}/{zip_path.name}"

    return JSONResponse({"zip": zip_url})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
