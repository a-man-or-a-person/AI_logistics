import pytest
import test_clustering_frontend_contract as frontend


def test_mandatory_frontend_browser_cannot_skip_when_edge_is_missing(monkeypatch):
    monkeypatch.setenv("REQUIRE_FRONTEND_BROWSER", "1")
    monkeypatch.setattr(frontend, "_edge_path", lambda: None)

    try:
        with pytest.raises(RuntimeError, match="Required Edge browser is unavailable"):
            frontend._run_browser_script("document.body.dataset.result = '{}'")
    except pytest.skip.Exception:
        pytest.fail("Missing mandatory browser was silently skipped")
