import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import io
import numpy as np
from PIL import Image
from ai_edge_litert.interpreter import Interpreter
from app.core.config import settings
from app.core.logging import logger


class SoilTypeModelAdapter:
    """Isolated, CPU-friendly adapter for soil_type_classifier.tflite.
    
    Responsibilities:
    - Safe lazy-loading & caching of the TFLite Interpreter using LiteRT runtime.
    - Verified image preprocessing matching the training pipeline (ImageDataGenerator rescale=1./255, 224x224 RGB).
    - CPU inference without GPU dependencies.
    - Returns 7 softmax probability scores and top ranked classes.
    - Preserves verification status and honest disclaimers (no lab test inference).
    """

    def __init__(self):
        self._interpreter: Optional[Interpreter] = None
        self._labels_data: Optional[Dict[str, Any]] = None
        self._input_details = None
        self._output_details = None

    def _resolve_path(self, path_str: str) -> Path:
        path = Path(path_str)
        if not path.is_absolute():
            cand1 = (Path.cwd() / path).resolve()
            if cand1.exists():
                return cand1
            cand2 = (Path.cwd().parent / path.name).resolve()
            if cand2.exists():
                return cand2
            return cand1
        return path

    def load_labels(self) -> Dict[str, Any]:
        if self._labels_data is not None:
            return self._labels_data

        labels_path = self._resolve_path(settings.SOIL_TYPE_LABELS_PATH)
        if not labels_path.exists():
            logger.warning(f"Soil type labels file not found at {labels_path}. Using unverified fallback.")
            self._labels_data = {
                "model_name": "soil_type_classifier.tflite",
                "verification_status": "unverified",
                "verification_source": "Missing label file",
                "classes": []
            }
            return self._labels_data

        try:
            with open(labels_path, "r", encoding="utf-8") as f:
                self._labels_data = json.load(f)
            logger.info(f"Loaded soil type class labels with status: {self._labels_data.get('verification_status')}")
        except Exception as e:
            logger.error(f"Failed to read soil type labels: {e}")
            self._labels_data = {
                "model_name": "soil_type_classifier.tflite",
                "verification_status": "unverified",
                "verification_source": f"Error: {e}",
                "classes": []
            }
        return self._labels_data

    def load_model(self) -> Interpreter:
        if self._interpreter is not None:
            return self._interpreter

        model_path = self._resolve_path(settings.SOIL_TYPE_MODEL_PATH)
        if not model_path.exists():
            logger.error(f"Soil type model artifact not found at {model_path}")
            raise FileNotFoundError(f"Soil type model artifact not found at {model_path}")

        logger.info(f"Loading TFLite soil type classifier from {model_path} via LiteRT on CPU...")
        try:
            interpreter = Interpreter(model_path=str(model_path))
            interpreter.allocate_tensors()
            self._input_details = interpreter.get_input_details()
            self._output_details = interpreter.get_output_details()
            self._interpreter = interpreter
            logger.info("Soil type classifier model loaded and tensor shapes allocated successfully.")
            return self._interpreter
        except Exception as e:
            logger.critical(f"Failed to load soil type TFLite model: {e}")
            raise RuntimeError(f"Failed to initialize soil type classifier: {e}")

    def is_loaded(self) -> bool:
        return self._interpreter is not None

    def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        if not image_bytes:
            raise ValueError("Empty image content provided.")

        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
        except Exception as e:
            raise ValueError("Corrupt or invalid image format.") from e

        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            raise ValueError("Failed to decode image to RGB modality.") from e

        if img.width < 10 or img.height < 10:
            raise ValueError("Image dimensions too small to be a valid soil photo.")

        # Match training preprocessing: resize to (224, 224) and rescale to 1./255
        img = img.resize((224, 224))
        arr = np.array(img, dtype=np.float32) / 255.0
        return np.expand_dims(arr, axis=0)  # Shape: (1, 224, 224, 3)

    def predict(self, image_bytes: bytes) -> Dict[str, Any]:
        input_data = self.preprocess_image(image_bytes)
        interpreter = self.load_model()
        labels_meta = self.load_labels()
        is_verified = labels_meta.get("verification_status") == "verified"
        class_list = labels_meta.get("classes", [])

        input_index = self._input_details[0]["index"]
        output_index = self._output_details[0]["index"]

        interpreter.set_tensor(input_index, input_data)
        interpreter.invoke()
        output_tensor = interpreter.get_tensor(output_index)[0]  # Shape: (7,)

        # Sort indices descending by model probability score
        sorted_indices = np.argsort(output_tensor)[::-1]

        candidates = []
        for rank, idx in enumerate(sorted_indices):
            score = float(output_tensor[idx])
            class_info = next((c for c in class_list if c.get("index") == int(idx)), None)

            if is_verified and class_info:
                candidates.append({
                    "rank": rank + 1,
                    "class_index": int(idx),
                    "raw_class_name": class_info.get("raw_class_name"),
                    "display_name_en": class_info.get("display_name_en"),
                    "display_name_bn": class_info.get("display_name_bn"),
                    "model_score": round(score, 4),
                    "is_verified": True
                })
            else:
                candidates.append({
                    "rank": rank + 1,
                    "class_index": int(idx),
                    "raw_class_name": f"Soil_Class_{idx} (Unverified)",
                    "display_name_en": f"Soil Class #{idx} (Unverified)",
                    "display_name_bn": f"মাটির শ্রেণি ইনডেক্স #{idx} (যাচাইহীন)",
                    "model_score": round(score, 4),
                    "is_verified": False
                })

        primary = candidates[0]

        return {
            "model_identifier": "MobileNetV2 TFLite (7 soil classes, CPU)",
            "verification_status": labels_meta.get("verification_status", "unverified"),
            "verification_source": labels_meta.get("verification_source", "Unknown"),
            "primary_prediction": primary,
            "all_classes": candidates,
            "disclaimer_bn": "ছবি ভিত্তিক মাটির ধরন অনুমান কোনো ল্যাবরেটরি মৃত্তিকা পরীক্ষার সমতুল্য নয়। এটি মাটির সুনির্দিষ্ট pH, NPK পুষ্টিগুণ বা উর্বরতা নিশ্চিত করে না। সঠিক ফলাফলের জন্য সরকারি মৃত্তিকা স্বাস্থ্য কার্ড (Soil Health Card) পরিষেবা নিন।",
            "disclaimer_en": "Image-based soil classification is an automated visual estimate and cannot replace laboratory soil testing. It does not measure pH, NPK, or nutrient concentrations. Obtain an official Soil Health Card for precise management."
        }


soil_type_service = SoilTypeModelAdapter()
