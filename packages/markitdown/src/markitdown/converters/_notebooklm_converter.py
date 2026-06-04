import re
from typing import BinaryIO, Any
from urllib.parse import urlparse

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._stream_info import StreamInfo
from ._html_converter import HtmlConverter

NOTEBOOKLM_HOST = "notebooklm.google.com"
NOTEBOOKLM_API_BASE = "https://notebooklm.googleapis.com/v1"


class NotebookLMConverter(DocumentConverter):
    """
    Converts Google NotebookLM notebook URLs to markdown.

    For authenticated access set GOOGLE_API_KEY (or pass notebooklm_api_key kwarg)
    to use the NotebookLM API and retrieve full notebook content. Without credentials,
    the converter extracts whatever public metadata is available from the page.
    """

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        url = stream_info.url or ""
        parsed = urlparse(url)
        return parsed.netloc in (NOTEBOOKLM_HOST, f"www.{NOTEBOOKLM_HOST}")

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        url = stream_info.url or ""
        notebook_id = self._extract_notebook_id(url)

        api_key = kwargs.get("notebooklm_api_key") or kwargs.get("gemini_api_key")
        if api_key and notebook_id:
            result = self._fetch_via_api(notebook_id, api_key)
            if result:
                return result

        # Fall back to HTML extraction
        html_result = HtmlConverter().convert(file_stream, stream_info, **kwargs)
        md = html_result.markdown if html_result else ""

        header = f"# NotebookLM Notebook\n\n**URL:** {url}\n\n"
        if notebook_id:
            header += f"**Notebook ID:** `{notebook_id}`\n\n"

        if md.strip():
            return DocumentConverterResult(markdown=header + md)

        return DocumentConverterResult(
            markdown=(
                header
                + "> This notebook requires authentication to view. "
                "Set `GOOGLE_API_KEY` or pass `notebooklm_api_key` to access its content.\n"
            )
        )

    def _extract_notebook_id(self, url: str) -> str:
        # Typical pattern: notebooklm.google.com/notebooklm/<notebook_id>
        match = re.search(r"/notebooklm/([a-zA-Z0-9_-]+)", url)
        return match.group(1) if match else ""

    def _fetch_via_api(self, notebook_id: str, api_key: str):
        """Fetch notebook content via the NotebookLM API."""
        try:
            import requests

            headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
            endpoint = f"{NOTEBOOKLM_API_BASE}/notebooks/{notebook_id}"
            resp = requests.get(endpoint, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            title = data.get("displayName") or data.get("name") or "NotebookLM Notebook"
            md = f"# {title}\n\n"

            if "createTime" in data:
                md += f"**Created:** {data['createTime']}\n\n"
            if "updateTime" in data:
                md += f"**Updated:** {data['updateTime']}\n\n"

            sources = data.get("sources", [])
            if sources:
                md += "## Sources\n\n"
                for src in sources:
                    src_title = src.get("displayName") or src.get("name") or "Untitled"
                    md += f"- {src_title}\n"
                md += "\n"

            notes = data.get("notes", [])
            if notes:
                md += "## Notes\n\n"
                for note in notes:
                    note_title = note.get("title") or "Note"
                    note_body = note.get("content") or note.get("text") or ""
                    md += f"### {note_title}\n\n{note_body}\n\n"

            return DocumentConverterResult(markdown=md, title=title)
        except Exception:
            return None
