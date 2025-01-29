import cv2
import sys
from sahi.models import Yolov8DetectionModel
from sahi.predict import get_sliced_prediction
import supervision as sv
import numpy as np

# Check the number of command-line arguments
if len(sys.argv) != 8:
    print("Usage: python yolov8_video_inference.py <model_path> <input_video_path> <output_video_path> <slice_height> <slice_width> <overlap_height_ratio> <overlap_width_ratio>")
    sys.exit(1)

# Get command-line arguments
model_path = sys.argv[1]
input_video_path = sys.argv[2]
output_video_path = sys.argv[3]
slice_height = int(sys.argv[4])
slice_width = int(sys.argv[5])
overlap_height_ratio = float(sys.argv[6])
overlap_width_ratio = float(sys.argv[7])

# Load YOLOv8 model with SAHI
detection_model = Yolov8DetectionModel(
    model_path=model_path,
    confidence_threshold=0.1,
    device="cuda"  # or "cpu"
)

# Open input video
cap = cv2.VideoCapture(input_video_path)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")

# Set up output video writer
out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

# Create bounding box and label annotators
#box_annotator = sv.BoundingBoxAnnotator(thickness=1)
box_annotator = sv.BoxCornerAnnotator(thickness=2)
label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=2)

# Process each frame
frame_count = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Perform sliced inference on the current frame using SAHI
    result = get_sliced_prediction(
        image=frame,
        detection_model=detection_model,
        slice_height=slice_height,
        slice_width=slice_width,
        overlap_height_ratio=overlap_height_ratio,
        overlap_width_ratio=overlap_width_ratio
    )

    # Extract data from SAHI result
    object_predictions = result.object_prediction_list

    # Initialize lists to hold the data
    xyxy = []
    confidences = []
    class_ids = []
    class_names = []

    # Loop over the object predictions and extract data
    for pred in object_predictions:
        bbox = pred.bbox.to_xyxy()  # Convert bbox to [x1, y1, x2, y2]
        xyxy.append(bbox)
        confidences.append(pred.score.value)
        class_ids.append(pred.category.id)
        class_names.append(pred.category.name)

    # Check if there are any detections
    if xyxy:
        # Convert lists to numpy arrays
        xyxy = np.array(xyxy, dtype=np.float32)
        confidences = np.array(confidences, dtype=np.float32)
        class_ids = np.array(class_ids, dtype=int)

        # Create sv.Detections object
        detections = sv.Detections(
            xyxy=xyxy,
            confidence=confidences,
            class_id=class_ids
        )

        # Prepare labels for label annotator
        labels = [
            f"{class_name} {confidence:.2f}"
            for class_name, confidence in zip(class_names, confidences)
        ]

        # Annotate frame with detection results
        annotated_frame = frame.copy()
        annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=detections)
        annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections, labels=labels)
    else:
        # If no detections, use the original frame
        annotated_frame = frame.copy()

    # Write the annotated frame to the output video
    out.write(annotated_frame)

    frame_count += 1
    print(f"Processed frame {frame_count}", end='\r')

# Release resources
cap.release()
out.release()
print("\nInference complete. Video saved at", output_video_path)

