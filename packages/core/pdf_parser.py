"""
GradeTrace Core — Universal LLM Parser (Gemini 1.5 Flash)

Parses complex PDFs and images using Gemini with vision support,
returning clean JSON with course data.
"""

import io
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

COURSE_VALIDATOR = re.compile(r"^[A-Z]{2,4}\d{3}$", re.IGNORECASE)

SUPPORTED_IMAGE_TYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',
    'gif': 'image/gif',
    'bmp': 'image/bmp',
}


class VisionParser:
    """
    LLM transcript parser using Gemini.
    Extracts course data from PDFs and images.
    """

    @classmethod
    def parse(cls, file_bytes: bytes, gemini_api_key: str = "", filename: str = "", google_creds: str = "") -> list[dict]:
        """
        Parse any supported file (PDF, JPG, PNG, WEBP) into a list of course dicts.
        Uses Gemini with vision to extract tabular data.
        """
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for transcript parsing.")

        try:
            import google.generativeai as genai
            from PIL import Image
        except ImportError as e:
            raise ImportError(f"Required packages not installed: {e}")

        genai.configure(api_key=gemini_api_key)

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        try:
            if ext == "pdf":
                images = cls._pdf_to_images(file_bytes)
            else:
                images = [Image.open(io.BytesIO(file_bytes)).convert("RGB")]
        except Exception as e:
            raise ValueError(f"Could not read image file: {e}")

        if not images:
            raise ValueError("Could not extract any pages from the uploaded file.")

        pages_to_process = cls._select_pages(images)
        logger.info(f"[Gemini] Processing {len(pages_to_process)} page(s)")

        prompt = """You are a transcript parser for North South University (NSU) Bangladesh. 
Extract every course listed in this image. Ignore any watermarks, headers, 
or decorative text. Return ONLY a valid JSON array, no explanation, no markdown 
code blocks. Each object must have exactly these keys:
- course_code (string, e.g. "CSE115")
- course_name (string)
- credits (float)
- grade (string, null if no grade e.g. waiver/transfer courses)
- semester (string, e.g. "Summer")
- year (integer, e.g. 2023)

Example output:
[{"course_code": "CSE115", "course_name": "Programming Language I", "credits": 3, "grade": "A", "semester": "Spring", "year": 2023}]"""

        try:
            model = genai.GenerativeModel('models/gemini-2.5-flash-image')
            contents = [prompt]
            for img in pages_to_process:
                contents.append(img)
            response = model.generate_content(contents)
            
            raw_text = response.text.strip()
            
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            
        except Exception as e:
            error_msg = str(e)
            if "does not support image input" in error_msg or "image" in error_msg.lower():
                raise ValueError(
                    "The Gemini model does not support image input. "
                    "Please use a CSV file or contact support."
                )
            raise ValueError(f"Gemini API error: {error_msg}")

        try:
            parsed_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"[Gemini] Failed to decode JSON: {raw_text[:200]}...")
            raise ValueError("Failed to parse transcript data (invalid format returned by AI).")

        if not isinstance(parsed_data, list):
            raise ValueError("Failed to parse transcript data (did not return an array).")

        processed_records = []
        for item in parsed_data:
            item_lower = {k.lower(): v for k, v in item.items()}

            course_code = str(item_lower.get("course_code", "")).replace(" ", "").upper()
            
            if not COURSE_VALIDATOR.match(course_code):
                continue
                
            name = str(item_lower.get("course_name", ""))
            
            try:
                credit_val = float(item_lower.get("credits", 3.0))
                credits_str = str(int(credit_val)) if credit_val.is_integer() else str(credit_val)
            except (ValueError, TypeError):
                credits_str = "3"
                
            grade_val = item_lower.get("grade")
            grade = str(grade_val) if grade_val and str(grade_val).strip().lower() != "null" else "T"
            
            semester = str(item_lower.get("semester", "")).title()
            year = str(item_lower.get("year", ""))
            sem_str = f"{semester}{year}".strip() if semester else "Unknown"

            processed_records.append({
                "course_code": course_code,
                "course_name": name,
                "credits": credits_str,
                "grade": grade,
                "semester": sem_str,
            })

        seen = {}
        for rec in processed_records:
            key = (rec["course_code"], rec["semester"])
            seen[key] = rec
        records_deduped = list(seen.values())

        if not records_deduped:
            raise ValueError(
                "No course data could be extracted. "
                "Ensure the transcript is clear and in a supported format."
            )

        logger.info(f"[Gemini] Extracted {len(records_deduped)} validated courses.")
        return records_deduped

    @classmethod
    def _pdf_to_images(cls, file_bytes: bytes) -> list:
        try:
            import pypdfium2 as pdfium
        except ImportError:
            try:
                import pymupdf as fitz
            except ImportError:
                raise ValueError("pypdfium2 or pymupdf is required for PDF parsing.")

        images = []
        
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(file_bytes)
            scale = 300 / 72
            for page in pdf:
                bitmap = page.render(scale=scale, rotation=0)
                pil_img = bitmap.to_pil()
                images.append(pil_img.convert("RGB"))
                bitmap.close()
                page.close()
            pdf.close()
        except:
            try:
                import pymupdf as fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                for page in doc:
                    pix = page.get_pixmap(dpi=300)
                    img_data = pix.tobytes("png")
                    from PIL import Image
                    images.append(Image.open(io.BytesIO(img_data)).convert("RGB"))
                doc.close()
            except ImportError:
                raise ValueError("Could not read PDF. Install pypdfium2 or pymupdf.")

        return images

    @classmethod
    def _select_pages(cls, images: list) -> list:
        if len(images) == 1:
            return images
        return images[1:]
