import os
from pathlib import Path
from typing import Optional


class DocumentParser:
    """Converte PDF, DOCX, PPTX, XLSX → texto markdown via Microsoft MarkItDown."""

    SUPPORTED_EXTS = {".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".html", ".txt"}

    def __init__(self):
        from markitdown import MarkItDown
        self._converter = MarkItDown()

    def parse(self, file_path: str) -> Optional[str]:
        path = Path(file_path)
        if not path.exists():
            print(f"[DocumentParser] Arquivo nao encontrado: {file_path}")
            return None
        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTS:
            print(f"[DocumentParser] Extensao nao suportada: {ext}. Suportadas: {self.SUPPORTED_EXTS}")
            return None
        try:
            result = self._converter.convert(str(path))
            text = result.text_content if hasattr(result, "text_content") else str(result)
            print(f"[DocumentParser] OK: {path.name} -> {len(text)} chars")
            return text
        except Exception as e:
            print(f"[DocumentParser] Erro ao converter {path.name}: {e}")
            return None

    def parse_to_file(self, file_path: str, output_path: str) -> Optional[str]:
        text = self.parse(file_path)
        if text:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[DocumentParser] Salvo em: {output_path}")
            return output_path
        return None
