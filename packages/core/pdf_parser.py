"""
GradeTrace Core — Universal LLM Parser (Gemini 2.5 Flash Lite)

Parses complex PDFs and images using Gemini with vision support,
returning clean JSON with course data.
"""

import gc
import difflib
import io
import json
import logging
import re
from typing import Optional

import google.generativeai as genai
from PIL import Image
from packages.core.course_catalog import ALL_COURSES

logger = logging.getLogger(__name__)

COURSE_VALIDATOR = re.compile(r"^[A-Z]{2,4}\d{3}$", re.IGNORECASE)
VALID_GRADES = {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F", "W", "I", "T"}

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
Extract every COURSE ROW exactly as printed in the transcript table.
Do not hallucinate or rewrite course names. Ignore watermarks and headers.

Output rules:
1) Return ONLY a valid JSON array (no markdown, no explanation)
2) Keep one object per course row
3) Use exactly these keys:
   - course_code (string, e.g. "CSE115")
   - course_name (string)
   - credits (float)
   - grade (string, null if no grade)
   - semester (string, one of Spring/Summer/Fall)
   - year (integer)

If a row is unreadable, skip that row. Do not invent data.

Example:
[{"course_code": "CSE115", "course_name": "Programming Language I", "credits": 3, "grade": "A", "semester": "Spring", "year": 2023}]"""

        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
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

            course_code = cls._normalize_course_code(str(item_lower.get("course_code", "")))
            name = str(item_lower.get("course_name", "")).strip()

            inferred_from_name = cls._infer_code_from_name(name)
            if (not course_code) and inferred_from_name:
                course_code = inferred_from_name

            if not course_code or (not COURSE_VALIDATOR.match(course_code)):
                continue
            
            try:
                credit_val = float(item_lower.get("credits", 3.0))
            except (ValueError, TypeError):
                credit_val = float(ALL_COURSES.get(course_code, ("", 3))[1])

            expected_credits = float(ALL_COURSES.get(course_code, ("", credit_val))[1])
            if course_code in ALL_COURSES and abs(credit_val - expected_credits) > 2:
                credit_val = expected_credits
            credits_str = str(int(credit_val)) if float(credit_val).is_integer() else str(credit_val)
                
            grade_val = item_lower.get("grade")
            grade = cls._normalize_grade(grade_val)

            semester = str(item_lower.get("semester", "")).strip()
            year = str(item_lower.get("year", "")).strip()
            sem_str = cls._normalize_semester(semester, year)

            canonical_name = ALL_COURSES.get(course_code, (name, 0))[0]

            if course_code in ALL_COURSES and name:
                inferred_code_strict = cls._infer_code_from_name(name, threshold=0.9)
                if inferred_code_strict and inferred_code_strict != course_code:
                    inferred_name = ALL_COURSES.get(inferred_code_strict, ("", 0))[0]
                    name_norm = cls._normalize_title(name)
                    current_norm = cls._normalize_title(canonical_name)
                    inferred_norm = cls._normalize_title(inferred_name)

                    sim_current = difflib.SequenceMatcher(None, name_norm, current_norm).ratio()
                    sim_inferred = difflib.SequenceMatcher(None, name_norm, inferred_norm).ratio()

                    mismatch_current = cls._has_semantic_mismatch(name_norm, current_norm)
                    mismatch_inferred = cls._has_semantic_mismatch(name_norm, inferred_norm)

                    if (
                        (mismatch_current and not mismatch_inferred and sim_inferred >= 0.86) or
                        (sim_inferred >= 0.92 and sim_inferred - sim_current >= 0.08)
                    ):
                        course_code = inferred_code_strict
                        canonical_name = inferred_name

            processed_records.append({
                "course_code": course_code,
                "course_name": name or canonical_name,
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
        
        del images
        gc.collect()
        
        return records_deduped

    @staticmethod
    def _normalize_title(text: str) -> str:
        t = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()
        t = re.sub(r"\s+", " ", t)
        return t

    @classmethod
    def _infer_code_from_name(cls, course_name: str, threshold: float = 0.86) -> str:
        if not course_name:
            return ""
        target = cls._normalize_title(course_name)
        if not target:
            return ""

        best_code = ""
        best_ratio = 0.0
        for code, (name, _cr) in ALL_COURSES.items():
            ratio = difflib.SequenceMatcher(None, target, cls._normalize_title(name)).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_code = code
        return best_code if best_ratio >= threshold else ""

    @staticmethod
    def _has_semantic_mismatch(a: str, b: str) -> bool:
        opposite_pairs = [
            ("micro", "macro"),
            ("financial", "managerial"),
            ("biology", "business"),
            ("communication", "composition"),
            ("intermediate", "international"),
        ]
        for x, y in opposite_pairs:
            if (x in a and y in b) or (y in a and x in b):
                return True
        return False

    @staticmethod
    def _normalize_course_code(raw_code: str) -> str:
        code = re.sub(r"\s+", "", (raw_code or "").upper())
        if not code:
            return ""
        if not re.search(r"\d", code):
            return ""
        code = code.replace("O", "0") if re.search(r"[A-Z]{2,4}O\d{2}$", code) else code
        code = code.replace("I", "1") if re.search(r"[A-Z]{2,4}\dI\d$", code) else code
        return code

    @staticmethod
    def _normalize_grade(grade_val: object) -> str:
        if grade_val is None:
            return "T"
        g = str(grade_val).strip().upper().replace(" ", "")
        if not g or g == "NULL":
            return "T"
        grade_fixes = {
            "A+": "A",
            "B0": "B",
            "C0": "C",
            "0": "O",
        }
        g = grade_fixes.get(g, g)
        return g if g in VALID_GRADES else "T"

    @staticmethod
    def _normalize_semester(semester: str, year: str) -> str:
        s = (semester or "").strip().title()
        if s.startswith("Spr"):
            s = "Spring"
        elif s.startswith("Sum"):
            s = "Summer"
        elif s.startswith("Fal"):
            s = "Fall"

        y = (year or "").strip()
        if len(y) == 2 and y.isdigit():
            y = f"20{y}"
        if len(y) == 4 and y.isdigit() and s in {"Spring", "Summer", "Fall"}:
            return f"{s}{y}"
        return "Unknown"

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
