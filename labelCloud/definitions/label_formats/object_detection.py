from .base import BaseLabelFormat


class ObjectDetectionFormat(BaseLabelFormat):
    VERTICES = "vertices"
    CENTROID_REL = "centroid_rel"
    CENTROID_ABS = "centroid_abs"
    KITTI = "kitti"
    KITTI_UNTRANSFORMED = "kitti_untransformed"
