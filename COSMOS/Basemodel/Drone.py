from abc import *


class Drone(metaclass=ABCMeta):

    @abstractmethod
    def __set_connection():
        pass

    @abstractmethod
    def __ceate_parts():
        pass
    
    @abstractmethod
    def __create_object_val():
        pass
    
    @abstractmethod
    def __get_object_val():
        pass

    @abstractmethod
    def __set_tof_val():
        pass
    
    @abstractmethod
    def __set_window_coors():
        pass
    
    @abstractmethod
    def __insert_queue():
        pass
    
    @abstractmethod
    def __pop_queue():
        pass
