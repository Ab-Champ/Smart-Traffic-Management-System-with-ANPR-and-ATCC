from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import os
from werkzeug.utils import secure_filename
import cv2
from app_instance import create_app
from dotenv import load_dotenv
import pymysql

# Load environment variables from .env file
load_dotenv()

# Initialize the app using the create_app function
app = create_app()

# Fetch camera IPs from environment variables (comma-separated list)
camera_ips_env = os.getenv('LIVE_CCTV_IPS', '')
if camera_ips_env:
    app.config['CAMERA_IPS'] = camera_ips_env.split(',')
else:
    app.config['CAMERA_IPS'] = []

UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



def dbconnection():
     connection = pymysql.connect(host='127.0.0.1',database='traffic control',user='root',password='Abchamp@75')
     return connection


# Routes
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/validate_login', methods=['POST'])
def validate_login():
    username = request.form.get('username')
    password = request.form.get('password')
    connection = dbconnection()
    print(f"number_plate......................{connection}")
    print(username, password)
    with connection.cursor() as cursor:
        # Use parameterized query to prevent SQL injection
        sql_query = "SELECT * FROM login_details WHERE username = %s AND password = %s"
        cursor.execute(sql_query, (username, password))
        result = cursor.fetchone() 
        print("SQL Statement Executed:", sql_query)
        if result:
            print(f"User {username} logged in successfully.")
            return redirect(url_for('home'))
    
    return render_template('login.html', error="Invalid username or password.")


@app.route('/home')
def home():
    return render_template('home.html')


import pymysql

@app.route('/search', methods=['GET', 'POST'])
def search_license_plate():
    number_plate = request.form.get('number_plate')  # Get license plate from form
    connection = dbconnection()
    print(f"Database Connection: {connection}")
    vehicle_data = None
    error = None
    if request.method == 'POST' and number_plate:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Use parameterized query to prevent SQL injection
            sql_query = "SELECT * FROM vehicle_data WHERE number_plate = %s"
            cursor.execute(sql_query, (number_plate,))
            result = cursor.fetchone()  # Fetch single record
            print("SQL Statement Executed:", sql_query)
            if result:
                print(f"Vehicle data found for {number_plate}")
                vehicle_data = result  # No need to manually map if using DictCursor
            else:
                error = "No details found for the entered number plate."

    return render_template('search.html', vehicle_data=vehicle_data, error=error)

################################################################################
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
@app.route('/upload_video', methods=['GET', 'POST'])
def upload_video():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('upload_video.html', error="No file selected.")
        file = request.files['file']
        if file and allowed_file(file.filename):
            # Ensure the filename is safe
            filename = secure_filename(file.filename)
            # Save the file in the static/uploads directory
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return render_template('upload_video.html', success=True, filename=filename)
        else:
            return render_template('upload_video.html', error="Invalid file type. Allowed: mp4, avi, mov, mkv.")
    return render_template('upload_video.html')


@app.route('/results', methods=['GET'])
def results():
    return render_template('results.html')

@app.route('/logout')
def logout():
    return redirect(url_for('login'))

#############################################################################################

def load_videos_from_folder(videos_folder):
    """Load all video files from the provided folder."""
    video_files = []
    for filename in os.listdir(videos_folder):
        if filename.endswith(".mp4"):
            video_files.append({"path": os.path.join(videos_folder, filename), "road_name": filename})
    return video_files

def load_videos_from_folder(videos_folder):
    """Load all video files from the provided folder."""
    video_files = []
    for filename in os.listdir(videos_folder):
        if filename.endswith(".mp4"):
            video_files.append({"path": os.path.join(videos_folder, filename), "road_name": filename})
    return video_files
########################################################################################
from flask import session

