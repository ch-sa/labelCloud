#!/usr/bin/env python3
"""详细分析坐标转换问题 - 特别关注边界情况"""

import json
import math
import numpy as np
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
#                              详细测试函数                                     #
# ============================================================================ #

def manual_rotate_vertex(vertex, center, x_angle, y_angle, z_angle):
    """手动计算顶点旋转（用于验证）"""
    # 1. 平移到原点
    v = np.array(vertex) - np.array(center)
    
    # 2. 按顺序旋转：x -> y -> z（与 rotate_around_zyx 一致）
    v = rotate_around_x(v, x_angle, degrees=True)
    v = rotate_around_y(v, y_angle, degrees=True)
    v = rotate_around_z(v, z_angle, degrees=True)
    
    # 3. 平移回去
    v = v + np.array(center)
    return v


def test_rotation_matrix_correctness():
    """测试旋转矩阵的正确性"""
    print("=" * 80)
    print("测试1: 旋转矩阵正确性验证")
    print("=" * 80)
    
    # 测试点 (1, 0, 0) 绕 z 轴旋转 90° 应该变成 (0, 1, 0)
    p = np.array([1.0, 0.0, 0.0])
    result = rotate_around_z(p, 90, degrees=True)
    expected = np.array([0.0, 1.0, 0.0])
    
    print(f"点 (1,0,0) 绕 z 轴旋转 90°:")
    print(f"  预期: {expected}")
    print(f"  实际: {result}")
    print(f"  匹配: {np.allclose(result, expected)}")
    
    # 测试复合旋转 - 与现有测试用例匹配
    print(f"\n验证现有测试用例的旋转 (90°, 180°, 270°):")
    
    # 创建单位立方体
    bbox = SimpleBBox(0, 0, 0, 1, 1, 1)
    bbox.set_rotations(90, 180, 270)
    vertices = bbox.get_vertices()
    
    # 测试用例预期的顶点
    expected_vertices = np.array([
        [0.5, -0.5, 0.5],
        [0.5, -0.5, -0.5],
        [0.5, 0.5, -0.5],
        [0.5, 0.5, 0.5],
        [-0.5, -0.5, 0.5],
        [-0.5, -0.5, -0.5],
        [-0.5, 0.5, -0.5],
        [-0.5, 0.5, 0.5],
    ])
    
    print(f"原始轴对齐顶点（旋转前）:")
    bbox0 = SimpleBBox(0, 0, 0, 1, 1, 1)
    for i, v in enumerate(bbox0.get_vertices()):
        print(f"  顶点 {i}: {v}")
    
    print(f"\n旋转后顶点 (x=90°, y=180°, z=270°):")
    for i, v in enumerate(vertices):
        match = np.allclose(v, expected_vertices[i])
        status = "✓" if match else "✗"
        print(f"  顶点 {i}: {v} (预期: {expected_vertices[i]}) {status}")
    
    all_match = np.allclose(vertices, expected_vertices)
    print(f"\n所有顶点匹配: {all_match}")
    
    return all_match


def test_vertices2rotations_recovery():
    """测试 vertices2rotations 能否正确恢复旋转角度"""
    print("\n" + "=" * 80)
    print("测试2: vertices2rotations 旋转恢复能力")
    print("=" * 80)
    
    test_cases = [
        ("无旋转", (0, 0, 0)),
        ("只有Z旋转", (0, 0, 45)),
        ("只有Y旋转", (0, 45, 0)),
        ("只有X旋转", (45, 0, 0)),
        ("复合旋转1", (30, 45, 60)),
        ("复合旋转2", (90, 180, 270)),
        ("大角度", (120, 240, 300)),
    ]
    
    all_passed = True
    
    for name, rotations in test_cases:
        print(f"\n--- {name}: {rotations} ---")
        
        bbox = SimpleBBox(0, 0, 0, 4, 6, 8)
        bbox.set_rotations(*rotations)
        
        vertices = bbox.get_vertices()
        center = (0, 0, 0)
        
        # 尝试恢复旋转
        recovered = vertices2rotations(vertices.tolist(), center)
        
        # 检查是否等价（考虑 360° 循环）
        def angles_equal(a, b):
            diff = abs((a % 360) - (b % 360))
            return diff < 0.1 or abs(diff - 360) < 0.1
        
        x_match = angles_equal(rotations[0], recovered[0])
        y_match = angles_equal(rotations[1], recovered[1])
        z_match = angles_equal(rotations[2], recovered[2])
        
        print(f"  原始旋转: x={rotations[0]}, y={rotations[1]}, z={rotations[2]}")
        print(f"  恢复旋转: x={recovered[0]}, y={recovered[1]}, z={recovered[2]}")
        print(f"  匹配: x={x_match}, y={y_match}, z={z_match}")
        
        # 用恢复的旋转创建新BBox，比较顶点
        new_bbox = SimpleBBox(0, 0, 0, 4, 6, 8)
        new_bbox.set_rotations(*recovered)
        new_vertices = new_bbox.get_vertices()
        
        vertex_match = np.allclose(vertices, new_vertices, atol=1e-6)
        max_diff = np.max(np.abs(vertices - new_vertices))
        print(f"  顶点匹配: {vertex_match}, 最大差异: {max_diff}")
        
        if not (x_match and y_match and z_match and vertex_match):
            all_passed = False
            print(f"  ✗ 测试失败!")
            
            # 详细对比顶点
            for i in range(8):
                if not np.allclose(vertices[i], new_vertices[i], atol=1e-6):
                    print(f"    顶点 {i}: 原始={vertices[i]}, 恢复={new_vertices[i]}")
    
    print(f"\n--- 总结 ---")
    print(f"所有测试通过: {all_passed}")
    return all_passed


