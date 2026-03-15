"""
Vision Agent — Uses Google Gemini Vision to analyse images.
Capabilities:
  1. Describe an image in Arabic
  2. Extract text from an image (OCR)
  3. Extract structured data from tables / invoices
"""

import base64
import json
import google.generativeai as genai
from typing import Optional


# ═══════════════════════ VisionAgent ═══════════════════════
class VisionAgent:
    """
    Wrapper around Gemini's multimodal capabilities for image analysis.
    """

    SUPPORTED_MODES = {
        "describe":   "وصف الصورة",
        "ocr":        "استخراج النص (OCR)",
        "structured": "استخراج بيانات منظمة",
    }

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        """
        Initialise the agent with a Gemini API key.

        Args:
            api_key: Google AI Studio / Gemini API key.
            model_name: The generative model to use (must support vision).
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    # ───────── internal helper ─────────

    @staticmethod
    def _image_to_part(image_bytes: bytes, mime_type: str = "image/png") -> dict:
        """Convert raw image bytes into the dict format Gemini expects."""
        return {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }
        }

    def _generate(self, prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Send a prompt + image to Gemini and return the text response."""
        image_part = self._image_to_part(image_bytes, mime_type)
        response = self.model.generate_content([prompt, image_part])
        return response.text.strip()

    # ───────── public API ─────────

    def describe_image(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """
        Return a rich Arabic description of the image.
        """
        prompt = (
            "أنت محلل صور محترف. قم بوصف هذه الصورة بالتفصيل باللغة العربية.\n"
            "اذكر:\n"
            "1. المحتوى الرئيسي للصورة\n"
            "2. الألوان والتفاصيل البصرية\n"
            "3. أي نصوص أو أرقام ظاهرة\n"
            "4. السياق العام والمعنى\n"
            "اكتب الوصف بأسلوب واضح ومنظم."
        )
        return self._generate(prompt, image_bytes, mime_type)

    def extract_text(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """
        OCR — extract every piece of readable text from the image.
        """
        prompt = (
            "أنت نظام OCR متقدم. استخرج كل النصوص الموجودة في هذه الصورة.\n"
            "- حافظ على الترتيب الأصلي للنصوص.\n"
            "- اذكر اللغة المستخدمة (عربي / إنجليزي / غيرها).\n"
            "- لو النص غير واضح، اكتب [غير واضح].\n"
            "اكتب النصوص المستخرجة فقط بدون شرح إضافي."
        )
        return self._generate(prompt, image_bytes, mime_type)

    def extract_structured_data(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """
        Extract structured data (tables, invoices, forms) and return
        a JSON-formatted string with the parsed fields.
        """
        prompt = (
            "أنت محلل بيانات محترف. "
            "استخرج البيانات المنظمة من هذه الصورة (جدول، فاتورة، نموذج، إلخ).\n"
            "أرجع النتيجة بتنسيق JSON واضح باللغة العربية.\n"
            "- لو الصورة فيها جدول: أرجعه كـ list of objects.\n"
            "- لو الصورة فاتورة: أرجع الحقول (اسم المنتج، الكمية، السعر، الإجمالي).\n"
            "- لو الصورة نموذج: أرجع الحقول وقيمها.\n"
            "أرجع JSON فقط بدون أي شرح إضافي."
        )
        raw = self._generate(prompt, image_bytes, mime_type)

        # Try to clean markdown code fences if Gemini wraps them
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        # Validate it's proper JSON; if not, return as-is
        try:
            parsed = json.loads(cleaned)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return cleaned

    def analyze(self, image_bytes: bytes, mode: str = "describe", mime_type: str = "image/png") -> str:
        """
        Convenience dispatcher.

        Args:
            image_bytes: Raw image bytes.
            mode: One of 'describe', 'ocr', 'structured'.
            mime_type: MIME type of the image.
        """
        if mode == "ocr":
            return self.extract_text(image_bytes, mime_type)
        elif mode == "structured":
            return self.extract_structured_data(image_bytes, mime_type)
        else:
            return self.describe_image(image_bytes, mime_type)
