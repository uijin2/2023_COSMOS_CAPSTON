from abc import *


class Monocular(metaclass=ABCMeta):
    
    """_summary_
    1) take_from_camera
    2) detect_object
    3) save_to_drone
    순으로 실행
    """
    
    @abstractmethod
    def __take_from_camera(self): 
        pass
    
    @abstractmethod
    def __detect_object(self):
        pass
    
    @abstractmethod
    def __save_to_drone(self):
        pass