def test_kitti_rotation_offset():
    """测试 KITTI 格式的旋转偏移转换"""
    print("\n" + "=" * 80)
    print("测试3: KITTI 格式旋转偏移转换")
    print("=" * 80)
    
    print("""
KITTI transformed 格式的旋转转换:
  导出: rotation = -(z_rotation_rad - pi/2)
  导入: rotation = -rotation_y + pi/2

这应该是一个逆操作，让我们验证...
""")
    
    test_angles = [0, 45, 90, 180, 270, 30, 60, 120]
    
    all_passed = True
    
    for z_deg in test_angles:
        # 模拟 KITTI transformed 格式的导出
        z_rad = abs2rel_rotation(z_deg)
        
        # 导出转换
        kitti_rotation_y = -(z_rad - math.pi / 2)
        
        # 导入转换（逆操作）
        recovered_z_rad = -kitti_rotation_y + math.pi / 2
        recovered_z_deg = rel2abs_rotation(recovered_z_rad)
        
        # 检查
        match = np.isclose(z_deg % 360, recovered_z_deg % 360, atol=0.1)
        
        print(f"原始 z_rotation: {z_deg}° ({z_rad:.4f} rad)")
        print(f"  -> KITTI rotation_y: {kitti_rotation_y:.4f} rad")
        print(f"  -> 恢复 z_rotation: {recovered_z_deg}° ({recovered_z_rad:.4f} rad)")
        print(f"  匹配: {match}")
        
        if not match:
            all_passed = False
    
    print(f"\n--- 总结 ---")
    print(f"KITTI 旋转偏移转换自洽: {all_passed}")
    return all_passed


def test_kitti_centroid_offset():
    """测试 KITTI 格式的中心点偏移（底面中心 vs 几何中心）"""
    print("\n" + "=" * 80)
    print("测试4: KITTI 格式中心点偏移转换")
    print("=" * 80)
    
    print("""
KITTI 格式:
  - location: 物体底面中心点 (bottom face center)
  - dimensions: height, width, length

labelCloud 内部:
  - center: 物体几何中心点 (centroid)
  - dimensions: length, width, height

转换关系:
  导出: kitti_z = centroid_z - height / 2
  导入: centroid_z = kitti_z + height / 2
""")
    
    test_cases = [
        ((0, 0, 0), (4, 5, 6)),
        ((10, 20, 30), (2, 3, 4)),
        ((-5, -5, 5), (1, 1, 1)),
    ]
    
    all_passed = True
    
    for center, dims in test_cases:
        length, width, height = dims
        
        # labelCloud 内部表示
        centroid = np.array(center)
        
        # 导出到 KITTI: 几何中心 -> 底面中心
        kitti_location = centroid.copy()
        kitti_location[2] = kitti_location[2] - height / 2  # 底面中心
        
        # KITTI dimensions 顺序: height, width, length
        kitti_dims = (height, width, length)
        
        # 从 KITTI 导入: 底面中心 -> 几何中心
        recovered_centroid = kitti_location.copy()
        recovered_centroid[2] = recovered_centroid[2] + kitti_dims[0] / 2  # 几何中心
        recovered_dims = (kitti_dims[2], kitti_dims[1], kitti_dims[0])  # length, width, height
        
        print(f"\n原始: center={center}, dims={dims} (l,w,h)")
        print(f"  -> KITTI: location={kitti_location}, dims={kitti_dims} (h,w,l)")
        print(f"  -> 恢复: center={recovered_centroid}, dims={recovered_dims} (l,w,h)")
        
        center_match = np.allclose(centroid, recovered_centroid)
        dims_match = np.allclose(dims, recovered_dims)
        
        print(f"  匹配: center={center_match}, dims={dims_match}")
        
        if not (center_match and dims_match):
            all_passed = False
    
    print(f"\n--- 总结 ---")
    print(f"KITTI 中心点偏移转换自洽: {all_passed}")
    return all_passed


