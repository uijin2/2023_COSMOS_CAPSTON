#완성
import sys
import tkinter
import threading
from PIL import ImageTk
from time import sleep
import traceback
import numpy as np
from PIL import Image,ImageTk



class TelloVirtualController:
    """
    가상의 컨트롤러를 의미하는 클래스
    -GUI 화면을 띄움
    -Tello의 ToF값을 화면에 출력
    -YOLO의 감지화면을 화면에 출력
    -키보드 및 화면의 버튼을 통해 Tello를 조작
    -thread_stay_connection 스레드를 통해 지속적으로 Tello에게 "command" 메세지를 전달
    -종료시 stop_event를 실행
    """



    #=====VirtualController의 인스턴스를 생성시 실행될 함수=====
    def __init__(self, main):
        self.__printc("생성")
        
        #Planner
        self.__socket8889 = main.socket8889
        self.__tello_address = main.tello_address
        self.__planner = main.planner

        #종료를 위한 stop_event
        self.__stop_event:threading.Event = main.stop_event
        self.__thread_stop_event = threading.Event()

        #Tello 조작시 동작범위
        self.__cm = 50
        self.__degree = 50
        
        #화면, tof를 갱신할 시간
        self.__renewal_tof_time = 0.3

        #queue에 동시접근을 방지하기 위한 lock
        self.__lock = threading.Lock()

        #화면 기본 설정
        self.root = tkinter.Tk()  # GUI 화면 객체 생성
        self.root.geometry("-10+0")
        # self.root.attributes('-fullscreen',True)
        self.root.wm_title("CAD TEST for RMTT") #GUI 화면의 title 설정  
        self.root.wm_protocol("WM_DELETE_WINDOW", self.__onClose) #종료버튼을 클릭시 실행할 함수 설정

        #화면에 띄울 문구 설정
        self.__text_tof = tkinter.Label(self.root, text= "ToF: None", font='Helvetica 10 bold') ##re
        self.__text_tof.pack(side='top')

        self.__text_keyboard = tkinter.Label(self.root, justify="left", text="""
        W - Move Tello Up\t\t\tArrow Up - Move Tello Forward
        S - Move Tello Down\t\t\tArrow Down - Move Tello Backward
        A - Rotate Tello Counter-Clockwise\t\tArrow Left - Move Tello Left
        D - Rotate Tello Clockwise\t\tArrow Right - Move Tello Right
        """)
        self.__text_keyboard.pack(side="top")

        #영상을 출력하기 위한 panel 선언
        self.__panel_image = None

        #착륙 버튼
        self.__btn_landing = tkinter.Button(self.root, text="Land", relief="raised", command=self.__land)
        self.__btn_landing.pack(side="bottom", fill="both", expand="yes", padx=10, pady=5)

        #이륙 버튼
        self.__btn_takeoff = tkinter.Button(self.root, text="Takeoff", relief="raised", command=self.__takeoff)
        self.__btn_takeoff.pack(side="bottom", fill="both", expand="yes", padx=10, pady=5)

        #키보드 버튼들과 Tello 동작을 바인딩
        self.__keyboard_connection = tkinter.Frame(self.root, width=100, height=2)
        self.__keyboard_connection.bind('<KeyPress-q>', self.__on_keypress_q)
        self.__keyboard_connection.bind('<KeyPress-w>', self.__on_keypress_w)
        self.__keyboard_connection.bind('<KeyPress-s>', self.__on_keypress_s)
        self.__keyboard_connection.bind('<KeyPress-a>', self.__on_keypress_a)
        self.__keyboard_connection.bind('<KeyPress-d>', self.__on_keypress_d)
        self.__keyboard_connection.bind('<KeyPress-Up>', self.__on_keypress_up)
        self.__keyboard_connection.bind('<KeyPress-Down>', self.__on_keypress_down)
        self.__keyboard_connection.bind('<KeyPress-Left>', self.__on_keypress_left)
        self.__keyboard_connection.bind('<KeyPress-Right>', self.__on_keypress_right)
        self.__keyboard_connection.pack(side="bottom")
        self.__keyboard_connection.focus_set()

        #실행될 스레드 선언
        self.__thread_update_tof = threading.Thread(target=self.__func_update_tof, daemon=True)
        self.__thread_update_tof.start()

        self.__thread_print_video = threading.Thread(target=self.__func_print_video, daemon=True)
        self.__thread_print_video.start()
    


    #=====버튼을 클릭했을 때 실행될 함수들=====
    def __land(self): #return: Tello의 receive 'OK' or 'FALSE'
        self.__send_cmd('land')

    def __takeoff(self): #return: Tello의 receive 'OK' or 'FALSE'
         self.__send_cmd('takeoff')



    #=====키보드를 입력했을 때 실행될 함수들=====
    def __on_keypress_q(self, event):
        self.__printm("Q", "stop")
        self.__send_cmd("stop")
    
    
    def __on_keypress_w(self, event):
        self.__printm("W","up")
        self.__move('up',self.__cm)


    def __on_keypress_s(self, event):
        self.__printm("S","down")
        self.__move('down',self.__cm)


    def __on_keypress_a(self, event):
        self.__printr("A","CCW")
        self.__rotate("ccw",self.__degree)


    def __on_keypress_d(self, event):
        self.__printr("D","CW")
        self.__rotate("cw",self.__degree)


    def __on_keypress_up(self, event):
        self.__printm("UP","forward")
        self.__move('forward',self.__cm)


    def __on_keypress_down(self, event):
        self.__printm("DOWN","back")
        self.__move('back',self.__cm)


    def __on_keypress_left(self, event):
        self.__printm("LEFT","left")
        self.__move('left',self.__cm)


    def __on_keypress_right(self, event):
        self.__printm("RIGHT","right")
        self.__move('right',self.__cm)


    def __move(self, direction, distance): 
        """
        direction: up, down, forward, back, right, left
        distance: 20~500 cm
        """
        self.__send_cmd("{} {}".format(direction, distance))
    
    
    def __rotate(self, direction, degree):
        """
        direction: ccw, cw
        degree: 0~360 degree
        """
        self.__send_cmd("{} {}".format(direction, degree))



    #=====스레드에서 실행될 함수=====
    #Tello에게서 0.3초 간격으로 ToF값을 받아와 GUI를 갱신하는 함수
    def __func_update_tof(self):
        self.__printf("실행",sys._getframe().f_code.co_name)
        try:
            while not self.__thread_stop_event.is_set():
                tof = self.__planner.get_info_8889Sensor_tof()
                self.__text_tof.config(text = "ToF: {} cm".format(tof))
                sleep(self.__renewal_tof_time)
        except Exception as e:
            self.__printf("ERROR {}".format(e),sys._getframe().f_code.co_name)
            print(traceback.format_exc())
        
        self.__printf("종료",sys._getframe().f_code.co_name)



    #객체인식 화면을 출력하는 함수
    def __func_print_video(self):
        self.__printf("실행",sys._getframe().f_code.co_name)
        try:
            while not self.__thread_stop_event.is_set():
                # ORIGIN START
                image:ImageTk.PhotoImage = self.__planner.get_info_11111Sensor_image()
                # ORIGIN END

                if self.__panel_image is None: 
                    self.__panel_image:tkinter.Label = tkinter.Label(image=image)
                    self.__panel_image.image = image
                    self.__panel_image.pack(side="right", padx=10, pady=10)
                
                else:
                    self.__panel_image.configure(image=image)
                    self.__panel_image.image = image


        except Exception as e:
            self.__printf("ERROR {}".format(e),sys._getframe().f_code.co_name)
            print(traceback.format_exc())
        
        self.__printf("종료",sys._getframe().f_code.co_name)
    


    #=====Tello에게 보낼 명령을 controller queue에 저장하는 함수=====
    def __send_cmd(self, msg:str):
        # self.__lock.acquire() #락 획득
        try:
            self.insert_controller_queue(msg)
            sleep(0.4)
            self.insert_controller_queue("stop")

        except Exception as e:
            self.__printf("ERROR {}".format(e),sys._getframe().f_code.co_name)
            print(traceback.format_exc())
        # self.__lock.release() #락 해제

    # def insert_controller_queue(self,cmd):
    #     self.__controller_queue.append(cmd)
    
    # def pop_controller_queue(self):
    #     data = None
    #     if len(self.__controller_queue)>0:
    #         data = self.__controller_queue.pop(0)
    #     return data
    def insert_controller_queue(self,cmd):
        self.__planner.insert_cmd_queue(cmd)
    
    

    #=====종료버튼을 클릭시 실행할 함수=====
    def __onClose(self):
        self.__socket8889.sendto("land".encode('utf-8'), self.__tello_address)
        sleep(0.5)
        self.__socket8889.sendto("motoroff".encode('utf-8'), self.__tello_address)
        sleep(0.5)
        
        #update_tof, print_video를 종료
        self.__thread_stop_event.set()
        self.__printc("종료중... >> thread stop event 실행")    
        
        #모든 스레드 종료 명령인 stop_event를 실행
        self.__stop_event.set()
        self.__printc("종료중... >> global stop event 실행")
        
        #화면 종료 
        self.root.quit() 
        self.__printc("종료")
        
        #현 스레드 종료
        exit()
        
        
    def onClose(self):
        self.__onClose()



    #=====실행내역 출력을 위한 함수=====
    #클래스명을 포함하여 출력하는 함수
    def __printc(self,msg:str):
        print("[{}] {}".format(self.__class__.__name__,msg))
    
    
    #클래스명 + 함수명을 출력하는 함수
    def __printf(self,msg:str,fname:str):
        self.__printc("[{}]: {}".format(fname, msg))


    #직선이동 명령을 출력하는 함수
    def __printm(self,key:str,action:str):
        self.__printc("KEYBOARD {}: {} {} cm".format(key, action,self.__cm))


    #회전 명령을 출력하는 함수
    def __printr(self,key:str,action:str):
        self.__printc("KEYBOARD {}: {} {} degree".format(key, action,self.__degree))