#!/usr/bin/env python3
"""全面的坐标转换Round-Trip测试"""

import json
import math
import numpy as np
from pathlib import Path
from typing import Tuple, List


# ============================================================================ #
#                          核心数学函数（从源码复制）                           #
# ============================================================================ #

def degrees_to_radians(degrees: float) -> float:
    return degrees * (np.pi / 180)


def radians_to_degrees(radians: float) -> float:
    return radians * (180 / np.pi)


def rotate_around_x(point, angle: float, degrees: bool = False):
    if degrees:
        angle = degrees_to_radians(angle)
    r_matrix = np.array([
        [1, 0, 0],
        [0, np.cos(angle), -np.sin(angle)],
        [0, np.sin(angle), np.cos(angle)],
    ])
    return r_matrix.dot(point)


def rotate_around_y(point, angle: float, degrees: bool = False):
    if degrees:
        angle = degrees_to_radians(angle)
    r_matrix = np.array([
        [math.cos(angle), 0, math.sin(angle)],
        [0, 1, 0],
        [-math.sin(angle), 0, math.cos(angle)],
    ])
    return r_matrix.dot(point)


def rotate_around_z(point, angle: float, degrees: bool = False):
    if degrees:
        angle = degrees_to_radians(angle)
    r_matrix = np.array([
        [np.cos(angle), -np.sin(angle), 0],
        [np.sin(angle), np.cos(angle), 0],
        [0, 0, 1],
    ])
    return r_matrix.dot(point)


def rotate_around_zyx(point, x_angle: float, y_angle: float, z_angle: float, 
                      degrees: bool = False):
    return rotate_around_z(
        rotate_around_y(rotate_around_x(point, x_angle, degrees), y_angle, degrees),
        z_angle, degrees,
    )


def translate_point(point, dx: float, dy: float, dz: float, backwards: bool = False):
    if backwards:
        dx, dy, dz = (-dx, -dy, -dz)
    return tuple(np.add(np.array(point), np.array([dx, dy, dz])))


def vector_length(point) -> float:
    return float(np.linalg.norm(point))


def rotate_bbox_around_center(vertices, center, rotations):
    rotated_vertices = []
    for vertex in vertices:
        centered_vertex = translate_point(vertex, *center, backwards=True)
        rotated_vertex = rotate_around_zyx(centered_vertex, *rotations, degrees=True)
        rotated_vertices.append(translate_point(rotated_vertex, *center))
    return rotated_vertices


def vertices2rotations(vertices, centroid):
    """从顶点计算旋转角度"""
    x_rotation, y_rotation, z_rotation = (0.0, 0.0, 0.0)
    vertices_trans = np.subtract(vertices, centroid)
    
    x_vec = vertices_trans[3] - vertices_trans[0]  # length向量
    z_rotation = radians_to_degrees(np.arctan2(x_vec[1], x_vec[0])) % 360
    
    if vertices[3][2] != vertices[0][2]:
        x_vec_rot = rotate_around_z(x_vec, -z_rotation, degrees=True)
        y_rotation = -radians_to_degrees(np.arctan2(x_vec_rot[2], x_vec_rot[0])) % 360
    
    if vertices[0][2] != vertices[1][2]:
        y_vec = np.subtract(vertices_trans[1], vertices_trans[0])  # width向量
        y_vec_rot = rotate_around_z(y_vec, -z_rotation, degrees=True)
        y_vec_rot = rotate_around_y(y_vec_rot, -y_rotation, degrees=True)
        x_rotation = radians_to_degrees(np.arctan2(y_vec_rot[2], y_vec_rot[1])) % 360
    
    return x_rotation, y_rotation, z_rotation


def abs2rel_rotation(abs_rotation: float) -> float:
    """Convert absolute rotation 0..360° into -pi..+pi from x-Axis."""
    rel_rotation = np.deg2rad(abs_rotation)
    if rel_rotation > np.pi:
        rel_rotation = rel_rotation - 2 * np.pi
    return rel_rotation


def rel2abs_rotation(rel_rotation: float) -> float:
    """Convert relative rotation from -pi..+pi into 0..360° from x-Axis."""
    abs_rotation = np.rad2deg(rel_rotation)
    if abs_rotation < 0:
        abs_rotation = abs_rotation + 360
    return abs_rotation