def test_comprehensive_roundtrip_with_vertices():
    """全面测试 Vertices 格式的 round-trip"""
    print("\n" + "=" * 80)
    print("测试5: Vertices 格式全面 Round-Trip 测试")
    print("=" * 80)
    
    test_cases = [
        ("轴对齐无旋转", (0, 0, 0), (0, 0, 0)),
        ("带平移无旋转", (10, 20, 30), (0, 0, 0)),
        ("原点Z旋转", (0, 0, 0), (0, 0, 45)),
        ("带平移Z旋转", (5, 5, 5), (0, 0, 90)),
        ("原点复合旋转", (0, 0, 0), (30, 45, 60)),
        ("带平移复合旋转", (1, 2, 3), (90, 180, 270)),
        ("大角度", (0, 0, 0), (120, 240, 300)),
    ]
    
    all_passed = True
    
    for name, center, rotations in test_cases:
        print(f"\n--- {name} ---")
        
        # 创建原始 BBox
        original = SimpleBBox(*center, 4, 6, 8)
        original.set_rotations(*rotations)
        original_vertices = original.get_vertices()
        
        # 模拟 VerticesFormat 导出: 直接保存顶点
        exported = original_vertices.tolist()
        
        # 模拟 VerticesFormat 导入
        # 1. 计算中心点: (vertices[4] - vertices[2])/2 + vertices[2]
        imported_center = tuple(np.add(np.subtract(exported[4], exported[2]) / 2, exported[2]))
        
        # 2. 计算尺寸
        length = vector_length(np.subtract(exported[0], exported[3]))
        width = vector_length(np.subtract(exported[0], exported[1]))
        height = vector_length(np.subtract(exported[0], exported[4]))
        
        # 3. 计算旋转
        imported_rotations = vertices2rotations(exported, imported_center)
        
        # 创建导入后的 BBox
        imported = SimpleBBox(*imported_center, length, width, height)
        imported.set_rotations(*imported_rotations)
        imported_vertices = imported.get_vertices()
        
        # 比较
        center_match = np.allclose(center, imported_center)
        dims_match = np.allclose((4, 6, 8), (length, width, height))
        
        def angles_equal(a, b):
            diff = abs((a % 360) - (b % 360))
            return diff < 0.1 or abs(diff - 360) < 0.1
        
        rot_match = all(angles_equal(r, ir) for r, ir in zip(rotations, imported_rotations))
        vertex_match = np.allclose(original_vertices, imported_vertices, atol=1e-6)
        max_diff = np.max(np.abs(original_vertices - imported_vertices))
        
        print(f"  原始: center={center}, dims=(4,6,8), rot={rotations}")
        print(f"  导入: center={imported_center}, dims=({length:.1f},{width:.1f},{height:.1f}), rot={imported_rotations}")
        print(f"  匹配: center={center_match}, dims={dims_match}, rot={rot_match}, vertices={vertex_match}")
        print(f"  最大顶点差异: {max_diff}")
        
        if not (center_match and dims_match and vertex_match):
            all_passed = False
            print(f"  ✗ 测试失败!")
            
            for i in range(8):
                if not np.allclose(original_vertices[i], imported_vertices[i], atol=1e-6):
                    print(f"    顶点 {i}: 原始={original_vertices[i]}, 导入={imported_vertices[i]}")
    
    print(f"\n--- 总结 ---")
    print(f"Vertices 格式 Round-Trip 全部通过: {all_passed}")
    return all_passed


