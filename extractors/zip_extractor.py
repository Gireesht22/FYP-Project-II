"""
ZIP Extractor Module
Extracts all files from ZIP archives, processes each one, generates summary
No external APIs
"""

import os
import zipfile
import io
import tempfile
from pathlib import Path
from datetime import datetime


def get_file_category(filename):
    ext = Path(filename).suffix.lower()
    categories = {
        'document': ['.pdf', '.docx', '.doc', '.odt', '.rtf'],
        'spreadsheet': ['.xlsx', '.xls', '.csv', '.ods'],
        'presentation': ['.pptx', '.ppt', '.odp'],
        'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg'],
        'text': ['.txt', '.md', '.log', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg'],
        'code': ['.py', '.js', '.ts', '.html', '.htm', '.css', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go'],
        'archive': ['.zip', '.tar', '.gz', '.rar', '.7z'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg'],
        'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv'],
    }
    for category, exts in categories.items():
        if ext in exts:
            return category
    return 'other'


def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def extract_zip(filepath, extract_text=True, max_extract_size_mb=50):
    """
    Extract ZIP file and process all contents.
    Returns structured info + extracted text per file.
    """
    results = {
        "filename": os.path.basename(filepath),
        "file_size": format_size(os.path.getsize(filepath)),
        "success": True,
        "files": [],
        "summary": "",
        "statistics": {},
        "errors": []
    }
    
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            all_info = zf.infolist()
            
            # ZIP metadata
            results["total_files"] = len([i for i in all_info if not i.is_dir()])
            results["total_dirs"] = len([i for i in all_info if i.is_dir()])
            
            # Check comment
            if zf.comment:
                results["zip_comment"] = zf.comment.decode('utf-8', errors='replace')
            
            # Process each file
            category_counts = {}
            total_uncompressed = 0
            all_text_parts = []
            
            for info in all_info:
                if info.is_dir():
                    continue
                
                fname = info.filename
                ext = Path(fname).suffix.lower()
                category = get_file_category(fname)
                
                compressed_size = info.compress_size
                uncompressed_size = info.file_size
                total_uncompressed += uncompressed_size
                
                category_counts[category] = category_counts.get(category, 0) + 1
                
                file_entry = {
                    "name": fname,
                    "extension": ext,
                    "category": category,
                    "compressed_size": format_size(compressed_size),
                    "uncompressed_size": format_size(uncompressed_size),
                    "compression_ratio": round(
                        (1 - compressed_size / uncompressed_size) * 100, 1
                    ) if uncompressed_size > 0 else 0,
                    "date_modified": datetime(*info.date_time).strftime('%Y-%m-%d %H:%M'),
                    "text": "",
                    "word_count": 0,
                    "error": None,
                }
                
                # Extract and process text content
                if extract_text and uncompressed_size < max_extract_size_mb * 1024 * 1024:
                    try:
                        file_bytes = zf.read(fname)
                        
                        if category == 'image':
                            # OCR on images inside ZIP
                            try:
                                from extractors.image_extractor import extract_image_from_bytes
                                img_result = extract_image_from_bytes(file_bytes, fname)
                                file_entry["text"] = img_result.get("text", "")
                                file_entry["word_count"] = img_result.get("word_count", 0)
                                file_entry["ocr_applied"] = True
                            except Exception as e:
                                file_entry["error"] = f"OCR failed: {str(e)}"
                        
                        elif category in ('document', 'spreadsheet', 'presentation', 
                                          'text', 'code'):
                            # Save to temp file then extract
                            with tempfile.NamedTemporaryFile(
                                suffix=ext, delete=False
                            ) as tmp:
                                tmp.write(file_bytes)
                                tmp_path = tmp.name
                            
                            try:
                                from extractors.text_extractor import extract_file
                                text_result = extract_file(tmp_path)
                                file_entry["text"] = text_result.get("text", "")[:5000]  # cap per file
                                file_entry["word_count"] = text_result.get("word_count", 0)
                                if text_result.get("text"):
                                    all_text_parts.append(
                                        f"[{fname}]\n{text_result['text'][:1000]}"
                                    )
                            finally:
                                os.unlink(tmp_path)
                        
                        elif category == 'archive':
                            # Nested ZIP
                            try:
                                nested_zip_path = None
                                with tempfile.NamedTemporaryFile(
                                    suffix='.zip', delete=False
                                ) as tmp:
                                    tmp.write(file_bytes)
                                    nested_zip_path = tmp.name
                                nested = extract_zip(nested_zip_path, extract_text=False)
                                file_entry["nested_zip"] = {
                                    "files": nested.get("total_files", 0),
                                    "file_list": [
                                        f["name"] for f in nested.get("files", [])[:10]
                                    ]
                                }
                                if nested_zip_path:
                                    os.unlink(nested_zip_path)
                            except Exception as e:
                                file_entry["error"] = f"Nested ZIP error: {str(e)}"
                    
                    except Exception as e:
                        file_entry["error"] = str(e)
                        results["errors"].append(f"{fname}: {str(e)}")
                
                results["files"].append(file_entry)
            
            # Statistics
            results["statistics"] = {
                "by_category": category_counts,
                "total_uncompressed_size": format_size(total_uncompressed),
                "total_files": len(results["files"]),
                "files_with_text": len([f for f in results["files"] if f.get("text")])
            }
            
            # Overall summary
            from extractors.text_extractor import generate_summary
            if all_text_parts:
                combined_text = "\n\n".join(all_text_parts)
                results["summary"] = generate_summary(combined_text, max_sentences=6)
                results["combined_text"] = combined_text
                results["total_word_count"] = sum(
                    f.get("word_count", 0) for f in results["files"]
                )
            else:
                file_names = [f["name"] for f in results["files"]]
                results["summary"] = (
                    f"ZIP archive containing {results['total_files']} files: "
                    + ", ".join(file_names[:10])
                    + ("..." if len(file_names) > 10 else "")
                )
    
    except zipfile.BadZipFile:
        results["success"] = False
        results["error"] = "Invalid or corrupted ZIP file"
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
    
    return results
