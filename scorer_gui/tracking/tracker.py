import numpy as np
import cv2
import math
# import threading
# import Queue
# import pdb
# import time
# from skimage import morphology
# from skimage import filters
#
# from geometry import *
import scorer_gui.geometry as geometry


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
        distances = [2, 4, 6, 8, 10]
        for p in postures:
            for d in distances:
                moved = geometry.point_along_a_line_p(p.back, p.front, d)
                delta = moved.difference(p.back)
                result.append(self.Posture(p.head.sum(delta), p.front.sum(delta), moved))
        return result

    def move_front(self, postures):
        """move only the head and the front?"""
        result = []
        distances = [-4, -2, 2, 4]
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
                delta = moved.difference(p.front)
                result.append(self.Posture(p.head.sum(delta), moved, p.back))
        return result

    def move_head(self, postures):
        """move only the head"""
        result = []
        distances = [-2, 2]
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
        angles = [-20, -10, 10, 20]
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
        angles = [-20, -10, 10, 20]
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
        distances = [-1, 2, 4, 6, 8, 10]
        for p in postures:
            for d in distances:
                moved = geometry.point_along_a_line_p(p.back, p.head, d)
                delta = moved.difference(p.back)
                result.append(self.Posture(p.head.sum(delta), moved, moved, True))
        return result

    def move_head_contracted(self, postures):
        result = []
        distances = [-2, 2]
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

        postures = [self.Posture(self.head, self.front, self.back, self.contracted)]

        if not self.contracted:
            p = self.move_back(postures)
            postures = postures + p

            p = self.rotate_front(postures)
            postures = postures + p

            p = self.move_front(postures)
            postures = postures + p

            p = self.move_head(postures)
            postures = postures + p

            p = self.rotate_head(postures)
            postures = postures + p

        else:
            p = self.move_back_contracted(postures)
            postures = postures + p

            p = self.move_head_contracted(postures)
            postures = postures + p

            p = self.rotate_head_contracted(postures)
            postures = postures + p

            p = self.move_front_contracted(postures)
            postures = postures + p

        return postures

    # noinspection PyShadowingBuiltins
    def __init__(self, host, id, start_x, start_y, end_x, end_y, config=Configuration()):

        self.host = host  # the calling tracker object
        self.id = id  # a id number for the animal
        self.config = config

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

        self.scaled_head_radius = 5
        self.scaled_front_radius = 6
        self.scaled_back_radius = 7

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

        return r

    # noinspection PyUnusedLocal
    def track(self, source, raw_matrix, weight_matrix, animals, frame_time):
        """tracking a single animal"""
        # source is the original frame, raw_matrix the subtracted one

        debug = [("rm", raw_matrix)]
        # find a threshold for the subtracted image using the Otsu's method
        thr, thresh_matrix = cv2.threshold(raw_matrix, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # thr, foo = cv2.threshold(raw_matrix, 50, 255, cv2.THRESH_BINARY)
        # thr = 50

        debug.append(("otsu", thresh_matrix))
        # self.host.logger.log("threshold: " + str(thr))

        matrix = raw_matrix.astype(np.float)
        matrix = matrix - thr
        # matrix[matrix < 0] = -50

        # setting up the alternative postures
        postures = self.generate_postures()

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

            h = p.head.diff(animal_center).add(mask_center)
            f = p.front.diff(animal_center).add(mask_center)
            b = p.back.diff(animal_center).add(mask_center)

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
            mh = mask_half

            product = np.multiply(mask, matrix[int(ac.y - mh): int(ac.y + mh), int(ac.x - mh):int(ac.x + mh)])

            val = product.sum()

            # self.host.logger.log("val: " + str(val))

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

        total_postures = len(postures)

        self.host.logger.log("total postures: " + str(total_postures))

        c = 0
        dc = 1
        cell_size = 40

        while c < min(total_postures, 10):

            debug_postures = np.zeros((rows, cols), np.uint8)

            for y in range(0, 5):
                done = False
                for x in range(0, 7):
                    if c == total_postures:
                        done = True
                        break

                    white = (255, 255, 255)
                    gray = (155, 155, 155)

                    p = postures[c]

                    cell_center = geometry.Point(x * cell_size + cell_size / 2, y * cell_size + cell_size / 2)
                    animal_center = self.back

                    cv2.rectangle(debug_postures, (x * cell_size, y * cell_size),
                                  (x * cell_size + cell_size, y * cell_size + cell_size), gray)

                    cv2.circle(debug_postures, p.head.diff(animal_center).add(cell_center).as_int_tuple(),
                               self.scaled_head_radius, white)
                    cv2.circle(debug_postures, p.front.diff(animal_center).add(cell_center).as_int_tuple(),
                               self.scaled_front_radius, white)
                    cv2.circle(debug_postures, p.back.diff(animal_center).add(cell_center).as_int_tuple(),
                               self.scaled_back_radius, white)

                    c += 1

                if done:
                    break

            debug.append(("postures " + str(dc), debug_postures))
            dc = dc + 1

        return debug


class TrackingFlowElement:
    """container for the results of the tracking operation."""

    def __init__(self, time, positions, filtered_image, debug):
        self.time = time
        self.positions = positions
        self.filtered_image = filtered_image
        self.debug_frames = debug


class Tracker:
    class Configuration:
        """configuration values TODO to be superseded by a config file?"""
        skeletonization_res_width = 320
        skeletonization_res_height = 240
        skeletonization_border = 20
        vertebra_length = 10
        pixels_to_meters = 1
        scale = 1
        max_animal_velocity = 1  # m/s

        def __init__(self):
            pass

    scale_factor = 1

    finished = False

    animals = []  # the list of tracked animals

    # noinspection PyArgumentList
    def __init__(self, frame_size, config=Configuration()):
        self.config = config

        frame_width, frame_height = frame_size
        self.scale_factor = self.calculate_scale_factor(frame_width, frame_height)
        config.pixels_to_meters = float(config.scale) / frame_width
        config.max_animal_velocity = 1  # m/s
        config.vertebra_length = config.vertebra_length * self.scale_factor
        self.background = None
        self.show_model = True
        self.show_posture = True
        self.image_scale_factor = 1

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

    @staticmethod
    def calculate_background(self, frame):
        """calculate background from the frames before the video stream ends, by averaging """
        bg = frame.astype(np.uint8)
        self.background = bg

    # TODO must add to GUI routine to add animals
    def add_animal(self, start_x, start_y, end_x, end_y, config=Animal.Configuration()):
        """add an animal to the list of animals"""
        self.animals.append(Animal(self, len(self.animals), start_x, start_y, end_x, end_y, config))
        return self.animals[-1]

    def delete_all_animals(self):
        """delete all tracked animals from the list"""
        self.animals = []

    # noinspection PyUnusedLocal
    def track_animals(self, source, matrix_fs, matrix, frame_time):
        """loop over animals and call the tracker in the animal class"""
        debug = []

        weights = []  # TODO these are initialized to matrices of ones, but what are they for?
        rows, cols = matrix.shape[:2]

        index = 2
        for _ in self.animals:
            weight = np.ones((rows, cols), np.float)
            weights.append(weight)
            index += 1

        for a, w in zip(self.animals, weights):
            debug1 = a.track(source, matrix, w, self.animals, frame_time)
            debug = debug + debug1

        return debug

    def track(self, frame, frame_time=0):
        """track one frame"""

        if self.background is None:
            return
        debug = []

        frame_gr = cv2.absdiff(frame, self.background)  # take the absolute difference
        frame_gr = cv2.cvtColor(frame_gr, cv2.COLOR_BGR2GRAY)  # convert to grayscale
        cv2.normalize(frame_gr, frame_gr, 0, 255, cv2.NORM_MINMAX)  # normalize so that the minimum is zero

        # kernel = np.ones((10, 10), np.uint8)
        # frame_gr = cv2.erode(frame_gr, kernel, iterations = 3)

        # frame_gr = morphology.skeletonize(frame_gr > 50)
        # frame_gr, distance = morphology.medial_axis(frame_gr > 50, return_distance = True)
        # frame_gr = bwmorph_thin.bwmorph_thin(frame_gr > 50, 30)
        # frame_gr = frame_gr.astype(np.uint8);

        # cv2.normalize(frame_gr, frame_gr, 0, 255, cv2.NORM_MINMAX)

        debug.append(("source", frame_gr))

        # frame_gr_resized1 = filters.gaussian_filter(frame_gr, 8)
        # cv2.normalize(frame_gr_resized1, frame_gr_resized1, 0, 255, cv2.NORM_MINMAX)

        frame_gr_resized1 = frame_gr

        debug.append(("smoothed", frame_gr_resized1))

        frame_gr_resized = self.resize(frame_gr_resized1)  # resize to the skeletonized size and go to 8-bit integers
        frame_gr_resized = frame_gr_resized.astype(np.uint8)

        # ret, frame_gr_resized = cv2.threshold(frame_gr_resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # frame_gr_resized = morphology.remove_small_objects(frame_gr_resized > 0, 100, 2, in_place = True)
        # frame_gr_resized = frame_gr_resized.astype(np.uint8)
        cv2.normalize(frame_gr_resized, frame_gr_resized, 0, 255, cv2.NORM_MINMAX)

        # add borders to the frame, fill with zeros
        border = self.config.skeletonization_border
        frame_gr_resized = cv2.copyMakeBorder(frame_gr_resized, border, border, border, border, cv2.BORDER_CONSTANT, 0)

        # track animals
        debug1 = self.track_animals(frame, frame_gr, frame_gr_resized, frame_time)

        debug = debug + debug1

        positions = self.get_animal_positions()

        tracking_flow_element = TrackingFlowElement(frame_time, positions, frame_gr, debug)

        self.draw_animals(frame)
        return tracking_flow_element

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

            white = (255, 255, 255)
            green = (0, 255, 0)
            red = (255, 0, 0)
            yellow = (255, 255, 0)

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
                fr = self.scaled_radius(a.front_radius)
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