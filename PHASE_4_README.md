# Phase 4 — Real Document Preprocessing + OCR

## Goal

Replace the Phase 3 preprocessing and OCR mocks with a real document-processing
pipeline.

At the end of this phase, the system should accept a real document image,
improve/normalize it, run OCR, extract structured fields, and return a result
that the existing pipeline can consume without changing its API contract.

---

# 1. Phase 4 Outcome

```text
Raw Document Image
        |
        v
File Validation
        |
        v
Image Quality Analysis
        |
        v
Document Detection
        |
        v
Perspective Correction
        |
        v
Crop + Resize
        |
        v
Denoise / Contrast
        |
        v
Deskew
        |
        v
Preprocessed Document
        |
        v
OCR
        |
        v
Text + Bounding Boxes
        |
        v
Field Extraction / Normalization
        |
        v
Structured OCR Result
```

---

# 2. Technology Stack

## Primary

```text
Python
OpenCV
PaddleOCR
Pydantic
FastAPI
NumPy
```

## Fallback

```text
Tesseract
```

## Optional document helpers

```text
Pillow
python-dateutil
```

---

# 3. Input Data

Primary development data:

```text
data/raw/midv500/
data/raw/midv2019/
```

Additional controlled samples:

```text
data/samples/documents/
```

Required categories:

```text
clear
blurred
rotated
perspective
low_light
low_contrast
cropped
compressed
```

Do not use real sensitive identity documents in development unless the data is
properly authorized and handled according to the applicable requirements.

---

# 4. Preprocessing Pipeline

The preprocessing service is responsible for producing the best possible
document image for downstream OCR and forensic analysis.

## Step 1 — Decode

Load the image safely.

Checks:

```text
file exists
readable
valid image
supported MIME type
maximum size
```

Output:

```json
{
  "width": 1920,
  "height": 1080,
  "channels": 3,
  "format": "jpeg"
}
```

---

## Step 2 — Image Quality

Calculate basic quality indicators.

Initial signals:

```text
resolution
brightness
contrast
blur
noise
exposure
```

Example:

```json
{
  "quality_score": 0.86,
  "blur_score": 0.91,
  "brightness_score": 0.80,
  "contrast_score": 0.84
}
```

These are quality indicators, not authenticity decisions.

---

# 5. Blur Detection

Use a simple baseline such as variance of the Laplacian.

Concept:

```text
Image
  |
  v
Laplacian
  |
  v
Variance
  |
  v
Blur indicator
```

Very low variance suggests the image may be heavily blurred.

The threshold must be calibrated using our dataset.

---

# 6. Brightness / Contrast Normalization

Use OpenCV-based enhancement.

Possible operations:

```text
grayscale
CLAHE
gamma correction
contrast normalization
```

Do not blindly apply every operation to every image.

Create a controlled preprocessing pipeline that chooses operations according to
image quality.

---

# 7. Noise Reduction

Possible baseline:

```text
Gaussian blur
median filtering
bilateral filtering
```

Use conservative processing.

Over-aggressive denoising can destroy character edges and document-security
features.

---

# 8. Document Boundary Detection

The first version should attempt:

```text
grayscale
edge detection
contours
quadrilateral detection
largest plausible document region
```

Concept:

```text
Camera Frame
     |
     v
Edges
     |
     v
Contours
     |
     v
Quadrilateral
     |
     v
Document boundary
```

Output:

```json
{
  "document_detected": true,
  "corners": [
    [x1, y1],
    [x2, y2],
    [x3, y3],
    [x4, y4]
  ]
}
```

---

# 9. Perspective Correction

After detecting the four document corners:

```text
findHomography
       +
warpPerspective
```

Convert the document to a normalized front-facing image.

Example:

```text
angled document
      |
      v
four corners
      |
      v
homography
      |
      v
rectified document
```

This is critical for OCR.

---

# 10. Rotation / Deskew

Detect residual orientation and rotate the image.

Supported baseline:

```text
0°
90°
180°
270°
```

and small-angle deskew where practical.

Output:

```json
{
  "rotation_degrees": 1.8,
  "deskew_applied": true
}
```

---

# 11. Region Cropping

Create optional regions for OCR.

Example:

```text
Full document
 ├── name region
 ├── document number
 ├── date fields
 ├── photo region
 └── MRZ region
```

Important:

The initial implementation should not hard-code coordinates for every identity
document type.

Use a document-type abstraction:

```text
document_type
      |
      v
layout definition
      |
      v
field regions
```

If the type is unknown, run full-document OCR.

---

# 12. Image Resizing

OCR should receive images at a suitable resolution.

Avoid:

```text
tiny image → OCR
```

and:

```text
huge image → unnecessary memory usage
```

Define configurable limits in `config.py`.

Example:

```text
MIN_OCR_WIDTH
MAX_OCR_WIDTH
```

---

# 13. OCR

Use **PaddleOCR as the primary OCR engine**.

