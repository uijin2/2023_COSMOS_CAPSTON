#완성
"""
값을 확인하는 함수에 대한 모듈
"""



#입력값이 Tello ToF 범위(0~8192)의 값이 맞는지 확인
def is_tof_val(val:str):
    
    val_list = val.split()
    if val_list[0] == 'tof' and val_list[-1].isdigit():
        int_val = int(val_list[-1])
        if 0 <= int_val <= 8192:
            return True
        else:
            return False
    else:
        return False

#입력값이 Tello SDK가 맞는지 확인
def is_sdk_val(val:str):
    """
    Tello SDK 명령어의 첫 어절에는 숫자가 없음
    """
    first_part:str = val.split()[0]

    for char in first_part:
        if char.isdigit():
            print("[is_sdk_val] val에서 숫자가 감지되었습니다.")
            return False
    return True