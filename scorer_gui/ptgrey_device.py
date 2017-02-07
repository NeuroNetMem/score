import pyfly2

from scorer_gui.video_devices import VideoCapture

class PtGreyCameraCapture(VideoCapture):
    def __init__(self, index):
        super().__init__()
        # cv2.VideoCapture(0)
        print("Starting Fly Capture:")
        self._context = pyfly2.Context()
        print("FlyCapture context opened.")

        if index >= self._context.num_cameras:
            raise ValueError('Camera index does not exist')

        print("Getting camera ...")
        self.cam = self._context.get_camera(index)
        print("Got it.")

        print("Connecting to camera ...")
        self.cam.connect()
        print("Done.")

        print("Starting capture mode ...", end=' ')
        self.cam.start_capture()
        print("Done.")

        print("Querying camera information ...")
        self.info = self.cam.info.copy()

        print(self.info)

    def isOpened(self):
        return self.cam is not None

    def release(self):
        print("Stopping Capture...", end=' ')
        self.cam.stop_capture()

    def get_frame_count(self):
        raise RuntimeError("Can't give the total number of frames for a camera")

    def get_current_frame(self):
        pass

    def get_time_ms(self):
        pass

    def set_frame_no(self, val):
        raise RuntimeError("Can't set the frame number for a camera.")

    def get_width(self):
        w, _ = self.cam.get_size()
        return w

    def get_height(self):
        _, h = self.cam.get_size()
        return h

    def get_fps(self):
        _, frame_rate = self._context.get_mode()  # TODO what is videoMode?
        return frame_rate

    def read(self):
        frame = self.cam.grab_numpy_image()
        return True, frame
