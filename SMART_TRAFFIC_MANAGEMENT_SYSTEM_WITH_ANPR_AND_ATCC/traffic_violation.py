import numpy as np
import matplotlib.pyplot as plt
import cv2
import os
import pytesseract
import easyocr
import re
import mysql.connector
import pytesseract
from PIL import Image
from collections import deque
from mysql.connector import Error

# Database Connection Constants
DB_HOST = 'localhost'
DB_USER = 'divyansh'
DB_PASSWORD = 'admin123'
DB_NAME = 'traffic_management'

import cv2
# Define the license plate cascade
license_plate_cascade = cv2.CascadeClassifier("./models/YOLO/haarcascade_russian_plate_number.xml")
# Ensure the file exists and is loaded correctly
if license_plate_cascade.empty():
    raise FileNotFoundError("Haar Cascade for license plate detection not found. Ensure the path is correct.")


def detect_traffic_light_color(image, rect):
    # Extract rectangle dimensions
    x, y, w, h = rect
    # Extract region of interest (ROI) from the image based on the rectangle
    roi = image[y:y+h, x:x+w]
    
    # Convert ROI to HSV color space
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Define HSV range for red color
    red_lower = np.array([0, 120, 70])
    red_upper = np.array([10, 255, 255])
    
    # Define HSV range for yellow color
    yellow_lower = np.array([20, 100, 100])
    yellow_upper = np.array([30, 255, 255])

    # Create binary masks for detecting red and yellow in the ROI
    red_mask = cv2.inRange(hsv, red_lower, red_upper)
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    
    # Font details for overlaying text on the image
    font = cv2.FONT_HERSHEY_TRIPLEX
    font_scale = 1  
    font_thickness = 2  
    
    # Check which color is present based on the masks
    if cv2.countNonZero(red_mask) > 0:
        text_color = (0, 0, 255)
        message = "Detected Signal Status: Stop"
        color = 'red'
    elif cv2.countNonZero(yellow_mask) > 0:
        text_color = (0, 255, 255)
        message = "Detected Signal Status: Caution"
        color = 'yellow'
    else:
        text_color = (0, 255, 0)
        message = "Detected Signal Status: Go"
        color = 'green'
        
    # Overlay the detected traffic light status on the main image
    cv2.putText(image, message, (15, 70), font, font_scale+0.5, text_color, font_thickness+1, cv2.LINE_AA)
    # Add a separator line
    cv2.putText(image, 34*'-', (10, 115), font, font_scale, (255,255,255), font_thickness, cv2.LINE_AA)
    
    # Return the modified image and detected color
    return image, color


