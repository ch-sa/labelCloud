# order in which the bounding box edges are drawn
BBOX_EDGES = [
    (0, 1),
    (0, 3),
    (0, 4),
    (2, 1),
    (2, 3),
    (2, 6),
    (5, 1),
    (5, 4),
    (5, 6),
    (7, 3),
    (7, 4),
    (7, 6),
]


# vertices of each side
BBOX_SIDES = {
    "top": [4, 5, 6, 7],
    "bottom": [0, 1, 2, 3],
    "right": [2, 3, 7, 6],
    "back": [0, 3, 7, 4],
    "left": [0, 1, 5, 4],
    "front": [1, 2, 6, 5],
}
