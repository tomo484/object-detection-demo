# Digital Number OCR Reading System

## 📋 Overview

This system is a **high-precision digital number recognition system that combines Azure Computer Vision API with a proprietary multi-stage preprocessing engine**. It automatically extracts numbers from digital display devices (thermometers, stopwatches, calculators, digital clocks, etc.) and normalizes/analyzes them to achieve automated digital reading.

### 🎯 System Features
- **Multi-stage preprocessing**: 4-stage adaptive preprocessing (S0→S1→S2→S3)
- **Early termination**: Efficient processing termination upon success
- **Digital display optimization**: Preprocessing presets optimized for LCD/LED displays
- **ROI fallback**: Region-based processing when overall processing fails
- **Smart normalization**: Context-aware character replacement and normalization
- **Comprehensive analysis**: Detailed failure stage analysis and visualization

### 📊 Current Performance
- **OCR Success Rate**: 76.9% (20 out of 26 images successful)
- **Target Devices**: Thermometers, stopwatches, calculators, digital clocks, etc.
- **Processing Efficiency**: Reduced average number of attempts through early termination

## 🔧 System Architecture

### 📁 File Structure
```
scripts/ocr/
├── run_ocr.py              # Main execution script
├── analyze_ocr_results.py  # Result analysis and visualization
├── utils.py               # Utility functions
└── preprocess/            # Preprocessing engine
    ├── __init__.py        # Module initialization
    ├── engine.py          # Multi-stage preprocessing engine
    ├── operations.py      # Image processing operations
    └── logger.py          # Log management
```

### 🧩 Main Components

#### 1. PreprocessingEngine (`preprocess/engine.py`)
Main engine that controls multi-stage preprocessing

**Key Methods**:
- `process_image()`: Execute 4-stage preprocessing
- `_try_ocr()`: OCR attempt and early termination decision
- `_is_valid_numeric()`: Strict numeric validity check

**Processing Stages**:
- **S0**: Pass-through (OCR on original image)
- **S1**: Basic preset application (invert, clahe, lcd_strong, decimal_enhance)
- **S2**: Scaling × preset combinations (closing-1.5 as highest priority)
- **S3**: ROI extraction fallback processing

#### 2. PreprocessingOperations (`preprocess/operations.py`)
Implementation of image preprocessing operations

**Preset List**:
- `invert`: Color inversion processing
- `clahe`: Adaptive histogram equalization
- `closing`: Morphological closing
- `lcd_strong`: Powerful preprocessing specialized for LCD displays
- `decimal_enhance`: Decimal point detection specialized processing
- `as-is`: No transformation (scaling only)

**ROI Functions**:
- `extract_horizontal_rois()`: Automatic extraction of horizontal regions
- `crop_roi()`: Region cropping
- NMS (Non-Maximum Suppression) for duplicate removal

#### 3. PreprocessingLogger (`preprocess/logger.py`)
Log management and summary generation for attempt results

## 🎮 Usage

### 1. OCR Execution (`run_ocr.py`)

#### Basic Execution
```bash
# Execute OCR with default settings
python scripts/ocr/run_ocr.py

# Specify specific pattern images
python scripts/ocr/run_ocr.py --glob "data_ocr/images/*.jpg"

# Specify output destination
python scripts/ocr/run_ocr.py --outdir "runs/ocr/my_experiment"
```

#### Preprocessing Control
```bash
# Disable preprocessing (conventional processing only)
python scripts/ocr/run_ocr.py --no-preprocessing

# Enable preprocessing (default)
python scripts/ocr/run_ocr.py
```

#### Output Files
- `results.jsonl`: Detailed data of all results (JSONL format)
- `numeric_lines.tsv`: Numeric extraction results (TSV format)
- `details/`: Detailed JSON for each image (readability focused)

### 2. Result Analysis (`analyze_ocr_results.py`)

#### Basic Analysis
```bash
# Execute basic analysis
python scripts/ocr/analyze_ocr_results.py --results-dir runs/ocr/20250816-160044

# Custom output destination
python scripts/ocr/analyze_ocr_results.py --results-dir runs/ocr/20250816-160044 --output-dir analysis_custom

# Test regular expressions
python scripts/ocr/analyze_ocr_results.py --results-dir runs/ocr/20250816-160044 --test-regex "^[0-9:.,]+$"
```

#### Output Files
- `analysis_summary.json`: Comprehensive analysis results
- `failed_cases.json`: Details of failed cases
- `visualizations/`: Visualization images with bounding boxes

## 🔍 Number Extraction Process

### 1. OCR Processing
Execute text detection using Azure Computer Vision API:
```python
def analyze_image_bytes(client: ImageAnalysisClient, img_bytes: bytes):
    result = client.analyze(image_data=img_bytes, visual_features=[VisualFeatures.READ])
    # Generate structured data including bounding polygons and confidence information
```

### 2. Numeric Pattern Recognition
Extract numeric candidates using regular expressions:
```python
NUMERIC_RE = re.compile(r"^(?!.*[IO]/[IO])(?![IO]+$)(?![A-Z]+$)[0-9OIl:.,+\-_/\\()\s°C°F%℃]+$")
```

### 3. Smart Normalization
Correct OCR misrecognitions based on context:
```python
def smart_normalize(text: str) -> str:
    """Simple smart normalization"""
    # Return non-numeric patterns as-is
    non_numeric = ['I/O', 'O/I', 'ON', 'OFF', 'IO', 'OI']
    if text.upper() in non_numeric:
        return text
    
    # Preprocessing cleanup for time displays
    # Convert ". 1 1:38" → "11:38"
    cleaned = text
    cleaned = re.sub(r'^[.\-\s]+', '', cleaned)
    cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', cleaned)
    
    # Character replacement only when digits are present
    if re.search(r'\d', cleaned):
        cleaned = cleaned.replace("O", "0").replace("I", "1").replace("l", "1")
    
    return cleaned
```

