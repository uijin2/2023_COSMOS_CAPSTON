#완성
from CAD.Basemodel.ObjectDetector import ObjectDetector
from CAD.Calculation import ValueChanger
import numpy as np
from PIL import Image,ImageTk
import cv2
import onnxruntime
from CAD.ObjectDetector.utils import xywh2xyxy, nms


class YOLOv8(ObjectDetector):
    """
    객체인식을 담당하는 클래스
    """
    
    def __init__(self, planner):

        self.class_names = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
               'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
               'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
               'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
               'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
               'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
               'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard',
               'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase',
               'scissors', 'teddy bear', 'hair drier', 'toothbrush']

        # Create a list of colors for each class where each color is a tuple of 3 integer values
        rng = np.random.default_rng(3)
        self.colors = rng.uniform(0, 255, size=(len(self.class_names), 3))

        self.__planner = planner
        
        self.conf_threshold = 0.5
        self.iou_threshold = 0.5
        self.path = "CAD/ObjectDetector/models/yolov8m.onnx"
        self.session = onnxruntime.InferenceSession(self.path,
                                                    providers=['CUDAExecutionProvider',
                                                               'CPUExecutionProvider'])
        # Get model info
        self.get_input_details()
        self.get_output_details()

      
        

    def get_input_details(self):
        model_inputs = self.session.get_inputs()
        self.input_names = [model_inputs[i].name for i in range(len(model_inputs))]

        self.input_shape = model_inputs[0].shape
        self.input_height = self.input_shape[2]
        self.input_width = self.input_shape[3]

    def get_output_details(self):
        model_outputs = self.session.get_outputs()
        self.output_names = [model_outputs[i].name for i in range(len(model_outputs))]
        
    
    
    def detect_from_frame(self, frame:np.fromstring, tof:int): 
        """
        frame에서 객체를 감지하고, 윈도우를 적용한 image와 윈도우 리턴
        """        

        window_coor_list = []

        self.height, self.width = frame.shape[:2]

        input_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Resize input image
        input_frame = cv2.resize(input_frame, (self.input_width, self.input_height))

        # Scale input pixel values to 0 to 1
        input_frame = input_frame / 255.0
        input_frame = input_frame.transpose(2, 0, 1)
        input_tensor = input_frame[np.newaxis, :, :, :].astype(np.float32)
        
        # Perform inference on the image
        outputs = self.session.run(self.output_names, {self.input_names[0]: input_tensor})

        self.boxes, self.scores, self.class_ids = self.process_output(outputs)

        mask_frame = frame.copy()
        det_frame = frame.copy()

        size = min([self.height, self.width]) * 0.0006
        text_thickness = int(min([self.height, self.width]) * 0.001)

        # Draw bounding boxes and labels of detections
        for box, score, class_id in zip(self.boxes, self.scores, self.class_ids):
            color = self.colors[class_id]

            x1, y1, x2, y2 = box.astype(int)

            # Draw rectangle
            cv2.rectangle(det_frame, (x1, y1), (x2, y2), color, 2)

            # Draw fill rectangle in mask image
            cv2.rectangle(mask_frame, (x1, y1), (x2, y2), color, -1)

            label = self.class_names[class_id]
            caption = f'{label} {int(score * 100)}%'
            (tw, th), _ = cv2.getTextSize(text=caption, fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                                        fontScale=size, thickness=text_thickness)
            th = int(th * 1.2)

            cv2.rectangle(det_frame, (x1, y1),
                        (x1 + tw, y1 - th), color, -1)
            cv2.rectangle(mask_frame, (x1, y1),
                        (x1 + tw, y1 - th), color, -1)
            cv2.putText(det_frame, caption, (x1, y1),
                        cv2.FONT_HERSHEY_SIMPLEX, size, (255, 255, 255), text_thickness, cv2.LINE_AA)

            cv2.putText(mask_frame, caption, (x1, y1),
                        cv2.FONT_HERSHEY_SIMPLEX, size, (255, 255, 255), text_thickness, cv2.LINE_AA)
        
        combined_frame = cv2.addWeighted(mask_frame, 0.3, det_frame, 0.7, 0)
            
        fusion_window_coor = None #IR 윈도우에 겹치는 윈도우의 좌표 튜플을 저장할 변수
        
        #IR 윈도우의 좌표를 계산하여 저장
        ir_window_left_up_coor, ir_window_right_down_coor = self.__calculate_ir_window_coor(tof,self.height,self.width)
        
        #IR 윈도우가 존재(ToF가 적정거리)인 경우, 
        if ir_window_left_up_coor and ir_window_right_down_coor:
            #IR 윈도우를 frame에 반영
            RGB = (255, 0, 0) #(빨간색)
            cv2.rectangle(frame, ir_window_left_up_coor, ir_window_right_down_coor, RGB, 5)
            cv2.putText(frame, "IR AREA", (ir_window_left_up_coor[0], ir_window_left_up_coor[1] - 20), cv2.FONT_ITALIC, 0.5, (255, 255, 255), 1)
    
            #IR 윈도우에 겹치는 윈도우들을 모아 하나의 윈도우로 변환
            fusion_window_coor = ValueChanger.change_windows_to_window(window_coor_list, ir_window_left_up_coor, ir_window_right_down_coor)
            
            #겹치는 윈도우를 frame에 반영
            RGB = (0, 0, 255) #(파란색)
            cv2.rectangle(frame, fusion_window_coor[0], fusion_window_coor[1], RGB, 5)
        
        #frame을 image로 변환
        image = Image.fromarray(combined_frame)

        #image = Image.fromarray(frame1)
        
        #image를 imagetk 형식으로 변환
        image = ImageTk.PhotoImage(image)
        
        return (image, fusion_window_coor)
    
    
    def __calculate_ir_window_coor(self, tof, height, width):
        #ToF의 측정가능 거리는 약 60cm
        if tof is None or tof > 60 or tof <= 3:
            return None, None
        
        x = tof - 3
        
        #스크린의 높이, 너비 픽셀
        screen_height = height
        screen_width = width
        
        #IR 윈도우의 좌상단 y좌표, IR 윈도우의 우하단 y좌표를 저장할 변수
        ir_window_left_up_coor_y = None
        ir_window_right_down_coor_y = None
        
        #IR 윈도우의 좌상단 x좌표, IR 윈도우의 우하단 x좌표를 저장할 변수
        ir_window_left_up_coor_x = None
        ir_window_right_down_coor_x = None
        
        #영상에서 IR 윈도우의 세로 픽셀 계산
        height_length_fov = 0.758 * x
        height_length_tof_start = 0.203 * x - 4.472
        height_length_tof_end = 0.555 * x - 5.528
        
        height_proportion_start = height_length_tof_start / height_length_fov
        height_proportion_end = height_length_tof_end / height_length_fov
        
        if height_proportion_start <= 0:
            ir_window_left_up_coor_y = 0
        else:
            ir_window_left_up_coor_y = int(height_proportion_start*screen_height)
        
        if height_proportion_end <= 0:
            ir_window_right_down_coor_y = 0
        else:
            ir_window_right_down_coor_y = int(height_proportion_end*screen_height)
        
        # 영상에서 IR 윈도우의 가로 픽셀 계산
        width_length_fov = 1.048 * x
        width_length_tof_start = 0.348 * x + 0.528
        width_length_tof_end = 0.7 * x - 0.528
        
        width_proportion_start = width_length_tof_start / width_length_fov
        width_proportion_end = width_length_tof_end / width_length_fov
        
        if width_proportion_start <= 0:
            ir_window_left_up_coor_x = 0
        else:
            ir_window_left_up_coor_x = int(width_proportion_start*screen_width)
            
        if width_proportion_end <= 0:
            ir_window_right_down_coor_x = 0
        else:
            ir_window_right_down_coor_x = int(width_proportion_end*screen_width)
            
        ir_window_left_up_coor = (ir_window_left_up_coor_x, ir_window_left_up_coor_y)
        ir_window_right_down_coor = (ir_window_right_down_coor_x, ir_window_right_down_coor_y)
        
        return (ir_window_left_up_coor, ir_window_right_down_coor)
    
    
    def process_output(self, output):
        predictions = np.squeeze(output[0]).T

        # Filter out object confidence scores below threshold
        scores = np.max(predictions[:, 4:], axis=1)
        predictions = predictions[scores > self.conf_threshold, :]
        scores = scores[scores > self.conf_threshold]

        if len(scores) == 0:
            return [], [], []

        # Get the class with the highest confidence
        class_ids = np.argmax(predictions[:, 4:], axis=1)

        # Get bounding boxes for each object
        boxes = self.extract_boxes(predictions)

        # Apply non-maxima suppression to suppress weak, overlapping bounding boxes
        indices = nms(boxes, scores, self.iou_threshold)

        return boxes[indices], scores[indices], class_ids[indices]
    
    def extract_boxes(self, predictions):
        # Extract boxes from predictions
        boxes = predictions[:, :4]

        # Scale boxes to original image dimensions
        boxes = self.rescale_boxes(boxes)

        # Convert boxes to xyxy format
        boxes = xywh2xyxy(boxes)

        return boxes
    
    def rescale_boxes(self, boxes):

        # Rescale boxes to original image dimensions
        input_shape = np.array([self.input_width, self.input_height, self.input_width, self.input_height])
        boxes = np.divide(boxes, input_shape, dtype=np.float32)
        boxes *= np.array([self.width, self.height, self.width, self.height])
        return boxes
    
    
    