Pipeline:

```text
Preprocessed image
      |
      v
PaddleOCR
      |
      ├── text
      ├── confidence
      └── bounding boxes
```

Example low-level output:

```json
{
  "text": "DEMO USER",
  "confidence": 0.98,
  "bbox": [
    [100, 150],
    [400, 150],
    [400, 190],
    [100, 190]
  ]
}
```

---

# 14. OCR Result Normalization

Raw OCR output should be normalized before entering validation.

Operations:

```text
trim whitespace
normalize repeated spaces
normalize line breaks
preserve original OCR text
create normalized text
```

Keep both:

```text
raw_text
normalized_text
```

Never overwrite the raw OCR result.

---

# 15. Field Extraction

Convert OCR text into structured fields.

Initial target fields:

```text
name
document_number
date_of_birth
expiry_date
gender
nationality
address
```

Not every document will have every field.

Therefore:

```json
{
  "name": null,
  "document_number": null,
  "date_of_birth": null,
  "expiry_date": null
}
```

is valid.

Never fabricate missing fields.

---

# 16. Field Extraction Strategy

Use a layered approach.

```text
OCR text
   |
   v
Document type
   |
   ├── known layout → field regions / rules
   |
   └── unknown layout → label/value heuristics
                              |
                              v
                       normalization
```

Do not use the LLM as the primary OCR parser in this phase.

---

# 17. Date Normalization

Convert recognized dates into one internal representation.

Preferred internal form:

```text
YYYY-MM-DD
```

Support multiple OCR formats:

```text
DD/MM/YYYY
DD-MM-YYYY
YYYY-MM-DD
```

Handle ambiguous dates conservatively.

When uncertain:

```text
parse_status = uncertain
```

Do not silently assume.

---

# 18. Document Number Normalization

Document numbers may contain:

```text
letters
numbers
spaces
hyphens
```

Create:

```text
raw_document_number
normalized_document_number
```

Example:

```text
Raw:
AB 12-345 678

Normalized:
AB12345678
```

Normalization rules must be document-type specific later.

---

# 19. MRZ

Phase 4 should prepare the OCR layer for MRZ.

Flow:

```text
Document
   |
   v
OCR
   |
   v
MRZ candidate lines
   |
   v
MRZ parser
   |
   v
fields + checksum validation
```

The full robust MRZ implementation can be extended later.

For now, create an isolated parser interface:

```text
backend/document/mrz_parser.py
```

---

# 20. Tesseract Fallback

Tesseract is a fallback/benchmarking OCR engine.

Use it when:

```text
PaddleOCR fails
PaddleOCR confidence is very low
manual/diagnostic comparison is requested
```

Do not automatically combine outputs from both engines without a defined
fusion strategy.

---

# 21. OCR Confidence

Store confidence at multiple levels:

```text
overall OCR confidence
line confidence
field confidence
```

Example:

```json
{
  "overall_confidence": 0.91,
  "fields": {
    "name": {
      "value": "DEMO USER",
      "confidence": 0.97
    },
    "document_number": {
      "value": "AB123456",
      "confidence": 0.82
    }
  }
}
```

---

# 22. Preprocessing Result Contract

The existing Phase 3 contract must remain compatible.

Example:

```json
{
  "stage": "preprocessing",
  "status": "completed",
  "document_detected": true,
  "image_quality": 0.88,
  "rotation": 1.4,
  "output_path": "...",
  "warnings": []
}
```

Additional fields may be added without breaking existing consumers.

---

# 23. OCR Result Contract

```json
{
  "stage": "ocr",
  "status": "completed",
  "engine": "paddleocr",
  "confidence": 0.92,
  "raw_text": "...",
  "fields": {
    "name": {
      "value": "DEMO USER",
      "confidence": 0.97
    },
    "document_number": {
      "value": "AB123456",
      "confidence": 0.84
    },
    "date_of_birth": {
      "value": "2000-01-01",
      "confidence": 0.89
    },
    "expiry_date": {
      "value": "2030-01-01",
      "confidence": 0.94
    }
  },
  "warnings": []
}
```

---

# 24. Storage

Store:

```text
raw input
processed image
OCR JSON
processing metadata
```

Suggested structure:

```text
data/
├── raw/
│   └── midv500/
│
├── processed/
│   ├── documents/
│   └── ocr/
│
└── runtime/
    └── cases/
        └── CASE-000001/
            ├── input/
            ├── processed/
            └── results/
```

In production, large file storage should move to an object-storage service.

---

# 25. API Integration

The existing endpoint remains:

```http
POST /api/v1/cases/{case_id}/screen
```

The orchestrator now calls:

```text
preprocessing.py
      ↓
ocr_extraction.py
```

while the remaining Phase 3 stages remain mocked.

Therefore Phase 4 creates a **hybrid pipeline**:

```text
REAL
 ├── preprocessing
 └── OCR

MOCK
 ├── tampering
 ├── liveness
 ├── validation
 ├── face verification
 └── anomaly
```

