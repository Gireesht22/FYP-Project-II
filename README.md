# UniExtract — Universal Data Extraction Suite

A production-level web application for extracting text from files, images, ZIP archives, and web pages.
**No external APIs. 100% local processing.**

---

## Features

| Module | Description | Supported Formats |
|---|---|---|
| **File Extractor** | Extract text from documents | PDF, DOCX, XLSX, PPTX, CSV, TXT, HTML, JSON, XML, YAML, and 20+ more |
| **Image OCR** | Extract text from images using Tesseract | PNG, JPG, BMP, TIFF, WEBP, GIF |
| **ZIP Analyzer** | Inspect + extract all contents of ZIP archives | .zip (with nested support) |
| **Web Scraper** | Scrape structured content from URLs | Any public webpage, batch up to 10 URLs |

---

## Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Tesseract OCR (for image extraction)

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
# For additional languages:
sudo apt-get install tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-spa
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

### 3. Run the Application
```bash
cd fyp_extractor
python app.py
```

Open http://localhost:5000 in your browser.

---

## Project Structure

```
fyp_extractor/
├── app.py                          # Flask application & API routes
├── requirements.txt                # Python dependencies
├── templates/
│   └── index.html                  # Full frontend UI
├── extractors/
│   ├── __init__.py
│   ├── text_extractor.py           # Document text extraction
│   ├── image_extractor.py          # OCR via Tesseract
│   ├── zip_extractor.py            # ZIP archive analysis
│   └── web_scraper.py              # Web scraping with BeautifulSoup
└── uploads/                        # Temp upload directory (auto-created)
```

---

## API Reference

All endpoints return JSON.

### POST `/api/extract/file`
Extract text from any document.
- Body: `multipart/form-data` with `file` field
- Returns: `{ text, summary, word_count, metadata, ... }`

### POST `/api/extract/image`
OCR text from an image.
- Body: `multipart/form-data` with `file` and optional `lang` (default: `eng`)
- Returns: `{ text, summary, confidence, word_count, ... }`

### POST `/api/extract/zip`
Analyze a ZIP archive.
- Body: `multipart/form-data` with `file` and optional `extract_text` (bool)
- Returns: `{ files, summary, statistics, combined_text, ... }`

### POST `/api/scrape`
Scrape a single URL.
- Body: `{ "url": "https://example.com" }`
- Returns: `{ title, full_text, summary, headings, links, images, ... }`

### POST `/api/scrape/multiple`
Scrape up to 10 URLs.
- Body: `{ "urls": ["https://...", "https://..."] }`
- Returns: `{ results: [...], total, successful }`

### GET `/api/info`
API documentation endpoint.

---

## Technical Details

### Text Extraction Pipeline
- **PDF**: `pdfplumber` — extracts text + tables page by page
- **DOCX**: `python-docx` — paragraphs, tables, metadata
- **XLSX**: `openpyxl` — all sheets, all cells
- **PPTX**: `python-pptx` — all slides, all shapes
- **CSV**: `csv` + `chardet` auto-encoding detection
- **HTML/XML**: `BeautifulSoup` — noise-filtered clean text
- **JSON**: structured flatten + pretty-print

### OCR Pipeline
1. Load image with Pillow
2. Auto-upscale to minimum 1000px
3. Convert to grayscale
4. Enhance contrast ×2
5. Sharpen filter
6. Run Tesseract PSM-3 on both original and processed
7. Select result with most text
8. Return confidence scores per word

### Web Scraper
- Custom headers for bot-detection avoidance
- Smart main content extraction (tries `main`, `article`, `[role=main]`, etc.)
- Removes scripts, styles, nav, footer, popups
- Extracts: title, author, date, paragraphs, headings, links, images, tables
- Classifies internal vs external links
- Extractive summarization (no LLM needed)

### Summarization Algorithm
- Sentence tokenization
- Word frequency scoring
- Position bias (first + last sentences boosted)
- Top-N extraction sorted by original order

---

## Limitations
- Scanned PDFs without embedded text need OCR (use Image OCR tab)
- Web scraping may not work on pages requiring JavaScript rendering
- Tesseract accuracy depends on image quality
- Max upload size: 200MB (configurable in app.py)
