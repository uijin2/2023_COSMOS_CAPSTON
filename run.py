#완성
from threading import Thread
from ackermann_msgs.msg import AckermannDriveStamped
import sys
import socket
import rospy
import time
from COSMOS.Plan.Planner import Planner
from COSMOS.Sensor.Tello8890Sensor import Tello8890Sensor
from COSMOS.Sensor.Tello11111Sensor import Tello11111Sensor
from COSMOS.Sensor.Tello8889Actor import Tello8889Actor
from COSMOS.Test.TelloVirtualController import TelloVirtualController
from COSMOS.Donkey.PCA9685 import PCA9685
import os

class Main(object):
    
    def __init__(self):


        print(">>> 프로그램 준비중...")
        #종료를 위한 stop_event
        self.stop_event = Thread.Event()
        
        #Tello의 주소, 포트
        self.tello_address = ('192.168.10.1',8889) #텔로에게 접속했을 때, 텔로의 IP주소
        
        #비행상태 확인을 위한 변수
        self.is_takeoff = False

        print("차량 연결 대기종...")

        self._throttle = PCA9685(channel=0, busnum=1)
        self._steering_servo = PCA9685(channel=1, busnum=1) 

        print("차량 연결 완료")

        
        #연결 정의
        print("드론 연결 대기중...")
        self.socket8889 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4, UDP 통신 소켓 객체를 생성(command용)
        self.socket8889.bind(('', 8889)) #소켓 객체를 텔로와 바인딩(8889 포트)

        
        self.socket8889.sendto("command".encode('utf-8'), self.tello_address)
        response,addr= self.socket8889.recvfrom(1024)
        print("8889 port connect: {} ({})".format(response,addr))
        
        self.socket8889.sendto("streamon".encode('utf-8'), self.tello_address)
        response,addr = self.socket8889.recvfrom(1024)
        print("video stream on: {} ({})".format(response,addr))
        
        self.socket8889.sendto("motoron".encode('utf-8'), self.tello_address)
        response,addr = self.socket8889.recvfrom(1024)
        print("motor on: {} ({})".format(response,addr))
    
        self.socket11111 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4, UDP 통신 소켓 객체를 생성(camera용)
        self.socket11111.bind(('', 11111)) #소켓 객체를 텔로와 바인딩(11111 포트)

        self.socket8890 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4, UDP 통신 소켓 객체를 생성(ToF sensor용)
        self.socket8890.bind(('', 8890)) #소켓 객체를 텔로와 바인딩(8890 포트)

        
        self.socket8889.sendto("downvision 1".encode('utf-8'), self.tello_address)
        
        
        print("드론 연결 완료")
        
        #객체 생성
        self.planner = Planner(self)
        
        self.tello8890sensor = Tello8890Sensor(self)
        self.tello11111sensor = Tello11111Sensor(self)
        self.tello8889actor = Tello8889Actor(self)
        
        self.virtual_controller = TelloVirtualController(self)


        #GUI 메인 루프 시작
        print(">>> 프로그램 실행")
        self.virtual_controller.root.mainloop()

        

if __name__ == "__main__":
    version = sys.version.split(".")
    if version[0] == "3" and version[1] == "9":
        rospy.init_node("donkey_control")

        myCar = Main("donkey_ros")

        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            rate.sleep()
    else:
        print(">>>파이썬 3.9만 지원됩니다.")
        print(">>>현재 버젼: {}".format(sys.version))
    print(">>> 프로그램 종료")