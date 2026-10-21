import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import io
from PIL import Image, UnidentifiedImageError
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from app.core.config import settings
from app.core.logging import logger


class DiseaseModelAdapter:
    """Isolated, CPU-friendly adapter for plant_disease_classifier.pth.
    
    Responsibilities:
    - Safe lazy-loading & caching of the MobileNetV2 PyTorch model.
    - Verified image preprocessing matching the training pipeline (Resize 224x224, ToTensor, ImageNet Normalization).
    - CPU inference using torch.inference_mode().
    - Numerically stable softmax probability calculation.
    - Honest class-label mapping verification handling.
    """

    def __init__(self):
        self._model: Optional[torch.nn.Module] = None
        self._labels_data: Optional[Dict[str, Any]] = None
        self._device = torch.device("cpu")
        self._transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def _resolve_path(self, path_str: str) -> Path:
        path = Path(path_str)
        if not path.is_absolute():
            # Check relative to backend cwd or project root
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

        labels_path = self._resolve_path(settings.PLANT_DISEASE_LABELS_PATH)
        if not labels_path.exists():
            logger.warning(f"Label mappings file not found at {labels_path}. Using fallback unverified configuration.")
            self._labels_data = {
                "model_name": "plant_disease_classifier.pth",
                "verification_status": "unverified",
                "verification_source": "None - file missing",
                "classes": []
            }
            return self._labels_data

        try:
            with open(labels_path, "r", encoding="utf-8") as f:
                self._labels_data = json.load(f)
            logger.info(f"Loaded class labels with status: {self._labels_data.get('verification_status')}")
        except Exception as e:
            logger.error(f"Failed to load labels file: {e}")
            self._labels_data = {
                "model_name": "plant_disease_classifier.pth",
                "verification_status": "unverified",
                "verification_source": f"Error loading labels: {e}",
                "classes": []
            }
        return self._labels_data

    def load_model(self) -> torch.nn.Module:
        if self._model is not None:
            return self._model

        model_path = self._resolve_path(settings.PLANT_DISEASE_MODEL_PATH)
        if not model_path.exists():
            logger.error(f"Model artifact not found at {model_path}")
            raise FileNotFoundError(f"Model artifact not found at {model_path}")

        logger.info(f"Loading MobileNetV2 weights from {model_path} onto CPU...")
        try:
            model = models.mobilenet_v2(weights=None)
            model.classifier[1] = torch.nn.Linear(model.last_channel, 15)
            
            # Load checkpoint strictly onto CPU
            ckpt = torch.load(model_path, map_location=self._device)
            model.load_state_dict(ckpt)
            model.to(self._device)
            model.eval()
            self._model = model
            logger.info("Plant disease classifier model loaded and verified successfully.")
            return self._model
        except Exception as e:
            logger.critical(f"Failed to load model weights: {e}")
            raise RuntimeError(f"Failed to initialize disease classifier model: {e}")

    def is_loaded(self) -> bool:
        return self._model is not None

    def preprocess_image(self, image_bytes: bytes) -> torch.Tensor:
        """Decode and validate image bytes into a normalized (1, 3, 224, 224) tensor."""
        if not image_bytes:
            raise ValueError("Empty image content provided.")

        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()  # Verify image integrity
        except Exception as e:
            raise ValueError("Corrupt or invalid image format.") from e

        # Reopen for processing because verify() corrupts the image object in PIL
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            raise ValueError("Failed to decode image to RGB modality.") from e

        # Validate minimum dimension
        if img.width < 10 or img.height < 10:
            raise ValueError("Image dimensions too small to be a valid leaf photo.")

        tensor = self._transform(img)  # Shape: (3, 224, 224)
        return tensor.unsqueeze(0)  # Shape: (1, 3, 224, 224)

    def predict(self, image_bytes: bytes, top_k: int = 3) -> Dict[str, Any]:
        """Perform inference on input image bytes and return structured results with limitations."""
        tensor = self.preprocess_image(image_bytes)
        model = self.load_model()
        labels_meta = self.load_labels()
        is_verified = labels_meta.get("verification_status") == "verified"
        class_list = labels_meta.get("classes", [])

        with torch.inference_mode():
            logits = model(tensor)
            # Numerically stable softmax
            probs = torch.softmax(logits, dim=1)[0]
            scores, indices = torch.topk(probs, min(top_k, 15))

        top_predictions = []
        for rank, (score_t, idx_t) in enumerate(zip(scores, indices)):
            idx = idx_t.item()
            score = float(score_t.item())

            class_info = next((c for c in class_list if c.get("index") == idx), None)
            
            if is_verified and class_info:
                top_predictions.append({
                    "rank": rank + 1,
                    "class_index": idx,
                    "raw_class_name": class_info.get("raw_class_name"),
                    "crop": class_info.get("crop"),
                    "disease": class_info.get("disease"),
                    "is_healthy": class_info.get("is_healthy", False),
                    "display_name_en": class_info.get("display_name_en"),
                    "display_name_bn": class_info.get("display_name_bn"),
                    "model_score": round(score, 4),
                    "is_verified": True
                })
            else:
                top_predictions.append({
                    "rank": rank + 1,
                    "class_index": idx,
                    "raw_class_name": f"Class_{idx} (Unverified)",
                    "crop": "unknown",
                    "disease": "unverified",
                    "is_healthy": False,
                    "display_name_en": f"Class index #{idx} (Unverified)",
                    "display_name_bn": f"শ্রেণি ইনডেক্স #{idx} (যাচাইহীন)",
                    "model_score": round(score, 4),
                    "is_verified": False
                })

        primary = top_predictions[0]

        return {
            "model_identifier": "MobileNetV2 (15 classes, CPU)",
            "verification_status": labels_meta.get("verification_status", "unverified"),
            "verification_source": labels_meta.get("verification_source", "Unknown"),
            "primary_prediction": primary,
            "top_candidates": top_predictions,
            "disclaimer_bn": "মডেলের ফলাফল চূড়ান্ত রোগ নির্ণয় নয়। ক্ষেত্রবিশেষে আলোকচিত্রের কোণ বা অন্যান্য উপসর্গের কারণে পার্থক্য হতে পারে। কোনো রাসায়নিক ব্যবহারের পূর্বে স্থানীয় কৃষি বিশেষজ্ঞের পরামর্শ নিন।",
            "disclaimer_en": "Model output is an automated statistical estimate, not a definitive diagnosis. Consult a certified local agricultural extension officer before taking chemical measures."
        }


# Global singleton instance
disease_model_service = DiseaseModelAdapter()