class LineDetector:
    def __init__(self, num_frames_avg=10):
        # Initialize two deque queues to hold y-coordinate values across frames
        self.y_start_queue = deque(maxlen=num_frames_avg)
        self.y_end_queue = deque(maxlen=num_frames_avg)

    
    def detect_white_line(self, frame, color, 
                          slope1=0.03, intercept1=920, slope2=0.03, intercept2=770, slope3=-0.8, intercept3=2420):
        
        # Function to map color names to BGR values
        def get_color_code(color_name):
            color_codes = {
                'red': (0, 0, 255),
                'green': (0, 255, 0),
                'yellow': (0, 255, 255)
                 }
            return color_codes.get(color_name.lower())

        frame_org = frame.copy()
        
        # Line equations for defining region of interest (ROI)
        def line1(x): return slope1 * x + intercept1
        def line2(x): return slope2 * x + intercept2
        def line3(x): return slope3 * x + intercept3

        height, width, _ = frame.shape
        
        # Create a mask to spotlight the line's desired area
        mask1 = frame.copy()
        # Set pixels below the first line to black in mask1
        for x in range(width):
            y_line = line1(x)
            mask1[int(y_line):, x] = 0

        mask2 = mask1.copy()
        # Set pixels above the second line to black in mask2
        for x in range(width):
            y_line = line2(x)
            mask2[:int(y_line), x] = 0

        mask3 = mask2.copy()
        # Set pixels to the left of the third line to black in mask3 (final mask)
        for y in range(height):
            x_line = line3(y)
            mask3[y, :int(x_line)] = 0

        # Convert the mask to grayscale
        gray = cv2.cvtColor(mask3, cv2.COLOR_BGR2GRAY)

        # Apply a Gaussian filter to the ROI
        blurred_gray = cv2.GaussianBlur(gray, (7, 7), 0)

        # Apply CLAHE to equalize the histogram
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray_clahe = clahe.apply(blurred_gray)

        # Perform edge detection
        edges = cv2.Canny(gray, 30, 100)

        # Perform a dilation and erosion to close gaps in between object edges
        dilated_edges = cv2.dilate(edges, None, iterations=1)
        edges = cv2.erode(dilated_edges, None, iterations=1)

        # Perform Hough Line Transform
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=160, maxLineGap=5)

        # Calculate x coordinates for the start and end of the line
        x_start = 0
        x_end = width - 1

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]

                # Calculate line parameters
                slope = (y2 - y1) / (x2 - x1 + np.finfo(float).eps)  # Add a small number to avoid division by zero
                intercept = y1 - slope * x1

                # Calculate corresponding y coordinates
                y_start = int(slope * x_start + intercept)
                y_end = int(slope * x_end + intercept)

                # Add the y_start and y_end values to the queues
                self.y_start_queue.append(y_start)
                self.y_end_queue.append(y_end)

        # Compute the average y_start and y_end values
        avg_y_start = int(sum(self.y_start_queue) / len(self.y_start_queue)) if self.y_start_queue else 0
        avg_y_end = int(sum(self.y_end_queue) / len(self.y_end_queue)) if self.y_end_queue else 0

        
        # Draw the line
        line_start_ratio=0.32
        x_start_adj = x_start + int(line_start_ratio * (x_end - x_start))  # Adjusted x_start
        avg_y_start_adj = avg_y_start + int(line_start_ratio * (avg_y_end - avg_y_start))  # Adjusted avg_y_start

        # Create a mask with the same size as the frame and all zeros (black)
        mask = np.zeros_like(frame)

        # Draw the line on the mask
        cv2.line(mask, (x_start_adj, avg_y_start_adj), (x_end, avg_y_end), (255, 255, 255), 4)

        # Determine which color channel(s) to change based on the color argument
        color_code = get_color_code(color)
        if color_code == (0, 255, 0):  # Green
            channel_indices = [1]
        elif color_code == (0, 0, 255):  # Red
            channel_indices = [2]
        elif color_code == (0, 255, 255):  # Yellow
            # Yellow in BGR is a combination of green and red channels.
            # Here we modify both green and red channels.
            channel_indices = [1, 2]
        else:
            raise ValueError('Unsupported color')

        # Change the specified color channels of the frame where the mask is white
        for channel_index in channel_indices:
            frame[mask[:,:,channel_index] == 255, channel_index] = 255
                
                
        # Calculate slope and intercept for the average green line
        slope_avg = (avg_y_end - avg_y_start) / (x_end - x_start + np.finfo(float).eps)
        intercept_avg = avg_y_start - slope_avg * x_start

        # Create a mask with the pixels above the green line set to black
        mask_line = np.copy(frame_org)
        for x in range(width):
            y_line = slope_avg * x + intercept_avg - 35
            mask_line[:int(y_line), x] = 0  # set pixels above the line to black

        return frame, mask_line
    


