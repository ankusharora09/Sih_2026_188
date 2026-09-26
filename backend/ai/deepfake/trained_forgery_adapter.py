"""Trained forgery-classifier deepfake adapter.

Loads the ResNet18 checkpoint trained on the Genuine/Tampered synthetic-face
dataset (``models/document_forgery_gt2.pth``) and grades the live capture as
genuine or forged. When the model or torch is unavailable, the adapter falls
back to the spectral heuristics (SimpleDeepfakeAdapter) so the pipeline keeps
working offline.
"""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from .adapter import DeepfakeDetectionAdapter
from .simple_deepfake_adapter import SimpleDeepfakeAdapter

# Project-root-relative default; overridable via DEEPFAKE_MODEL_PATH.
_DEFAULT_WEIGHTS = Path("models") / "document_forgery_gt2.pth"


class TrainedForgeryDeepfakeAdapter(DeepfakeDetectionAdapter):
    """Deepfake detection using the project's trained forgery classifier.

    Pipeline per call:
      1. Detect + align the best face in the live capture (YuNet + SFace).
      2. Run the ResNet18 forgery classifier on the aligned 224x224 crop.
      3. Blend the neural P(forged) with the spectral heuristics (0.75/0.25).
    """

    def __init__(self, weights_path: str | Path | None = None) -> None:
        self.model_name = "resnet18_forgery_classifier"
        self.model_version = "document_forgery_gt2"

        self.heuristic = SimpleDeepfakeAdapter()
        self.class_names: list[str] = ["forged", "genuine"]
        self.image_size = 224
        self.model = None
        self.device = "cpu"
        self._load_error: str | None = None

        import os
        path = Path(weights_path or os.getenv("DEEPFAKE_MODEL_PATH") or _DEFAULT_WEIGHTS)
        self._load_model(path)

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_model(self, path: Path) -> None:
        try:
            import torch
            import torch.nn as nn
            from torchvision import models as tv_models

            if not path.is_file():
                self._load_error = f"checkpoint not found: {path}"
                return
            try:
                checkpoint = torch.load(path, map_location="cpu", weights_only=True)
            except Exception:
                checkpoint = torch.load(path, map_location="cpu", weights_only=False)

            if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
                self._load_error = "unsupported checkpoint format"
                return

            arch = str(checkpoint.get("architecture") or "resnet18")
            if arch != "resnet18":
                self._load_error = f"unsupported architecture '{arch}'"
                return

            num_classes = int(checkpoint.get("num_classes") or 2)
            self.image_size = int(checkpoint.get("image_size") or 224)
            names = checkpoint.get("class_names")
            if isinstance(names, (list, tuple)) and names:
                self.class_names = [str(n) for n in names]

            net = tv_models.resnet18(weights=None)
            # Head matches the training-time layout: Dropout -> Linear(512, num_classes).
            net.fc = nn.Sequential(nn.Dropout(0.2), nn.Linear(net.fc.in_features, num_classes))
            net.load_state_dict(checkpoint["model_state_dict"])
            net.eval()
            self.model = net
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            if self.device != "cpu":
                self.model = self.model.to(self.device)
        except Exception as exc:  # pragma: no cover - defensive
            self.model = None
            self._load_error = str(exc)

    @property
    def ready(self) -> bool:
        return self.model is not None

    def _mse(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Delegate to the spectral heuristics (monkeypatch-friendly seam)."""
        return self.heuristic._mse(img1, img2)

    # ------------------------------------------------------------------
    # Face crop for classification
    # ------------------------------------------------------------------

    def _face_crop(self, live_image: np.ndarray) -> tuple[np.ndarray, str]:
        """Return the best available crop for the classifier.

        Prefers a YuNet + SFace aligned 112x112 face; falls back to the whole
        (downscaled) frame when no face is found — the training images are
        portrait-style faces, so a full frame can still carry the signal.
        """
        try:
            from ..face import get_verifier

            verifier = get_verifier()
            face, scaled = verifier._detect_best_face_yunet(live_image)
            if face is not None and scaled is not None and verifier.recognizer is not None:
                aligned = verifier.recognizer.alignCrop(scaled, face)
                if aligned is not None and aligned.size:
                    return aligned, "yunet_sface_aligned"
        except Exception:
            pass

        h, w = live_image.shape[:2]
        scale = min(1.0, float(self.image_size) / max(h, w))
        if scale < 1.0:
            live_image = cv2.resize(live_image, (max(1, int(w * scale)), max(1, int(h * scale))))
        return live_image, "full_frame"

    def _neural_score(self, crop: np.ndarray) -> float:
        """P(forged) in [0,1] from the trained classifier."""
        import torch

        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (self.image_size, self.image_size))
        tensor = torch.from_numpy(rgb.astype(np.float32) / 255.0).permute(2, 0, 1)
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        tensor = (tensor - mean) / std
        batch = tensor.unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(batch)
            probs = torch.softmax(logits, dim=1)[0]

        probs = probs.detach().cpu().tolist()
        forged_idx = (self.class_names.index("forged")
                      if "forged" in self.class_names else 0)
        return float(probs[forged_idx])

    # ------------------------------------------------------------------
    # Adapter interface
    # ------------------------------------------------------------------

    def detect(self, document_image: np.ndarray, live_image: np.ndarray = None) -> dict:
        start = time.time()
        if live_image is None:
            return {
                "status": "unavailable",
                "model": self.model_name,
                "latency_ms": int((time.time() - start) * 1000),
            }

        try:
            heuristic = self.heuristic.detect(document_image, live_image)
            if heuristic.get("status") != "success":
                return heuristic

            neural_score: float | None = None
            crop_source = None
            if self.ready:
                try:
                    crop, crop_source = self._face_crop(live_image)
                    neural_score = self._neural_score(crop)
                except Exception:
                    neural_score = None

            h_score = float(heuristic.get("score") or 0.0)
            if neural_score is None:
                # Honest fallback: heuristics only.
                result = dict(heuristic)
                result["model"] = self.heuristic.model_name
                result["neural_model"] = self.model_name
                result["neural_available"] = False
                result["note"] = self._load_error or "neural classifier unavailable; spectral heuristics only"
                result["latency_ms"] = int((time.time() - start) * 1000)
                return result

            score = float(np.clip(0.75 * neural_score + 0.25 * h_score, 0.0, 1.0))
            threshold = self.heuristic.threshold

            indicators: list[str] = []
            if neural_score >= threshold:
                indicators.append("trained_forgery_classifier_flagged")
            for ind in heuristic.get("indicators", []):
                indicators.append(str(ind))

            return {
                "status": "success",
                "model": self.model_name,
                "model_version": self.model_version,
                "neural_model": self.model_name,
                "neural_available": True,
                "score": round(score, 4),
                "neural_score": round(neural_score, 4),
                "spectral_score": round(h_score, 4),
                "score_threshold": threshold,
                "crop_source": crop_source,
                "indicators": indicators,
                "verdict": "forged" if neural_score >= threshold else "genuine",
                "latency_ms": int((time.time() - start) * 1000),
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "status": "failed",
                "error": str(exc),
                "model": self.model_name,
                "latency_ms": int((time.time() - start) * 1000),
            }
