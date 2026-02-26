# UTF Encoding Validation Tool

A desktop application for validating UTF-8 character encoding of files from open data portals. Built with Python and PyQt5.

---

## About the Project

Open data portals publish datasets in formats such as **CSV, JSON, and GeoJSON**. These files must be UTF-8 encoded to ensure compatibility across different systems and data pipelines. However, many datasets — especially from legacy systems — use non-standard encodings like *Windows-1252* or *ISO-8859-1*, causing data corruption and processing failures.

The **UTF Encoding Validation Tool** solves this by scanning entire dataset directories, detecting character encodings, and providing clear visual feedback on which files are UTF-8 compliant and which are not.

This project was developed as part of the **Forschungspraktikum (Research Internship)** in the *Datenmanagement* module at **TU Chemnitz**, M.Sc. Web Engineering, Wintersemester 2025/2026.

---

## Features

- **Batch scanning** — scan a single file or an entire folder at once
- **Two-step UTF-8 validation** — strict decode first, chardet fallback for accuracy
- **Percentage-based metrics** — see exactly how UTF-8 compliant each file is
- **Visual statistics** — donut chart, summary cards, progress bars, mini pie charts
- **Encoding detection** — identifies Windows-1252, ISO-8859-1, ISO-8859-2, ASCII, and more
- **Clear invalid UTF warnings** — flags files not suitable for open data publishing
- **Export results** — save reports as CSV or PDF
- **Smooth animated loader** — dedicated thread animation during scanning
- **Supports multiple formats** — CSV, JSON, GeoJSON, TTL, RDF, XML, TXT, and more

---

## Screenshots

> Add screenshots of your application here after upload.

---

## Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.10+ | Core language |
| PyQt5 | Desktop GUI framework |
| chardet | Encoding detection |
| matplotlib | Charts and visualizations |
| reportlab | PDF export |
| QThread | Multi-threaded scanning |

---

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/sanjana0329/UTF-Validator-Tool.git
cd UTF-Validator-Tool
```

**2. Create a virtual environment**
```bash
python -m venv .venv
```

**3. Activate the virtual environment**

On Windows:
```bash
.venv\Scripts\activate
```

On Mac/Linux:
```bash
source .venv/bin/activate
```

**4. Install dependencies**
```bash
pip install -r requirements.txt
```

**5. Run the application**
```bash
python main.py
```

---

## How It Works

The tool uses a **two-step validation algorithm**:

1. **Binary check** — files with binary extensions (.pdf, .xlsx, .png etc.) are skipped instantly
2. **Strict UTF-8 decode** — if the file decodes without errors, it is 100% UTF-8 (fast path, chardet not needed)
3. **chardet fallback** — if strict decode fails, chardet identifies the actual encoding and a UTF-8 percentage is calculated

Files are classified into four categories:

| Category | Condition | Meaning |
|---|---|---|
| ✅ 100% UTF | utf_percent = 100 | Fully valid UTF-8 |
| ⚠️ Mostly UTF | >= 90% | Minor issues, review recommended |
| ⛔ Invalid UTF | < 90% | Not suitable for open data portals |
| 📦 Binary | Extension match | Skipped, not applicable |

---

## Project Structure

```
utf_validator/
├── main.py          # Entry point — launches maximized window
├── ui.py            # Complete PyQt5 GUI and export logic
├── validator.py     # Two-step encoding detection engine
├── requirements.txt # Project dependencies
└── README.md        # Project documentation
```

---

## Supported File Formats

| Category | Extensions |
|---|---|
| Open Data Core | .csv, .json, .geojson |
| Semantic Web | .ttl, .rdf, .n3 |
| Markup | .xml, .html, .htm |
| Plain Text | .txt, .md, .yaml |
| Binary (skipped) | .pdf, .xlsx, .png, .jpg, .zip, ... |

---

## Research Context

This tool was developed to address the following research question:

> *"Can a desktop application provide more accurate and complete UTF-8 encoding validation for open data portal files (CSV, JSON, GeoJSON) by performing full-file analysis without size limitations?"*

**Hypotheses tested:**
- **H1:** UTF encoded files can be reliably identified using automated detection. ✅ Confirmed
- **H2:** chardet confidence scores reliably indicate encoding detection certainty. ✅ Confirmed

---

## Author

**Sanjana Hebha Nandania**  
M.Sc. Web Engineering — TU Chemnitz  
Matrikelnummer: 905639  

**Supervisor:** Prof. Dr. Michael Martin  
**Scientific Supervision:** Florian Hahn, Sara Todorovikj

---

## License

This project is licensed under the MIT License.
