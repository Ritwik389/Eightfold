"""
SENTINEL — Video Monitoring Utilities

Frame processing via MediaPipe FaceLandmarker (Tasks API) for gaze + lip tracking,
and YOLOv8 for object detection.

Supports two modes:
  1. WebRTC mode (primary): receives frames from streamlit-webrtc callbacks
  2. Fallback mode: captures from webcam via OpenCV VideoCapture daemon thread
"""

import os
import threading
import time
import logging
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass

import numpy as np
import cv2

from sentinel.config import (
    MIA_GAZE_DRIFT_SECONDS,
    MIA_YOLO_CLASSES_OF_INTEREST,
    SNAPSHOT_DIR,
)

logger = logging.getLogger("sentinel.video")

# ════════════════════════════════════════════════════════════
# MediaPipe Tasks API — FaceLandmarker
# ════════════════════════════════════════════════════════════
_FaceLandmarker = None
_BaseOptions = None
_FaceLandmarkerOptions = None
_RunningMode = None
_MpImage = None
_MpImageFormat = None

try:
    import mediapipe as mp
    from mediapipe.tasks.python.vision import (
        FaceLandmarker,
        FaceLandmarkerOptions,
        RunningMode,
    )
    from mediapipe.tasks.python import BaseOptions

    _FaceLandmarker = FaceLandmarker
    _BaseOptions = BaseOptions
    _FaceLandmarkerOptions = FaceLandmarkerOptions
    _RunningMode = RunningMode
    _MpImage = mp.Image
    _MpImageFormat = mp.ImageFormat
    logger.info("MediaPipe Tasks API (FaceLandmarker) available.")
except ImportError as e:
    logger.warning(f"MediaPipe not available: {e} — face tracking disabled.")
except Exception as e:
    logger.warning(f"MediaPipe import error: {e} — face tracking disabled.")

# Model path
_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
_FACE_LANDMARKER_MODEL = os.path.join(_MODEL_DIR, "face_landmarker.task")


@dataclass
class GazeDriftEvent:
    """Emitted when gaze drifts off-centre for too long."""
    timestamp_str: str
    duration: float
    gaze_x: float
    gaze_y: float
    snapshot_path: str


@dataclass
class ObjectDetectedEvent:
    """Emitted when YOLO detects a suspicious object."""
    timestamp_str: str
    class_name: str
    confidence: float
    snapshot_path: str


@dataclass
class LipApertureFrame:
    """Lip aperture measurement for a single frame."""
    timestamp: float
    aperture: float


