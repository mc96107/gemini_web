import os
import pypandoc
import logging
import pandas as pd
from app.core.config import UPLOAD_DIR

logger = logging.getLogger(__name__)

class FileConversionService:
    def __init__(self):
        # Verify pandoc is available for docx
        try:
            pypandoc.get_pandoc_version()
        except OSError:
            logger.error("Pandoc not found. Please ensure it is installed on the system.")

    def convert_to_markdown(self, file_path: str) -> str:
        """
        Converts a .docx or .xlsx file to markdown.
        Returns the path to the converted .md file.
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in [".docx", ".xlsx"]:
            raise ValueError(f"Unsupported file extension: {file_ext}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        output_path = os.path.splitext(file_path)[0] + ".md"
        
        try:
            if file_ext == ".docx":
                # For docx, we convert to gfm (GitHub Flavored Markdown)
                # We explicitly do NOT use --extract-media to ensure images are not kept.
                pypandoc.convert_file(
                    file_path, 
                    'gfm', 
                    outputfile=output_path,
                    extra_args=['--wrap=none']
                )
            elif file_ext == ".xlsx":
                # For xlsx, use pandas to read all sheets and convert to markdown tables
                all_sheets = pd.read_excel(file_path, sheet_name=None)
                md_content = []
                for sheet_name, df in all_sheets.items():
                    md_content.append(f"## Sheet: {sheet_name}\n")
                    # Use to_markdown() which requires 'tabulate' but we can also use a simple conversion
                    # Actually to_markdown() is very good if tabulate is installed.
                    # Let's check if we can use it or fall back.
                    try:
                        md_content.append(df.to_markdown(index=False))
                    except ImportError:
                        # Simple fallback to CSV-like table if tabulate is missing
                        md_content.append(df.to_string(index=False))
                    md_content.append("\n\n")
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(md_content))
            
            return output_path
        except Exception as e:
            logger.error(f"Error converting file {file_path} to markdown: {e}")
            raise RuntimeError(f"Conversion failed: {e}")