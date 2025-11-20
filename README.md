# PDF Split API

This project provides a small FastAPI application that downloads a multi-page PDF from a public URL, splits it into single-page PDFs, and exposes each page as a public download link. Generated PDFs are automatically deleted after 60 minutes to avoid unbounded storage growth.

## Features

- **Health check** available at `/`.
- **Split endpoint** at `/pdf-split` that accepts either a JSON body with a `"pdf-url"` property pointing to a publicly accessible PDF **or** raw PDF binary data in the request body.
- **Public download links** returned for every generated page under `/files/{request-id}/...`.
- **Zip endpoint** at `/pdf-split-zip` that splits the PDF into single-page PDFs, then returns a downloadable zip containing all generated pages.
- **Automatic cleanup** removes generated files after 60 minutes (configurable via the `PDF_CLEANUP_SECONDS` environment variable).

## Getting started

### Requirements

- Python 3.10+
- `pip`

Install dependencies:

```bash
pip install -r requirements.txt
```

### Run the app

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000` by default.

### Environment variables

| Variable              | Default | Description |
| --------------------- | ------- | ----------- |
| `PDF_CLEANUP_SECONDS` | `3600`  | Number of seconds to keep generated PDFs before cleanup. |
| `PORT`                | `8000`  | Listening port. Many platforms (including Coolify) inject their own value. |

## Usage

1. Send a `POST` request to `http://127.0.0.1:8000/pdf-split` with either:

   - A JSON body such as:

     ```json
     {
       "pdf-url": "https://example.com/sample.pdf"
     }
     ```

   - Or raw PDF binary data (for example `curl -X POST --data-binary @sample.pdf http://127.0.0.1:8000/pdf-split`).

2. The response contains a `files` array of public URLs that each serve a single PDF page:

   ```json
   {
     "files": [
       "http://127.0.0.1:8000/files/1a2b3c4d/.../sample_1a2b3c4d_page_1.pdf",
       "http://127.0.0.1:8000/files/1a2b3c4d/.../sample_1a2b3c4d_page_2.pdf"
     ]
   }
   ```

3. To receive a zip containing the split pages, send the same JSON or binary payload to `http://127.0.0.1:8000/pdf-split-zip`.
   The response includes a single `zip` URL pointing to the archive of all generated pages.

4. Download links are valid for 60 minutes. Set the `PDF_CLEANUP_SECONDS` environment variable to adjust the retention period if needed.

## Deployment

### Docker

Build the container image locally:

```bash
docker build -t pdf-split:latest .
```

Run the container:

```bash
docker run --rm -p 8000:8000 -e PORT=8000 -e PDF_CLEANUP_SECONDS=3600 pdf-split:latest
```

The API will be available at `http://127.0.0.1:8000`.

### Coolify

1. Create a new **Service ➜ Application** in Coolify and choose **Git Repository** as the deployment source.
2. Point Coolify at this repository and select the branch you want to deploy.
3. When prompted for the build strategy, choose **Docker** and keep the default Dockerfile path (`Dockerfile`).
4. Under **Environment Variables**, add any overrides you need (for example `PDF_CLEANUP_SECONDS`). Coolify automatically injects the `PORT` variable that the container honours.
5. Add a persistent storage mount (e.g. `/app/storage`) if you want to retain generated PDFs between container restarts.
6. Trigger the deployment. Once the container is running, Coolify will proxy requests to the exposed port.

## Notes

- The application stores temporary files in the `storage/` directory. Each request receives a unique identifier that is appended to generated file names to avoid collisions. Mount the directory to persistent storage in production if you need to retain files across deployments.
- For production usage, consider placing the application behind a reverse proxy that serves static files efficiently.