class VideoMonitor:
    """
    Video frame processor for SENTINEL.
    Primary: frames from streamlit-webrtc via process_frame().
    Fallback: daemon thread with OpenCV VideoCapture.
    """

    # Face Mesh landmark indices (478 standard + 10 iris)
    LEFT_IRIS = [468, 469, 470, 471, 472]
    RIGHT_IRIS = [473, 474, 475, 476, 477]
    LEFT_EYE_CORNERS = (33, 133)
    RIGHT_EYE_CORNERS = (362, 263)
    UPPER_LIP = 13
    LOWER_LIP = 14
    NOSE_TIP = 1
    CHIN = 152

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cap = None
        self._face_landmarker = None
        self._yolo_model = None
        self._frame_count = 0
        self._current_frame = None
        self._lock = threading.Lock()

        # Gaze tracking state
        self._gaze_drift_start: Optional[float] = None
        self._last_gaze_x = 0.0
        self._last_gaze_y = 0.0

        # Lip aperture stream
        self._lip_apertures: list[LipApertureFrame] = []
        self._lip_aperture_buffer: list[float] = []

        # Event callbacks
        self._on_gaze_drift: Optional[Callable] = None
        self._on_object_detected: Optional[Callable] = None

        # UI state
        self._gaze_drifting = False
        self._last_yolo_detections: list[dict] = []
        self._face_detected = False

        # Mode
        self._webrtc_mode = False
        self._camera_available = False

    # ══════════════════════════════════════════════════════
    # MODEL LOADING
    # ══════════════════════════════════════════════════════

    def init_models(self):
        """Load FaceLandmarker and YOLO models."""
        self._load_face_landmarker()
        self._load_yolo()

    def _load_face_landmarker(self):
        """Load MediaPipe FaceLandmarker (Tasks API)."""
        if _FaceLandmarker is None:
            logger.warning("FaceLandmarker class unavailable — skipping.")
            return

        if not os.path.exists(_FACE_LANDMARKER_MODEL):
            logger.warning(
                f"FaceLandmarker model not found at {_FACE_LANDMARKER_MODEL}. "
                "Attempting download..."
            )
            self._download_model()

        if not os.path.exists(_FACE_LANDMARKER_MODEL):
            logger.warning("FaceLandmarker model not available — face tracking disabled.")
            return

        try:
            options = _FaceLandmarkerOptions(
                base_options=_BaseOptions(
                    model_asset_path=_FACE_LANDMARKER_MODEL
                ),
                running_mode=_RunningMode.IMAGE,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._face_landmarker = _FaceLandmarker.create_from_options(options)
            logger.info("MediaPipe FaceLandmarker initialised.")
        except Exception as e:
            logger.warning(f"FaceLandmarker init failed: {e}")
            self._face_landmarker = None

    @staticmethod
    def _download_model():
        """Download the face_landmarker.task model file."""
        try:
            import urllib.request
            os.makedirs(_MODEL_DIR, exist_ok=True)
            url = (
                "https://storage.googleapis.com/mediapipe-models/"
                "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            )
            logger.info(f"Downloading FaceLandmarker model from {url}...")
            urllib.request.urlretrieve(url, _FACE_LANDMARKER_MODEL)
            logger.info("FaceLandmarker model downloaded.")
        except Exception as e:
            logger.error(f"Model download failed: {e}")

    def _load_yolo(self):
        """Load YOLOv8 model."""
        try:
            from ultralytics import YOLO
            self._yolo_model = YOLO("yolov8n.pt")
            logger.info("YOLOv8 model loaded.")
        except Exception as e:
            logger.warning(f"YOLOv8 load failed: {e}")
            self._yolo_model = None

    # ══════════════════════════════════════════════════════
    # PRIMARY API — process_frame (from webrtc or daemon)
    # ══════════════════════════════════════════════════════

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process a single video frame through FaceLandmarker and YOLO.
        Returns an annotated frame for display.

        Args:
            frame: BGR numpy array from webcam.
        Returns:
            Annotated BGR numpy array.
        """
        self._frame_count += 1
        self._camera_available = True

        with self._lock:
            self._current_frame = frame.copy()

        # Face landmark detection every frame
        self._process_face_landmarks(frame)

        # YOLO every 10 frames
        if self._frame_count % 10 == 0:
            self._process_yolo(frame)

        return self._annotate_frame(frame)

    # ══════════════════════════════════════════════════════
    # FACE LANDMARK PROCESSING (Tasks API)
    # ══════════════════════════════════════════════════════

    def _process_face_landmarks(self, frame: np.ndarray):
        """Process frame through MediaPipe FaceLandmarker."""
        if self._face_landmarker is None:
            self._face_detected = False
            return

        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = _MpImage(
                image_format=_MpImageFormat.SRGB,
                data=rgb_frame,
            )
            result = self._face_landmarker.detect(mp_image)

            if not result.face_landmarks:
                self._face_detected = False
                return

            self._face_detected = True
            landmarks = result.face_landmarks[0]  # First face
            h, w, _ = frame.shape

            self._track_gaze(landmarks, w, h)
            self._track_lip_aperture(landmarks)

        except Exception as e:
            logger.debug(f"Face landmark processing error: {e}")
            self._face_detected = False

    def _track_gaze(self, landmarks, w, h):
        """Track iris position relative to eye corners."""
        try:
            # Landmark objects have .x, .y, .z (normalised 0-1)
            left_iris = np.mean(
                [[landmarks[i].x, landmarks[i].y] for i in self.LEFT_IRIS],
                axis=0,
            )
            right_iris = np.mean(
                [[landmarks[i].x, landmarks[i].y] for i in self.RIGHT_IRIS],
                axis=0,
            )

            l_inner = np.array([landmarks[self.LEFT_EYE_CORNERS[0]].x,
                                landmarks[self.LEFT_EYE_CORNERS[0]].y])
            l_outer = np.array([landmarks[self.LEFT_EYE_CORNERS[1]].x,
                                landmarks[self.LEFT_EYE_CORNERS[1]].y])
            r_inner = np.array([landmarks[self.RIGHT_EYE_CORNERS[0]].x,
                                landmarks[self.RIGHT_EYE_CORNERS[0]].y])
            r_outer = np.array([landmarks[self.RIGHT_EYE_CORNERS[1]].x,
                                landmarks[self.RIGHT_EYE_CORNERS[1]].y])

            l_eye_width = np.linalg.norm(l_outer - l_inner) + 1e-6
            r_eye_width = np.linalg.norm(r_outer - r_inner) + 1e-6

            l_gaze_x = (left_iris[0] - l_inner[0]) / l_eye_width - 0.5
            r_gaze_x = (right_iris[0] - r_inner[0]) / r_eye_width - 0.5
            gaze_x = (l_gaze_x + r_gaze_x) / 2.0

            l_gaze_y = (left_iris[1] - l_inner[1]) / l_eye_width - 0.5
            r_gaze_y = (right_iris[1] - r_inner[1]) / r_eye_width - 0.5
            gaze_y = (l_gaze_y + r_gaze_y) / 2.0

            self._last_gaze_x = gaze_x
            self._last_gaze_y = gaze_y

            if abs(gaze_x) > 0.35 or abs(gaze_y) > 0.30:
                if self._gaze_drift_start is None:
                    self._gaze_drift_start = time.time()
                    self._gaze_drifting = True
                elif time.time() - self._gaze_drift_start > MIA_GAZE_DRIFT_SECONDS:
                    snapshot_path = self.snapshot()
                    event = GazeDriftEvent(
                        timestamp_str=datetime.now().strftime("%H:%M:%S"),
                        duration=time.time() - self._gaze_drift_start,
                        gaze_x=gaze_x,
                        gaze_y=gaze_y,
                        snapshot_path=snapshot_path,
                    )
                    if self._on_gaze_drift:
                        self._on_gaze_drift(event)
                    self._gaze_drift_start = None
                    self._gaze_drifting = False
            else:
                self._gaze_drift_start = None
                self._gaze_drifting = False

        except Exception as e:
            logger.debug(f"Gaze tracking error: {e}")

    def _track_lip_aperture(self, landmarks):
        """Measure lip aperture normalised by face height."""
        try:
            upper = np.array([landmarks[self.UPPER_LIP].x,
                              landmarks[self.UPPER_LIP].y])
            lower = np.array([landmarks[self.LOWER_LIP].x,
                              landmarks[self.LOWER_LIP].y])

            nose_y = landmarks[self.NOSE_TIP].y
            chin_y = landmarks[self.CHIN].y
            face_h = abs(chin_y - nose_y) + 1e-6

            aperture = np.linalg.norm(upper - lower) / face_h

            self._lip_aperture_buffer.append(aperture)
            if len(self._lip_aperture_buffer) > 5:
                self._lip_aperture_buffer.pop(0)

            smoothed = float(np.mean(self._lip_aperture_buffer))
            self._lip_apertures.append(LipApertureFrame(
                timestamp=time.time(),
                aperture=smoothed,
            ))

            # Keep only last 5 minutes
            cutoff = time.time() - 300
            self._lip_apertures = [
                la for la in self._lip_apertures if la.timestamp > cutoff
            ]

        except Exception as e:
            logger.debug(f"Lip tracking error: {e}")

    # ══════════════════════════════════════════════════════
    # YOLO PROCESSING
    # ══════════════════════════════════════════════════════

    def _process_yolo(self, frame):
        """Run YOLOv8 object detection."""
        if self._yolo_model is None:
            return

        try:
            results = self._yolo_model(frame, verbose=False)
            if not results or len(results) == 0:
                self._last_yolo_detections = []
                return

            detections = results[0].boxes
            if detections is None:
                self._last_yolo_detections = []
                return

            person_boxes = []
            for i, box in enumerate(detections):
                cls_id = int(box.cls[0])
                cls_name = results[0].names[cls_id]
                conf = float(box.conf[0])
                if cls_name == "person" and conf > 0.5:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    area = (x2 - x1) * (y2 - y1)
                    person_boxes.append((i, area))

            primary_idx = None
            if person_boxes:
                person_boxes.sort(key=lambda p: p[1], reverse=True)
                primary_idx = person_boxes[0][0]

            flagged = []
            for i, box in enumerate(detections):
                cls_id = int(box.cls[0])
                cls_name = results[0].names[cls_id]
                conf = float(box.conf[0])

                if conf < 0.5 or cls_name not in MIA_YOLO_CLASSES_OF_INTEREST:
                    continue
                if cls_name == "person" and i == primary_idx:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                flagged.append({"class": cls_name, "conf": conf,
                                "box": (x1, y1, x2, y2)})

                snapshot_path = self.snapshot()
                event = ObjectDetectedEvent(
                    timestamp_str=datetime.now().strftime("%H:%M:%S"),
                    class_name=cls_name,
                    confidence=conf,
                    snapshot_path=snapshot_path,
                )
                if self._on_object_detected:
                    self._on_object_detected(event)

            self._last_yolo_detections = flagged

        except Exception as e:
            logger.debug(f"YOLO processing error: {e}")

    # ══════════════════════════════════════════════════════
    # ANNOTATION OVERLAY
    # ══════════════════════════════════════════════════════

    def _annotate_frame(self, frame: np.ndarray) -> np.ndarray:
        """Draw SENTINEL visual indicators on the frame."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # ─── SENTINEL badge ───
        cv2.rectangle(annotated, (w - 155, 5), (w - 5, 35), (20, 20, 20), -1)
        cv2.rectangle(annotated, (w - 155, 5), (w - 5, 35), (0, 200, 200), 1)
        cv2.putText(annotated, "SENTINEL", (w - 145, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 200), 1,
                    cv2.LINE_AA)

        # ─── Status dot ───
        if self._gaze_drifting:
            cv2.rectangle(annotated, (0, 0), (w - 1, h - 1), (0, 0, 255), 3)
            cv2.putText(annotated, "! GAZE DRIFT", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
                        cv2.LINE_AA)
        elif self._face_detected:
            cv2.circle(annotated, (w - 170, 20), 8, (0, 200, 0), -1)
        else:
            cv2.circle(annotated, (w - 170, 20), 8, (0, 200, 255), -1)

        # ─── YOLO detections ───
        for det in self._last_yolo_detections:
            x1, y1, x2, y2 = det["box"]
            label = f"{det['class']} {det['conf']:.0%}"
            color = (0, 0, 255) if det["class"] != "person" else (255, 165, 0)
            cv2.rectangle(annotated, (int(x1), int(y1)),
                          (int(x2), int(y2)), color, 2)
            cv2.putText(annotated, label, (int(x1), int(y1) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
                        cv2.LINE_AA)

        # ─── Lip aperture bar ───
        if self._lip_aperture_buffer:
            apt = float(np.mean(self._lip_aperture_buffer))
            bar_h = int(min(apt * 500, 60))
            bar_color = (0, 200, 0) if apt > 0.015 else (0, 0, 255)
            cv2.rectangle(annotated, (10, h - 70), (25, h - 70 + bar_h),
                          bar_color, -1)
            cv2.putText(annotated, "Lip", (5, h - 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

        return annotated

    # ══════════════════════════════════════════════════════
    # SNAPSHOT
    # ══════════════════════════════════════════════════════

    def snapshot(self) -> str:
        """Save current frame to SNAPSHOT_DIR. Returns file path."""
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filepath = os.path.join(SNAPSHOT_DIR, f"frame_{timestamp}.jpg")

        with self._lock:
            if self._current_frame is not None:
                try:
                    cv2.imwrite(filepath, self._current_frame)
                    return filepath
                except Exception as e:
                    logger.warning(f"Snapshot save failed: {e}")

        try:
            from PIL import Image
            img = Image.new("RGB", (640, 480), color=(30, 30, 30))
            img.save(filepath)
        except Exception:
            pass
        return filepath

    def get_lip_apertures(self, since: Optional[float] = None) -> list[LipApertureFrame]:
        """Get lip aperture stream, optionally filtered by timestamp."""
        if since is None:
            return list(self._lip_apertures)
        return [la for la in self._lip_apertures if la.timestamp >= since]

    # ══════════════════════════════════════════════════════
    # STARTUP / SHUTDOWN
    # ══════════════════════════════════════════════════════

    def start(self,
              on_gaze_drift: Optional[Callable] = None,
              on_object_detected: Optional[Callable] = None) -> bool:
        """Start video monitoring. Returns True if available."""
        self._on_gaze_drift = on_gaze_drift
        self._on_object_detected = on_object_detected
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        self.init_models()

        if self._webrtc_mode:
            self._camera_available = True
            return True

        try:
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                logger.warning("Webcam not available — text-only mode.")
                self._camera_available = False
                return False

            self._camera_available = True
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            return True

        except Exception as e:
            logger.warning(f"Video monitor init failed: {e}")
            self._camera_available = False
            return False

    def set_webrtc_mode(self, enabled: bool = True):
        """Enable webrtc mode — frames come via process_frame()."""
        self._webrtc_mode = enabled
        self._camera_available = enabled

    def set_callbacks(self,
                      on_gaze_drift: Optional[Callable] = None,
                      on_object_detected: Optional[Callable] = None):
        """Set event callbacks without starting capture."""
        self._on_gaze_drift = on_gaze_drift
        self._on_object_detected = on_object_detected

    def _run_loop(self):
        """Daemon thread capture loop (fallback mode)."""
        while self._running:
            try:
                ret, frame = self._cap.read()
                if not ret:
                    time.sleep(0.033)
                    continue
                self.process_frame(frame)
                time.sleep(0.033)
            except Exception as e:
                logger.error(f"Video loop error: {e}")
                time.sleep(0.1)

    def stop(self):
        """Stop monitoring and release resources."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
        if self._face_landmarker is not None:
            try:
                self._face_landmarker.close()
            except Exception:
                pass

    @property
    def is_available(self) -> bool:
        return self._camera_available