# ============================================================================ #
#                               简化的BBox类                                   #
# ============================================================================ #

class SimpleBBox:
    """简化的BBox类，模拟labelCloud的BBox"""
    
    def __init__(self, cx: float, cy: float, cz: float, 
                 length: float, width: float, height: float):
        self.center = (cx, cy, cz)
        self.length = length
        self.width = width
        self.height = height
        self.x_rotation = 0.0
        self.y_rotation = 0.0
        self.z_rotation = 0.0
        self.classname = "Car"
        
        self.verticies = np.zeros((8, 3))
        self.set_axis_aligned_verticies()
    
    def set_axis_aligned_verticies(self):
        self.verticies = np.array([
            [-self.length / 2, -self.width / 2, -self.height / 2],  # 0
            [-self.length / 2, self.width / 2, -self.height / 2],   # 1
            [self.length / 2, self.width / 2, -self.height / 2],    # 2
            [self.length / 2, -self.width / 2, -self.height / 2],   # 3
            [-self.length / 2, -self.width / 2, self.height / 2],   # 4
            [-self.length / 2, self.width / 2, self.height / 2],    # 5
            [self.length / 2, self.width / 2, self.height / 2],     # 6
            [self.length / 2, -self.width / 2, self.height / 2],    # 7
        ])
    
    def get_center(self):
        return self.center
    
    def get_dimensions(self):
        return self.length, self.width, self.height
    
    def get_rotations(self):
        return self.x_rotation, self.y_rotation, self.z_rotation
    
    def get_z_rotation(self):
        return self.z_rotation
    
    def get_classname(self):
        return self.classname
    
    def set_classname(self, name):
        self.classname = name
    
    def set_rotations(self, x_angle, y_angle, z_angle):
        self.x_rotation = x_angle % 360
        self.y_rotation = y_angle % 360
        self.z_rotation = z_angle % 360
    
    def get_axis_aligned_vertices(self):
        coords = []
        for vertex in self.verticies:
            coords.append(translate_point(vertex, *self.center))
        return coords
    
    def get_vertices(self):
        self.set_axis_aligned_verticies()
        rotated_vertices = rotate_bbox_around_center(
            self.get_axis_aligned_vertices(),
            self.center,
            self.get_rotations(),
        )
        return np.array(rotated_vertices)


# ============================================================================ #
#                               格式模拟类                                     #
# ============================================================================ #

class MockCentroidFormat:
    """模拟CentroidFormat"""
    
    @staticmethod
    def export_bbox(bbox: SimpleBBox, relative_rotation: bool = False):
        label = {
            "name": bbox.get_classname(),
            "centroid": {
                "x": bbox.get_center()[0],
                "y": bbox.get_center()[1],
                "z": bbox.get_center()[2],
            },
            "dimensions": {
                "length": bbox.get_dimensions()[0],
                "width": bbox.get_dimensions()[1],
                "height": bbox.get_dimensions()[2],
            },
        }
        
        conv_rotations = bbox.get_rotations()
        if relative_rotation:
            conv_rotations = tuple(abs2rel_rotation(r) for r in conv_rotations)
        
        label["rotations"] = {
            "x": conv_rotations[0],
            "y": conv_rotations[1],
            "z": conv_rotations[2],
        }
        return label
    
    @staticmethod
    def import_bbox(label: dict, relative_rotation: bool = False):
        x = label["centroid"]["x"]
        y = label["centroid"]["y"]
        z = label["centroid"]["z"]
        length = label["dimensions"]["length"]
        width = label["dimensions"]["width"]
        height = label["dimensions"]["height"]
        
        bbox = SimpleBBox(x, y, z, length, width, height)
        
        rotations = (label["rotations"]["x"], label["rotations"]["y"], label["rotations"]["z"])
        if relative_rotation:
            rotations = tuple(rel2abs_rotation(r) for r in rotations)
        
        bbox.set_rotations(*rotations)
        bbox.set_classname(label["name"])
        return bbox


