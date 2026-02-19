"""
17-February-2026 - Basti
Abstract: Thin wrapper around the standalone import_dataset module that makes it
    callable from within the SemanticPaper application (main.py).

    On first run the downloader fetches the JSONL dataset, this module imports it
    into Postgres via the high-performance COPY-based importer, and optionally
    cleans up the raw file afterwards.
"""

import os
import sys
from pathlib import Path

from util.logger import Logger

logger = Logger("Importer")


def run_import(dataset_path: str | Path, batch_size: int = 5000) -> bool:
    """
    17-February-2026 - Basti
    Abstract: Imports the JSONL dataset into the Postgres database.
    Args:
    - dataset_path: Path to the .jsonl file
    - batch_size: Number of papers per batch INSERT
    Returns: bool -> True if import completed successfully
    """
    dataset_path = Path(dataset_path)
    if not dataset_path.exists():
        logger.error(f"Dataset file not found: {dataset_path}")
        return False

    logger.info(f"Starting dataset import from {dataset_path} (batch_size={batch_size})...")
    logger.info(f"File size: {dataset_path.stat().st_size / (1024**3):.2f} GB")

    try:
        # Add project root to path so import_dataset can be found
        project_root = Path(__file__).resolve().parents[4]  # MonaaLisa/src/SemanticPaper/data -> root
        sys.path.insert(0, str(project_root))

        from import_dataset import import_dataset
        import_dataset(str(dataset_path), batch_size)
        logger.info("Dataset import completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Dataset import failed: {e}")
        return False