def extract_license_plate(frame, mask_line):    
    # Convert the image to grayscale (Haar cascades are typically trained on grayscale images)
    gray = cv2.cvtColor(mask_line, cv2.COLOR_BGR2GRAY)
    
    # Apply CLAHE to equalize the histogram
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    # Erode the image using a 2x2 kernel to remove noise
    kernel = np.ones((2, 2), np.uint8)
    gray = cv2.erode(gray, kernel, iterations=1)

    # Find the bounding box of non-black pixels
    non_black_points = cv2.findNonZero(gray)
    x, y, w, h = cv2.boundingRect(non_black_points)

    # Calculate the new width of the bounding box, excluding 30% on the right side
    w = int(w * 0.7)

    # Crop the image to the bounding box
    cropped_gray = gray[y:y+h, x:x+w]

    # Detect license plates in the image (this returns a list of rectangles)
    license_plates = license_plate_cascade.detectMultiScale(cropped_gray, scaleFactor=1.07, minNeighbors=15, minSize=(20, 20))

    # List to hold cropped license plate images
    license_plate_images = []

    # Loop over the license plates
    for (x_plate, y_plate, w_plate, h_plate) in license_plates:
        # Draw a rectangle around the license plate in the original frame (here you need the original coordinates)
        cv2.rectangle(frame, (x_plate + x, y_plate + y), (x_plate + x + w_plate, y_plate + y + h_plate), (0, 255, 0), 3)
    
        # Crop the license plate and append it to the list (here x_plate and y_plate are relative to cropped_gray)
        license_plate_image = cropped_gray[y_plate:y_plate+h_plate, x_plate:x_plate+w_plate]
        license_plate_images.append(license_plate_image)

    return frame, license_plate_images

def apply_ocr_to_image(license_plate_image):
    # Threshold the image
    _, img = cv2.threshold(license_plate_image, 120, 255, cv2.THRESH_BINARY)

    # Convert the image to a format suitable for Tesseract (if not already grayscale)
    if len(img.shape) == 3:  # Check if the image is colored (3 channels)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Use pytesseract to extract text from the image
    text = pytesseract.image_to_string(img, config='--psm 8')  # PSM 8 is used for single-word or sparse text recognition

    # Clean up and return the extracted text, if any
    text = text.strip()

    if text:
        return text  # Return the extracted text

    return "No text detected"  # Return a fallback message if no text is detected


def draw_penalized_text(frame):
    # Set font, scale, thickness, and color
    font = cv2.FONT_HERSHEY_TRIPLEX
    font_scale = 1  
    font_thickness = 2
    color = (255, 255, 255)  # White color
    
    # Initial position for Y-coordinate
    y_pos = 180
    
    # Put title on the frame
    cv2.putText(frame, 'Fined license plates:', (25, y_pos), font, font_scale, color, font_thickness)
    
    # Update Y-coordinate position
    y_pos += 80

    # Loop through all fined license plates
    for text in penalized_texts:
        # Add fined license plate text on the frame
        cv2.putText(frame, '->  '+text, (40, y_pos), font, font_scale, color, font_thickness)
        
        # Update Y-coordinate for next license plate
        y_pos += 60


