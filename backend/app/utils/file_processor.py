"""Evidence file processing helpers."""

import mimetypes
from pathlib import Path


class FileProcessor:
    """Extract lightweight summaries from uploaded evidence files."""

    TEXT_EXTENSIONS = {".txt", ".csv", ".md", ".json"}
    MAX_TEXT_CHARS = 4000

    def process_image(self, file_path: str) -> str:
        """Return image metadata useful for downstream AI analysis."""
        path = self._require_file(file_path)
        mime_type = mimetypes.guess_type(path.name)[0] or "unknown"
        width, height = self._read_image_dimensions(path)

        parts = [
            f"Image file: {path.name}",
            f"type: {mime_type}",
            f"size: {path.stat().st_size} bytes",
        ]
        if width and height:
            parts.append(f"dimensions: {width}x{height}")
        else:
            parts.append("dimensions: unavailable")
        return "; ".join(parts)

    def process_document(self, file_path: str) -> str:
        """Extract readable text when possible, otherwise return file metadata."""
        path = self._require_file(file_path)
        mime_type = mimetypes.guess_type(path.name)[0] or "unknown"
        size = path.stat().st_size

        if path.suffix.lower() in self.TEXT_EXTENSIONS:
            text = self._read_text_preview(path)
            return (
                f"Document file: {path.name}; type: {mime_type}; "
                f"size: {size} bytes; text preview: {text}"
            )

        if path.suffix.lower() == ".pdf":
            page_count = self._estimate_pdf_pages(path)
            return (
                f"PDF document: {path.name}; type: {mime_type}; "
                f"size: {size} bytes; estimated pages: {page_count}"
            )

        return f"Document file: {path.name}; type: {mime_type}; size: {size} bytes"

    @staticmethod
    def _require_file(file_path: str) -> Path:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        return path

    def _read_text_preview(self, path: Path) -> str:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                text = path.read_text(encoding=encoding, errors="replace")
                break
            except UnicodeError:
                continue
        else:
            text = ""
        text = " ".join(text.split())
        return text[: self.MAX_TEXT_CHARS] if text else "unavailable"

    @staticmethod
    def _estimate_pdf_pages(path: Path) -> int:
        data = path.read_bytes()
        return max(1, data.count(b"/Type /Page"))

    @staticmethod
    def _read_image_dimensions(path: Path) -> tuple[int | None, int | None]:
        data = path.read_bytes()
        if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
            return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
        if data.startswith(b"\xff\xd8"):
            return FileProcessor._read_jpeg_dimensions(data)
        return None, None

    @staticmethod
    def _read_jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in {0xD8, 0xD9}:
                continue
            if index + 2 > len(data):
                break
            segment_length = int.from_bytes(data[index : index + 2], "big")
            if segment_length < 2:
                break
            if marker in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            } and index + 7 <= len(data):
                height = int.from_bytes(data[index + 3 : index + 5], "big")
                width = int.from_bytes(data[index + 5 : index + 7], "big")
                return width, height
            index += segment_length
        return None, None
