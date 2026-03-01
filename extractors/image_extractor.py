"""
Image Text Extractor (OCR) Module
Supports: PNG, JPG, JPEG, BMP, TIFF, WEBP, GIF
Uses: pytesseract (Tesseract OCR) + Pillow for preprocessing
No external APIs
"""

import os
import io
import re
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from pathlib import Path


def preprocess_image(img):
    """Multi-step image preprocessing to improve OCR accuracy"""
    # Convert to RGB if needed
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    
    # Upscale small images for better OCR
    w, h = img.size
    if w < 1000 or h < 1000:
        scale = max(1000 / w, 1000 / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
    
    # Grayscale
    gray = img.convert('L')
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(2.0)
    
    # Sharpen
    gray = gray.filter(ImageFilter.SHARPEN)
    
    return gray


def extract_image_text(filepath, lang='eng'):
    """Extract text from image using Tesseract OCR"""
    try:
        import pytesseract
        
        img = Image.open(filepath)
        
        results = {}
        
        # Try original first
        try:
            original_text = pytesseract.image_to_string(img, lang=lang, config='--psm 3')
            results['original'] = original_text.strip()
        except Exception:
            results['original'] = ""
        
        # Try with preprocessing
        try:
            processed = preprocess_image(img.copy())
            processed_text = pytesseract.image_to_string(processed, lang=lang, config='--psm 3')
            results['processed'] = processed_text.strip()
        except Exception:
            results['processed'] = ""
        
        # Use whichever gave more text
        best_text = results['processed'] if len(results.get('processed', '')) >= len(results.get('original', '')) else results['original']
        
        # Get detailed data (bounding boxes, confidence)
        try:
            data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
            words = []
            for i, word in enumerate(data['text']):
                conf = int(data['conf'][i])
                if conf > 0 and word.strip():
                    words.append({
                        "word": word,
                        "confidence": conf,
                        "left": data['left'][i],
                        "top": data['top'][i],
                        "width": data['width'][i],
                        "height": data['height'][i],
                    })
            avg_conf = sum(w['confidence'] for w in words) / len(words) if words else 0
        except Exception:
            words = []
            avg_conf = 0
        
        from extractors.text_extractor import count_words, generate_summary
        
        return {
            "text": best_text,
            "word_count": count_words(best_text),
            "summary": generate_summary(best_text),
            "confidence": round(avg_conf, 1),
            "words_detail": words[:50],  # first 50 words with bounding boxes
            "image_size": f"{img.width}x{img.height}",
            "image_mode": img.mode,
            "filename": os.path.basename(filepath),
            "metadata": {
                "format": img.format or Path(filepath).suffix.upper().strip('.'),
                "size": f"{img.width}x{img.height}",
                "mode": img.mode
            }
        }
    
    except Exception as e:
        return {
            "text": "",
            "error": str(e),
            "filename": os.path.basename(filepath),
            "metadata": {}
        }


def extract_image_from_bytes(file_bytes, filename='image', lang='eng'):
    """Extract text from image bytes (for API use)"""
    try:
        import pytesseract
        
        img = Image.open(io.BytesIO(file_bytes))
        
        original_text = pytesseract.image_to_string(img, lang=lang, config='--psm 3').strip()
        processed = preprocess_image(img.copy())
        processed_text = pytesseract.image_to_string(processed, lang=lang, config='--psm 3').strip()
        
        best_text = processed_text if len(processed_text) >= len(original_text) else original_text
        
        from extractors.text_extractor import count_words, generate_summary
        
        return {
            "text": best_text,
            "word_count": count_words(best_text),
            "summary": generate_summary(best_text),
            "image_size": f"{img.width}x{img.height}",
            "filename": filename
        }
    except Exception as e:
        return {"text": "", "error": str(e), "filename": filename}


SUPPORTED_IMAGE_EXTS = {
    '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp', '.gif'
}


def is_image(filename):
    return Path(filename).suffix.lower() in SUPPORTED_IMAGE_EXTS