### 4. Validity Verification
Strictly check the validity of extracted numbers:
```python
def _is_valid_numeric(self, numeric_results):
    """Simple numeric validity check"""
    if not numeric_results:
        return False
    
    text = numeric_results[0]["normalized"].strip()
    
    # Exclusion patterns (problematic ones)
    exclude_patterns = [
        r'^\.',                         # .11:34
        r'^0:\d{2}$',                  # 0:03  
        r'^\d{1,2}\.\d{3,}$',          # 10.004, 10.0045 (3+ decimal places)
        r'^\d+\.\s+\d+$',              # 10. 0045 (decimal with space)
        r'^0{3,}$',                    # 000
        r'^\d{1}[°℃°F%]$',            # 7℃
        r'^[°℃°FC%]+$',                # C, ℃ only
        r'^\([IO]/[IO]\)$',            # (I/O), (O/I)
    ]
    
    if any(re.match(p, text) for p in exclude_patterns):
        return False
    
    # Basically OK if 2+ digits are present
    digit_count = sum(1 for c in text if c.isdigit())
    return digit_count >= 2
```

## 📈 Analysis and Visualization Features

### Failure Stage Analysis
The system provides 4-stage failure classification:
1. **detection_failed**: OCR completely fails to detect text
2. **no_numeric_content**: No lines containing digits found
3. **regex_too_strict**: Regular expression filter too restrictive
4. **success**: Numeric extraction successful

### Visualization Features
- **Bounding box drawing**: Display detected text regions in blue
- **Numeric region highlighting**: Highlight regions recognized as numeric in green
- **Analysis result display**: Show failure stage, number of detected lines, and number of numeric candidates on image

## 🛠️ Technical Specifications

### Dependencies
- **OCR**: Azure Computer Vision API
- **Image Processing**: OpenCV (cv2)
- **Numerical Processing**: NumPy
- **Data Formats**: JSON, JSONL, TSV

### Environment Setup
```bash
# Environment variable setup (.env file)
VISION_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
VISION_KEY=your-api-key
```

### Performance Optimization
- **Image size limitation**: Automatic resize when exceeding 20MB
- **Early termination**: Immediate stop upon success
- **ROI fallback**: Region-based processing when overall processing fails

## 📊 Experimental Results

### Success Rate Statistics
- **Total Images**: 26 images (test dataset)
- **Successful**: 20 images
- **Success Rate**: 76.9%

### Device-specific Performance
- Thermometers: High accuracy (optimized for LCD displays)
- Stopwatches: Good (supports time format normalization)
- Calculators: Good (optimized for digit recognition)
- Digital clocks: Good (supports time patterns)

### Preprocessing Effects
- **S0 (Original image)**: Basic success rate
- **S1 (Basic presets)**: Improvement for LCD/LED displays
- **S2 (Scale × presets)**: Improvement for small characters/digits
- **S3 (ROI processing)**: Numeric extraction from complex backgrounds

## 🔧 Customization

### Regular Expression Pattern Adjustment
```python
# More strict pattern
NUMERIC_RE = re.compile(r"^[0-9:.,]+$")

# More lenient pattern
NUMERIC_RE = re.compile(r"^[0-9OIl:.,+\-_/\\()\s°C°F%℃A-Z]+$")
```

### Preprocessing Parameter Adjustment
```python
# Inside PreprocessingOperations class
def _lcd_strong(self, image):
    # Gamma correction value adjustment
    gamma = 0.4  # For darker displays: 0.3, for brighter displays: 0.6
    
    # CLAHE intensity adjustment
    clahe_strong = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4, 4))
```

### ROI Detection Parameter Adjustment
```python
def extract_horizontal_rois(self, image: np.ndarray, k: int = 3):
    # Aspect ratio threshold adjustment
    if aspect_ratio > 1.5 and area > (w * h * 0.005):  # 1.5 → 2.0 (more horizontal)
        
    # Minimum area threshold adjustment
    if aspect_ratio > 1.5 and area > (w * h * 0.01):   # 0.005 → 0.01 (larger regions)
```

## 🐛 Troubleshooting

### Common Issues

1. **Azure API Authentication Error**
   ```
   Solution: Check VISION_ENDPOINT and VISION_KEY in .env file
   ```

2. **Image Loading Error**
   ```
   Solution: Check image path and format (jpg, png)
   ```

3. **Low Number Recognition Rate**
   ```
   Solution: Adjust regular expression pattern with --test-regex option
   ```

4. **Preprocessing Not Effective**
   ```
   Solution: Adjust PreprocessingOperations parameters
   ```

### Debugging Methods

1. **Check Detailed Logs**
   ```bash
   python scripts/ocr/run_ocr.py --verbose
   ```

2. **Check via Visualization**
   ```bash
   python scripts/ocr/analyze_ocr_results.py --results-dir runs/ocr/latest
   # Check images in visualizations/ folder
   ```

3. **Analyze Failed Cases**
   ```bash
   # Check failed_cases.json to analyze failure patterns
   ```

## 📝 Future Improvements

### Short-term Improvements
- [ ] Support for more diverse digital display formats
- [ ] Automatic optimization of preprocessing parameters
- [ ] Result filtering using confidence scores

### Long-term Improvements
- [ ] Integration of deep learning-based number recognition
- [ ] Real-time processing optimization
- [ ] Multi-language support (non-alphanumeric characters)

## 📄 License

This project is provided under the CC BY 4.0 license. 