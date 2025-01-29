import cv2
from ultralytics import YOLO  # Import YOLOv8

# Load YOLOv8 model
model = YOLO('yolov8s.pt')  # 'yolov8s.pt' is the small version; replace with other versions if needed

# Set classes for motorbike and person
motorbike_class = 3  # Class ID for 'motorbike' in COCO dataset
person_class = 0     # Class ID for 'person' in COCO dataset

def detect_triple_riding(video_path):
    # Open video file or capture device
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Error: Unable to open video.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Perform object detection
        results = model(frame)

        # Extract boxes, scores, and class IDs
        detections = results[0].boxes.data.cpu().numpy()  # Convert to NumPy array
        motorbikes = []
        people = []

        # Separate motorbike and person detections
        for detection in detections:
            x1, y1, x2, y2, score, class_id = detection
            if int(class_id) == motorbike_class:
                motorbikes.append([x1, y1, x2, y2])
            elif int(class_id) == person_class:
                people.append([x1, y1, x2, y2])

        # Analyze motorbikes for triple riding
        for i, bike in enumerate(motorbikes, start=1):
            x1_b, y1_b, x2_b, y2_b = bike
            person_count = 0

            for person in people:
                x1_p, y1_p, x2_p, y2_p = person
                # Check overlap using Intersection over Union (IoU)
                if (
                    x1_p < x2_b and x2_p > x1_b and
                    y1_p < y2_b and y2_p > y1_b
                ):
                    person_count += 1

            # Determine offense status
            status = "offense" if person_count >= 3 else "not offense"
            print(f"Motorbike {i}: {person_count} people ({status})")

            # Annotate the frame
            color = (0, 0, 255) if status == "offense" else (0, 255, 0)
            cv2.rectangle(frame, (int(x1_b), int(y1_b)), (int(x2_b), int(y2_b)), color, 2)
            cv2.putText(
                frame, f"{person_count} ({status})",
                (int(x1_b), int(y1_b) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
            )

        # Display the frame
        cv2.imshow('Triple Riding Detection', frame)

        # Press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    cap.release()
    cv2.destroyAllWindows()


# Input video path
#video_path = r"D:\Traffic_voilation\traffic light\3691658-hd_1920_1080_30fps.mp4"
#detect_triple_riding(video_path)
