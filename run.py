#완성
import threading
import sys
import socket
from COSMOS.Plan.Planner import Planner
from COSMOS.Sensor.Tello8890Sensor import Tello8890Sensor
from COSMOS.Sensor.Tello11111Sensor import Tello11111Sensor
from COSMOS.Sensor.Tello8889Actor import Tello8889Actor
from COSMOS.Test.TelloVirtualController import TelloVirtualController
import os


"""
- Architecture: Sense - Plan - Act Pattern

- 입력방식(유선, 무선 및 포트)에 따라 Sense 계열 클래스 생성
- 연산을 담당하는 Planner 클래스 생성
- 출력방식(유선, 무선 및 포트)에 따라 Act 계열 클래스 생성

- Sense 계열 클래스들은 
    1) 데이터를 가져오고'
    2) 데이터를 Planner가 받아들일 수 있는 정보로 변경하고V2
    3) Planner에 저장
    
- Planner 클래스는
    1) 저장된 값을 원하는 정보로 가공(3차원 좌표값으로 변경)하고
    2) 가공한 정보를 바탕으로 회피 명령을 생성하고  n /
    3) 생성된 명령을 Planner 내부에 저장
    
- Act 계열 클래스들은 
    1) Planner에 저장된 값을 가져와서
    2) Drone이 이해할 수 있는 값으로 변경하고
    2) Actuator로 전송

- 이 모든 과정은 순차적이 아닌 병렬적으로 수행(사용자 명령이 존재하기 때문)
"""

class Main:
    
    def __init__(self):

        #os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

        print(">>> 프로그램 준비중...")
        #종료를 위한 stop_event
        self.stop_event = threading.Event()
        
        #Tello의 주소, 포트
        self.tello_address = ('192.168.10.1',8889) #텔로에게 접속했을 때, 텔로의 IP주소
        
        #비행상태 확인을 위한 변수
        self.is_takeoff = False
        
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
        Main()
    else:
        print(">>>파이썬 3.9만 지원됩니다.")
        print(">>>현재 버젼: {}".format(sys.version))
    print(">>> 프로그램 종료")