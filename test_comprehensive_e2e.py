#!/usr/bin/env python3
"""全面的端到端测试 - 模拟实际保存-加载场景"""

import numpy as np
import tempfile
import json
from pathlib import Path
import math


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
    
    x_vec = vertices_trans[3] - vertices_trans[0]
    z_rotation = radians_to_degrees(np.arctan2(x_vec[1], x_vec[0])) % 360
    
    if vertices[3][2] != vertices[0][2]:
        x_vec_rot = rotate_around_z(x_vec, -z_rotation, degrees=True)
        y_rotation = -radians_to_degrees(np.arctan2(x_vec_rot[2], x_vec_rot[0])) % 360
    
    if vertices[0][2] != vertices[1][2]:
        y_vec = np.subtract(vertices_trans[1], vertices_trans[0])
        y_vec_rot = rotate_around_z(y_vec, -z_rotation, degrees=True)
        y_vec_rot = rotate_around_y(y_vec_rot, -y_rotation, degrees=True)
        x_rotation = radians_to_degrees(np.arctan2(y_vec_rot[2], y_vec_rot[1])) % 360
    
    return x_rotation, y_rotation, z_rotation


def abs2rel_rotation(abs_rotation: float) -> float:
    rel_rotation = np.deg2rad(abs_rotation)
    if rel_rotation > np.pi:
        rel_rotation = rel_rotation - 2 * np.pi
    return rel_rotation


def rel2abs_rotation(rel_rotation: float) -> float:
    abs_rotation = np.rad2deg(rel_rotation)
    if abs_rotation < 0:
        abs_rotation = abs_rotation + 360
    return abs_rotation


# ============================================================================ #
#                               简化的BBox类                                   #
# ============================================================================ #

class SimpleBBox:
    """简化的BBox类"""
    
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
    
    def set_rotations(self, x_angle, y_angle, z_angle):
        self.x_rotation = x_angle % 360
        self.y_rotation = y_angle % 360
        self.z_rotation = z_angle % 360
    
    def set_x_rotation(self, angle):
        self.x_rotation = angle % 360
    
    def set_y_rotation(self, angle):
        self.y_rotation = angle % 360
    
    def set_z_rotation(self, angle):
        self.z_rotation = angle % 360
    
    def set_x_translation(self, x):
        self.center = (x, self.center[1], self.center[2])
    
    def set_y_translation(self, y):
        self.center = (self.center[0], y, self.center[2])
    
    def set_z_translation(self, z):
        self.center = (self.center[0], self.center[1], z)
    
    def set_length(self, length):
        self.length = length
        self.set_axis_aligned_verticies()
    
    def set_width(self, width):
        self.width = width
        self.set_axis_aligned_verticies()
    
    def set_height(self, height):
        self.height = height
        self.set_axis_aligned_verticies()
    
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
    
    def get_orientation_vector(self):
        """获取方向箭头向量"""
        arrow_length = self.length * 0.4
        bp2 = np.array([arrow_length, 0, 0])
        
        center = np.array(self.get_center())
        rotations = self.get_rotations()
        
        v = rotate_around_x(bp2, rotations[0], degrees=True)
        v = rotate_around_y(v, rotations[1], degrees=True)
        v = rotate_around_z(v, rotations[2], degrees=True)
        
        return center + v


# ============================================================================ #
#                              格式模拟类                                      #
# ============================================================================ #