def create_database_and_table(host, user, password, database):
    try:
        # Create a connection
        connection = mysql.connector.connect(
            host = host,
            user = user,
            password = password
        )
        
        if connection.is_connected():
            # Create a new database cursor
            cursor = connection.cursor()

            # Create a new database using the provided name
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            print(f"Database {database} created successfully!")

            # Use the newly created database
            cursor.execute(f"USE {database}")

            # Create a new table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS license_plates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    plate_number VARCHAR(255) NOT NULL UNIQUE,
                    violation_count INT DEFAULT 1
                )
            """)
            print("Table created successfully!")

            cursor.close()

    except Error as e:
        print("Error while connecting to MySQL", e)

    finally:
        if connection.is_connected():
            connection.close()


def update_database_with_violation(plate_number, host, user, password, database):
    try:
        connection = mysql.connector.connect(
            host = host,
            user = user,
            password = password,
            database = database
        )
        
        if connection.is_connected():
            cursor = connection.cursor()

            # Check if the license plate already exists in the table
            cursor.execute(f"SELECT violation_count FROM license_plates WHERE plate_number='{plate_number}'")
            result = cursor.fetchone()
            
            if result:
                # Increment violation_count by 1 if plate_number already exists
                cursor.execute(f"UPDATE license_plates SET violation_count=violation_count+1 WHERE plate_number='{plate_number}'")
            else:
                # Insert a new record if plate_number doesn't exist
                cursor.execute(f"INSERT INTO license_plates (plate_number) VALUES ('{plate_number}')")
            
            connection.commit()
            cursor.close()

    except Error as e:
        print("Error while connecting to MySQL", e)

    finally:
        if connection.is_connected():
            connection.close()


def print_all_violations(host, user, password, database):
    try:
        connection = mysql.connector.connect(
            host = host,
            user = user,
            password = password,
            database = database
        )
        
        if connection.is_connected():
            cursor = connection.cursor()

            # Fetch all violations from the database
            cursor.execute("SELECT plate_number, violation_count FROM license_plates ORDER BY violation_count DESC")
            result = cursor.fetchall()
            
            print("\n")
            print("-"*66)
            print("\nAll Registered Traffic Violations in the Database:\n")
            for record in result:
                print(f"Plate Number: {record[0]}, Violations: {record[1]}")
            
            cursor.close()

    except Error as e:
        print("Error while connecting to MySQL", e)

    finally:
        if connection.is_connected():
            connection.close()

def clear_license_plates(host, user, password, database):
    try:
        connection = mysql.connector.connect(
            host = host,
            user = user,
            password = password,
            database = database
        )
        
        if connection.is_connected():
            cursor = connection.cursor()

            # Delete all records from the table
            cursor.execute("DELETE FROM license_plates")

            connection.commit()
            cursor.close()

    except Error as e:
        print("Error while connecting to MySQL", e)

    finally:
        if connection.is_connected():
            connection.close()

def main(video_path):
    vid = cv2.VideoCapture(video_path)
    # Ensure the database and table exist (incorporates error handling)
    try:
        create_database_and_table(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
    except Error as err:
        print(f"Database creation error: {err}")

    # Clear the license plates from the previous run (optional)
    clear_license_plates(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)

    # Open the video file
    #vid = cv2.VideoCapture(r"D:\internship_final\final_project\uploads\traffic_video.mp4")

    # Check if video opened successfully
    if not vid.isOpened():
        print("Error opening video file")
        return

    # Create detector object
    detector = LineDetector()

    # Load pre-trained Haar Cascade for license plate detection
    global license_plate_cascade
    license_plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')

    # Initialize a list to hold penalized license plates
    global penalized_texts
    penalized_texts = []

    while vid.isOpened():
        ret, frame = vid.read()

        if not ret:
            break

        # Resize the frame for better performance (optional)
        frame = cv2.resize(frame, (1280, 720))

        # Detect traffic light (adjust rect coordinates as needed)
        rect = (1000, 50, 80, 160)
        frame, detected_color = detect_traffic_light_color(frame, rect)

        # Detect the white lane line based on traffic light color
        frame, mask_line = detector.detect_white_line(frame, detected_color)

        # Extract license plates from the processed frame
        frame, license_plate_images = extract_license_plate(frame, mask_line)

        # Apply OCR on each detected license plate
        for license_plate_image in license_plate_images:
            text = apply_ocr_to_image(license_plate_image)

            # Add the detected license plate to the list if it matches the pattern and is not already in the list
            if text is not None and re.match(r"^[A-Z]{2}\s[0-9]{3,4}$", text) and text not in penalized_texts:
                penalized_texts.append(text)
                print(f"\nFined license plate: {text}")

                    # Plot the license plate image
                plt.figure()
                plt.imshow(license_plate_image, cmap='gray')
                plt.axis('off')
                plt.show()

            # Only process unique license plates to avoid duplicates
            if text and text not in penalized_texts:
                penalized_texts.append(text)

                # Update the database with the detected license plate
                update_database_with_violation(text, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)

        # Overlay penalized license plates on the video
        draw_penalized_text(frame)

        # Display the frame
        cv2.imshow('Traffic Management System', frame)

        # Exit on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Print all violations from the database at the end
    print_all_violations(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)

    # Release video capture and close OpenCV windows
    vid.release()
    cv2.destroyAllWindows()

#if __name__ == "__main__":
#    main()