class MockVerticesFormat:
    """模拟VerticesFormat"""
    
    @staticmethod
    def export_bbox(bbox: SimpleBBox):
        return {
            "name": bbox.get_classname(),
            "vertices": bbox.get_vertices().tolist(),
        }
    
    @staticmethod
    def import_bbox(label: dict):
        vertices = label["vertices"]
        
        # 计算中心点: (vertices[4] - vertices[2])/2 + vertices[2]
        centroid = tuple(np.add(np.subtract(vertices[4], vertices[2]) / 2, vertices[2]))
        
        # 计算尺寸
        length = vector_length(np.subtract(vertices[0], vertices[3]))
        width = vector_length(np.subtract(vertices[0], vertices[1]))
        height = vector_length(np.subtract(vertices[0], vertices[4]))
        
        # 计算旋转
        rotations = vertices2rotations(vertices, centroid)
        
        bbox = SimpleBBox(*centroid, length, width, height)
        bbox.set_rotations(*rotations)
        bbox.set_classname(label["name"])
        return bbox


class MockKittiUntransformedFormat:
    """模拟KittiFormat (transformed=False)"""
    
    @staticmethod
    def export_bbox(bbox: SimpleBBox):
        """导出到KITTI格式"""
        classname = bbox.get_classname()
        centroid = bbox.get_center()
        length, width, height = bbox.get_dimensions()
        
        # KITTI dimensions: height, width, length
        kitti_dims = (height, width, length)
        
        # KITTI rotation_y (直接使用z_rotation转换)
        rotation = bbox.get_z_rotation()
        rotation = abs2rel_rotation(rotation)  # 角度转弧度
        
        return {
            "type": classname,
            "truncated": 0,
            "occluded": 0,
            "alpha": 0,
            "bbox_2d": (0, 0, 0, 0),
            "dimensions": kitti_dims,
            "location": centroid,
            "rotation_y": rotation,
        }
    
    @staticmethod
    def import_bbox(kitti_data: dict):
        """从KITTI格式导入"""
        classname = kitti_data["type"]
        centroid = kitti_data["location"]
        
        # KITTI dimensions: height, width, length
        height, width, length = kitti_data["dimensions"]
        
        # KITTI rotation_y
        rotation = kitti_data["rotation_y"]
        rotation_deg = rel2abs_rotation(rotation)  # 弧度转角度
        
        bbox = SimpleBBox(*centroid, length, width, height)
        bbox.set_rotations(0, 0, rotation_deg)
        bbox.set_classname(classname)
        return bbox


class MockKittiTransformedFormat:
    """模拟KittiFormat (transformed=True) - 带坐标系转换"""
    
    @staticmethod
    def export_bbox(bbox: SimpleBBox):
        """导出到KITTI格式（带相机-激光雷达转换模拟）"""
        classname = bbox.get_classname()
        centroid = list(bbox.get_center())
        length, width, height = bbox.get_dimensions()
        
        # KITTI: centroid is on bottom face
        centroid[2] = centroid[2] - height / 2
        
        # KITTI dimensions: height, width, length
        kitti_dims = (height, width, length)
        
        # KITTI rotation_y with 90° offset
        rotation = bbox.get_z_rotation()
        rotation = abs2rel_rotation(rotation)
        rotation = -(rotation - math.pi / 2)  # KITTI的特殊转换
        
        return {
            "type": classname,
            "truncated": 0,
            "occluded": 0,
            "alpha": 0,
            "bbox_2d": (0, 0, 0, 0),
            "dimensions": kitti_dims,
            "location": tuple(centroid),
            "rotation_y": rotation,
        }
    
    @staticmethod
    def import_bbox(kitti_data: dict):
        """从KITTI格式导入（带相机-激光雷达转换模拟）"""
        classname = kitti_data["type"]
        centroid = list(kitti_data["location"])
        
        # KITTI dimensions: height, width, length
        height, width, length = kitti_data["dimensions"]
        
        # KITTI: centroid is on bottom face -> convert to center
        centroid[2] = centroid[2] + height / 2
        
        # KITTI rotation_y with 90° offset
        rotation = kitti_data["rotation_y"]
        rotation = -rotation + math.pi / 2  # 逆转换
        rotation_deg = rel2abs_rotation(rotation)
        
        bbox = SimpleBBox(*centroid, length, width, height)
        bbox.set_rotations(0, 0, rotation_deg)
        bbox.set_classname(classname)
        return bbox


# ============================================================================ #
#                                 测试函数                                     #
# ============================================================================ #

