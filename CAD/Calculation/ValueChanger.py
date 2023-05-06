#완성
"""
값을 변환하는 함수에 대한 모듈
"""



#입력값(mm)을 cm단위로 변환
def change_mm_to_cm(val:int):
    return int(val/10)


def change_val_to_coor(object_val):
    """
    -입력값 - object_val: (tof값[cm], 윈도우좌표[px], screen의 최대픽셀[px])
    -리턴값 - object_coor: (tof값[cm], 물체 중앙 좌표[cm], 물체 길이[cm])

    입력값인 object_val을 드론을 원점으로 한 3차원 좌표인 object_coor로 변환하여 리턴

    ※좌표계 주의※
    -윈도우 좌표계[px]: 좌상단이 (0,0) / 우측이 x의 +방향, 하단이 y의 +방향
    -실제 좌표계[cm]: 영상의 중심이 (0,0) / 우측이 x의 +방향, 상단이 y의 +방향
    """

    #카메라와 ToF 센서의 가로길이 보정값[cm]
    c= -3   
    
    #ToF값[cm]
    tof_val:int = object_val[0]
    
    #ToF값이 전달되지 않은 경우, 바로 리턴
    if tof_val is None:
        return None
 
    # #윈도우 좌표가 전달되지 않은 경우, 윈도우를 무시하고 최대크기로 지정
    # if object_val is None or object_val[1] is None or object_val[1]==(None,None) or \
    #     object_val[2] is None or object_val[2]==(None,None):

    #     real_length_x = 1000
    #     real_length_y = 1000  
    #     real_center_coor_x = 0
    #     real_center_coor_y = 0
        
    #     real_length = (real_length_x , real_length_y)    
    #     real_center_coor = (real_center_coor_x, real_center_coor_y)

    #     #리턴값 생성 / object_coor: (tof값[cm], 물체 중앙 좌표[cm], 물체 길이[cm])
    #     object_coor = (tof_val, real_center_coor, real_length)
    #     return object_coor
    
    #[윈도우 좌표계] 윈도우의 좌상단, 우하단 점, 스크린 크기에 대한 좌표값: (x,y)
    window_left_up_coor = object_val[1][0]
    window_right_down_coor = object_val[1][1]
    screen_size  = object_val[2]
    
    #[윈도우 좌표계] 윈도우의 길이: (x,y)
    window_length_x = window_right_down_coor[0]-window_left_up_coor[0]
    window_length_y = window_right_down_coor[1]-window_left_up_coor[1]
    window_length = (window_length_x, window_length_y)

    #[윈도우 좌표계] 윈도우의 중앙 좌표: (x,y)
    window_center_coor_x = (window_left_up_coor[0] + window_right_down_coor[0])/2
    window_center_coor_y = (window_left_up_coor[1] + window_right_down_coor[1])/2
    window_center_coor = (window_center_coor_x, window_center_coor_y )

    #[윈도우 좌표계] 스크린의 중앙 좌표: (x,y)
    screen_center_coor_x = screen_size[0]/2
    screen_center_coor_y = screen_size[1]/2
    screen_center_coor = (screen_center_coor_x, screen_center_coor_y)

    #[윈도우 좌표계] 윈도우의 중앙 좌표를 실제 좌표계 방향으로 변경
    window_center_coor_x_re = window_center_coor[0] - screen_center_coor[0]
    window_center_coor_y_re = screen_center_coor[1] - window_center_coor[1]
    window_center_coor_re = (window_center_coor_x_re, window_center_coor_y_re)

    #[실제 좌표계] 물체의 길이: (x,y)
    real_length_x = window_length[0] * (tof_val+c) / 960
    real_length_y = window_length[1] * (tof_val+c) / 960
    
    #[실제 좌표계] 물체의 중앙 좌표: (x,y)
    real_center_coor_x = window_center_coor_re[0] * (tof_val+c) / 960
    real_center_coor_y = window_center_coor_re[1] * (tof_val+c) / 960
    
    #비정상적으로 큰 값에 대해 1000으로 설정
    if real_length_x > 1000:
        real_length_x = 1000
    if real_length_y < 1000:
        real_length_y = 1000  
    if real_center_coor_x > 1000:
        real_center_coor_x = 1000
    if real_center_coor_y > 1000:
        real_center_coor_y = 1000
    
    real_length = (real_length_x , real_length_y)    
    real_center_coor = (real_center_coor_x, real_center_coor_y)

    #리턴값 생성 / object_coor: (tof값[cm], 물체 중앙 좌표[cm], 물체 길이[cm])
    object_coor = (tof_val, real_center_coor, real_length)
    return object_coor