@app.route('/live_monitoring', methods=['GET', 'POST'])
def live_monitoring():
    if request.method == 'POST':
        # Save form data in session to repopulate the form after submission
        session['numCameras'] = request.form.get('numCameras', 1)
        session['processType'] = request.form.get('processType', 'anpr')

        # Save camera inputs (IPs or File Uploads)
        num_cameras = int(session['numCameras'])
        session['cameraInputs'] = []
        for i in range(1, num_cameras + 1):
            ip_or_file_key = f"cameraIp{i}" if f"cameraIp{i}" in request.form else f"cameraFile{i}"
            session['cameraInputs'].append({
                'label': f'Camera {i} Input',
                'type': 'text' if f"cameraIp{i}" in request.form else 'file',
                'name': ip_or_file_key,
                'value': request.form.get(ip_or_file_key, '')
            })

        # Perform any processing here
        print("Processing started...")

        # Redirect back to the page with the same form values
        return redirect('/live_monitoring')

    # For GET requests, repopulate the form using session data or defaults
    num_cameras = session.get('numCameras', 1)
    process_type = session.get('processType', 'anpr')
    camera_inputs = session.get('cameraInputs', [
        {'label': 'Camera 1 Input', 'type': 'file', 'name': 'cameraFile1', 'value': ''}
    ])

    return render_template(
        'live_monitoring.html',
        numCameras=num_cameras,
        processType=process_type,
        cameraInputs=camera_inputs
    )

######################################################################################################

#####################################################################################################################
from atcc import *
import os

from anpr_video import PlateFinder  # Ensure PlateFinder is properly imported
from anpr_video import OCR  # Ensure OCR is properly imported
from anpr_video import *
from ultralytics import YOLO

@app.route('/start_processing', methods=['POST'])
def start_processing():
    """Handle form submission and start video processing."""
    process_type = request.form.get('processType')
    num_cameras = int(request.form.get('numCameras', 0))
    input_files = []

    # Save uploaded files
    for i in range(1, num_cameras + 1):
        file = request.files.get(f'cameraFile{i}')
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            input_files.append(filepath)

    # Handle processes
    if process_type.lower() == 'atcc':
        # Display videos in OpenCV
        # display_videos(input_files)
        model = YOLO("yolov8n.pt")
        process_atcc_videos(input_files, model)
        return render_template('live_monitoring.html', video_paths=input_files, process="ATCC")
    
    elif process_type.lower() == 'anpr':
        start_anpr(input_files)
        return render_template('live_monitoring.html', video_paths=input_files, process="ANPR")

    else:
        return "Invalid process type selected", 400
#####################################################################################
    
    
#####################################################################################

from atcc import *
@app.route('/atcc', methods=['POST'])
def atcc():
    try:
        # Get number of cameras and files
        num_cameras = int(request.form.get('numCameras', 0))
        uploaded_files = []
        for i in range(1, num_cameras + 1):
            file_key = f'cameraFile{i}'
            if file_key in request.files:
                file = request.files[file_key]
                if file and file.filename != '':
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'])
                    file.save(file_path)
                    uploaded_files.append(file_path)

        # Add logic for processing the uploaded files using ATCC
        if uploaded_files:
            print(f"Processing ATCC for files: {uploaded_files}")
            # Example: Call your ATCC function here
            model = YOLO("yolov8n.pt")
            process_videos(file_path, model)
        return render_template('Traffic_signal_controlling.html', success=True)
        return {"success": True, "message": "ATCC processing started successfully."}, 200
    except Exception as e:
        print(f"Error during ATCC: {e}")
        return {"success": False, "message": "An error occurred during ATCC processing."}, 500
#####################################################################################
from helmet_detection import *  # Import your helmet detection logic
import os

@app.route('/helmet_detection', methods=['POST'])
def helmet_detection():
    """
    Handle the request for helmet detection and process the uploaded video(s).
    """
    try:
        # Collect all uploaded files
        uploaded_files = [request.files[key] for key in request.files if key.startswith('cameraFile')]

        if not uploaded_files:
            return jsonify({"success": False, "message": "No files uploaded."}), 400

        # Process each uploaded file
        for file_index, video_file in enumerate(uploaded_files, start=1):
            # Save the file to the uploads folder
            video_path = os.path.join(UPLOAD_FOLDER, video_file.filename)
            video_file.save(video_path)

            # Call the helmet detection function
            print(f"Processing file {file_index}: {video_path}")
            main_fun(video_path)  # Pass the video file path to the detection logic

        return jsonify({"success": True, "message": "Helmet Detection started for all videos. Check OpenCV window for output."}), 200

    except Exception as e:
        print(f"Error during Helmet Detection: {e}")
        return jsonify({"success": False, "message": "Error during Helmet Detection."}), 500

#####################################################################################

from traffic_violation import *
import os