def test_special_edge_cases():
    """测试特殊边界情况"""
    print("\n" + "=" * 80)
    print("测试6: 特殊边界情况")
    print("=" * 80)
    
    all_passed = True
    
    # 测试1: 90度旋转导致顶点位置交换
    print("\n--- 测试 90° 旋转 ---")
    
    bbox = SimpleBBox(0, 0, 0, 2, 4, 6)  # 非立方体，更容易看出问题
    bbox.set_rotations(0, 0, 90)
    
    original_vertices = bbox.get_vertices()
    
    # 导出再导入
    exported = original_vertices.tolist()
    imported_center = tuple(np.add(np.subtract(exported[4], exported[2]) / 2, exported[2]))
    length = vector_length(np.subtract(exported[0], exported[3]))
    width = vector_length(np.subtract(exported[0], exported[1]))
    height = vector_length(np.subtract(exported[0], exported[4]))
    imported_rotations = vertices2rotations(exported, imported_center)
    
    print(f"原始: dims=(2,4,6), rot=(0,0,90)")
    print(f"导入: dims=({length:.1f},{width:.1f},{height:.1f}), rot={imported_rotations}")
    
    # 注意：旋转90度后，length 和 width 可能看起来交换了
    # 但实际上 vertices2rotations 应该能正确恢复旋转角度，
    # 从而 get_vertices() 能产生相同的顶点
    
    new_bbox = SimpleBBox(*imported_center, length, width, height)
    new_bbox.set_rotations(*imported_rotations)
    new_vertices = new_bbox.get_vertices()
    
    vertex_match = np.allclose(original_vertices, new_vertices, atol=1e-6)
    print(f"顶点匹配: {vertex_match}")
    
    if not vertex_match:
        all_passed = False
        print(f"  ✗ 顶点不匹配!")
        max_diff = np.max(np.abs(original_vertices - new_vertices))
        print(f"  最大差异: {max_diff}")
    
    # 测试2: 180度旋转
    print("\n--- 测试 180° 旋转 ---")
    
    bbox2 = SimpleBBox(0, 0, 0, 2, 4, 6)
    bbox2.set_rotations(0, 0, 180)
    original_vertices2 = bbox2.get_vertices()
    
    exported2 = original_vertices2.tolist()
    imported_center2 = tuple(np.add(np.subtract(exported2[4], exported2[2]) / 2, exported2[2]))
    length2 = vector_length(np.subtract(exported2[0], exported2[3]))
    width2 = vector_length(np.subtract(exported2[0], exported2[1]))
    height2 = vector_length(np.subtract(exported2[0], exported2[4]))
    imported_rotations2 = vertices2rotations(exported2, imported_center2)
    
    print(f"原始: rot=(0,0,180)")
    print(f"导入: rot={imported_rotations2}")
    
    new_bbox2 = SimpleBBox(*imported_center2, length2, width2, height2)
    new_bbox2.set_rotations(*imported_rotations2)
    new_vertices2 = new_bbox2.get_vertices()
    
    vertex_match2 = np.allclose(original_vertices2, new_vertices2, atol=1e-6)
    print(f"顶点匹配: {vertex_match2}")
    
    if not vertex_match2:
        all_passed = False
    
    print(f"\n--- 总结 ---")
    print(f"边界情况测试全部通过: {all_passed}")
    return all_passed


if __name__ == "__main__":
    print("=" * 80)
    print("坐标转换问题详细分析")
    print("=" * 80)
    
    results = []
    
    results.append(("旋转矩阵正确性", test_rotation_matrix_correctness()))
    results.append(("旋转恢复能力", test_vertices2rotations_recovery()))
    results.append(("KITTI旋转偏移", test_kitti_rotation_offset()))
    results.append(("KITTI中心点偏移", test_kitti_centroid_offset()))
    results.append(("Vertices Round-Trip", test_comprehensive_roundtrip_with_vertices()))
    results.append(("边界情况", test_special_edge_cases()))
    
    print("\n" + "=" * 80)
    print("最终测试结果汇总")
    print("=" * 80)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"[{status}] {name}")
        if not passed:
            all_passed = False
    
    print("-" * 80)
    if all_passed:
        print("所有测试通过! 代码逻辑看起来是自洽的。")
        print("""
可能的问题来源:
1. 用户描述的问题可能涉及 Open3D 显示坐标与内部坐标的差异
2. 或者是在交互操作（如鼠标旋转）时的坐标转换问题
3. 或者是配置文件中的坐标系设置问题

建议检查:
1. labelCloud 与 Open3D 之间的坐标转换
2. 鼠标交互时的旋转逻辑
3. 配置文件中的坐标系设置
""")
    else:
        print("部分测试失败! 需要修复代码逻辑。")
