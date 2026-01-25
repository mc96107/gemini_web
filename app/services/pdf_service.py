import os
import shutil
import asyncio
import logging
import uuid
import sys
import subprocess
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
        
        Uses synchronous subprocess.run in a thread for maximum reliability on Windows.
        """
        if not self.is_gs_available():
            return input_path

        if not os.path.exists(input_path):
            global_log(f"Input file not found: {input_path}", level="ERROR")
            return input_path

        # Create safe temporary paths to avoid encoding issues with Ghostscript on Windows
        base_dir = os.path.dirname(input_path)
        safe_id = uuid.uuid4().hex
        safe_in_path = os.path.join(base_dir, f"gs_in_{safe_id}.pdf")
        safe_out_path = os.path.join(base_dir, f"gs_out_{safe_id}.pdf")
        
        try:
            # Copy input to safe path
            shutil.copy2(input_path, safe_in_path)
            
            # Ghostscript command for ebook quality (150 dpi)
            cmd = [
                self.gs_path,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/ebook",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                f"-sOutputFile={safe_out_path}",
                safe_in_path
            ]

            global_log(f"Starting compression (sync thread): {input_path}", level="INFO")
            
            # Using asyncio.to_thread to run the synchronous subprocess call
            # This bypasses all Proactor/Selector event loop issues on Windows.
            def run_sync():
                return subprocess.run(cmd, capture_output=True, text=False)

            result = await asyncio.to_thread(run_sync)

            if result.returncode != 0:
                stderr_text = result.stderr.decode(errors='replace')
                global_log(f"Ghostscript failed with return code {result.returncode}: {stderr_text}", level="ERROR")
                return input_path

            if not os.path.exists(safe_out_path):
                global_log(f"Ghostscript finished but output file missing: {safe_out_path}", level="ERROR")
                return input_path

            # Compare sizes
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(safe_out_path)
            
            reduction = original_size - compressed_size
            if reduction > 0:
                percent = (reduction / original_size) * 100
                global_log(f"Compression successful: {original_size} -> {compressed_size} ({percent:.1f}% reduction)", level="INFO")
                
                # Move safe output to final destination
                shutil.move(safe_out_path, output_path)
                return output_path
            else:
                global_log(f"Compression did not reduce size ({original_size} -> {compressed_size}). Keeping original.", level="INFO")
                return input_path

        except Exception as e:
            global_log(f"Error during PDF compression: {repr(e)}", level="ERROR")
            return input_path
        finally:
            # Clean up temp files
            if os.path.exists(safe_in_path):
                try: os.remove(safe_in_path)
                except: pass
            if os.path.exists(safe_out_path):
                try: os.remove(safe_out_path)
                except: pass
