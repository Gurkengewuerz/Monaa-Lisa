import os
import sys
from pathlib import Path

from util.logger import Logger

logger = Logger("Importer")

"""
Abstract: Imports the JSONL dataset into the Postgres database.
Args:
- dataset_path: Path to the .jsonl file
- batch_size: Number of papers per batch INSERT
Returns: bool -> True if import completed successfully
"""
def run_import(dataset_path: str | Path, batch_size: int = 5000) -> bool:
    
    dataset_path = Path(dataset_path)
    # Prüfe ob Dataset Datei überhaupt existiert
    if not dataset_path.exists():
        logger.error(f"Dataset file not found: {dataset_path}")
        return False

    logger.info(f"Starting dataset import from {dataset_path} (batch_size={batch_size})...")
    logger.info(f"File size: {dataset_path.stat().st_size / (1024**3):.2f} GB")

    try:
        # aus dem Subfolder "SemanticPaper/data" in "MonaaLisa" root imports zu machen
        project_root = Path(__file__).resolve().parents[4]  
        sys.path.insert(0, str(project_root))

        # Importiere die Funktion aus import_dataset.py im Root
        from import_dataset import import_dataset
        import_dataset(str(dataset_path), batch_size)
        logger.info("Dataset import completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Dataset import failed: {e}")
        return False
