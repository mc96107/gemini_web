import os
import shutil
import asyncio
import logging
from datetime import datetime
from app.core import config

logger = logging.getLogger(__name__)

def global_log(msg, level="INFO"):
    if config.LOG_LEVEL == "NONE":
        return
    if config.LOG_LEVEL == "INFO" and level == "DEBUG":
        return
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{ts}] [{level}] [PDFService] {msg}")
    except: pass

class PDFService:
    def __init__(self):
        self.gs_path = self._find_ghostscript()
        if self.gs_path:
            global_log(f"Ghostscript found at: {self.gs_path}", level="INFO")
        else:
            global_log("Ghostscript not found. PDF compression will be skipped.", level="WARNING")

    def _find_ghostscript(self):
        # Check for common Ghostscript executable names
        for name in ["gswin64c", "gswin32c", "gs"]:
            path = shutil.which(name)
            if path:
                return path
        return None

    def is_gs_available(self):
        return self.gs_path is not None

    async def compress_pdf(self, input_path: str, output_path: str) -> str:
        """
        Compresses a PDF file using Ghostscript.
        Returns the path to the compressed file if successful and smaller,
        otherwise returns the original input_path.
        """
        if not self.is_gs_available():
            return input_path

        if not os.path.exists(input_path):
            global_log(f"Input file not found: {input_path}", level="ERROR")
            return input_path

        try:
            # Ghostscript command for ebook quality (150 dpi)
            # Using list for subprocess to avoid shell injection
            cmd = [
                self.gs_path,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/ebook",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                f"-sOutputFile={output_path}",
                input_path
            ]

            global_log(f"Starting compression: {input_path}", level="INFO")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                global_log(f"Ghostscript failed with return code {process.returncode}: {stderr.decode()}", level="ERROR")
                return input_path

            if not os.path.exists(output_path):
                global_log(f"Ghostscript finished but output file missing: {output_path}", level="ERROR")
                return input_path

            # Compare sizes
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(output_path)
            
            reduction = original_size - compressed_size
            if reduction > 0:
                percent = (reduction / original_size) * 100
                global_log(f"Compression successful: {original_size} -> {compressed_size} ({percent:.1f}% reduction)", level="INFO")
                return output_path
            else:
                global_log(f"Compression did not reduce size ({original_size} -> {compressed_size}). Keeping original.", level="INFO")
                if os.path.exists(output_path):
                    os.remove(output_path)
                return input_path

        except Exception as e:
            global_log(f"Error during PDF compression: {str(e)}", level="ERROR")
            return input_path
