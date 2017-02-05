import cv2


class VideoCapture:
    def __init__(self):
        # cv2.VideoCapture(0)
        pass

    def isOpened(self):
        pass

    def release(self):
        pass

    def get_frame_count(self):
        pass

    def get_current_frame(self):
        pass

    def get_time_ms(self):
        pass

    def set_frame_no(self, val):
        pass

    def get_width(self):
        pass

    def get_height(self):
        pass

    def get_fps(self):
        pass

    def read(self):
        pass


class Cv2Capture(VideoCapture):
    def __init__(self):
        super().__init__()
        self.cam = None

    def isOpened(self):
        return self.cam.isOpened()

    def release(self):
        self.cam.release()

    def get_frame_count(self):
        return self.cam.get(cv2.CAP_PROP_FRAME_COUNT)

    def get_current_frame(self):
        return self.cam.get(cv2.CAP_PROP_POS_FRAMES)

    def get_time_ms(self):
        return self.cam.get(cv2.CAP_PROP_POS_MSEC)

    def set_frame_no(self, val):
        self.cam.set(cv2.CAP_PROP_POS_FRAMES, float(val))
        pass

    def get_width(self):
        return int(self.cam.get(cv2.CAP_PROP_FRAME_WIDTH))

    def get_height(self):
        return int(self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def get_fps(self):
        return int(self.cam.get(cv2.CAP_PROP_FPS))
        pass

    def read(self):
        print('in read')
        ret, frame = self.cam.read()
        return ret, frame


class Cv2CameraCapture(Cv2Capture):
    def __init__(self, index):
        super().__init__()
        # noinspection PyArgumentList
        self.cam = cv2.VideoCapture(index)

    def set_frame_no(self, val):
        raise RuntimeError("Can't set the frame number for a camera!")


class Cv2VideoFileCapture(Cv2Capture):
    def __init__(self, filename):
        super().__init__()
        # noinspection PyArgumentList
        self.cam = cv2.VideoCapture(filename)
