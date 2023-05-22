#완성
from COSMOS.Basemodel.ObjectDetector import ObjectDetector
from COSMOS.Calculation import ValueChanger
import torch
import numpy as np
from PIL import Image,ImageTk
import cv2
from time import time



class YOLOv5(ObjectDetector):
    """
    객체인식을 담당하는 클래스(YOLOv5s 사용)
    """
    
    
    
    def __init__(self, planner):
        
        #planner 객체
        self.__planner = planner
        
        #모델 객체 생성
        #local에서 YOLO 사용: https://stackoverflow.com/questions/71251177/how-to-use-yolov5-api-with-flask-offline
        self.__model = torch.hub.load(r'COSMOS/ObjectDetector/yolov5', 'custom', path=r'COSMOS/ObjectDetector/yolov5s.pt', source='local')
        self.__classes = self.__model.names
        self.__device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(">>>>>>GPU 사용:",self.__device)
        
    
    def detect_from_frame(self, frame:np.fromstring, tof: int): 
        """
        frame에서 객체를 감지하고, 윈도우를 적용한 image와 윈도우 리턴
        """
        #감지한 객체 윈도우들의 좌표를 저장할 리스트
        window_coor_list = []
        
        #프레임에서 감지한 객체들의 레이블들, 좌표들이 들어있는 리스트
        object_label_list, object_coor_list = self.__score_frame(frame)
        
        #감지한 객체들을 frame에 표시
        n = len(object_label_list)
        x_shape, y_shape = frame.shape[1], frame.shape[0]
        for i in range(n):
            row = object_coor_list[i]
            if row[4] >= 0.2:
                #윈도우의 좌표 계산
                x1, y1, x2, y2 = int(row[0]*x_shape), int(row[1]*y_shape), int(row[2]*x_shape), int(row[3]*y_shape)
                
                #윈도우의 좌표를 window_coor_list에 저장
                window_coor_list.append(((x1,y1), (x2,y2)))
                
                #frame에 그리기
                RGB = (0, 255, 0) #(초록색)
                cv2.rectangle(frame, (x1, y1), (x2, y2), RGB, 2)
                name = self.__classes[int(object_label_list[i])]
                text = "{}: ({},{}), ({},{})".format(name, x1,y1,x2,y2)
                cv2.putText(frame, text, (x1, y1-20), cv2.FONT_HERSHEY_SIMPLEX, 0.9, RGB, 2)
        
        #IR 윈도우의 좌상단좌표(x,y), IR 윈도우의 우하단좌표(x,y)
        ir_window_left_up_coor, ir_window_right_down_coor = self.__calculate_ir_window_coor(tof,y_shape,x_shape)
            
        #IR 윈도우에 겹치는 윈도우의 좌표 튜플을 저장할 변수
        fusion_window_coor = None 
        
        #IR 윈도우가 존재하는 경우, 
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
        image = Image.fromarray(frame)
        
        #image를 imagetk 형식으로 변환
        image = ImageTk.PhotoImage(image)
        
        if fusion_window_coor is None and tof and tof < 50:
            #안전거리 내이면, 스크린 크기의 장애물로 지정
            fusion_window_coor = ((0,0), (x_shape,y_shape))
        
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
        
        #영상에서 IR 윈도우의 가로 픽셀 계산
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
    

    def __score_frame(self, frame):
        # frame: 단일 프레임; numpy/list/tuple 형식
        # return: 프레임에서 모델이 감지한 객체의 레이블과 좌표
        self.__model.to(self.__device)
        frame = [frame]
        object_label_and_coor_list = self.__model(frame)
        labels, coors = object_label_and_coor_list.xyxyn[0][:, -1].cpu().numpy(), object_label_and_coor_list.xyxyn[0][:, :-1].cpu().numpy()
        return labels, coors