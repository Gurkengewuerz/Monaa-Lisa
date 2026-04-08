from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# All patches target the module where the names are looked up
MOD = "pipeline.data.downloader"


@pytest.fixture(autouse=True)
def patch_globals():
    """
    Patches module-level globals so no real config / mirrors.json is needed.
    Every test gets a clean, predictable state.
    """
    fake_settings = {
        "max_retries": 2,
        "retry_delay_seconds": 0,  # no waiting in tests, we just want to trigger the retry logic immediately
        "timeout_seconds": 10,
        "chunk_size_bytes": 1024,
    }
    fake_files = {
        "dataset": {
            "filename": "dataset.jsonl",
            "description": "Test dataset",
            "mirrors": ["https://mirror1.example.com/dataset.jsonl"],
            "gdrive_fallback": {"file_id": "GDRIVE_DATASET_ID"},
        },
        "pca_model": {
            "filename": "pca.pkl",
            "description": "PCA model",
            "mirrors": ["https://mirror1.example.com/pca.pkl"],
            "gdrive_fallback": {"file_id": "GDRIVE_PCA_ID"},
        },
        "umap_model": {
            "filename": "umap.pkl",
            "description": "UMAP model",
            "mirrors": ["https://mirror1.example.com/umap.pkl"],
            "gdrive_fallback": {"file_id": "GDRIVE_UMAP_ID"},
        },
    }
    with (
        patch(f"{MOD}.DOWNLOAD_SETTINGS", fake_settings),
        patch(f"{MOD}.FILES_CONFIG", fake_files),
        patch(f"{MOD}.logger"),
    ):
        yield


@pytest.fixture
def tmp_dest(tmp_path):
    """Provides a temporary destination path for downloads."""
    return tmp_path / "test_file.bin"


class TestDownloadHttp:
    """Tests the conditional logic in _download_http()."""

    @patch(f"{MOD}.requests.get")
    def test_returns_true_on_successful_download(self, mock_get, tmp_dest):
        """
        Tests the successful path.
        chunks are written, file is non-empty → returns True.
        """
        from pipeline.data.downloader import _download_http

        # We mock requests.get to return a response with content-length and iter_content.
        mock_response = Mock()
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content.return_value = [b"x" * 100]
        mock_response.raise_for_status = Mock()
        mock_get.return_value.__enter__ = Mock(return_value=mock_response)
        mock_get.return_value = mock_response
        # When _download_http calls requests.get, it will get our mock_response,
        # which simulates a successful download of 100 bytes.
        result = _download_http("https://example.com/f", tmp_dest, "test")

        # We expect the function to write the content to tmp_dest and return True.
        assert result is True
        assert tmp_dest.exists()
        assert tmp_dest.stat().st_size == 100

    @patch(f"{MOD}.requests.get")
    def test_returns_false_on_request_exception(self, mock_get, tmp_dest):
        """
        Tests the branch: except requests.exceptions.RequestException

        Network errors must not crash; the function should return False
        and clean up any partial file.
        """
        import requests as real_requests

        from pipeline.data.downloader import _download_http

        # Simulate a network error like a timeout. This should trigger the exception handling in _download_http.
        mock_get.side_effect = real_requests.exceptions.ConnectionError("timeout")

        result = _download_http("https://example.com/f", tmp_dest, "test")

        assert result is False
        assert not tmp_dest.exists()

    @patch(f"{MOD}.requests.get")
    def test_returns_false_when_downloaded_file_is_empty(self, mock_get, tmp_dest):
        """
        Tests the branch: if dest.exists() and dest.stat().st_size > 0 → else

        If the server returns a 200 but with no body content, the file is 0 bytes.
        We must detect this and return False.
        """
        from pipeline.data.downloader import _download_http

        mock_response = Mock()
        mock_response.headers = {"content-length": "0"}
        mock_response.iter_content.return_value = []  # no chunks
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = _download_http("https://example.com/f", tmp_dest, "test")
        assert result is False

    @patch(f"{MOD}.requests.get")
    def test_returns_false_on_unexpected_exception(self, mock_get, tmp_dest):
        """
        Tests the branch: except Exception as e (generic fallback)

        Unexpected errors (e.g. disk full, permission error) should be caught and logged without crashing.
        """
        from pipeline.data.downloader import _download_http

        mock_get.side_effect = OSError("disk full")

        result = _download_http("https://example.com/f", tmp_dest, "test")

        # we expect the function to catch the OSError, log an error message, and return False without crashing.
        import pipeline.data.downloader as dl_mod

        assert result is False
        dl_mod.logger.error.assert_called_once()
        args, _ = dl_mod.logger.error.call_args
        assert "disk full" in str(args)


