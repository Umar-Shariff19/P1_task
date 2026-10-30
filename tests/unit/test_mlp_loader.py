"""Unit tests for safe MLP checkpoint loading and format enforcement."""
import pytest
import torch
import torch.nn as nn
import joblib
from pathlib import Path

from iot_ids.runtime.engine import InferenceEngine, MLPModule
from iot_ids.provenance.windows_access import RealDataAuthorizationUnavailable


class DummyPreprocessor:
    feature_names = list(range(21))
    def transform(self, X):
        return X


@pytest.fixture
def dummy_preprocessor(tmp_path):
    pre_path = tmp_path / "prep_standardized.joblib"
    joblib.dump(DummyPreprocessor(), pre_path)
    return pre_path


@pytest.fixture
def dummy_rf(tmp_path):
    from sklearn.ensemble import RandomForestClassifier
    rf = RandomForestClassifier()
    rf.n_features_in_ = 21
    rf.classes_ = [0, 1]
    rf_path = tmp_path / "rf_model.joblib"
    joblib.dump(rf, rf_path)
    return rf_path


def test_mlp_loader_accepts_valid_state_dict(tmp_path):
    """Valid state-dict with strict weights_only loads cleanly."""
    mlp = MLPModule(input_dim=21)
    mlp_path = tmp_path / "mlp_adversarial.pt"
    torch.save(mlp.state_dict(), mlp_path)

    loaded = InferenceEngine._load_mlp_checkpoint(mlp_path, expected_dim=21)
    assert isinstance(loaded, nn.Module)
    assert loaded.training is False


def test_mlp_loader_rejects_full_model_pickle(tmp_path):
    """Pickled nn.Module must be rejected by weights_only=True."""
    mlp = MLPModule(input_dim=21)
    mlp_path = tmp_path / "mlp_adversarial.pt"
    torch.save(mlp, mlp_path)

    with pytest.raises(TypeError, match="Failed to safely load MLP state dictionary|must be a state dictionary"):
        InferenceEngine._load_mlp_checkpoint(mlp_path, expected_dim=21)


def test_mlp_loader_rejects_scripted_model(tmp_path):
    """TorchScript archive must be rejected by weights_only state-dict loader."""
    mlp = MLPModule(input_dim=21)
    scripted = torch.jit.script(mlp)
    mlp_path = tmp_path / "mlp_adversarial.pt"
    scripted.save(str(mlp_path))

    with pytest.raises(TypeError, match="Failed to safely load MLP state dictionary|must be a state dictionary"):
        InferenceEngine._load_mlp_checkpoint(mlp_path, expected_dim=21)


def test_mlp_loader_rejects_dimension_mismatch(tmp_path):
    """State dict with dimension != expected_dim must raise ValueError."""
    mlp_13 = MLPModule(input_dim=13)
    mlp_path = tmp_path / "mlp_adversarial.pt"
    torch.save(mlp_13.state_dict(), mlp_path)

    with pytest.raises(ValueError, match="Dimension Mismatch"):
        InferenceEngine._load_mlp_checkpoint(mlp_path, expected_dim=21)


def test_mlp_loader_rejects_missing_keys(tmp_path):
    """Malformed state dict without net.0.weight must raise KeyError."""
    mlp_path = tmp_path / "mlp_adversarial.pt"
    torch.save({"wrong_layer.weight": torch.randn(10, 21)}, mlp_path)

    with pytest.raises(KeyError, match="missing required key 'net.0.weight'"):
        InferenceEngine._load_mlp_checkpoint(mlp_path, expected_dim=21)


def test_mlp_loader_rejects_corrupted_artifact(tmp_path):
    """Empty or corrupted file must raise TypeError fail-closed."""
    bad_path = tmp_path / "corrupt.pt"
    bad_path.write_bytes(b"not a valid pytorch tensor")

    with pytest.raises(TypeError):
        InferenceEngine._load_mlp_checkpoint(bad_path, expected_dim=21)


def test_checkpoint_backed_engine_refuses_without_authorization(tmp_path, dummy_preprocessor, dummy_rf):
    """Production InferenceEngine constructor must fail closed before inspecting artifacts."""
    with pytest.raises(RealDataAuthorizationUnavailable):
        InferenceEngine(profile="standardized_21", dataset="ToN-IoT", models_base_dir=tmp_path)
