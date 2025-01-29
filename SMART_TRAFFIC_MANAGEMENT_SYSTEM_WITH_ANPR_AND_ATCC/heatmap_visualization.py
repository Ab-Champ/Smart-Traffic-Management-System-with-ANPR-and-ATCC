#heatmap visualization
import cv2
import numpy as np
from ultralytics import YOLO
import os

# def load_videos_from_folder(videos_folder):
#     """Load all video files from the provided folder."""
#     import os
#     video_files = []
#     for filename in os.listdir(videos_folder):
#         if filename.endswith(".mp4"):
#             video_files.append({"path": os.path.join(videos_folder, filename), "road_name": filename})
#     return video_files

def generate_heatmap(frame, vehicle_positions, intensity=15):
    """
    Generate a heatmap of vehicle positions and overlay it on the frame.
    Args:
        frame: The original video frame.
        vehicle_positions: List of (x, y) center points of detected vehicles.
        intensity: The heatmap intensity factor.
    Returns:
        Frame with heatmap overlay.
    """
    heatmap = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.float32)
    
    for x, y in vehicle_positions:
        heatmap[int(y), int(x)] += 1
    
    heatmap = cv2.GaussianBlur(heatmap, (0, 0), intensity)
    heatmap = np.clip(heatmap / heatmap.max(), 0, 1) * 255  # Normalize and scale to 255
    
    heatmap_colored = cv2.applyColorMap(heatmap.astype(np.uint8), cv2.COLORMAP_JET)
    overlayed_frame = cv2.addWeighted(frame, 0.6, heatmap_colored, 0.4, 0)
    return overlayed_frame

def track_vehicle_movement(vehicle_centers, prev_centers):
    """
    Draw arrows to show vehicle movement direction.
    Args:
        vehicle_centers: Current frame's vehicle centers.
        prev_centers: Previous frame's vehicle centers.
    Returns:
        List of movement vectors.
    """
    movement_vectors = []
    for i, (cx, cy) in enumerate(vehicle_centers):
        if i < len(prev_centers):
            px, py = prev_centers[i]
            movement_vectors.append(((int(px), int(py)), (int(cx), int(cy))))
    return movement_vectors

def process_frame(frame, model, road_name, directions, prev_positions):
    """
    Process a video frame: Detect objects, classify directions, and overlay information.
    Args:
        frame: The input video frame.
        model: The YOLO model for object detection.
        road_name: Name of the road the video corresponds to.
        directions: Dictionary to count vehicle directions.
        prev_positions: List of vehicle positions from the previous frame.
    Returns:
        Processed frame with detection overlays and vehicle count per direction.
    """
    results = model(frame)
    detections = results[0].boxes.data.cpu().numpy()
    vehicle_count = {"car": 0, "truck": 0, "motorcycle": 0, "bus": 0}
    vehicle_positions = []

    for det in detections:
        x1, y1, x2, y2, conf, class_id = det
        class_id = int(class_id)
        label = model.names[class_id]
        
        if label in vehicle_count:
            vehicle_count[label] += 1
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            vehicle_positions.append((center_x, center_y))

            if center_x < frame.shape[1] / 2:
                directions['left'] += 1
            else:
                directions['right'] += 1

            color = (0, 255, 0) if conf > 0.5 else (0, 0, 255)
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            cv2.putText(frame, f"{label} {conf:.2f}", (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Add Heatmap Overlay
    frame = generate_heatmap(frame, vehicle_positions)

    # Add Movement Arrows
    movement_vectors = track_vehicle_movement(vehicle_positions, prev_positions)
    for start, end in movement_vectors:
        cv2.arrowedLine(frame, start, end, (0, 255, 0), 2)

    cv2.putText(frame, f"Road: {road_name}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    y_offset = 50
    for direction, count in directions.items():
        cv2.putText(frame, f"{direction.capitalize()}: {count}", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_offset += 25

    total_vehicles = sum(vehicle_count.values())
    cv2.putText(frame, f"Total Vehicles: {total_vehicles}", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    y_offset += 25
    
    # Determine signal based on vehicle count
    signal_color, signal_rgb = determine_signal(total_vehicles)
    cv2.putText(frame, f"Signal: {signal_color}", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, signal_rgb, 2)
    
    return frame, vehicle_count, vehicle_positions

def determine_signal(total_vehicles):
    """Determine the signal color based on vehicle count."""
    if total_vehicles < 10:
        return "Green", (0, 255, 0)
    elif total_vehicles < 20:
        return "Yellow", (0, 255, 255)
    else:
        return "Red", (0, 0, 255)

def process_videos(video_files, model):
    """Process a list of video file paths and display results."""
    caps = []
    road_names = []  # Use filenames as road names if not provided
    prev_positions_list = []  # Store vehicle positions for each video

    # Initialize video capture objects for each file
    for video_path in video_files:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file: {video_path}")
            continue
        caps.append(cap)
        road_names.append(os.path.basename(video_path))  # Use file name as default road name
        prev_positions_list.append([])

    # Define the target size for all frames (ensure consistent dimensions for stacking)
    target_width, target_height = 640, 480

    while True:
        processed_frames = []
        for i, cap in enumerate(caps):
            ret, frame = cap.read()
            if not ret:
                print(f"End of video stream for {road_names[i]}.")
                caps[i].release()
                continue

            directions = {"left": 0, "right": 0}
            frame_resized = cv2.resize(frame, (target_width, target_height))  # Resize all frames to the same size

            processed_frame, vehicle_count, vehicle_positions = process_frame(
                frame_resized, model, road_names[i], directions, prev_positions_list[i]
            )

            # Update previous positions
            prev_positions_list[i] = vehicle_positions

            # Determine signal based on vehicle count
            total_vehicles = sum(vehicle_count.values())
            signal_color, signal_rgb = determine_signal(total_vehicles)

            # Add processed frame to the list
            processed_frames.append(processed_frame)

        if len(processed_frames) == 0:
            break

        # Stack the frames into a grid
        rows = []
        for i in range(0, len(processed_frames), 2):
            row = np.hstack(processed_frames[i:i + 2]) if i + 1 < len(processed_frames) else processed_frames[i]
            rows.append(row)

        # Ensure all rows have consistent height for vertical stacking
        row_heights = [row.shape[0] for row in rows]
        max_height = max(row_heights)
        rows_resized = [cv2.resize(row, (target_width * (row.shape[1] // target_width), max_height)) for row in rows]

        grid_frame = np.vstack(rows_resized)  # Stack the rows into a grid

        cv2.imshow("Traffic Management System", grid_frame)

        if cv2.waitKey(20) & 0xFF == ord('q'):
            break

    for cap in caps:
        cap.release()
    cv2.destroyAllWindows()

# if __name__ == "__main__":
#     videos_folder = r"C:\Users\Mugdhi Saxena\Documents\Mugdhi S\Infosys Springboard\internship\project files\videos"  # Provide your folder path here
#     model = YOLO("yolov8n.pt")
#     process_videos(videos_folder, model)