#입력값(cmd)를 tello sdk 명령으로 변환
def change_cmd_for_tello(cmd:str):
    
    if cmd is None:
        return None
    
    cmd_list = cmd.split(" ")
    
    if cmd_list[0] in ["forward", "back", "right", "left", "cw", "ccw", "up", "down", "stop"]:

        weight = int(float(cmd_list[1])) if cmd_list[0] != "stop" else 0
        if weight > 100: 
            weight = 100
        
        if weight < 60:
            weight = 60
        
        rc_cmd = None
        
        if cmd_list[0] == "forward":
            rc_cmd = "rc 0 {} 0 0".format(weight)
            
        elif cmd_list[0] == "back":
            rc_cmd = "rc 0 {} 0 0".format(-1*weight)
        
        elif cmd_list[0] == "left":
            rc_cmd = "rc {} 0 0 0".format(-1*weight)
        
        elif cmd_list[0] == "right":
            rc_cmd = "rc {} 0 0 0".format(weight)
        
        elif cmd_list[0] == "up":
            rc_cmd = "rc 0 0 {} 0".format(weight)
        
        elif cmd_list[0] == "down":
            rc_cmd = "rc 0 0 {} 0".format(-1*weight)

        elif cmd_list[0] == "cw":
            rc_cmd = "rc 0 0 0 {}".format(weight)
            
        elif cmd_list[0] == "ccw":
            rc_cmd = "rc 0 0 0 {}".format(-1*weight)
        
        elif cmd_list[0] =='stop':
            rc_cmd = "rc 0 0 0 0"
        
        return rc_cmd.encode('utf-8')
    
    else:
        return cmd.encode("utf-8")


