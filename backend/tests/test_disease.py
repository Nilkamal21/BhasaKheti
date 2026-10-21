import io
from PIL import Image
import pytest
import torch
from fastapi.testclient import TestClient
from app.main import app
from app.services.disease_service import DiseaseModelAdapter, disease_model_service


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_dummy_image_bytes(format="JPEG", size=(224, 224), color=(0, 255, 0)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


def test_model_loading_and_shape():
    """Verify that model loads on CPU and returns output tensor of shape [1, 15]."""
    adapter = DiseaseModelAdapter()
    model = adapter.load_model()
    assert model is not None
    assert isinstance(model, torch.nn.Module)
    
    dummy_input = torch.randn(1, 3, 224, 224)
    with torch.inference_mode():
        output = model(dummy_input)
    assert output.shape == (1, 15)


def test_probabilities_finite_and_sum_to_one():
    """Verify that softmax probabilities are finite and sum approximately to 1.0."""
    adapter = DiseaseModelAdapter()
    img_bytes = create_dummy_image_bytes()
    result = adapter.predict(img_bytes, top_k=15)
    
    scores = [c["model_score"] for c in result["top_candidates"]]
    assert len(scores) == 15
    for s in scores:
        assert s >= 0.0
        assert s <= 1.0
    assert abs(sum(scores) - 1.0) < 0.01


def test_verified_labels_loaded():
    """Verify that verified labels metadata is loaded correctly with 15 classes."""
    adapter = DiseaseModelAdapter()
    labels = adapter.load_labels()
    assert labels["verification_status"] == "verified"
    assert len(labels["classes"]) == 15
    assert labels["classes"][0]["raw_class_name"] == "Pepper__bell___Bacterial_spot"
    assert labels["classes"][14]["raw_class_name"] == "Tomato_healthy"


def test_predict_api_valid_image(client):
    """Test POST /api/v1/disease/predict with a valid dummy leaf image."""
    img_bytes = create_dummy_image_bytes()
    files = {"file": ("leaf.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/disease/predict", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["verification_status"] == "verified"
    assert "primary_prediction" in data
    assert "disclaimer_bn" in data
    assert data["primary_prediction"]["is_verified"] is True
    assert len(data["top_candidates"]) <= 3


def test_predict_api_invalid_image_corrupt(client):
    """Test POST /api/v1/disease/predict with corrupt non-image bytes."""
    corrupt_bytes = b"this is not an image file header"
    files = {"file": ("corrupt.jpg", corrupt_bytes, "image/jpeg")}
    response = client.post("/api/v1/disease/predict", files=files)
    assert response.status_code == 400
    assert "ব্যর্থ" in response.json()["detail"]


def test_predict_api_unsupported_media_type(client):
    """Test POST /api/v1/disease/predict with disallowed file type (e.g. PDF/text)."""
    text_bytes = b"sample text"
    files = {"file": ("test.txt", text_bytes, "text/plain")}
    response = client.post("/api/v1/disease/predict", files=files)
    assert response.status_code == 415


def test_predict_api_empty_file(client):
    """Test POST /api/v1/disease/predict with empty file."""
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    response = client.post("/api/v1/disease/predict", files=files)
    assert response.status_code == 400


def test_unverified_fallback_behavior():
    """Test that when label metadata is unverified, UI/API labels it as unverified class."""
    adapter = DiseaseModelAdapter()
    # Force unverified status
    adapter._labels_data = {
        "model_name": "test",
        "verification_status": "unverified",
        "verification_source": "test",
        "classes": []
    }
    img_bytes = create_dummy_image_bytes()
    result = adapter.predict(img_bytes)
    assert result["verification_status"] == "unverified"
    assert result["primary_prediction"]["is_verified"] is False
    assert "যাচাইহীন" in result["primary_prediction"]["display_name_bn"]