def create_test_bboxes():
    """创建各种测试用的BBox"""
    test_cases = []
    
    # 案例1: 轴对齐，无旋转
    bbox1 = SimpleBBox(10.0, 20.0, 30.0, 4.0, 5.0, 6.0)
    bbox1.set_classname("Car")
    test_cases.append(("轴对齐，无旋转", bbox1))
    
    # 案例2: 只有Z轴旋转
    bbox2 = SimpleBBox(0.0, 0.0, 0.0, 4.0, 6.0, 8.0)
    bbox2.set_rotations(0, 0, 45.0)
    bbox2.set_classname("Pedestrian")
    test_cases.append(("只有Z轴旋转(45°)", bbox2))
    
    # 案例3: 复杂旋转
    bbox3 = SimpleBBox(5.0, 5.0, 5.0, 2.0, 3.0, 4.0)
    bbox3.set_rotations(30.0, 45.0, 60.0)
    bbox3.set_classname("Cyclist")
    test_cases.append(("复杂旋转(30°, 45°, 60°)", bbox3))
    
    # 案例4: 特殊角度
    bbox4 = SimpleBBox(0.0, 0.0, 0.0, 2.0, 2.0, 2.0)
    bbox4.set_rotations(0, 0, 90.0)
    bbox4.set_classname("Van")
    test_cases.append(("Z轴旋转90°", bbox4))
    
    # 案例5: 负角度测试
    bbox5 = SimpleBBox(1.0, 2.0, 3.0, 3.0, 4.0, 5.0)
    bbox5.set_rotations(0, 0, 270.0)  # 等于-90°
    bbox5.set_classname("Truck")
    test_cases.append(("Z轴旋转270°(=-90°)", bbox5))
    
    return test_cases


def test_roundtrip(name: str, original_bbox: SimpleBBox, 
                   export_func, import_func, 
                   compare_rotations: bool = True) -> Tuple[bool, str]:
    """测试Round-Trip一致性"""
    
    # 导出
    exported = export_func(original_bbox)
    
    # 重新导入
    imported_bbox = import_func(exported)
    
    # 获取原始和导入后的顶点
    original_vertices = original_bbox.get_vertices()
    imported_vertices = imported_bbox.get_vertices()
    
    # 比较
    center_match = np.allclose(original_bbox.get_center(), imported_bbox.get_center())
    dims_match = np.allclose(original_bbox.get_dimensions(), imported_bbox.get_dimensions())
    vertices_match = np.allclose(original_vertices, imported_vertices, atol=1e-6)
    
    if compare_rotations:
        # 对于旋转，我们需要考虑等价角度（如 45° 和 405° 是等价的）
        orig_rot = original_bbox.get_rotations()
        imp_rot = imported_bbox.get_rotations()
        
        # 检查是否是等价角度（差360°的倍数）
        rot_match = all(
            np.isclose(o % 360, i % 360, atol=0.1) or
            np.isclose((o % 360) - 360, i % 360, atol=0.1) or
            np.isclose(o % 360, (i % 360) - 360, atol=0.1)
            for o, i in zip(orig_rot, imp_rot)
        )
    else:
        rot_match = True  # KITTI只支持Z旋转
    
    all_match = center_match and dims_match and vertices_match and rot_match
    
    # 生成详细信息
    details = f"\n  原始: center={original_bbox.get_center()}, dims={original_bbox.get_dimensions()}"
    if compare_rotations:
        details += f", rot={original_bbox.get_rotations()}"
    else:
        details += f", z_rot={original_bbox.get_z_rotation()}"
    
    details += f"\n  导入: center={imported_bbox.get_center()}, dims={imported_bbox.get_dimensions()}"
    if compare_rotations:
        details += f", rot={imported_bbox.get_rotations()}"
    else:
        details += f", z_rot={imported_bbox.get_z_rotation()}"
    
    details += f"\n  匹配: center={center_match}, dims={dims_match}, rot={rot_match}, vertices={vertices_match}"
    
    max_vertex_diff = np.max(np.abs(original_vertices - imported_vertices))
    details += f"\n  最大顶点差异: {max_vertex_diff}"
    
    return all_match, details