@app.route('/traffic_violation_detection', methods=['POST'])
def traffic_violation_detection():
    """
    Handle the request for traffic violation detection and process the uploaded video(s).
    """
    try:
        # Collect all uploaded files
        uploaded_files = [request.files[key] for key in request.files if key.startswith('cameraFile')]

        if not uploaded_files:
            return jsonify({"success": False, "message": "No files uploaded."}), 400

        # Process each uploaded file
        for file_index, video_file in enumerate(uploaded_files, start=1):
            # Save the file to the uploads folder
            video_path = os.path.join(UPLOAD_FOLDER, video_file.filename)
            video_file.save(video_path)

            # Call the detection function
            print(f"Processing file {file_index}: {video_path}")
            main(video_path)

        return jsonify({"success": True, "message": "Traffic Violation Detection started for all videos. Check OpenCV window for output."}), 200

    except Exception as e:
        print(f"Error during Traffic Violation Detection: {e}")
        return jsonify({"success": False, "message": "Error during Traffic Violation Detection."}), 500

##############################################################################################
from heatmap_visualization import *
import os
@app.route('/heatmap_visualisation', methods=['POST'])
def heatmap_visualisation():
    """
    Handle the request for heatmap visualization and display the processed videos.
    """
    # Retrieve uploaded files
    num_cameras = int(request.form.get('numCameras', 0))
    input_files = []

    for i in range(1, num_cameras + 1):
        file = request.files.get(f'cameraFile{i}')
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            input_files.append(filepath)

    # Initialize YOLO model
    model = YOLO("yolov8n.pt")

    # Process and display videos for heatmap visualization
    process_videos(input_files, model)

    # Provide confirmation once the process is complete
    return "Heatmap visualization displayed in OpenCV window", 200

##################################

from accident import AccidentDetectionSystem
from concurrent.futures import ThreadPoolExecutor
import os

@app.route('/accident_detection', methods=['POST'])
def accident_detection():
    """
    Handle the request for accident detection and process uploaded videos using multithreading.
    """
    try:
        # Retrieve the number of uploaded files
        num_cameras = int(request.form.get('numCameras', 0))
        input_files = []

        # Collect uploaded video files
        for i in range(1, num_cameras + 1):
            file = request.files.get(f'cameraFile{i}')
            if file:
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)
                input_files.append(filepath)

        if not input_files:
            return "No files uploaded. Please upload at least one video.", 400

        # Debugging: Print uploaded file paths
        print("Uploaded files:", input_files)

        # Initialize the AccidentDetectionSystem
        model_path = "../models/best.pt"  # Use your YOLO model path
        detector = AccidentDetectionSystem(model_path, conf_threshold=0.4, enable_gui=False)

        # Define a thread-safe function to process a single video
        def process_single_video(video_path):
            try:
                print(f"Processing video: {video_path}")
                output_path = os.path.join(UPLOAD_FOLDER, f"processed_{os.path.basename(video_path)}")
                detector.process_video_with_gui(video_path, output_path)
                print(f"Completed processing for: {video_path}")
            except Exception as e:
                print(f"Error processing {video_path}: {e}")

        # Use ThreadPoolExecutor to process videos in parallel
        max_threads = min(len(input_files), 6)  # Limit threads to 4 or the number of videos
        with ThreadPoolExecutor(max_threads) as executor:
            executor.map(process_single_video, input_files)

        # GUI Visualization for all videos
        print("Launching GUI visualization...")
        detector.process_video_with_gui(input_files)

        return "Accident Detection completed. Check the GUI window for output.", 200

    except Exception as e:
        print(f"Error during accident detection: {e}")
        return f"An error occurred: {str(e)}", 500

##############################################################################################
from triple_riding import *
import os
@app.route('/triple_riding_detection', methods=['POST'])
def triple_riding_detection():
    """
    Handle the request for triple riding detection and process the uploaded video(s).
    """
    try:
        # Collect all uploaded files
        uploaded_files = [request.files[key] for key in request.files if key.startswith('cameraFile')]

        if not uploaded_files:
            return jsonify({"success": False, "message": "No files uploaded."}), 400

        # Process each uploaded file
        for file_index, video_file in enumerate(uploaded_files, start=1):
            # Save the file to the uploads folder
            video_path = os.path.join(UPLOAD_FOLDER, video_file.filename)
            video_file.save(video_path)

            # Call the detection function
            print(f"Processing file {file_index}: {video_path}")
            detect_triple_riding(video_path)

        return jsonify({"success": True, "message": "Triple Riding Detection started for all videos. Check OpenCV window for output."}), 200

    except Exception as e:
        print(f"Error during Triple Riding Detection: {e}")
        return jsonify({"success": False, "message": "Error during Triple Riding Detection."}), 500


