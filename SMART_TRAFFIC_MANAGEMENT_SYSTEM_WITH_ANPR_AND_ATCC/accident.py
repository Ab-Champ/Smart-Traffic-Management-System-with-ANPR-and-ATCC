import cv2
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO

class AccidentDetectionSystem:
    def __init__(self, model_path, conf_threshold=0.4, enable_gui=True):
        """Initialize the accident detection system."""
        self.conf_threshold = conf_threshold
        self.enable_gui = enable_gui
        self.output_dir = Path("accident_detections")
        self.output_dir.mkdir(exist_ok=True)

        try:
            # Load YOLOv8 model
            self.model = YOLO(model_path)
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            raise

    def process_frame(self, frame):
        """Process a single frame and return detections."""
        try:
            # Perform detection
            results = self.model(frame, conf=self.conf_threshold)
            return results[0]  # Return first result
        except Exception as e:
            print(f"Error processing frame: {str(e)}")
            return None

    def process_video_with_gui(self, video_paths):
        """Process multiple video feeds and display them in a grid GUI."""
        caps = [cv2.VideoCapture(path) for path in video_paths]
        target_width, target_height = 640, 480  # Consistent frame size for stacking

        while True:
            frames = []
            for cap in caps:
                ret, frame = cap.read()
                if ret:
                    frame_resized = cv2.resize(frame, (target_width, target_height))
                    results = self.process_frame(frame_resized)

                    # Process detections
                    if results is not None:
                        for box in results.boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            if conf > self.conf_threshold:
                                cv2.rectangle(frame_resized,
                                              (int(x1), int(y1)),
                                              (int(x2), int(y2)),
                                              (0, 255, 0), 2)
                                label = f"Accident {conf:.2f}"
                                cv2.putText(frame_resized, label,
                                            (int(x1), int(y1) - 10),
                                            cv2.FONT_HERSHEY_SIMPLEX,
                                            0.5, (0, 255, 0), 2)

                    frames.append(frame_resized)
                else:
                    frames.append(None)

            # Remove None frames and stack them
            valid_frames = [f for f in frames if f is not None]
            if len(valid_frames) == 0:
                break

            # Stack frames into a grid
            rows = [valid_frames[i:i+2] for i in range(0, len(valid_frames), 2)]
            stacked_rows = [np.hstack(row) for row in rows]
            grid_frame = np.vstack(stacked_rows)

            # Display the grid
            cv2.imshow("Accident Detection System", grid_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Release all resources
        for cap in caps:
            cap.release()
        cv2.destroyAllWindows()

    @staticmethod
    def detect_accident(video_paths):
        """Static method to initialize and run accident detection."""
        MODEL_PATH = "./models/best.pt"  # Replace with the path to your model
        CONFIDENCE_THRESHOLD = 0.4

        try:
            detector = AccidentDetectionSystem(MODEL_PATH, CONFIDENCE_THRESHOLD, enable_gui=True)
            detector.process_video_with_gui(video_paths)
        except Exception as e:
            print(f"Error: {str(e)}")
