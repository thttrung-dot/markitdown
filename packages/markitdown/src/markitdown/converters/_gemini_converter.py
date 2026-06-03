import sys
import os
import base64
import mimetypes
from typing import BinaryIO, Any, Union

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._stream_info import StreamInfo
from .._exceptions import MissingDependencyException

_dependency_exc_info = None
try:
    from openai import OpenAI
except ImportError:
    _dependency_exc_info = sys.exc_info()

ACCEPTED_MIME_TYPE_PREFIXES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
]
ACCEPTED_FILE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


class GeminiConverter(DocumentConverter):
    """
    Converts images to markdown using Google Gemini Vision via the OpenAI-compatible API.
    Requires GOOGLE_API_KEY env var or gemini_api_key kwarg at conversion time.
    """

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()

        if extension in ACCEPTED_FILE_EXTENSIONS:
            return True
        for prefix in ACCEPTED_MIME_TYPE_PREFIXES:
            if mimetype.startswith(prefix):
                return True
        return False

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        if _dependency_exc_info is not None:
            raise MissingDependencyException(
                "GeminiConverter requires the 'openai' package. "
                "Install it with: pip install openai"
            ) from _dependency_exc_info[1].with_traceback(_dependency_exc_info[2])

        api_key = (
            kwargs.get("gemini_api_key")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not api_key:
            return DocumentConverterResult(markdown="")

        model = kwargs.get("gemini_model") or DEFAULT_GEMINI_MODEL
        prompt = kwargs.get("llm_prompt") or "Write a detailed caption for this image."

        content_type = stream_info.mimetype
        if not content_type:
            content_type, _ = mimetypes.guess_type(
                "_dummy" + (stream_info.extension or "")
            )
        if not content_type:
            content_type = "image/jpeg"

        cur_pos = file_stream.tell()
        try:
            image_bytes = file_stream.read()
        except Exception:
            return DocumentConverterResult(markdown="")
        finally:
            file_stream.seek(cur_pos)

        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{content_type};base64,{base64_image}"

        client = OpenAI(api_key=api_key, base_url=GEMINI_OPENAI_BASE_URL)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                    ],
                }
            ],
        )
        description = response.choices[0].message.content or ""
        return DocumentConverterResult(
            markdown="\n# Description:\n" + description.strip() + "\n"
        )