class MockCentroidFormat:
    """模拟 Centroid 格式"""
    
    def __init__(self, export_precision=6, relative_rotation=False):
        self.export_precision = export_precision
        self.relative_rotation = relative_rotation
    
    def round_dec(self, x):
        return np.round(x, self.export_precision).tolist()
    
    def export_to_dict(self, bbox):
        """导出为字典"""
        centroid = bbox.get_center()
        length, width, height = bbox.get_dimensions()
        rotations = bbox.get_rotations()
        
        if self.relative_rotation:
            rotations = tuple(abs2rel_rotation(r) for r in rotations)
        
        return {
            "name": bbox.classname,
            "centroid": {
                "x": self.round_dec(centroid[0]),
                "y": self.round_dec(centroid[1]),
                "z": self.round_dec(centroid[2]),
            },
            "dimensions": {
                "length": self.round_dec(length),
                "width": self.round_dec(width),
                "height": self.round_dec(height),
            },
            "rotations": {
                "x": self.round_dec(rotations[0]),
                "y": self.round_dec(rotations[1]),
                "z": self.round_dec(rotations[2]),
            }
        }
    
    def import_from_dict(self, data):
        """从字典导入"""
        x = data["centroid"]["x"]
        y = data["centroid"]["y"]
        z = data["centroid"]["z"]
        length = data["dimensions"]["length"]
        width = data["dimensions"]["width"]
        height = data["dimensions"]["height"]
        
        bbox = SimpleBBox(x, y, z, length, width, height)
        
        rotations = (data["rotations"]["x"], data["rotations"]["y"], data["rotations"]["z"])
        if self.relative_rotation:
            rotations = tuple(rel2abs_rotation(r) for r in rotations)
        
        bbox.set_rotations(*rotations)
        bbox.classname = data["name"]
        
        return bbox


class MockKittiFormat:
    """模拟 KITTI 格式（简化，不包含校准变换）"""
    
    def __init__(self, export_precision=6, transformed=True):
        self.export_precision = export_precision
        self.transformed = transformed
    
    def round_dec(self, x):
        return np.round(x, self.export_precision).tolist()
    
    def export_to_dict(self, bbox):
        """导出为 KITTI 格式字典"""
        centroid = list(bbox.get_center())
        length, width, height = bbox.get_dimensions()
        
        dimensions = (height, width, length)
        
        if self.transformed:
            centroid[2] = centroid[2] - height / 2
        
        rotation = bbox.get_z_rotation()
        rotation = abs2rel_rotation(rotation)
        if self.transformed:
            rotation = -(rotation - math.pi / 2)
        
        return {
            "type": bbox.classname,
            "location": self.round_dec(centroid),
            "dimensions": self.round_dec(dimensions),
            "rotation_y": self.round_dec(rotation),
        }
    
    def import_from_dict(self, data):
        """从 KITTI 格式字典导入"""
        centroid = tuple(data["location"])
        height, width, length = tuple(data["dimensions"])
        
        bbox = SimpleBBox(*centroid, length, width, height)
        
        if self.transformed:
            bbox.set_z_translation(bbox.get_center()[2] + height / 2)
        
        rotation = data["rotation_y"]
        if self.transformed:
            rotation = -rotation + math.pi / 2
        rotation = rel2abs_rotation(rotation)
        
        bbox.set_rotations(0, 0, rotation)
        bbox.classname = data["type"]
        
        return bbox


class MockVerticesFormat:
    """模拟 Vertices 格式"""
    
    def __init__(self, export_precision=6):
        self.export_precision = export_precision
    
    def round_dec(self, x):
        return np.round(x, self.export_precision).tolist()
    
    def export_to_dict(self, bbox):
        """导出为顶点格式"""
        vertices = bbox.get_vertices()
        return {
            "name": bbox.classname,
            "vertices": [self.round_dec(v) for v in vertices],
        }
    
    def import_from_dict(self, data):
        """从顶点格式导入"""
        vertices = data["vertices"]
        
        centroid = tuple(
            np.add(np.subtract(vertices[4], vertices[2]) / 2, vertices[2])
        )
        
        length = vector_length(np.subtract(vertices[3], vertices[0]))
        width = vector_length(np.subtract(vertices[1], vertices[0]))
        height = vector_length(np.subtract(vertices[4], vertices[0]))
        
        x_rot, y_rot, z_rot = vertices2rotations(vertices, centroid)
        
        bbox = SimpleBBox(*centroid, length, width, height)
        bbox.set_rotations(x_rot, y_rot, z_rot)
        bbox.classname = data["name"]
        
        return bbox


