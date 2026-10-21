import io
from PIL import Image
import pytest
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.services.soil_type_service import SoilTypeModelAdapter, soil_type_service
from app.services.soil_moisture_service import SoilMoistureModelAdapter, soil_moisture_service


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_dummy_soil_image_bytes(format="JPEG", size=(224, 224), color=(139, 69, 19)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


# ==========================================
# Soil Type Model Unit & API Tests
# ==========================================

def test_soil_type_loading_and_shape():
    adapter = SoilTypeModelAdapter()
    interp = adapter.load_model()
    assert interp is not None
    
    in_details = interp.get_input_details()
    out_details = interp.get_output_details()
    
    assert list(in_details[0]["shape"]) == [1, 224, 224, 3]
    assert list(out_details[0]["shape"]) == [1, 7]


def test_soil_type_probabilities_sum_to_one():
    adapter = SoilTypeModelAdapter()
    img_bytes = create_dummy_soil_image_bytes()
    result = adapter.predict(img_bytes)
    
    scores = [c["model_score"] for c in result["all_classes"]]
    assert len(scores) == 7
    for s in scores:
        assert s >= 0.0
        assert s <= 1.0
    assert abs(sum(scores) - 1.0) < 0.02


def test_soil_type_labels_loaded():
    adapter = SoilTypeModelAdapter()
    labels = adapter.load_labels()
    assert labels["verification_status"] == "verified"
    assert len(labels["classes"]) == 7
    assert labels["classes"][0]["raw_class_name"] == "Alluvial_Soil"
    assert labels["classes"][6]["raw_class_name"] == "Yellow_Soil"


def test_soil_type_predict_api_valid(client):
    img_bytes = create_dummy_soil_image_bytes()
    files = {"file": ("soil.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/soil/type/predict", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["verification_status"] == "verified"
    assert "primary_prediction" in data
    assert len(data["all_classes"]) == 7
    assert "ল্যাবরেটরি" in data["disclaimer_bn"]


# ==========================================
# Soil Moisture Model Unit & API Tests
# ==========================================

def test_soil_moisture_loading_and_shape():
    adapter = SoilMoistureModelAdapter()
    interp = adapter.load_model()
    assert interp is not None
    
    in_details = interp.get_input_details()
    out_details = interp.get_output_details()
    
    assert list(in_details[0]["shape"]) == [1, 224, 224, 3]
    assert list(out_details[0]["shape"]) == [1, 2]


def test_soil_moisture_probabilities_sum_to_one():
    adapter = SoilMoistureModelAdapter()
    img_bytes = create_dummy_soil_image_bytes()
    result = adapter.predict(img_bytes)
    
    scores = [c["model_score"] for c in result["all_classes"]]
    assert len(scores) == 2
    for s in scores:
        assert s >= 0.0
        assert s <= 1.0
    assert abs(sum(scores) - 1.0) < 0.01


def test_soil_moisture_labels_loaded():
    adapter = SoilMoistureModelAdapter()
    labels = adapter.load_labels()
    assert labels["verification_status"] == "verified"
    assert len(labels["classes"]) == 2
    assert labels["classes"][0]["raw_class_name"] == "dry"
    assert labels["classes"][1]["raw_class_name"] == "wet"


def test_soil_moisture_predict_api_valid(client):
    img_bytes = create_dummy_soil_image_bytes()
    files = {"file": ("soil_moist.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/soil/moisture/predict", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["verification_status"] == "verified"
    assert "primary_prediction" in data
    assert len(data["all_classes"]) == 2
    assert "টেনসিওমিটার" in data["disclaimer_bn"]


# ==========================================
# Error Handling & Edge Cases Tests
# ==========================================

def test_soil_endpoints_corrupt_image(client):
    corrupt_bytes = b"not a valid image content"
    files = {"file": ("bad.jpg", corrupt_bytes, "image/jpeg")}
    
    res1 = client.post("/api/v1/soil/type/predict", files=files)
    assert res1.status_code == 400
    
    res2 = client.post("/api/v1/soil/moisture/predict", files=files)
    assert res2.status_code == 400


def test_soil_endpoints_unsupported_media_type(client):
    text_bytes = b"hello world"
    files = {"file": ("bad.txt", text_bytes, "text/plain")}
    
    res1 = client.post("/api/v1/soil/type/predict", files=files)
    assert res1.status_code == 415
    
    res2 = client.post("/api/v1/soil/moisture/predict", files=files)
    assert res2.status_code == 415


def test_soil_endpoints_empty_file(client):
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    
    res1 = client.post("/api/v1/soil/type/predict", files=files)
    assert res1.status_code == 400
    
    res2 = client.post("/api/v1/soil/moisture/predict", files=files)
    assert res2.status_code == 400


def test_soil_type_unverified_fallback():
    adapter = SoilTypeModelAdapter()
    adapter._labels_data = {
        "model_name": "test",
        "verification_status": "unverified",
        "verification_source": "test",
        "classes": []
    }
    img_bytes = create_dummy_soil_image_bytes()
    res = adapter.predict(img_bytes)
    assert res["verification_status"] == "unverified"
    assert res["primary_prediction"]["is_verified"] is False
    assert "যাচাইহীন" in res["primary_prediction"]["display_name_bn"]
