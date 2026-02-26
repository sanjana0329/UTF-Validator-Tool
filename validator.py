# validator.py
import os
import chardet

BINARY_EXTENSIONS = (
    ".pdf", ".xls", ".xlsx", ".doc", ".docx", ".ppt", ".pptx",
    ".zip", ".rar", ".exe", ".png", ".jpg", ".jpeg", ".gif",
    ".mp3", ".mp4", ".avi", ".mkv", ".wav", ".bmp", ".ico",
    ".db", ".sqlite", ".pyc", ".class"
)

# Explicitly supported open data portal formats
SUPPORTED_TEXT_FORMATS = (
    ".csv", ".json", ".geojson",        # Core open data formats
    ".xml", ".rdf", ".ttl", ".n3",      # Semantic Web / Linked Data
    ".txt", ".md", ".html", ".htm",     # Text formats
    ".yaml", ".yml", ".tsv",            # Config / tabular
    ".py", ".js", ".ts",                # Code
)

def scan_single_file(file_path):
    """
    Accurate UTF detection using a two-step approach:
    
    Step 1 — Strict decode: try decoding as UTF-8 with errors='strict'.
             If it succeeds with NO exceptions → 100% valid UTF-8.
    
    Step 2 — If strict fails, use chardet to detect actual encoding,
             then decode with 'replace' and count bad bytes to get
             the exact % of content that is valid UTF-8.
    
    This prevents false positives where Latin-1/Windows-1252 files
    (which are mostly ASCII) get wrongly reported as UTF-8.
    """
    ext = os.path.splitext(file_path)[1].lower()

    # Binary files — flag immediately, no scanning needed
    if ext in BINARY_EXTENSIONS:
        return {
            "utf_percent":     0.0,
            "non_utf_percent": 100.0,
            "total_chars":     0,
            "non_utf_chars":   0,
            "is_utf":          False,
            "is_mostly_utf":   False,
            "is_binary":       True,
            "detected_encoding": "Binary",
            "error":           None
        }

    try:
        with open(file_path, "rb") as f:
            raw = f.read()

        # Empty file
        if len(raw) == 0:
            return {
                "utf_percent":     100.0,
                "non_utf_percent": 0.0,
                "total_chars":     0,
                "non_utf_chars":   0,
                "is_utf":          True,
                "is_mostly_utf":   True,
                "is_binary":       False,
                "detected_encoding": "UTF-8 (empty)",
                "error":           None
            }

        # ── Step 1: Strict UTF-8 decode ──
        # If this succeeds, the file is genuinely 100% valid UTF-8
        try:
            raw.decode("utf-8", errors="strict")
            # Check for BOM (UTF-8 with BOM is still UTF-8)
            has_bom = raw.startswith(b'\xef\xbb\xbf')
            enc_label = "UTF-8 (BOM)" if has_bom else "UTF-8"
            total_chars = len(raw.decode("utf-8", errors="strict"))
            return {
                "utf_percent":     100.0,
                "non_utf_percent": 0.0,
                "total_chars":     total_chars,
                "non_utf_chars":   0,
                "is_utf":          True,
                "is_mostly_utf":   True,
                "is_binary":       False,
                "detected_encoding": enc_label,
                "error":           None
            }
        except UnicodeDecodeError:
            pass  # Not pure UTF-8, continue to Step 2

        # ── Step 2: Detect actual encoding with chardet ──
        detection    = chardet.detect(raw)
        detected_enc = detection.get("encoding") or "Unknown"
        confidence   = detection.get("confidence", 0.0)

        # Now decode with replace to count bad bytes
        decoded       = raw.decode("utf-8", errors="replace")
        total_chars   = len(decoded)
        non_utf_chars = decoded.count("\ufffd")
        utf_chars     = total_chars - non_utf_chars

        utf_percent     = (utf_chars / total_chars) * 100 if total_chars > 0 else 0.0
        non_utf_percent = (non_utf_chars / total_chars) * 100 if total_chars > 0 else 0.0

        return {
            "utf_percent":     round(utf_percent, 2),
            "non_utf_percent": round(non_utf_percent, 2),
            "total_chars":     total_chars,
            "non_utf_chars":   non_utf_chars,
            "is_utf":          False,   # Failed strict check so definitely not pure UTF-8
            "is_mostly_utf":   utf_percent >= 90.0,
            "is_binary":       False,
            "detected_encoding": f"{detected_enc} ({confidence:.0%} confidence)",
            "error":           None
        }

    except Exception as e:
        return {
            "utf_percent":     0.0,
            "non_utf_percent": 100.0,
            "total_chars":     0,
            "non_utf_chars":   0,
            "is_utf":          False,
            "is_mostly_utf":   False,
            "is_binary":       False,
            "detected_encoding": "Error",
            "error":           str(e)
        }


def scan_folder(folder_path):
    """
    Scans ALL files in the folder. Binary files are flagged instantly.
    Returns:
      results: list of dicts with file path + detailed encoding info
      skipped_files: always empty (nothing is skipped)
    """
    results = []

    for root, dirs, files in os.walk(folder_path):
        for f in files:
            full_path = os.path.join(root, f)
            info          = scan_single_file(full_path)
            info["file"]     = full_path
            info["filename"] = f
            results.append(info)

    return results, []