# ============================================================================ #
#                              测试函数                                        #
# ============================================================================ #

def test_format_roundtrip(format_name, format_class, bbox, **format_kwargs):
    """测试单个格式的 round-trip"""
    fmt = format_class(**format_kwargs)
    
    original_vertices = bbox.get_vertices()
    original_orientation = bbox.get_orientation_vector()
    original_center = bbox.get_center()
    original_dims = bbox.get_dimensions()
    
    exported = fmt.export_to_dict(bbox)
    imported = fmt.import_from_dict(exported)
    
    imported_vertices = imported.get_vertices()
    imported_orientation = imported.get_orientation_vector()
    imported_center = imported.get_center()
    imported_dims = imported.get_dimensions()
    
    vertices_match = np.allclose(original_vertices, imported_vertices, atol=1e-4)
    orientation_match = np.allclose(original_orientation, imported_orientation, atol=1e-4)
    center_match = np.allclose(original_center, imported_center, atol=1e-4)
    dims_match = np.allclose(original_dims, imported_dims, atol=1e-4)
    
    max_vertex_diff = np.max(np.abs(original_vertices - imported_vertices))
    max_orient_diff = np.max(np.abs(original_orientation - imported_orientation))
    max_center_diff = np.max(np.abs(np.array(original_center) - np.array(imported_center)))
    max_dims_diff = np.max(np.abs(np.array(original_dims) - np.array(imported_dims)))
    
    return {
        "format": format_name,
        "vertices_match": vertices_match,
        "orientation_match": orientation_match,
        "center_match": center_match,
        "dims_match": dims_match,
        "all_match": all([vertices_match, orientation_match, center_match, dims_match]),
        "max_vertex_diff": max_vertex_diff,
        "max_orient_diff": max_orient_diff,
        "max_center_diff": max_center_diff,
        "max_dims_diff": max_dims_diff,
        "original_rot": bbox.get_rotations(),
        "imported_rot": imported.get_rotations(),
    }