def run_all_tests():
    """运行所有Round-Trip测试"""
    print("=" * 80)
    print("全面的坐标转换Round-Trip测试")
    print("=" * 80)
    
    test_cases = create_test_bboxes()
    
    all_passed = True
    
    # ======================================================================== #
    # 测试1: Centroid格式（绝对角度）
    # ======================================================================== #
    print("\n" + "-" * 80)
    print("测试1: Centroid格式（绝对角度）")
    print("-" * 80)
    
    for name, bbox in test_cases:
        passed, details = test_roundtrip(
            name, bbox,
            MockCentroidFormat.export_bbox,
            lambda x: MockCentroidFormat.import_bbox(x, relative_rotation=False),
            compare_rotations=True
        )
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n[{status}] {name}{details}")
        if not passed:
            all_passed = False
    
    # ======================================================================== #
    # 测试2: Centroid格式（相对角度/弧度）
    # ======================================================================== #
    print("\n" + "-" * 80)
    print("测试2: Centroid格式（相对角度/弧度）")
    print("-" * 80)
    
    for name, bbox in test_cases:
        passed, details = test_roundtrip(
            name, bbox,
            lambda x: MockCentroidFormat.export_bbox(x, relative_rotation=True),
            lambda x: MockCentroidFormat.import_bbox(x, relative_rotation=True),
            compare_rotations=True
        )
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n[{status}] {name}{details}")
        if not passed:
            all_passed = False
    
    # ======================================================================== #
    # 测试3: Vertices格式
    # ======================================================================== #
    print("\n" + "-" * 80)
    print("测试3: Vertices格式")
    print("-" * 80)
    
    for name, bbox in test_cases:
        passed, details = test_roundtrip(
            name, bbox,
            MockVerticesFormat.export_bbox,
            MockVerticesFormat.import_bbox,
            compare_rotations=True
        )
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n[{status}] {name}{details}")
        if not passed:
            all_passed = False
    
    # ======================================================================== #
    # 测试4: KITTI Untransformed格式
    # ======================================================================== #
    print("\n" + "-" * 80)
    print("测试4: KITTI Untransformed格式")
    print("-" * 80)
    
    # KITTI只支持Z轴旋转，所以过滤测试用例
    kitti_test_cases = [
        (name, bbox) for name, bbox in test_cases 
        if bbox.x_rotation == 0 and bbox.y_rotation == 0
    ]
    
    for name, bbox in kitti_test_cases:
        passed, details = test_roundtrip(
            name, bbox,
            MockKittiUntransformedFormat.export_bbox,
            MockKittiUntransformedFormat.import_bbox,
            compare_rotations=False  # 只比较Z旋转
        )
        
        # 额外检查Z旋转
        z_rot_match = np.isclose(
            bbox.get_z_rotation() % 360,
            MockKittiUntransformedFormat.import_bbox(
                MockKittiUntransformedFormat.export_bbox(bbox)
            ).get_z_rotation() % 360,
            atol=0.1
        )
        
        if not z_rot_match:
            passed = False
            imported = MockKittiUntransformedFormat.import_bbox(
                MockKittiUntransformedFormat.export_bbox(bbox)
            )
            details += f"\n  Z旋转不匹配: 原始={bbox.get_z_rotation()}, 导入={imported.get_z_rotation()}"
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n[{status}] {name}{details}")
        if not passed:
            all_passed = False
    
    # ======================================================================== #
    # 测试5: KITTI Transformed格式（带90°偏移）
    # ======================================================================== #
    print("\n" + "-" * 80)
    print("测试5: KITTI Transformed格式（带90°偏移和中心点调整）")
    print("-" * 80)
    
    for name, bbox in kitti_test_cases:
        passed, details = test_roundtrip(
            name, bbox,
            MockKittiTransformedFormat.export_bbox,
            MockKittiTransformedFormat.import_bbox,
            compare_rotations=False
        )
        
        # 额外检查Z旋转
        imported = MockKittiTransformedFormat.import_bbox(
            MockKittiTransformedFormat.export_bbox(bbox)
        )
        z_rot_match = np.isclose(
            bbox.get_z_rotation() % 360,
            imported.get_z_rotation() % 360,
            atol=0.1
        )
        
        if not z_rot_match:
            passed = False
            details += f"\n  Z旋转不匹配: 原始={bbox.get_z_rotation()}, 导入={imported.get_z_rotation()}"
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n[{status}] {name}{details}")
        if not passed:
            all_passed = False
    
    # ======================================================================== #
    # 总结
    # ======================================================================== #
    print("\n" + "=" * 80)
    if all_passed:
        print("所有测试通过！")
    else:
        print("部分测试失败！")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()
