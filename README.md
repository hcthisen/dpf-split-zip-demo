# PDF Split API

This project provides a small FastAPI application that downloads a multi-page PDF from a public URL, splits it into single-page PDFs, and exposes each page as a public download link. Generated PDFs are automatically deleted after 60 minutes to avoid unbounded storage growth.

## Features

- **Health check** available at `/`.
- **Split endpoint** at `/pdf-split` that accepts a JSON body with a `"pdf-url"` property pointing to a publicly accessible PDF.
- **Public download links** returned for every generated page under `/files/{request-id}/...`.
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

## Usage

1. Send a `POST` request to `http://127.0.0.1:8000/pdf-split` with a JSON body such as:

   ```json
   {
     "pdf-url": "https://example.com/sample.pdf"
   }
   ```

2. The response contains a `files` array of public URLs that each serve a single PDF page:

   ```json
   {
     "files": [
       "http://127.0.0.1:8000/files/1a2b3c4d/.../sample_1a2b3c4d_page_1.pdf",
       "http://127.0.0.1:8000/files/1a2b3c4d/.../sample_1a2b3c4d_page_2.pdf"
     ]
   }
   ```

3. Download links are valid for 60 minutes. Set the `PDF_CLEANUP_SECONDS` environment variable to adjust the retention period if needed.

## Notes

- The application stores temporary files in the `storage/` directory. Each request receives a unique identifier that is appended to generated file names to avoid collisions.
- For production usage, consider placing the application behind a reverse proxy that serves static files efficiently.