def run_comprehensive_tests():
    """运行全面的测试"""
    print("=" * 80)
    print("全面的端到端测试 - 保存-加载场景验证")
    print("=" * 80)
    
    test_cases = [
        ("轴对齐无旋转", (0, 0, 0), (0, 0, 0), (4, 6, 8)),
        ("带平移无旋转", (10, 20, 30), (0, 0, 0), (4, 6, 8)),
        ("简单Z旋转", (0, 0, 0), (0, 0, 45), (4, 6, 8)),
        ("Z旋转带平移", (5, 5, 5), (0, 0, 90), (4, 6, 8)),
        ("复合旋转", (0, 0, 0), (30, 45, 60), (4, 6, 8)),
        ("复合旋转带平移", (1, 2, 3), (90, 180, 270), (4, 6, 8)),
        ("大角度", (0, 0, 0), (120, 240, 300), (4, 6, 8)),
        ("只有X旋转", (0, 0, 0), (30, 0, 0), (4, 6, 8)),
        ("只有Y旋转", (0, 0, 0), (0, 45, 0), (4, 6, 8)),
        ("X+Z旋转", (0, 0, 0), (30, 0, 60), (4, 6, 8)),
        ("Y+Z旋转", (0, 0, 0), (0, 45, 60), (4, 6, 8)),
        ("万向锁情况", (0, 0, 0), (45, 90, 45), (4, 6, 8)),
        ("实际使用场景1", (10, -5, 2), (0, 0, 120), (2, 1.5, 1.8)),
        ("实际使用场景2", (-3, 8, 0.5), (0, 0, 270), (3, 2, 2.5)),
    ]
    
    all_results = []
    all_passed = True
    
    for name, center, rotations, dims in test_cases:
        print(f"\n{'=' * 60}")
        print(f"测试: {name}")
        print(f"  中心: {center}, 旋转: {rotations}, 尺寸: {dims}")
        print(f"{'=' * 60}")
        
        bbox = SimpleBBox(*center, *dims)
        bbox.set_rotations(*rotations)
        
        formats = [
            ("Centroid (绝对角度)", MockCentroidFormat, {"relative_rotation": False}),
            ("Centroid (相对角度)", MockCentroidFormat, {"relative_rotation": True}),
            ("KITTI (transformed)", MockKittiFormat, {"transformed": True}),
            ("KITTI (untransformed)", MockKittiFormat, {"transformed": False}),
            ("Vertices", MockVerticesFormat, {}),
        ]
        
        for fmt_name, fmt_class, fmt_kwargs in formats:
            result = test_format_roundtrip(fmt_name, fmt_class, bbox, **fmt_kwargs)
            all_results.append(result)
            
            status = "✓" if result["all_match"] else "✗"
            print(f"\n  {status} {fmt_name}:")
            print(f"    顶点匹配: {result['vertices_match']} (差异: {result['max_vertex_diff']:.2e})")
            print(f"    方向匹配: {result['orientation_match']} (差异: {result['max_orient_diff']:.2e})")
            print(f"    中心匹配: {result['center_match']} (差异: {result['max_center_diff']:.2e})")
            print(f"    尺寸匹配: {result['dims_match']} (差异: {result['max_dims_diff']:.2e})")
            
            if not result["all_match"]:
                all_passed = False
                print(f"    原始旋转: {result['original_rot']}")
                print(f"    导入旋转: {result['imported_rot']}")
    
    print(f"\n{'=' * 80}")
    print("测试结果汇总")
    print("=" * 80)
    
    format_stats = {}
    for result in all_results:
        fmt = result["format"]
        if fmt not in format_stats:
            format_stats[fmt] = {"pass": 0, "fail": 0, "max_vertex_diff": 0}
        if result["all_match"]:
            format_stats[fmt]["pass"] += 1
        else:
            format_stats[fmt]["fail"] += 1
        format_stats[fmt]["max_vertex_diff"] = max(
            format_stats[fmt]["max_vertex_diff"],
            result["max_vertex_diff"]
        )
    
    print("\n按格式统计:")
    for fmt, stats in format_stats.items():
        total = stats["pass"] + stats["fail"]
        status = "✓" if stats["fail"] == 0 else "✗"
        print(f"  {status} {fmt}: {stats['pass']}/{total} 通过, 最大顶点差异: {stats['max_vertex_diff']:.2e}")
    
    print(f"\n{'=' * 80}")
    print(f"所有测试通过: {all_passed}")
    print(f"{'=' * 80}")
    
    return all_passed, all_results


def check_precision_effect():
    """检查导出精度对 round-trip 的影响"""
    print("\n" + "=" * 80)
    print("检查导出精度对 round-trip 的影响")
    print("=" * 80)
    
    bbox = SimpleBBox(10.123456, 20.654321, 5.987654, 2.12345, 1.54321, 1.87654)
    bbox.set_rotations(30.1234, 45.6789, 60.9876)
    
    precisions = [2, 4, 6, 8, 10]
    
    for precision in precisions:
        print(f"\n--- 精度: {precision} 位小数 ---")
        
        fmt = MockCentroidFormat(export_precision=precision)
        exported = fmt.export_to_dict(bbox)
        imported = fmt.import_from_dict(exported)
        
        original_vertices = bbox.get_vertices()
        imported_vertices = imported.get_vertices()
        max_diff = np.max(np.abs(original_vertices - imported_vertices))
        
        original_center = bbox.get_center()
        imported_center = imported.get_center()
        center_diff = np.max(np.abs(np.array(original_center) - np.array(imported_center)))
        
        print(f"  导出中心: {exported['centroid']}")
        print(f"  导出旋转: {exported['rotations']}")
        print(f"  最大顶点差异: {max_diff:.2e}")
        print(f"  中心点差异: {center_diff:.2e}")


if __name__ == "__main__":
    run_comprehensive_tests()
    check_precision_effect()
