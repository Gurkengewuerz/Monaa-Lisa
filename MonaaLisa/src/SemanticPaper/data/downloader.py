"""
Abstract: Downloads the initial dataset and pre-trained ML models from Google Drive.
    Files are stored under DATA_DIR (default /app/data) and are gitignored /
    dockerignored so they are never baked into an image.

    The download uses ``gdown`` which handles Google Drive's virus-scan warning
    for large files automatically.

    Integrity is verified by checking that the downloaded file size is non-zero
    and, for pkl models, that they can be loaded with joblib.
"""

import os
import hashlib
import pickle
import time
from pathlib import Path

import gdown
import joblib

from util.logger import Logger
from config import cfg


logger = Logger("Downloader")

# ----- Google Drive file IDs (configurable via config.ini) -----
DATASET_FILE_ID = cfg.get("semanticpaper", "gdrive_dataset_id", "1icCN9N3CsHxm8n3ccXetdU0yoZymBxuZ")
PCA_MODEL_FILE_ID = cfg.get("semanticpaper", "gdrive_pca_model_id", "1cGSFPfLtn4ccGR_aDkDLpktQKHGzWHD0")
UMAP_MODEL_FILE_ID = cfg.get("semanticpaper", "gdrive_umap_model_id", "1A98RFLD7TE9rT5Eb0pAzS6_eam3DpdXm")

# ----- File names (configurable via config.ini) -----
DATASET_FILENAME = cfg.get("semanticpaper", "dataset_filename", "Full_Dataset_WithCoordsAndEmbeddings.jsonl")
PCA_MODEL_FILENAME = cfg.get("semanticpaper", "pca_model_filename", "pca_model_128d.pkl")
UMAP_MODEL_FILENAME = cfg.get("semanticpaper", "umap_model_filename", "umap_model_2d.pkl")


def _data_dir() -> Path:
    """Resolve the data directory from config or env, ensuring it exists."""
    d = Path(cfg.get("semanticpaper", "data_dir", os.getenv("DATA_DIR", "/app/data")))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _models_dir() -> Path:
    """Resolve the models sub-directory, ensuring it exists."""
    d = _data_dir() / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _gdrive_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?id={file_id}"


def _download(file_id: str, dest: Path, description: str, max_retries: int = 3, retry_delay: int = 60) -> bool:
    """
    Abstract: Downloads a single file from Google Drive, verifying it arrived intact.
              Retries on transient failures (e.g. Google Drive rate limits).
    Args:
    - file_id: Google Drive file ID
    - dest: Local destination path
    - description: Human-readable label for log messages
    - max_retries: Maximum number of retry attempts
    - retry_delay: Seconds to wait between retries (doubles each attempt)
    Returns: bool -> True if download succeeded and file is non-empty
    """
    if dest.exists() and dest.stat().st_size > 0:
        logger.info(f"{description} already exists at {dest} ({dest.stat().st_size:,} bytes), skipping download.")
        return True

    url = _gdrive_url(file_id)
    delay = retry_delay

    for attempt in range(1, max_retries + 1):
        logger.info(f"Downloading {description} from Google Drive (attempt {attempt}/{max_retries})...")
        try:
            output = gdown.download(url, str(dest), quiet=False, fuzzy=True)
            if output is None or not dest.exists():
                logger.error(f"Download failed for {description}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                return False
            size = dest.stat().st_size
            if size == 0:
                logger.error(f"Downloaded file {dest} is empty!")
                dest.unlink(missing_ok=True)
                if attempt < max_retries:
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                return False
            logger.info(f"Downloaded {description}: {size:,} bytes → {dest}")
            return True
        except Exception as e:
            logger.error(f"Error downloading {description}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                return False
    return False


def _verify_pkl(path: Path, label: str, full_load: bool = True) -> bool:
    """
    Abstract: Verifies that a .pkl file is valid.
              When full_load=True, loads the entire object with joblib (suitable for small models).
              When full_load=False, does a lightweight check (file size + pickle header)
              to avoid OOM on very large models like UMAP (6+ GB).
    Args:
    - path: File path
    - label: Human-readable label for log messages
    - full_load: Whether to fully load the model into memory for verification
    Returns: bool
    """
    if not path.exists():
        logger.error(f"{label} file does not exist: {path}")
        return False

    file_size = path.stat().st_size
    if file_size < 1024:
        logger.error(f"{label} file is suspiciously small ({file_size} bytes): {path}")
        return False

    if not full_load:
        # Lightweight verification: check pickle header is valid
        try:
            with open(path, "rb") as f:
                header = f.read(2)
                if header[0:1] != b'\x80':
                    logger.error(f"{label} does not have a valid pickle header.")
                    return False
            logger.info(f"{label} header verified ({file_size / (1024**3):.2f} GB). Full load deferred to pipeline.")
            return True
        except Exception as e:
            logger.error(f"Failed lightweight verification of {label}: {e}")
            return False

    try:
        obj = joblib.load(path)
        if obj is None:
            logger.error(f"{label} loaded as None – file may be corrupt.")
            return False
        logger.info(f"{label} loaded and verified successfully (type: {type(obj).__name__}).")
        return True
    except Exception as e:
        logger.error(f"Failed to verify {label}: {e}")
        return False


# ---- Public API ----


def download_dataset() -> Path | None:
    """
    Abstract: Downloads the full dataset JSONL from Google Drive.
              Uses aggressive retry since large files often hit Google Drive rate limits.
    Returns: Path to the downloaded file, or None on failure.
    """
    dest = _data_dir() / DATASET_FILENAME
    if _download(DATASET_FILE_ID, dest, "Full dataset", max_retries=10, retry_delay=300):
        return dest
    return None


def download_models() -> bool:
    """
    Abstract: Downloads PCA and UMAP pre-trained models from Google Drive and
              verifies they can be loaded with joblib.
    Returns: bool -> True if both models were downloaded and verified.
    """
    models_dir = _models_dir()
    pca_path = models_dir / PCA_MODEL_FILENAME
    umap_path = models_dir / UMAP_MODEL_FILENAME

    pca_ok = _download(PCA_MODEL_FILE_ID, pca_path, "PCA model (768→128D)")
    umap_ok = _download(UMAP_MODEL_FILE_ID, umap_path, "UMAP model (128→2D)")

    if not pca_ok or not umap_ok:
        return False

    if not _verify_pkl(pca_path, "PCA model"):
        return False
    if not _verify_pkl(umap_path, "UMAP model", full_load=False):
        return False

    return True


def ensure_all_downloaded() -> bool:
    """
    Abstract: Ensures dataset + models are downloaded. Returns False if anything fails.
    """
    dataset_path = download_dataset()
    if dataset_path is None:
        return False
    if not download_models():
        return False
    return True


def ensure_models_exist() -> bool:
    """
    Abstract: Ensures only the ML models (PCA + UMAP) are present (no dataset needed).
              Called on non-first runs where the dataset has already been imported.
    Returns: bool
    """
    return download_models()


def get_dataset_path() -> Path:
    return _data_dir() / DATASET_FILENAME


def get_pca_model_path() -> Path:
    return _models_dir() / PCA_MODEL_FILENAME


def get_umap_model_path() -> Path:
    return _models_dir() / UMAP_MODEL_FILENAME


def cleanup_dataset():
    """
    Abstract: Removes the dataset JSONL after successful import to reclaim disk space.
    """
    path = get_dataset_path()
    if path.exists():
        size = path.stat().st_size
        path.unlink()
        logger.info(f"Cleaned up dataset file ({size / (1024**3):.2f} GB freed)")
