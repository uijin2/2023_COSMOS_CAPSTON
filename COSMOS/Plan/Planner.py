#완성
import threading
import sys
import traceback
from time import sleep
from COSMOS.Calculation import ValueChanger
from COSMOS.ObjectDetector.YOLOv8 import YOLOv8
from numpy import *



class Planner:
    """
    연산을 담당하는 클래스
    1) 거리 정보가 안전 거리 이내인 경우, 윈도우 정보(존재하는 경우)를 가져와서 물체의 실제 크기를 계산
    2) 계산한 크기를 바탕으로 물체의 실제 크기에 대한 좌표값을 생성
    3) 생성한 좌표값을 바탕으로 회피명령을 생성
    4) 회피명령을 queue에 저장
    """
    
    
    
    #=====Planner의 인스턴스를 생성시 실행될 함수=====
    def __init__(self, main):
        self.__printc("생성")
        
        self.endtime = 0
        #종료를 위한 stop_event
        self.__stop_event = main.stop_event
        
        #8889 소켓 & Tello address
        self.socket8889 = main.socket8889
        self.tello_address = main.tello_address
        
        self.model_path = "../models/yolov8m.onnx"
        self.threshold_distance = 60
        
        #종료를 위한 virtual controller 접근
        self.__main = main  
        
        #기본적으로 움직일 크기(cm)
        self.base_move_distance = 60
        
        #장애물 안전거리 보정치(cm) / Tello 지름의 절반보다 조금 큼
        self.safe_constant = 20
        
        #각 센서가 저장하는 값
        self.__cmd_queue = [] #명령을 저장할 큐
        self.__info_8889Sensor_tof = None #ToF
        self.__info_8889Sensor_cmd = None #수행확인명령
        self.__info_11111Sensor_frame = None #Frame
        self.__info_11111Sensor_image = None
        self.__info_11111Sensor_coor = None
        
        #객체감지를 위한 YOLOv5 객체
        self.__YOLOv8 = YOLOv8(self)
        
        
        #스레드 실행
        self.__thr_planner = threading.Thread(target=self.__func_planner, daemon=True)
        self.__thr_planner.start()
        
        
        self.__thr_stay_connection = threading.Thread(target=self.__func_stay_connection, daemon=True)
        self.__thr_stay_connection.start()
        
        self.__thr_requset_tof = threading.Thread(target=self.__func_request_tof, daemon=True)
        self.__thr_requset_tof.start()
                
                
                
    #=====스레드에서 실행될 함수=====
    #메인 스레드
    def __func_planner(self):
        self.__printf("실행",sys._getframe().f_code.co_name)
        thr_send = threading.Thread(target=self.__func_send,daemon=True)
        
        try:
            while not self.__stop_event.is_set() and not hasattr(self.__main, 'virtual_controller'):
                self.__printf("대기중",sys._getframe().f_code.co_name)
                sleep(1)
                
            self.__virtual_controller = self.__main.virtual_controller
                
            while not self.__stop_event.is_set():
                #1) frame 정보가 존재하면, frame에 대해 장애물 윈도우를 그리기
                
                frame, tof, object_coor =  self.__redraw_frame() #좌표받아오기
                
                #2) 장애물이 인지된 상태이고, 안정범위를 침범한 경우
                if self.__main.is_takeoff and object_coor:
                    #장애물의 실제 좌표를 계산
                    screen_size = (frame.shape[1], frame.shape[0])
                    real_coor = self.__create_real_coor(object_coor, tof, screen_size)                        
                    
                    print('___Object information___', real_coor)
                    
                    self.insert_cmd_queue("land")
                    sleep(0.5)
                    self.insert_cmd_queue("stop")

        except Exception as e:
            self.__printf("ERROR {}".format(e),sys._getframe().f_code.co_name)
            print(traceback.format_exc())
        
        self.__printf("종료",sys._getframe().f_code.co_name)
        
        #VirtualController 종료
        try:
            self.__virtual_controller.onClose()
        except Exception as e:
            self.__printf("ERROR {}".format(e),sys._getframe().f_code.co_name)
            print(traceback.format_exc())
    
    def __func_send(self):
            self.insert_cmd_queue(self.__avd_cmd)
            sleep(0.5)
            self.insert_cmd_queue("stop")
            
            
    #Tello에게 15초 간격으로 command를 전송하는 함수
    def __func_stay_connection(self):
        self.__printf("실행",sys._getframe().f_code.co_name)
        """
        Tello는 15초 이상 전달받은 명령이 없을시 자동 착륙하기 때문에,
        이를 방지하기 위해 5초 간격으로 Tello에게 "command" 명령을 전송
        """

        try:
            while not self.__stop_event.is_set():
                self.socket8889.sendto("command".encode(),self.tello_address)
                sleep(5)

        except Exception as e:
            self.__printf("ERROR {}".format(e),sys._getframe().f_code.co_name)
            print(traceback.format_exc())
        
        self.__printf("종료",sys._getframe().f_code.co_name)
        
        #virtual controller 종료
        try:
            self.__virtual_controller.onClose()
        except Exception as e:
            self.__printf("ERROR {}".format(e),sys._getframe().f_code.co_name)
            print(traceback.format_exc())


    def __func_request_tof(self):
        self.__printf("실행",sys._getframe().f_code.co_name)
        """
        Tello에게 0.2초 주기로 tof값 전송을 요청하는 스레드
        """
        try:
            while not self.__stop_event.is_set():
                self.socket8889.sendto("EXT tof?".encode(),self.tello_address)
                sleep(0.2)

        except Exception as e:
            self.__printf("ERROR {}".format(e),sys._getframe().f_code.co_name)
            print(traceback.format_exc())
        
        self.__printf("종료",sys._getframe().f_code.co_name)
        
        #virtual controller 종료
        try:
            self.__virtual_controller.onClose()
        except Exception as e:
            self.__printf("ERROR {}".format(e),sys._getframe().f_code.co_name)
            print(traceback.format_exc())

    
    def __redraw_frame(self):
        frame = self.get_info_11111Sensor_frame()
        tof = self.get_info_8890Sensor_tof()
        
        if frame is not None and frame.size != 0:     
            #YOLO에 frame을 전달하여, 객체인식이 적용된 이미지를 전달받음
            image, object_coor = self.__YOLOv8.detect_from_frame(frame, tof)
            
            #전달받은 값들을 저장
            self.set_info_11111Sensor_image(image)
            self.set_info_11111Sensor_coor(object_coor)
            return frame, tof, object_coor
        
        return None, None, None
    
    
    def __create_real_coor(self, object_coor, tof, screen_size):
        object_val = (tof, object_coor, screen_size) 
        object_coor = ValueChanger.change_val_to_coor(object_val)
        return object_coor

        
    
    #=====getter/setter 선언=====
    #cmd_queue
    def pop_cmd_queue(self):
        # self.__lock_cmd_queue.acquire()
        data = None
        if len(self.__cmd_queue)>0:
            data = self.__cmd_queue.pop(0)
        return data
    
    def insert_cmd_queue(self, info):
        # self.__lock_cmd_queue.acquire()
        self.__cmd_queue.append(info)
        # self.__lock_cmd_queue.release()
        
    #8890Sensor_tof   
    def get_info_8890Sensor_tof(self):
        # self.__lock_info_8889Sensor_tof.acquire()
        info = self.__info_8889Sensor_tof
        # self.__lock_info_8889Sensor_tof.release()
        return info
    
    def set_info_8890Sensor_tof(self, info):
        # self.__lock_info_8889Sensor_tof.acquire()
        self.__info_8889Sensor_tof = info
        # self.__lock_info_8889Sensor_tof.release()
        
        
    #8889Sensor_cmd
    def get_info_8889Sensor_cmd(self):
        # self.__lock_info_8889Sensor_cmd.acquire()
        info = self.__info_8889Sensor_cmd
        # self.__lock_info_8889Sensor_cmd.release()
        return info
    
    def set_info_8889Sensor_cmd(self, info):
        # self.__lock_info_8889Sensor_cmd.acquire()
        self.__info_8889Sensor_cmd = info
        # self.__lock_info_8889Sensor_cmd.release()
        
        
    #11111Sensor_frame    
    def get_info_11111Sensor_frame(self):
        # self.__lock_info_11111Sensor_frame.acquire()
        info = self.__info_11111Sensor_frame
        # self.__lock_info_11111Sensor_frame.release()
        return info
    
    def set_info_11111Sensor_frame(self, info):
        # self.__lock_info_11111Sensor_frame.acquire()
        self.__info_11111Sensor_frame = info
        # self.__lock_info_11111Sensor_frame.release()
    
    
    #11111Sensor_image    
    def get_info_11111Sensor_image(self):
        # self.__lock_info_11111Sensor_image.acquire()
        info = self.__info_11111Sensor_image
        # self.__lock_info_11111Sensor_image.release()
        return info
    
    def set_info_11111Sensor_image(self, info):
        # self.__lock_info_11111Sensor_image.acquire()
        self.__info_11111Sensor_image = info
        # self.__lock_info_11111Sensor_image.release()
            
            
    #11111Sensor_coor
    def get_info_11111Sensor_coor(self):
        # self.__lock_info_11111Sensor_coor.acquire()
        info = self.__info_11111Sensor_coor
        # self.__lock_info_11111Sensor_coor.release()
        return info
    
    def set_info_11111Sensor_coor(self, info):
        # self.__lock_info_11111Sensor_coor.acquire()
        self.__info_11111Sensor_coor = info
        # self.__lock_info_11111Sensor_coor.release()   
    


    #=====실행내역 출력을 위한 함수=====
    #클래스명을 포함하여 출력하는 함수
    def __printc(self,msg:str):
        print("[{}] {}".format(self.__class__.__name__,msg))
    
    #클래스명 + 함수명을 출력하는 함수
    def __printf(self,msg:str,fname:str):
        self.__printc("[{}]: {}".format(fname, msg))