##############################################################################################
import cv2
import numpy as np

# Define button coordinates on the top (adjusted for larger buttons and space between them)
BUTTONS = {
   
    "Heatmap Visualization": (10, 10, 450, 60),
    "Accident Detection": (470, 10, 450, 60),
    "Triple Riding Detection": (930, 10, 450, 60),
    "Helmet Detection": (1390, 10, 450, 60),
    # "Traffic Signal Control": (1850, 10, 450, 60)# Adjusted x-coordinate for spacing
    }

# Store the last clicked button
clicked_button = None

def mouse_callback(event, x, y, flags, param):
    """Mouse callback to detect button clicks."""
    global clicked_button
    if event == cv2.EVENT_LBUTTONDOWN:
        for label, (bx, by, bw, bh) in BUTTONS.items():
            if bx < x < bx + bw and by < y < by + bh:
                clicked_button = label
                print(f"Button clicked: {label}")
                # Trigger specific action based on the button clicked
                if label == "Heatmap Visualization":
                    print("Trigger Heatmap Visualization")
                elif label == "Accident View":
                    print("Trigger Accident View")
                elif label == "Triple Riding Detection":
                    print("Triple Riding Detection")
                elif label == "Helmet Detection":
                    print("Trigger Helmet Detection")
                elif label == "Traffic Signal Control":
                    print("Trigger Traffic Signal Control")
    
def display_videos(video_paths):
    """Display videos in OpenCV with horizontal and vertical concatenation and buttons at the top."""
    cap_list = [cv2.VideoCapture(path) for path in video_paths]

    cv2.namedWindow("ATCC Process - Video Grid", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("ATCC Process - Video Grid", mouse_callback)

    while True:
        frames = []
        for cap in cap_list:
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
            else:
                frames.append(None)

        # Stop if all videos are done
        if all(frame is None for frame in frames):
            break

        # Filter valid frames and find the minimum height for resizing
        valid_frames = [frame for frame in frames if frame is not None]
        if not valid_frames:
            break

        min_height = min(frame.shape[0] for frame in valid_frames)
        resized_frames = [
            cv2.resize(frame, (int(frame.shape[1] * min_height / frame.shape[0]), min_height))
            if frame is not None else np.zeros((min_height, 1, 3), dtype=np.uint8)  # Black placeholder
            for frame in frames
        ]

        # Group frames into rows of 2
        rows = [resized_frames[i:i+2] for i in range(0, len(resized_frames), 2)]

        # Ensure all frames in a row have the same height and pad if necessary
        padded_rows = []
        for row in rows:
            max_width = max(frame.shape[1] for frame in row)
            padded_row = [
                cv2.copyMakeBorder(frame, 0, 0, 0, max_width - frame.shape[1], cv2.BORDER_CONSTANT, value=(0, 0, 0))
                for frame in row
            ]
            # Horizontally concatenate the frames in the row
            padded_rows.append(np.hstack(padded_row))

        # Ensure all rows have the same width by padding
        max_row_width = max(row.shape[1] for row in padded_rows)
        padded_rows = [
            cv2.copyMakeBorder(row, 0, 0, 0, max_row_width - row.shape[1], cv2.BORDER_CONSTANT, value=(0, 0, 0))
            for row in padded_rows
        ]

        # Vertically concatenate the rows
        grid_frame = np.vstack(padded_rows)

        # Create a blank canvas for the button area (top of the window)
        button_area = np.zeros((100, grid_frame.shape[1], 3), dtype=np.uint8)  # Button bar height set to 100

        # Draw buttons on the top with larger font size
        font_scale = 1.2  # Increased font scale for bigger text
        for label, (x, y, w, h) in BUTTONS.items():
            cv2.rectangle(button_area, (x, y), (x + w, y + h), (200, 200, 200), -1)  # Gray button
            # Draw the text with a larger font size
            cv2.putText(button_area, label, (x + 10, y + 40), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 3)

        # Combine the button area on top with the video grid below it
        combined_frame = np.vstack((button_area, grid_frame))

        # Display the concatenated grid with buttons at the top
        cv2.imshow("ATCC Process - Video Grid", combined_frame)

        # Wait for user input (mouse clicks or key presses)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    # Release all video captures and close OpenCV windows
    for cap in cap_list:
        cap.release()
    cv2.destroyAllWindows()



if __name__ == "__main__":
    # Create the upload folder if it does not exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)