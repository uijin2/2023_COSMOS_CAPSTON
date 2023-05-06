#완성
import sys
from COSMOS.Basemodel.Sensor import Sensor
from COSMOS.Decoder import H264decoder
from COSMOS.Decoder.h264_39 import h264decoder
import threading
import traceback
from time import sleep
import cv2
import numpy as np



class Tello11111Sensor(Sensor):
    
    #=====Tello11111Sensor의 인스턴스를 생성시 실행될 함수=====
    def __init__(self, main):
        
        self.__printc("생성")
        self.__stop_event = main.stop_event
        self.__main = main
        self.__planner = main.planner
        self.__socket = main.socket11111
        
        self.__decoder = h264decoder.H264Decoder()
        self.__packet_data = bytes()
        
        #스레드 실행
        self.__thr_sensor = threading.Thread(target=self.__func_sensor, daemon=True)
        self.__thr_sensor.start()
        
        
    
    
    #=====스레드에서 실행될 함수=====
    def __func_sensor(self):
        self.__printf("실행",sys._getframe().f_code.co_name)
        try:
            while not self.__stop_event.is_set() and not hasattr(self.__main, 'virtual_controller'):
                self.__printf("대기중",sys._getframe().f_code.co_name)
                sleep(1)
            
            self.__virtual_controller = self.__main.virtual_controller
            
            while not self.__stop_event.is_set():
                self.take_data_from_sensor()
                self.change_data_to_info()

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
    
    
    def take_data_from_sensor(self): 
        """
        센서로부터 data를 가져온다
        """
        data:bytes = self.__socket.recv(2048)
        self.__packet_data += data
        
        
    
    def change_data_to_info(self):
        """
        data를 Planner가 이해할 수 있는 info로 변경한다
        """
        dist = np.array([ -0.094055,  -0.163824, 0.002484,  -0.009124])
        mtx = np.array([[831.628888,0,340.055398],[0,830.450549,331.060396],[0,0,1]])

        packet_data = self.__packet_data
        if len(packet_data) != 1460: # frame의 끝이 아니면,
            for frame in H264decoder.decode(self.__decoder, packet_data): 

                height, width = frame.shape[:2]

                newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (height, width),0)

                frame = cv2.undistort(frame, mtx, dist, None, newcameramtx)
                x, y, w, h = roi
                frame = frame[y:y+h, x:x+w]

                self.save_to_planner(frame)

            self.__packet_data = bytes()
    
    
    def save_to_planner(self, info):
        """
        info를 Planner에 저장한다
        """
        self.__planner.set_info_11111Sensor_frame(info)
        
            
    
    #=====실행내역 출력을 위한 함수=====
    #클래스명을 포함하여 출력하는 함수
    def __printc(self,msg:str):
        print("[{}] {}".format(self.__class__.__name__,msg))
    
    #클래스명 + 함수명을 출력하는 함수
    def __printf(self,msg:str,fname:str):
        self.__printc("[{}]: {}".format(fname, msg))