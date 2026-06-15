import io
from PyPDF2 import PdfReader
from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Takes raw PDF bytes, returns all text as a single string.
    Each page is separated by a newline.
    """
    try:
        pdf = PdfReader(io.BytesIO(file_bytes))
        pages = []

        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())

        full_text = "\n\n".join(pages)

        logger.info(
            "pdf_parsed",
            pages=len(pdf.pages),
            characters=len(full_text),
        )

        return full_text

    except Exception as e:
        logger.error("pdf_parse_failed", error=str(e))
        raise ValueError(f"Could not read PDF: {str(e)}")