import numpy as np
import cv2
import math
from enum import Enum

import score_behavior.tracking.geometry as geometry
from score_behavior.score_config import get_config_section
import logging

logger = logging.getLogger(__name__)


class AnimalPosition:
    def __init__(self):
        self.backbone = []
        self.head = 0
        self.front = 0
        self.back = 0
        self.contracted = 0


class Animal:
    class Configuration:
        model_normal = 0
        model_with_drive = 1
        max_body_length = 60
        max_body_width = 30
        min_body_width = 30
        front_min_value_coeff = 100
        back_min_value_coeff = 100

        def __init__(self):
            self.model = self.model_normal

    contours = None

    head = 0
    front = 0
    back = 0

    class Posture:
        def __init__(self, head, front, back, contracted=False):
            self.head = head
            self.front = front
            self.back = back
            self.contracted = contracted

    # the primitives for animal motion, essentially the dynamics model of the animal
    def move_back(self, postures):
        """move the entire animal of the same amount """
        result = []
        # distances = [2, 4, 6, 8, 10, 14, 18, 22]
        distances = np.arange(-10, 11, 1)
        for p in postures:
            for d in distances:
                moved = geometry.point_along_a_line_p(p.back, p.front, d)
                delta = moved - p.back
                result.append(self.Posture(p.head + delta, p.front + delta, moved))
        return result

    def move_front(self, postures):
        """move only the head and the front?"""
        result = []
        # distances = [-4, -2, 2, 4, 6, 8, 10]
        distances = np.arange(-5, 6, 1)
        min_dist = self.scaled_back_radius - self.scaled_front_radius
        max_dist = self.scaled_back_radius + self.scaled_front_radius
        for p in postures:
            cd = geometry.distance_p(p.back, p.front)
            for d in distances:
                if cd + d < min_dist:
                    continue
                if cd + d > max_dist:
                    continue
                moved = geometry.point_along_a_line_p(p.back, p.front, cd + d)
                delta = moved - p.front
                result.append(self.Posture(p.head + delta, moved, p.back))
        return result

    def move_head(self, postures):
        """move only the head"""
        result = []
        distances = np.arange(-5, 6, 1)
        min_dist = self.scaled_front_radius - self.scaled_head_radius
        max_dist = self.scaled_front_radius + self.scaled_head_radius
        for p in postures:
            cd = geometry.distance_p(p.front, p.head)
            for d in distances:
                if cd + d < min_dist:
                    continue
                if cd + d > max_dist:
                    continue
                moved = geometry.point_along_a_line_p(p.front, p.head, cd + d)
                result.append(self.Posture(moved, p.front, p.back))
        return result

    def rotate_front(self, postures):
        """rotate the front and the head"""
        result = []
        angles = np.arange(-20, 21, 4)
        for p in postures:
            for a in angles:
                ar = a * (math.pi / 180)
                rotated_front = geometry.rotate_p(p.front, p.back, ar)
                rotated_head = geometry.rotate_p(p.head, p.back, ar)
                result.append(self.Posture(rotated_head, rotated_front, p.back))
        return result

    def rotate_head(self, postures):
        """rotate only the head"""
        result = []
        # angles = [-20, -10, 10, 20]
        angles = np.arange(-20, 21, 4)
        for p in postures:
            for a in angles:
                ar = a * (math.pi / 180)

                rotated_head = geometry.rotate_p(p.head, p.front, ar)

                cos = geometry.cosine_p(p.back, p.front, rotated_head)
                if cos > 0.1:
                    continue

                result.append(self.Posture(rotated_head, p.front, p.back))
        return result

    def move_back_contracted(self, postures):
        result = []
        # distances = [-1, 2, 4, 6, 8, 10, 20, 30]
        distances = np.arange(-10, 11, 1)
        for p in postures:
            for d in distances:
                moved = geometry.point_along_a_line_p(p.back, p.head, d)
                delta = moved - p.back
                result.append(self.Posture(p.head + delta, moved, moved, True))
        return result

    def move_head_contracted(self, postures):
        result = []
        # distances = [-2, 2]
        distances = np.arange(-5, 6, 1)
        min_dist = self.scaled_back_radius - self.scaled_head_radius
        max_dist = self.scaled_back_radius + self.scaled_head_radius
        for p in postures:
            cd = geometry.distance_p(p.back, p.head)
            for d in distances:
                if cd + d < min_dist:
                    continue
                if cd + d > max_dist:
                    continue
                moved = geometry.point_along_a_line_p(p.back, p.head, cd + d)
                result.append(self.Posture(moved, p.back, p.back, True))
        return result

    def rotate_head_contracted(self, postures):
        result = []

        for p in postures:

            d = geometry.distance_p(p.back, p.head) + self.scaled_head_radius - self.scaled_back_radius
            if d <= self.scaled_head_radius / 4:
                angles = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 320, 340]
            else:
                angles = [-20, -10, 10, 20]

            for a in angles:
                ar = a * (math.pi / 180)
                rotated_head = geometry.rotate_p(p.head, p.back, ar)
                result.append(self.Posture(rotated_head, p.back, p.back, True))

        return result

    def move_front_contracted(self, postures):
        """moving the front gets the mouse out of the contracted state"""
        result = []
        distances = [2, 4, 6]
        base_distance = self.scaled_back_radius - self.scaled_front_radius
        for p in postures:
            hd = geometry.distance_p(p.back, p.head)
            for d in distances:
                moved_front = geometry.point_along_a_line_p(p.back, p.head, base_distance + d)
                moved_head = geometry.point_along_a_line_p(p.back, p.head, hd + d)
                result.append(self.Posture(moved_head, moved_front, p.back))
        return result

    def generate_postures(self):
        """enumerates the possible postures"""

        centroid_scaled = self.centroid.scaled(self.host.scale_factor, self.host.config.skeletonization_border)
        # "tether" the front to the centroid if it runs away too far
        if np.linalg.norm(self.back-centroid_scaled, ord=2) > 50:
            self.head = (self.head - self.front) + centroid_scaled
            self.front = (self.front - self.front) + centroid_scaled
            self.back = centroid_scaled

        disp = self.centroid - self.prev_centroid
        animal_vec = self.head - self.back

        # if it appears that the animal is running backwards, flip the Posture
        if np.dot(animal_vec, self.speed) < 0 and np.linalg.norm(self.speed) > self.host.speed_threshold \
                and not self.contracted:
            postures = [self.Posture(self.back + disp, self.front + disp,
                                     self.head + disp, self.contracted)]
        else:
            postures = [self.Posture(self.head + disp, self.front + disp,
                                     self.back + disp, self.contracted)]
        postures0 = postures[:]

        if not self.contracted:
            p = self.move_back(postures0)
            postures = postures + p

            p = self.move_front(postures0)
            postures = postures + p

            p = self.move_head(postures0)
            postures = postures + p

            if self.host.postures_two_steps:
                postures0 = postures[:]

            p = self.rotate_front(postures0)
            postures = postures + p

            p = self.rotate_head(postures0)
            postures = postures + p
        else:
            p = self.move_back_contracted(postures0)
            postures = postures + p

            p = self.move_head_contracted(postures0)
            postures = postures + p

            p = self.rotate_head_contracted(postures0)
            postures = postures + p

            p = self.move_front_contracted(postures0)
            postures = postures + p

        return postures

    def find_closest_centroid(self, c):
        if c.ndim == 1:
            return tuple(c)
        dist2 = np.sum((c - np.array(self.centroid)) ** 2, axis=1)
        closest_idx = np.argmin(dist2)
        return geometry.Point(c[closest_idx, :])

    # noinspection PyShadowingBuiltins
    def __init__(self, host, id, start_x, start_y, end_x, end_y, centroids, config=Configuration()):

        self.host = host  # the calling tracker object
        self.id = id  # a id number for the animal
        self.config = config
        self.centroid = None
        self.centroid = geometry.Point((start_x + end_x) / 2, (start_y + end_y) / 2)
        if centroids is not None:
            self.centroid = self.find_closest_centroid(centroids)
        self.prev_centroid = self.centroid
        self.speed = geometry.Point(0., 0.)
        self.speed_alpha = 0.92
        logger.log(5, "setting centroid at {}, {}".format(self.centroid[0], self.centroid[1]))
        self.scaled_max_body_length = config.max_body_length * self.host.scale_factor
        self.scaled_max_width = self.config.max_body_width * self.host.scale_factor
        self.scaled_min_width = self.config.min_body_width * self.host.scale_factor

        border = self.host.config.skeletonization_border
        '''
        start_x =  start_x * host.scale_factor + border
        start_y =  start_y * host.scale_factor + border
        end_x =  end_x * host.scale_factor + border
        end_y =  end_y * host.scale_factor + border
        '''

        start = geometry.Point(start_x, start_y)
        end = geometry.Point(end_x, end_y)

        self.scaled_head_radius = self.host.scaled_head_radius
        self.scaled_front_radius = self.host.scaled_front_radius
        self.scaled_back_radius = self.host.scaled_back_radius

        head_radius = self.scaled_head_radius / host.scale_factor
        front_radius = self.scaled_front_radius / host.scale_factor
        back_radius = self.scaled_back_radius / host.scale_factor

        length = geometry.distance_p(start, end)

        total = 2 * back_radius + 2 * front_radius + 2 * head_radius

        self.back = geometry.point_along_a_line_p(end, start, length * float(back_radius) / total)
        self.front = geometry.point_along_a_line_p(end, start, length * float(2 * back_radius + front_radius) / total)
        self.head = geometry.point_along_a_line_p(end, start, length * float(2 * back_radius + 2 * front_radius +
                                                                             head_radius) / total)

        self.head = self.head.scaled(self.host.scale_factor, border)
        self.front = self.front.scaled(self.host.scale_factor, border)
        self.back = self.back.scaled(self.host.scale_factor, border)

        self.head_radius = head_radius
        self.front_radius = front_radius
        self.back_radius = back_radius

        self.contracted = False

    def get_position(self):
        border = self.host.config.skeletonization_border

        r = AnimalPosition()
        r.head = self.head.affine_r(self.host.scale_factor, border)
        r.front = self.front.affine_r(self.host.scale_factor, border)
        r.back = self.back.affine_r(self.host.scale_factor, border)
        r.contracted = self.contracted
        r.speed = self.speed
        return r

    # noinspection PyUnusedLocal
    # @profile
    def track(self, raw_matrix, animals, centroids, frame_time):
        """tracking a single animal"""
        # source is the original frame, raw_matrix the subtracted one

        self.prev_centroid = self.centroid
        logger.log(5, "centroids are " + str(centroids))
        self.centroid = self.find_closest_centroid(centroids)
        self.speed = self.speed_alpha * self.speed + \
        (1. - self.speed_alpha) * (self.centroid - self.prev_centroid)
        logger.log(5, "speed is {}".format(np.linalg.norm(self.speed)))
        matrix = raw_matrix.astype(np.float)
        matrix = matrix - 100.
        # matrix = matrix - thr
        # matrix[matrix < 0] = -50

        # setting up the alternative pos    tures
        postures = self.generate_postures()
        logger.log(5, "generated {} postures".format(len(postures)))
        mask_size = 50
        mask_half = mask_size / 2

        mask = np.zeros((mask_size, mask_size), np.float)

        best_posture = None
        best_val = - 255 * mask_size * mask_size

        hr = self.scaled_head_radius
        fr = self.scaled_front_radius
        br = self.scaled_back_radius

        first = True
        current_val = None

        # find the optimal posture
        for p in postures:

            mask.fill(-1)
            mask_center = geometry.Point(mask_half, mask_half)
            animal_center = self.back

            h = p.head - animal_center + mask_center
            f = p.front - animal_center + mask_center
            b = p.back - animal_center + mask_center

            if not p.contracted:
                head_p1 = geometry.point_along_a_perpendicular(f.x, f.y, h.x, h.y, h.x, h.y, hr)
                head_p2 = geometry.point_along_a_perpendicular(f.x, f.y, h.x, h.y, h.x, h.y, -hr)

                front_p1 = geometry.point_along_a_perpendicular(f.x, f.y, h.x, h.y, f.x, f.y, fr)
                front_p2 = geometry.point_along_a_perpendicular(f.x, f.y, h.x, h.y, f.x, f.y, -fr)

                cv2.fillConvexPoly(mask,
                                   np.array([list(head_p1), list(front_p1), list(front_p2), list(head_p2)], 'int32'), 1)

                front_p1 = geometry.point_along_a_perpendicular(f.x, f.y, b.x, b.y, f.x, f.y, fr)
                front_p2 = geometry.point_along_a_perpendicular(f.x, f.y, b.x, b.y, f.x, f.y, -fr)
                back_p1 = geometry.point_along_a_perpendicular(f.x, f.y, b.x, b.y, b.x, b.y, br)
                back_p2 = geometry.point_along_a_perpendicular(f.x, f.y, b.x, b.y, b.x, b.y, -br)

                cv2.fillConvexPoly(mask,
                                   np.array([list(back_p1), list(front_p1), list(front_p2), list(back_p2)], 'int32'), 1)
            else:
                head_p1 = geometry.point_along_a_perpendicular(b.x, b.y, h.x, h.y, h.x, h.y, hr)
                head_p2 = geometry.point_along_a_perpendicular(b.x, b.y, h.x, h.y, h.x, h.y, -hr)

                front_p1 = geometry.point_along_a_perpendicular(b.x, b.y, h.x, h.y, b.x, b.y, br)
                front_p2 = geometry.point_along_a_perpendicular(b.x, b.y, h.x, h.y, b.x, b.y, -br)

                cv2.fillConvexPoly(mask,
                                   np.array([list(head_p1), list(front_p1), list(front_p2), list(head_p2)], 'int32'), 1)

            cv2.circle(mask, h.as_int_tuple(), hr, 1, -1)
            cv2.circle(mask, f.as_int_tuple(), fr, 1, -1)
            cv2.circle(mask, b.as_int_tuple(), br, 1, -1)

            ac = animal_center
            mh = int(mask_half)

            try:
                matrix_slice = matrix[max((int(ac.y) - mh), 0): int(ac.y) + mh, max(int(ac.x) - mh, 0):int(ac.x) + mh]
                mask_start_r = 0
                mask_start_c = 0
                mask_end_r = mask.shape[0]
                mask_end_c = mask.shape[1]
                if int(ac.y) - mh < 0:
                    mask_start_r = -(int(ac.y) - mh)
                if int(ac.x) - mh < 0:
                    mask_start_c = -(int(ac.x) - mh)
                if int(ac.y) + mh > matrix.shape[0]:
                    mask_end_r -= int(ac.y) + mh - matrix.shape[0]
                if int(ac.x) + mh > matrix.shape[1]:
                    mask_end_c -= int(ac.x) + mh - matrix.shape[1]
                mask_slice = mask[mask_start_r:mask_end_r, mask_start_c:mask_end_c]

                product = np.multiply(mask_slice, matrix_slice)
                # product = np.multiply(mask, matrix[(int(ac.y) - mh): int(ac.y) + mh, int(ac.x) - mh:int(ac.x) + mh])

                val = product.sum()
            except ValueError:
                logger.exception('tracker fault')
                logger.info("ac = ({}, {}), mh = {}".format(ac.x, ac.y, mh))
                logger.info(("matrix size = {}, {}".format(matrix.shape[0], matrix.shape[1])))
                val = 0
            if first:
                current_val = val
                first = False

            if val > best_val:
                best_posture = p
                best_val = val

        if best_val > current_val * 1.:

            self.head = best_posture.head
            self.front = best_posture.front
            self.back = best_posture.back

            if self.contracted:
                self.contracted = best_posture.contracted

            # condition to transition to contracted
            if not self.contracted:
                d = geometry.distance_p(self.back, self.front) - self.scaled_back_radius + self.scaled_front_radius

                if d <= self.scaled_front_radius / 2:
                    self.contracted = True
                    self.front = self.back
                    hd = geometry.distance_p(self.back, self.head)
                    self.head = geometry.point_along_a_line_p(self.back, self.head, hd - d)

        rows, cols = raw_matrix.shape[:2]

        position_data = {'id': self.id, 'centroid_x': self.centroid[0], 'centroid_y':self.centroid[1],
                         'head_x': self.head[0], 'head_y': self.head[1],
                         'front_x': self.front[0], 'front_y': self.front[1],
                         'back_x': self.back[0], 'back_y': self.back[1]}

        return position_data