def change_windows_to_window(window_coor_list:list, ir_left_up_coor: tuple, ir_right_down_coor:tuple):
    """
    입력값 - window_coor_list: 윈도우의 (좌상단좌표, 우하단좌표)들이 들어있는 리스트
    입력값 - ir_left_up_coor: 적외선 윈도우의 좌상단좌표
    입력값 - ir_right_down_coor: 적외선 윈도우의 우하단좌표
    출력값 - (window_left_up_coor, window_right_down_coor): 생성된 윈도우의 (좌상단좌표, 우하단좌표)
    #window_coor_list 내의 좌표들이 적외선 영역에 걸쳐있으면 남기고, 외부이면 제거
    #적외선 영역에 걸친 윈도우들은 하나로 융합
    #IR 영역이 감지범위 내인 경우만 실행됨
    """
    
    #적외선 윈도우에 걸친 윈도우 좌표를 저장할 리스트
    passing_windows = []
    
    ir_left_x = ir_left_up_coor[0]
    ir_right_x = ir_right_down_coor[0]
    ir_up_y = ir_left_up_coor[1]
    ir_down_y = ir_right_down_coor[1]
    
    #겹치는 윈도우 검출    
    for window in window_coor_list:
        window_left_up_coor = window[0]
        window_right_down_coor = window[1]
        
        window_left_x = window_left_up_coor[0]
        window_right_x = window_right_down_coor[0]
        window_up_y = window_left_up_coor[1]
        window_down_y = window_right_down_coor[1]
        
        #적외선 윈도우와 현재 윈도우가 겹치려면,
        #적외선 윈도우의 좌측좌표 보다 현재 윈도우의 우측좌표가 크다 and
        #적외선 윈도우의 우측좌표 보다 현재 윈도우의 좌측좌표가 작다 and
        #적외선 윈도우의 상단좌표 보다 현재 윈도우의 하단좌표가 크다 and
        #적외선 윈도우의 하단좌표 보다 현재 윈도우의 상단좌표가 작다
        if ir_left_x <= window_right_x and \
           ir_right_x >= window_left_x and \
           ir_up_y <= window_down_y and \
           ir_down_y >= window_up_y:
            passing_windows.append(window)
    
    #검출한 윈도우를 저장할 변수
    fusion_window = None
    
    if len(passing_windows) != 0:
        fusion_window = passing_windows.pop()
        
    #검출한 윈도우들 중 겹치는 윈도우들을 융합
    for window in passing_windows:
        
        #fusion window decapsulation
        fusion_window_left_up_coor = fusion_window[0]
        fusion_window_right_down_coor = fusion_window[1]

        fusion_window_left_x = fusion_window_left_up_coor[0]
        fusion_window_right_x = fusion_window_right_down_coor[0]
        fusion_window_up_y = fusion_window_left_up_coor[1]
        fusion_window_down_y = fusion_window_right_down_coor[1]
        
        #cur window decapsulation
        window_left_up_coor = window[0]
        window_right_down_coor = window[1]
        
        window_left_x = window_left_up_coor[0]
        window_right_x = window_right_down_coor[0]
        window_up_y = window_left_up_coor[1]
        window_down_y = window_right_down_coor[1]
        
        #겹친다면
        if fusion_window_left_x <= window_right_x and \
           fusion_window_right_x >= window_left_x and \
           fusion_window_up_y <= window_down_y and \
           fusion_window_down_y >= window_up_y:
               
            fusion_window_left_x = max(fusion_window_left_x,window_left_x)
            fusion_window_right_x = max(fusion_window_right_x,window_right_x)
            fusion_window_up_y = max(fusion_window_up_y, window_up_y)
            fusion_window_down_y = max(fusion_window_down_y, window_down_y)
            
            #fusion window encapsulation
            fusion_window_left_up_coor = (fusion_window_left_x, fusion_window_up_y)
            fusion_window_right_down_coor = (fusion_window_right_x, fusion_window_down_y)
            
            fusion_window = (fusion_window_left_up_coor, fusion_window_right_down_coor)


    #fusion_window가 None 이다 
    # = IR영역이 감지범위 내임에도 감지를 못했다
    # = 객체인식은 못했으나 무언가 장애물이 존재한다
    # = 매우 큰 크기로 매칭하여 전달한다
    if fusion_window is None:
        fusion_window_left_x = -131072
        fusion_window_right_x = 131072
        fusion_window_up_y = -131072
        fusion_window_down_y = 131072
        fusion_window_left_up_coor = (fusion_window_left_x, fusion_window_up_y)
        fusion_window_right_down_coor = (fusion_window_right_x, fusion_window_down_y)
        fusion_window = (fusion_window_left_up_coor, fusion_window_right_down_coor)
    
    #(window_left_up_coor, window_right_down_coor)
    return fusion_window


#충돌이 발생하지 않는 명령으로 변환
def change_to_safe_cmd(cmd:str, tof:int, threshold:int):
    
    if cmd is None:
        return None

    cmd_list = cmd.split(" ")
    
    #어차피 전방에 대해서만 장애물 감지가 가능하기 때문에, 전방이동만 고려하면 됨
    if cmd_list[0] !="forward":
        return cmd

    #장애물까지 남은 안정거리
    rest_safe_distance = tof - threshold
    
    #이동하고자 하는 거리
    move_distance = int(cmd_list[1])
    
    
    #계산된 거리
    new_move_distance = rest_safe_distance - move_distance
    if tof >= 1000:
        new_move_distance = move_distance
        return "forward {}".format(new_move_distance)
        
    if new_move_distance < 20:
        return "stop"

    return "forward {}".format(new_move_distance)