from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from iot_ids.data.cache import cache_fingerprint
from iot_ids.data.materialize import load_valid_manifest
from iot_ids.preprocessing.pipeline import FittedPreprocessor, fit_preprocessor


def test_cache_fingerprint_is_deterministic(tmp_path: Path) -> None:
    a = tmp_path / "a.csv"
    a.write_text("x\n1\n", encoding="utf-8")
    one = cache_fingerprint([a], "s1", "l1", "f1")
    two = cache_fingerprint([a], "s1", "l1", "f1")
    assert one == two
    assert one != cache_fingerprint([a], "s2", "l1", "f1")


def test_preprocessor_serialization(tmp_path: Path) -> None:
    frame = pd.DataFrame({"a": [1.0, np.inf, 3.0], "b": ["x", "y", None]})
    fitted = fit_preprocessor(frame, ["a", "b"])
    transformed = fitted.transform(frame)
    assert transformed.shape[0] == 3
    path = tmp_path / "preprocessor.joblib"
    fitted.save(path)
    loaded = FittedPreprocessor.load(path)
    assert loaded.feature_order == ["a", "b"]


def test_preprocessor_transform_does_not_change_fit_state() -> None:
    train = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": ["x", "x", "y"]})
    validation = pd.DataFrame({"a": [1000.0, 2000.0], "b": ["z", "z"]})
    target = pd.DataFrame({"a": [-999.0, 999.0], "b": ["new", "x"]})
    fitted = fit_preprocessor(train, ["a", "b"])
    before = dict(fitted.fit_summary or {})
    fitted.transform(validation)
    fitted.transform(target)
    after = dict(fitted.fit_summary or {})
    assert before == after
    assert fitted.fit_summary["numeric_medians"]["a"] == 2.0


def test_incomplete_cache_manifest_is_not_valid(tmp_path: Path) -> None:
    out = tmp_path / "cache"
    out.mkdir()
    manifest = out / "manifest.json"
    manifest.write_text('{"complete": false, "rows": 10, "partitions": 1}', encoding="utf-8")
    assert load_valid_manifest(manifest, out) is None
    (out / "part-0000-0000.parquet").write_text("placeholder", encoding="utf-8")
    manifest.write_text('{"complete": true, "rows": 10, "partitions": 2}', encoding="utf-8")
    assert load_valid_manifest(manifest, out) is None