class TrackingFlowElement:
    """container for the results of the tracking operation."""

    def __init__(self, time, positions, filtered_image, debug):
        self.time = time
        self.positions = positions
        self.filtered_image = filtered_image
        self.debug_frames = debug


class Tracker:

    class State(Enum):
        INACTIVE = 1  # no background or otherwise not ready
        READY = 2  # ready, but not tracking any animals
        TRACKING = 3  # tracking animals
        ACQUIRING_BG = 4

    state_labels = {State.INACTIVE: 'Inactive', State.READY: 'Ready', State.TRACKING: 'Tracking',
                    State.ACQUIRING_BG: 'BG Acq.'}

    class Configuration:
        """configuration values"""
        skeletonization_res_width = 550 / 1.4
        skeletonization_res_height = 420 / 1.4
        skeletonization_border = 20
        vertebra_length = 10
        pixels_to_meters = 1
        scale = 1

        def __init__(self):
            pass

    scale_factor = 1

    finished = False

    animals = []  # the list of tracked animals

    # noinspection PyArgumentList
    def __init__(self, frame_size, config=Configuration()):
        self.scaled_head_radius = 5
        self.scaled_front_radius = 7
        self.scaled_back_radius = 10
        self.component_threshold = 40
        self.speed_threshold = 1.2
        self.max_num_animals = 1
        self.read_config()

        frame_width, frame_height = frame_size
        config.skeletonization_res_height = frame_height
        config.skeletonization_res_width = frame_width
        self.config = config
        self.centroids = None
        self.scale_factor = self.calculate_scale_factor(frame_width, frame_height)
        config.pixels_to_meters = float(config.scale) / frame_width

        config.vertebra_length = config.vertebra_length * self.scale_factor
        self.show_thresholded = False

        self.background = None
        self.show_model = True
        self.show_posture = True
        self.image_scale_factor = 1
        self.postures_two_steps = False
        self._state = self.State.INACTIVE
        self.tracker_controller = None
        self.background_frames = 5
        self.background_countdown = 0
        self.background_buffer = None

    def read_config(self):
        d = get_config_section("tracker")
        if "max_num_animals" in d:
            self.max_num_animals = d['max_num_animals']
        if "component_threshold" in d:
            self.component_threshold = d['component_threshold']
        if "speed_threshold" in d:
            self.speed_threshold = d['speed_threshold']
        if "head_radius" in d:
            self.scaled_head_radius = d['head_radius']
        if "front_radius" in d:
            self.scaled_front_radius = d['front_radius']
        if "back_radius" in d:
            self.scaled_back_radius = d['back_radius']

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, s):
        self._state = s
        if self.tracker_controller:
            self.tracker_controller.set_tracker_state(self.state_labels[s])

    def calculate_scale_factor(self, frame_width, frame_height):
        """calculate a scale factor that will make the frame coincide the "dominant" dimension with the skeletonization
        frame
        """
        width = self.config.skeletonization_res_width
        height = self.config.skeletonization_res_height
        k = float(frame_width) / frame_height
        if k > float(width) / height:
            return float(width) / frame_width
        else:
            return float(height) / frame_height

    def resize(self, frame):
        """resize to make the dominant dimension coincide with the skeletonization frame"""
        width = self.config.skeletonization_res_width
        height = self.config.skeletonization_res_height
        rows, cols = frame.shape[:2]
        k = float(cols) / rows
        if k > float(width) / height:
            cols = width
            rows = cols / k
        else:
            rows = height
            cols = rows * k
        frame = cv2.resize(frame, (int(cols), int(rows)))
        return frame

    # noinspection PyAttributeOutsideInit
    def set_background(self, frame):
        """calculate background from the frames before the video stream ends, by averaging """
        bg = frame.astype(np.uint8)
        self.background = bg
        self.state = self.State.READY

    def add_animal_auto(self):
        if self.state == self.State.INACTIVE:
            return
        # TODO now only for one animal
        x = self.centroids[0, 0]
        y = self.centroids[0, 1]
        self.add_animal(x-10, y, x+10, y)

    def add_animal(self, start_x, start_y, end_x, end_y, config=Animal.Configuration()):
        """add an animal to the list of animals"""
        if len(self.animals) >= self.max_num_animals:
            logger.debug("Attempting to create too many animals")
            return
        logger.info("Adding animal")
        self.animals.append(Animal(self, len(self.animals), start_x, start_y, end_x, end_y, self.centroids, config))
        if len(self.animals) == self.max_num_animals:
            # noinspection PyAttributeOutsideInit
            self.state = self.State.TRACKING
        if self.tracker_controller:
            self.tracker_controller.set_tracked_animals_number(len(self.animals))
        return self.animals[-1]

    def delete_all_animals(self):
        """delete all tracked animals from the list"""
        self.animals = []
        self.state = self.State.READY
        self.tracker_controller.set_tracked_animals_number(len(self.animals))

    # noinspection PyUnusedLocal
    def track_animals(self, matrix, frame_time):
        """loop over animals and call the tracker in the animal class"""
        position_data = []

        for a in self.animals:
            position_data.append(a.track(matrix, self.animals, self.centroids, frame_time))

        return position_data

    def grab_background(self):
        self.background_countdown = self.background_frames
        self.state = self.State.ACQUIRING_BG

    def track(self, frame, frame_time=0):
        """track one frame"""
        logger.log(5, "start tracking {} animals".format(len(self.animals)))
        if self.background_countdown > 0:
            if self.background_buffer is None:
                self.background_buffer = np.zeros((self.config.skeletonization_res_height,
                                                   self.config.skeletonization_res_width,
                                                   3,
                                                   self.background_frames), frame.dtype)
            self.background_countdown -= 1
            self.background_buffer[:, :, :, self.background_countdown] = frame
            if self.background_countdown == 0:
                bg = np.median(self.background_buffer, axis=3)
                self.set_background(bg)
                self.background_buffer = None

        if self.background is None:
            return

        frame_gr = cv2.absdiff(frame, self.background)  # take the absolute difference
        frame_gr = cv2.cvtColor(frame_gr, cv2.COLOR_BGR2GRAY)  # convert to grayscale
        cv2.normalize(frame_gr, frame_gr, 0, 255, cv2.NORM_MINMAX)  # normalize so that the minimum is zero

        frame_gr1 = frame_gr.copy()

        thr, _ = cv2.threshold(frame_gr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        ret, frame_gr = cv2.threshold(frame_gr, thr + self.component_threshold, 254, cv2.THRESH_BINARY)

        nb_components, output, stats, centroids = cv2.connectedComponentsWithStats(frame_gr, connectivity=8)
        sizes = stats[1:, -1]
        max_comp = np.argmax(sizes)
        frame_gr_resized = np.zeros(frame_gr.shape, np.uint8)
        frame_gr_resized[output == max_comp + 1] = 255
        self.centroids = centroids[max_comp + 1, :]
        if self.centroids.ndim == 1:
            self.centroids = self.centroids[np.newaxis, :]
        frame_mask = frame_gr_resized.copy()
        frame_mask = cv2.normalize(frame_gr_resized, frame_mask, 0, 1, cv2.NORM_MINMAX)
        frame_gr_resized = cv2.multiply(frame_mask, frame_gr1)
        # except ValueError:
        #     print(np.min(frame_gr.astype(np.int8)), np.max(frame_gr.astype(np.int8)))
        # frame_gr_resized = frame_gr_resized.astype(np.uint8)
        cv2.normalize(frame_gr_resized, frame_gr_resized, 0, 255, cv2.NORM_MINMAX)

        # add borders to the frame, fill with zeros
        border = self.config.skeletonization_border
        frame_gr_resized = cv2.copyMakeBorder(frame_gr_resized, border, border, border, border, cv2.BORDER_CONSTANT, 0)

        position_data = self.track_animals(frame_gr_resized, frame_time)

        frame_display = frame_gr_resized[border:-border, border:-border]

        frame_display = cv2.cvtColor(frame_display, cv2.COLOR_GRAY2BGR)
        # frame_alpha = frame_display
        # foreground = cv2.multiply(frame_alpha, frame_display)
        # background = cv2.multiply((1 - frame_alpha), frame)
        #
        # frame_display = cv2.add(foreground, background)
        if self.show_thresholded:
            frame[:] = frame_display
        for ix in range(self.centroids.shape[0]):
            cv2.circle(frame, tuple(self.centroids[ix, :].astype(np.uint16)), 2, (0, 0, 255))
        self.draw_animals(frame)
        return position_data

    def project(self, pos):
        r = geometry.Point(pos.x * self.image_scale_factor, pos.y * self.image_scale_factor)
        return r

    def scaled_radius(self, r):
        return r * self.image_scale_factor

    def get_animal_positions(self):
        """extracts from the animal structures the current position of the animals"""
        positions = []
        for a in self.animals:
            positions.append((a, a.get_position()))
        return positions

    def draw_animals(self, frame):

        for ap in self.get_animal_positions():
            logger.log(5, "drawing animal")
            white = (255, 255, 255)
            green = (0, 255, 0)
            # red = (255, 0, 0)
            # yellow = (255, 255, 0)

            a = ap[0]
            p = ap[1]

            if self.show_model:

                ph = self.project(p.head)
                pf = self.project(p.front)
                pb = self.project(p.back)

                hr = self.scaled_radius(a.head_radius)
                fr = self.scaled_radius(a.front_radius)
                br = self.scaled_radius(a.back_radius)

                cv2.circle(frame, pb.as_int_tuple(), int(br), white)
                if not p.contracted:
                    cv2.circle(frame, pf.as_int_tuple(), int(fr), white)
                cv2.circle(frame, ph.as_int_tuple(), int(hr), white)

            if self.show_posture:

                hc = self.project(p.head)
                fc = self.project(p.front)
                bc = self.project(p.back)

                hr = self.scaled_radius(a.head_radius)
                # fr = self.scaled_radius(a.front_radius)
                br = self.scaled_radius(a.back_radius)

                fhd = geometry.distance(fc.x, fc.y, hc.x, hc.y)
                fbd = geometry.distance(fc.x, fc.y, bc.x, bc.y)

                if not p.contracted:

                    h = geometry.point_along_a_line(fc.x, fc.y, hc.x, hc.y, fhd + hr)
                    b = geometry.point_along_a_line(fc.x, fc.y, bc.x, bc.y, fbd + br)

                    cv2.line(frame, (int(b[0]), int(b[1])),
                             (int(fc.x), int(fc.y)), white)
                    cv2.line(frame, (int(fc.x), int(fc.y)),
                             (int(h[0]), int(h[1])), white)

                    cv2.circle(frame, (int(fc.x), int(fc.y)), 2, green)

                    ahd = fhd - 4
                    if ahd < 0:
                        ahd = 0

                    arrow_head = geometry.point_along_a_line(fc.x, fc.y, hc.x, hc.y, ahd)
                    arrow_line1 = geometry.point_along_a_perpendicular(fc.x, fc.y, hc.x, hc.y,
                                                                       arrow_head[0], arrow_head[1], 3)
                    arrow_line2 = geometry.point_along_a_perpendicular(fc.x, fc.y, hc.x, hc.y,
                                                                       arrow_head[0], arrow_head[1], -3)

                    cv2.line(frame, (int(h[0]), int(h[1])),
                             (int(arrow_line1[0]), int(arrow_line1[1])), white)
                    cv2.line(frame, (int(h[0]), int(h[1])),
                             (int(arrow_line2[0]), int(arrow_line2[1])), white)
                else:

                    hbd = geometry.distance(hc.x, hc.y, bc.x, bc.y)
                    h = geometry.point_along_a_line(bc.x, bc.y, hc.x, hc.y, hbd + hr)
                    b = geometry.point_along_a_line(hc.x, hc.y, bc.x, bc.y, hbd + br)
                    cv2.line(frame, (int(b[0]), int(b[1])),
                             (int(h[0]), int(h[1])), white)
                    ahd = hbd - 4
                    if ahd < 0:
                        ahd = 0
                    arrow_head = geometry.point_along_a_line(bc.x, bc.y, hc.x, hc.y, ahd)
                    arrow_line1 = geometry.point_along_a_perpendicular(bc.x, bc.y, hc.x, hc.y,
                                                                       arrow_head[0], arrow_head[1], 3)
                    arrow_line2 = geometry.point_along_a_perpendicular(bc.x, bc.y, hc.x, hc.y,
                                                                       arrow_head[0], arrow_head[1], -3)

                    cv2.line(frame, (int(h[0]), int(h[1])),
                             (int(arrow_line1[0]), int(arrow_line1[1])), white)
                    cv2.line(frame, (int(h[0]), int(h[1])),
                             (int(arrow_line2[0]), int(arrow_line2[1])), white)
        logger.log(5, "finished drawing animals")