# ─── _download_gdrive ───────────────────────────────────────────────────


class TestDownloadGdrive:
    """Tests the retry logic and edge cases in _download_gdrive()."""

    @patch(f"{MOD}.gdown.download")
    def test_returns_true_on_successful_download(self, mock_gdown, tmp_dest):
        """
        Tests happy path: gdown returns a path, file exists and is non-empty.
        """
        from pipeline.data.downloader import _download_gdrive

        def fake_download(url, dest_str, **kwargs):
            Path(dest_str).write_bytes(b"model-data")
            return dest_str

        mock_gdown.side_effect = fake_download

        result = _download_gdrive("FAKE_ID", tmp_dest, "test model", max_retries=1, retry_delay=0)

        assert result is True
        assert tmp_dest.exists()

    @patch(f"{MOD}.gdown.download")
    def test_returns_false_when_gdown_returns_none(self, mock_gdown, tmp_dest):
        """
        Tests the branch: if output is None or not dest.exists()

        gdown returns None when the download link is invalid or access is denied.
        Must return False after exhausting retries.
        """
        from pipeline.data.downloader import _download_gdrive

        mock_gdown.return_value = None
        # We set max_retries=2 and retry_delay=0 to trigger the retry logic immediately without waiting.
        result = _download_gdrive("FAKE_ID", tmp_dest, "test", max_retries=2, retry_delay=0)

        assert result is False
        assert mock_gdown.call_count == 2  # retried

    @patch(f"{MOD}.gdown.download")
    def test_returns_false_when_downloaded_file_is_empty(self, mock_gdown, tmp_dest):
        """
        Tests the branch: if size == 0

        gdown may create a file but with 0 bytes (e.g. HTML error page was not written).
        The function must detect this and retry, then return False.
        """
        from pipeline.data.downloader import _download_gdrive

        def fake_download(url, dest_str, **kwargs):
            Path(dest_str).write_bytes(b"")  # empty file
            return dest_str

        mock_gdown.side_effect = fake_download

        result = _download_gdrive("FAKE_ID", tmp_dest, "test", max_retries=2, retry_delay=0)
        import pipeline.data.downloader as dl_mod

        assert result is False
        # We expect the function to log an error about the empty file after retries are exhausted.
        # Since the function logs multiple types of errors,
        # we check that one of the calls contains "is empty".
        args, _ = dl_mod.logger.error.call_args
        assert "is empty" in str(args)

    @patch(f"{MOD}.gdown.download")
    def test_returns_false_on_exception_after_retries(self, mock_gdown, tmp_dest):
        """
        Tests the branch: except Exception as e (with retry exhaustion)

        Transient errors should be retried up to max_retries before giving up.
        """
        from pipeline.data.downloader import _download_gdrive

        mock_gdown.side_effect = Exception("rate limited")
        # We set max_retries=3 to ensure the function retries 3 times before returning False
        result = _download_gdrive("FAKE_ID", tmp_dest, "test", max_retries=3, retry_delay=0)

        assert result is False
        # The function should have attempted the download 3 times (initial try + 2 retries) before giving up.
        assert mock_gdown.call_count == 3

    @patch(f"{MOD}.gdown.download")
    def test_succeeds_on_second_attempt(self, mock_gdown, tmp_dest):
        """
        Tests that a transient failure followed by success returns True.
        Ensures the retry loop doesn't short-circuit on first failure.
        """
        from pipeline.data.downloader import _download_gdrive

        # We use a mutable object (list) to track call count inside the side_effect function.
        # Funfact: I learned this at my day job while keeping track of linked entities over a non-linked function loop.
        call_count = [0]

        def fake_download(url, dest_str, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("transient error")
            Path(dest_str).write_bytes(b"valid-data")
            return dest_str

        mock_gdown.side_effect = fake_download

        result = _download_gdrive("FAKE_ID", tmp_dest, "test", max_retries=3, retry_delay=0)
        # should succeed on the second attempt, so total call count should be 2
        assert mock_gdown.call_count == 2
        assert result is True


class TestDownloadFile:
    """Tests the mirror-first strategy and fallback logic in _download_file()."""

    @patch(f"{MOD}._download_http")
    def test_skips_download_when_file_already_exists(self, mock_http, tmp_path):
        """
        Tests the branch: if dest.exists() and dest.stat().st_size > 0 → return True

        When the file is already present, no download should be attempted.
        """
        from pipeline.data.downloader import _download_file

        dest = tmp_path / "dataset.jsonl"
        dest.write_bytes(b"existing data")

        result = _download_file("dataset", dest)

        assert result is True
        # Since the file already exists, _download_http should not be called at all.
        mock_http.assert_not_called()

    @patch(f"{MOD}._download_http", return_value=True)
    def test_returns_true_when_first_mirror_succeeds(self, mock_http, tmp_dest):
        """
        Tests happy path: first HTTP mirror works → returns True immediately.
        """
        from pipeline.data.downloader import _download_file

        result = _download_file("dataset", tmp_dest)

        assert result is True
        # Since the first mirror succeeds, _download_http should be called exactly once.
        assert mock_http.call_count == 1

    # Mock _download_http to fail, but _download_gdrive to succeed, to test the fallback logic.
    @patch(f"{MOD}._download_gdrive", return_value=True)
    @patch(f"{MOD}._download_http", return_value=False)
    def test_falls_back_to_gdrive_when_all_mirrors_fail(self, mock_http, mock_gdrive, tmp_dest):
        """
        Tests the branch: all mirrors fail → fall back to Google Drive

        If every HTTP mirror is exhausted, the function must try GDrive.
        Without this fallback, the download would silently fail.
        """
        from pipeline.data.downloader import _download_file

        result = _download_file("dataset", tmp_dest)

        assert result is True
        mock_gdrive.assert_called_once()

    @patch(f"{MOD}._download_gdrive", return_value=False)
    @patch(f"{MOD}._download_http", return_value=False)
    def test_returns_false_when_mirrors_and_gdrive_both_fail(self, mock_http, mock_gdrive, tmp_dest):
        """
        Tests the branch: GDrive also fails → return False

        Complete download failure must return False so the caller can handle it.
        """
        from pipeline.data.downloader import _download_file

        result = _download_file("dataset", tmp_dest)

        assert result is False

    def test_returns_false_for_unknown_file_key(self, tmp_dest):
        """
        Tests the branch: if not config → return False

        An unknown file_key has no config entry, so we must fail gracefully.
        """
        from pipeline.data.downloader import _download_file

        # We supply a file_key that doesn't exist in FILES_CONFIG.
        # Valid keys are "dataset", "pca_model", and "umap_model". We use "nonexistent_key" to trigger the error handling.
        result = _download_file("nonexistent_key", tmp_dest)
        assert result is False


class TestVerifyPkl:
    """Tests the verification logic in _verify_pkl()."""

    def test_returns_false_when_file_does_not_exist(self, tmp_path):
        """
        Tests the branch: if not path.exists() → return False
        """
        from pipeline.data.downloader import _verify_pkl

        result = _verify_pkl(tmp_path / "missing.pkl", "Test model")

        assert result is False

    def test_returns_false_when_file_is_suspiciously_small(self, tmp_path):
        """
        Tests the branch: if file_size < 1024 → return False

        A valid pkl model should be at least 1 KB. Anything smaller
        is likely a corrupt or incomplete download.
        """
        from pipeline.data.downloader import _verify_pkl

        small_file = tmp_path / "tiny.pkl"
        small_file.write_bytes(b"x" * 500)  # < 1024 bytes

        result = _verify_pkl(small_file, "Test model")

        assert result is False

    @patch(f"{MOD}.joblib.load")
    def test_full_load_returns_true_when_model_is_valid(self, mock_joblib, tmp_path):
        """
        Tests the full_load=True path: joblib.load succeeds and returns non-None.
        """
        from pipeline.data.downloader import _verify_pkl

        pkl_file = tmp_path / "model.pkl"
        pkl_file.write_bytes(b"x" * 2048)  # > 1024 bytes

        mock_joblib.return_value = Mock()  # valid model object

        result = _verify_pkl(pkl_file, "Test model", full_load=True)

        assert result is True

    @patch(f"{MOD}.joblib.load", return_value=None)
    def test_full_load_returns_false_when_model_loads_as_none(self, mock_joblib, tmp_path):
        """
        Tests the branch: if obj is None → return False

        A corrupt pkl file might deserialize to None. We must detect this.
        """
        from pipeline.data.downloader import _verify_pkl

        pkl_file = tmp_path / "model.pkl"
        pkl_file.write_bytes(b"x" * 2048)

        result = _verify_pkl(pkl_file, "Test model", full_load=True)
        import pipeline.data.downloader as dl_mod

        assert result is False
        dl_mod.logger.error.assert_called_once()
        args, _ = dl_mod.logger.error.call_args
        # Making sure that the error we receive is actually from this None case, not some other error in the function.
        assert "loaded as None" in str(args)
        assert result is False

    # Simulate joblib.load throwing an exception (e.g. due to a truly corrupt file) and ensure we catch it and return False.
    @patch(f"{MOD}.joblib.load", side_effect=Exception("corrupt pickle"))
    def test_full_load_returns_false_on_joblib_exception(self, mock_joblib, tmp_path):
        """
        Tests the branch: except Exception (joblib.load fails)

        A truly corrupt file will cause joblib to throw. We must catch it.
        """
        from pipeline.data.downloader import _verify_pkl

        pkl_file = tmp_path / "model.pkl"
        pkl_file.write_bytes(b"x" * 2048)

        result = _verify_pkl(pkl_file, "Test model", full_load=True)
        import pipeline.data.downloader as dl_mod

        assert result is False
        dl_mod.logger.error.assert_called_once()
        args, _ = dl_mod.logger.error.call_args
        # We want to confirm that the logged error message contains "corrupt pickle" to ensure we're catching the
        # expected exception from joblib.load, not some other unexpected error.
        assert "corrupt pickle" in str(args)

    def test_lightweight_check_returns_true_for_valid_pickle_header(self, tmp_path):
        """
        Tests the full_load=False path: file has valid pickle header (0x80).

        Even without fully deserializing, we can check the header bytes to confirm it's likely a valid pickle file.
        """
        from pipeline.data.downloader import _verify_pkl

        pkl_file = tmp_path / "big_model.pkl"
        # Valid pickle protocol 5 header: 0x80 0x05
        pkl_file.write_bytes(b"\x80\x05" + b"x" * 2048)

        result = _verify_pkl(pkl_file, "UMAP model", full_load=False)

        assert result is True

    def test_lightweight_check_returns_false_for_invalid_header(self, tmp_path):
        """
        Tests the branch: if header[0:1] != b'\\x80' → return False

        If the file doesn't start with a pickle magic byte, it's not a valid pickle.
        """
        from pipeline.data.downloader import _verify_pkl

        pkl_file = tmp_path / "bad_model.pkl"
        # This file is > 1024 bytes but does not start with the valid pickle header,
        # simulating a corrupt download that HIGHLY LIKELY isn't a pickle.
        pkl_file.write_bytes(b"NOT_A_PICKLE" + b"x" * 2048)
        # Load with full_load=False to trigger the lightweight header check
        # which should fail and return False without trying to deserialize.
        result = _verify_pkl(pkl_file, "Bad model", full_load=False)

        assert result is False


class TestDownloadModels:
    """Tests the combined download + verify logic in download_models()."""

    @patch(f"{MOD}._verify_pkl", return_value=True)
    @patch(f"{MOD}._download_file", return_value=True)
    @patch(f"{MOD}._models_dir")
    def test_returns_true_when_both_models_download_and_verify(self, mock_dir, mock_dl, mock_verify, tmp_path):
        """
        Tests the happy path: both downloads succeed and both verifications pass.
        """
        from pipeline.data.downloader import download_models

        mock_dir.return_value = tmp_path

        result = download_models()

        assert result is True

    # First Return False for PCA download, then True for UMAP
    # to test that the function returns False if either model fails to download.
    @patch(f"{MOD}._download_file", side_effect=[False, True])
    @patch(f"{MOD}._models_dir")
    def test_returns_false_when_pca_download_fails(self, mock_dir, mock_dl, tmp_path):
        """
        Tests the branch: if not pca_ok or not umap_ok → return False

        If even one model fails to download, we can't proceed.
        """
        from pipeline.data.downloader import download_models

        mock_dir.return_value = tmp_path

        result = download_models()

        assert result is False

    # First Return True for PCA download, then False for UMAP
    # to test that the function returns False if either model fails to download.
    @patch(f"{MOD}._download_file", side_effect=[True, False])
    @patch(f"{MOD}._models_dir")
    def test_returns_false_when_umap_download_fails(self, mock_dir, mock_dl, tmp_path):
        """
        Tests the branch: if not pca_ok or not umap_ok → return False (umap case)
        """
        from pipeline.data.downloader import download_models

        mock_dir.return_value = tmp_path

        result = download_models()

        assert result is False

    @patch(f"{MOD}._verify_pkl", side_effect=[False])
    @patch(f"{MOD}._download_file", return_value=True)
    @patch(f"{MOD}._models_dir")
    def test_returns_false_when_pca_verification_fails(self, mock_dir, mock_dl, mock_verify, tmp_path):
        """
        Tests the branch: if not _verify_pkl(pca_path, ...) → return False

        Download succeeded but the file is corrupt.
        """
        from pipeline.data.downloader import download_models

        mock_dir.return_value = tmp_path

        result = download_models()

        assert result is False

    @patch(f"{MOD}._verify_pkl", side_effect=[True, False])
    @patch(f"{MOD}._download_file", return_value=True)
    @patch(f"{MOD}._models_dir")
    def test_returns_false_when_umap_verification_fails(self, mock_dir, mock_dl, mock_verify, tmp_path):
        """
        Tests the branch: if not _verify_pkl(umap_path, ...) → return False

        PCA passes but UMAP is corrupt → overall failure.
        """
        from pipeline.data.downloader import download_models

        mock_dir.return_value = tmp_path

        result = download_models()

        assert result is False


class TestEnsureAllDownloaded:
    """Tests the sequential check logic in ensure_all_downloaded()."""

    @patch(f"{MOD}.download_models", return_value=True)
    @patch(f"{MOD}.download_dataset", return_value=Path("/fake/dataset.jsonl"))
    def test_returns_true_when_everything_succeeds(self, mock_ds, mock_models):
        """
        Tests happy path: dataset + models both OK → True.
        """
        from pipeline.data.downloader import ensure_all_downloaded

        assert ensure_all_downloaded() is True

    @patch(f"{MOD}.download_models")
    @patch(f"{MOD}.download_dataset", return_value=None)
    def test_returns_false_when_dataset_fails(self, mock_ds, mock_models):
        """
        Tests the branch: if dataset_path is None → return False

        If the dataset can't be downloaded, we abort early without trying models.
        """
        from pipeline.data.downloader import ensure_all_downloaded

        result = ensure_all_downloaded()

        assert result is False
        mock_models.assert_not_called()  # early exit

    @patch(f"{MOD}.download_models", return_value=False)
    @patch(f"{MOD}.download_dataset", return_value=Path("/fake/dataset.jsonl"))
    def test_returns_false_when_models_fail(self, mock_ds, mock_models):
        """
        Tests the branch: if not download_models() → return False
        """
        from pipeline.data.downloader import ensure_all_downloaded

        assert ensure_all_downloaded() is False


class TestCleanupDataset:
    """Tests the conditional file deletion in cleanup_dataset()."""

    @patch(f"{MOD}.get_dataset_path")
    def test_deletes_existing_dataset_file(self, mock_path, tmp_path):
        """
        Tests the branch: if path.exists() → unlink

        After a successful import, the large dataset JSONL should be deleted.
        """
        from pipeline.data.downloader import cleanup_dataset

        dataset_file = tmp_path / "dataset.jsonl"
        dataset_file.write_bytes(b"x" * 5000)
        mock_path.return_value = dataset_file

        cleanup_dataset()

        assert not dataset_file.exists()

    @patch(f"{MOD}.get_dataset_path")
    def test_does_not_crash_when_file_missing(self, mock_path, tmp_path):
        """
        Tests the branch: if path.exists() is False → do nothing

        If cleanup is called twice, or the file was never downloaded,
        it should not raise an exception.
        """
        from pipeline.data.downloader import cleanup_dataset

        mock_path.return_value = tmp_path / "nonexistent.jsonl"

        cleanup_dataset()  # should not raise