Risk scoring continues to work using the outputs available.

---

# 26. Tests

Create tests for:

## File handling

```text
[ ] valid image
[ ] corrupted image
[ ] oversized image
[ ] unsupported MIME type
```

## Preprocessing

```text
[ ] clear document
[ ] rotated document
[ ] perspective document
[ ] blurry document
[ ] low-light document
[ ] no document detected
```

## OCR

```text
[ ] high-confidence text
[ ] low-confidence text
[ ] missing field
[ ] noisy text
[ ] malformed date
```

## MRZ

```text
[ ] valid checksum
[ ] invalid checksum
[ ] malformed MRZ
```

---

# 27. Evaluation Metrics

Do not judge OCR using only one example.

Track:

```text
Character Error Rate (CER)
Word Error Rate (WER)
Field-level accuracy
Field-level confidence
Document detection rate
Processing latency
```

For structured identity fields, field-level accuracy is particularly important.

Example:

```text
Name accuracy
Document-number accuracy
DOB accuracy
Expiry-date accuracy
```

---

# 28. Dataset Split

Do not evaluate only on images used during development.

Use:

```text
training/development
validation
test
```

For Phase 4, even if no custom OCR model is trained, maintain a fixed
evaluation set.

Example:

```text
data/evaluation/
├── dev/
├── validation/
└── test/
```

Do not tune thresholds against the final test set.

---

# 29. Performance Targets

Initial prototype target:

```text
Preprocessing
   → < 1–2 sec/image

OCR
   → < 2–4 sec/image

Complete document stage
   → acceptable for demo usage
```

These are engineering targets for the prototype, not guaranteed production
benchmarks.

Record actual timings rather than claiming the target was achieved.

---

# 30. Security Requirements

Before OCR processing:

```text
validate upload
generate SHA-256
assign internal file ID
store safely
```

Do not log:

```text
raw document images
full identity numbers
full addresses
secrets
JWTs
encryption keys
```

OCR output containing PII should remain inside the protected application/data
boundary.

Only send the minimum necessary structured information to downstream services.

---

# 31. Ollama in Phase 4

Ollama remains optional.

It can be used later for:

```text
OCR result normalization assistance
ambiguous field explanation
officer-friendly summaries
```

It must not be treated as the authoritative OCR engine.

For document extraction:

```text
image
 ↓
PaddleOCR
 ↓
structured fields
```

not:

```text
image
 ↓
LLM
 ↓
identity fields
```

---

# 32. Phase 4 Folder Structure

Target:

```text
backend/
│
├── document/
│   ├── preprocessing.py
│   ├── quality.py
│   ├── document_detector.py
│   ├── perspective.py
│   ├── normalization.py
│   └── mrz_parser.py
│
├── pipeline/
│   ├── preprocessing.py
│   └── ocr_extraction.py
│
├── services/
│   ├── file_service.py
│   └── ocr_service.py
│
└── utils/
    └── image_utils.py
```

If the existing Phase 3 structure already has these modules, extend them rather
than creating duplicate implementations.

---

# 33. Definition of Done

Phase 4 is complete when:

```text
[ ] Real image preprocessing works
[ ] Blur/quality checks work
[ ] Document boundary detection works on development samples
[ ] Perspective correction works
[ ] Rotation/deskew works
[ ] Processed images are stored
[ ] PaddleOCR is integrated
[ ] OCR text is returned
[ ] OCR bounding boxes are stored
[ ] OCR confidence is stored
[ ] Structured fields are extracted
[ ] Raw and normalized OCR are separated
[ ] Basic MRZ interface exists
[ ] Tesseract fallback exists
[ ] Existing API contract still works
[ ] Phase 3 mock stages still execute
[ ] OCR/preprocessing tests pass
[ ] Evaluation set is established
```

---

# 34. What We Do NOT Build Yet

Do not implement in Phase 4:

```text
NO tampering ML model
NO real liveness model
NO deepfake model
NO face verification model
NO cross-case ML anomaly model
NO Hyperledger network
NO Kafka
NO Kubernetes
```

These remain isolated later phases.

---

# 35. Phase 4 → Phase 5

After Phase 4:

```text
REAL
├── preprocessing
└── OCR

MOCK
├── tampering
├── liveness
├── validation
├── face verification
└── anomaly
```

Phase 5 will focus on:

```text
REAL FACE VERIFICATION
+
REAL LIVENESS / ANTI-SPOOFING
```

Target flow:

```text
Document
   |
   ├── OCR
   |
   └── Document Face
             |
             v
       Face Embedding
             |
             +----------------+
                              |
Live Capture                  |
      |                       |
      v                       |
Liveness / Anti-Spoof         |
      |                       |
      v                       |
Live Face ───────────────→ Face Verification
                              |
                              v
                        Match / Similarity
```

The backend contracts should remain stable while the implementations behind
them become real.
