import os
from ultralytics import YOLO
import cv2

def main_fun(video_path):
    # Mapping class IDs to labels
    id2class_map = {
        '0': 'with helmet',
        '1': 'without helmet',
        '2': 'rider',
        '3': 'number_plate'
    }

    # Specify the path of the YOLO model
    model = YOLO('./models/YOLO/helmet_best.pt')

    # Input video file path
    #video_path = r"D:\internship_final\uploads\helmet2.mp4"  # Replace with your video file path

    # Check if the file exists
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    print(f"Processing video: {os.path.basename(video_path)}")

    # Open the video file
    cap = cv2.VideoCapture(video_path)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Run YOLO prediction on the current frame
        results = model.predict(frame, imgsz=640, conf=0.5)

        # Annotate the frame with detection results
        annotated_frame = results[0].plot()

        # Display the annotated frame
        cv2.imshow("Helmet Detection", annotated_frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the video capture object and close display window
    cap.release()
    cv2.destroyAllWindows()

    print("Finished processing video.")
