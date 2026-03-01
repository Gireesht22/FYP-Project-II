"""
FYP Universal Extractor - Semester 8 Upgrade
Powered by Groq AI (Llama 3.3 70B)
"""

import os, sys, json, uuid
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(__file__))

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['SECRET_KEY'] = 'fyp-extractor-sem8-groq'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ── CORS: allow your Vercel frontend to call this backend ──────
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "https://*.vercel.app",          # all vercel preview URLs
    "https://fyp-project-ii.vercel.app"  # ← replace with your actual Vercel URL
]}})

ALLOWED_EXTENSIONS = {
    'pdf','docx','doc','xlsx','xls','pptx','ppt','csv','txt','md',
    'html','htm','json','xml','yaml','yml','log','py','js','ts','rtf',
    'png','jpg','jpeg','bmp','tiff','tif','webp','gif','zip'
}

def allowed_file(f): return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS
def save_upload(file):
    ext = Path(file.filename).suffix.lower()
    fp = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4().hex}{ext}")
    file.save(fp)
    return fp, file.filename, ext

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/extract/file', methods=['POST'])
def api_extract_file():
    if 'file' not in request.files: return jsonify({"error":"No file"}),400
    file = request.files['file']
    if not file.filename or not allowed_file(file.filename): return jsonify({"error":"Not supported"}),400
    fp, name, ext = save_upload(file)
    try:
        from extractors.image_extractor import SUPPORTED_IMAGE_EXTS, extract_image_text
        from extractors.text_extractor import extract_file
        result = extract_image_text(fp) if ext in SUPPORTED_IMAGE_EXTS else extract_file(fp)
        result.update({'type':'image' if ext in SUPPORTED_IMAGE_EXTS else 'document','original_filename':name,'processed_at':datetime.now().isoformat()})
        return jsonify(result)
    except Exception as e: return jsonify({"error":str(e)}),500
    finally:
        try: os.remove(fp)
        except: pass

@app.route('/api/extract/zip', methods=['POST'])
def api_extract_zip():
    if 'file' not in request.files: return jsonify({"error":"No file"}),400
    file = request.files['file']
    fp, name, _ = save_upload(file)
    try:
        from extractors.zip_extractor import extract_zip
        result = extract_zip(fp, extract_text=request.form.get('extract_text','true').lower()=='true')
        result.update({'original_filename':name,'processed_at':datetime.now().isoformat()})
        return jsonify(result)
    except Exception as e: return jsonify({"error":str(e)}),500
    finally:
        try: os.remove(fp)
        except: pass

@app.route('/api/extract/image', methods=['POST'])
def api_extract_image():
    if 'file' not in request.files: return jsonify({"error":"No file"}),400
    file = request.files['file']
    fp, name, _ = save_upload(file)
    try:
        from extractors.image_extractor import extract_image_text
        result = extract_image_text(fp, lang=request.form.get('lang','eng'))
        result.update({'original_filename':name,'processed_at':datetime.now().isoformat()})
        return jsonify(result)
    except Exception as e: return jsonify({"error":str(e)}),500
    finally:
        try: os.remove(fp)
        except: pass

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    data = request.get_json(silent=True) or {}
    url = data.get('url','').strip()
    if not url: return jsonify({"error":"No URL"}),400
    try:
        from extractors.web_scraper import scrape_url
        result = scrape_url(url)
        result['processed_at'] = datetime.now().isoformat()
        return jsonify(result)
    except Exception as e: return jsonify({"error":str(e),"success":False}),500

@app.route('/api/scrape/multiple', methods=['POST'])
def api_scrape_multiple():
    data = request.get_json(silent=True) or {}
    urls = data.get('urls',[])
    if not urls or len(urls)>10: return jsonify({"error":"Provide 1-10 URLs"}),400
    try:
        from extractors.web_scraper import scrape_multiple
        results = scrape_multiple(urls)
        return jsonify({"results":results,"total":len(results),"successful":len([r for r in results if r.get("success")]),"processed_at":datetime.now().isoformat()})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route('/api/ai/analyze', methods=['POST'])
def api_ai_analyze():
    data = request.get_json(silent=True) or {}
    text = data.get('text','').strip()
    if not text: return jsonify({"error":"No text"}),400
    try:
        from extractors.ai_analyzer import full_analysis
        result = full_analysis(text)
        result['processed_at'] = datetime.now().isoformat()
        return jsonify(result)
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route('/api/ai/ask', methods=['POST'])
def api_ai_ask():
    data = request.get_json(silent=True) or {}
    text = data.get('text','').strip()
    question = data.get('question','').strip()
    if not text or not question: return jsonify({"error":"Provide text and question"}),400
    try:
        from extractors.ai_analyzer import ask_document
        answer = ask_document(text, question)
        return jsonify({"question":question,"answer":answer,"processed_at":datetime.now().isoformat()})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route('/api/ai/summarize', methods=['POST'])
def api_ai_summarize():
    data = request.get_json(silent=True) or {}
    text = data.get('text','').strip()
    domain = data.get('domain','General')
    if not text: return jsonify({"error":"No text"}),400
    try:
        from extractors.ai_analyzer import smart_summary
        result = smart_summary(text, domain)
        result['processed_at'] = datetime.now().isoformat()
        return jsonify(result)
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route('/api/info')
def api_info():
    return jsonify({"name":"FYP Universal Extractor Sem8","version":"2.0.0","ai":"Groq Llama 3.3 70B"})

@app.errorhandler(413)
def too_large(e): return jsonify({"error":"File too large"}),413

if __name__ == '__main__':
    print("="*60)
    print("  FYP Extractor Sem8 — Groq AI Powered")
    print("  URL: http://localhost:5000")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
