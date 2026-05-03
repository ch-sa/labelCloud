#!/usr/bin/env python3
"""详细分析 vertices2rotations 函数的逻辑"""

import numpy as np
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


def vertices2rotations_original(vertices, centroid):
    """从顶点计算旋转角度（原始实现）"""
    x_rotation, y_rotation, z_rotation = (0.0, 0.0, 0.0)

    vertices_trans = np.subtract(vertices, centroid)

    # Calculate z_rotation
    x_vec = vertices_trans[3] - vertices_trans[0]
    z_rotation = radians_to_degrees(np.arctan2(x_vec[1], x_vec[0])) % 360

    # Calculate y_rotation
    if vertices[3][2] != vertices[0][2]:
        x_vec_rot = rotate_around_z(x_vec, -z_rotation, degrees=True)
        y_rotation = -radians_to_degrees(np.arctan2(x_vec_rot[2], x_vec_rot[0])) % 360

    # Calculate x_rotation
    if vertices[0][2] != vertices[1][2]:
        y_vec = np.subtract(vertices_trans[1], vertices_trans[0])
        y_vec_rot = rotate_around_z(y_vec, -z_rotation, degrees=True)
        y_vec_rot = rotate_around_y(y_vec_rot, -y_rotation, degrees=True)
        x_rotation = radians_to_degrees(np.arctan2(y_vec_rot[2], y_vec_rot[1])) % 360

    return x_rotation, y_rotation, z_rotation


def vertices2rotations_fixed(vertices, centroid, epsilon=1e-6):
    """从顶点计算旋转角度（修复浮点比较）"""
    x_rotation, y_rotation, z_rotation = (0.0, 0.0, 0.0)

    vertices_trans = np.subtract(vertices, centroid)

    # Calculate z_rotation
    x_vec = vertices_trans[3] - vertices_trans[0]
    z_rotation = radians_to_degrees(np.arctan2(x_vec[1], x_vec[0])) % 360

    # Calculate y_rotation - 使用浮点比较容差
    if abs(vertices[3][2] - vertices[0][2]) > epsilon:
        x_vec_rot = rotate_around_z(x_vec, -z_rotation, degrees=True)
        y_rotation = -radians_to_degrees(np.arctan2(x_vec_rot[2], x_vec_rot[0])) % 360

    # Calculate x_rotation - 使用浮点比较容差
    if abs(vertices[0][2] - vertices[1][2]) > epsilon:
        y_vec = np.subtract(vertices_trans[1], vertices_trans[0])
        y_vec_rot = rotate_around_z(y_vec, -z_rotation, degrees=True)
        y_vec_rot = rotate_around_y(y_vec_rot, -y_rotation, degrees=True)
        x_rotation = radians_to_degrees(np.arctan2(y_vec_rot[2], y_vec_rot[1])) % 360

    return x_rotation, y_rotation, z_rotation


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
#                              测试函数                                        #
# ============================================================================ #

def test_float_comparison_issue():
    """测试浮点比较问题"""
    print("=" * 80)
    print("测试浮点比较问题")
    print("=" * 80)
    
    test_cases = [
        ("无旋转", (0, 0, 0)),
        ("只有Z旋转", (0, 0, 45)),
        ("只有Y旋转", (0, 45, 0)),
        ("只有X旋转", (30, 0, 0)),
        ("复合旋转", (30, 45, 60)),
        ("90°倍数旋转", (90, 180, 270)),
    ]
    
    issues_found = []
    
    for name, rotations in test_cases:
        print(f"\n--- {name}: {rotations} ---")
        
        bbox = SimpleBBox(0, 0, 0, 4, 6, 8)
        bbox.set_rotations(*rotations)
        
        vertices = bbox.get_vertices()
        centroid = tuple(np.add(np.subtract(vertices[4], vertices[2]) / 2, vertices[2]))
        
        # 检查顶点的 z 坐标
        print(f"  顶点 0 z: {vertices[0][2]}, 顶点 1 z: {vertices[1][2]}, 顶点 3 z: {vertices[3][2]}")
        print(f"  顶点 0 z == 顶点 3 z? {vertices[0][2] == vertices[3][2]}")
        print(f"  顶点 0 z == 顶点 1 z? {vertices[0][2] == vertices[1][2]}")
        print(f"  abs(顶点 0 z - 顶点 3 z) = {abs(vertices[0][2] - vertices[3][2])}")
        print(f"  abs(顶点 0 z - 顶点 1 z) = {abs(vertices[0][2] - vertices[1][2])}")
        
        # 测试原始实现
        rot_original = vertices2rotations_original(vertices.tolist(), centroid)
        rot_fixed = vertices2rotations_fixed(vertices.tolist(), centroid)
        
        print(f"  原始实现恢复: {rot_original}")
        print(f"  修复实现恢复: {rot_fixed}")
        print(f"  原始旋转: {rotations}")
        
        # 验证旋转是否等价
        test_point = np.array([1, 0, 0])
        r_original = rotate_around_zyx(test_point, *rot_original, degrees=True)
        r_fixed = rotate_around_zyx(test_point, *rot_fixed, degrees=True)
        r_expected = rotate_around_zyx(test_point, *rotations, degrees=True)
        
        print(f"  原始实现旋转 [1,0,0] -> {r_original}")
        print(f"  修复实现旋转 [1,0,0] -> {r_fixed}")
        print(f"  预期旋转 [1,0,0] -> {r_expected}")
        
        if not np.allclose(r_original, r_expected, atol=1e-6):
            issues_found.append(f"{name}: 原始实现有问题")
            print(f"  ✗ 原始实现与预期不等价!")
        else:
            print(f"  ✓ 原始实现与预期等价")
        
        if not np.allclose(r_fixed, r_expected, atol=1e-6):
            print(f"  ✗ 修复实现与预期不等价!")
        else:
            print(f"  ✓ 修复实现与预期等价")
    
    print(f"\n{'=' * 80}")
    if issues_found:
        print(f"发现问题: {issues_found}")
    else:
        print(f"浮点比较问题测试通过!")
    print(f"{'=' * 80}")
    
    return len(issues_found) == 0


def test_euler_angle_ambiguity():
    """测试欧拉角歧义性"""
    print("\n" + "=" * 80)
    print("测试欧拉角歧义性")
    print("=" * 80)
    
    test_cases = [
        ("测试1", (0, 0, 0), 4, 6, 8),
        ("测试2", (30, 45, 60), 4, 6, 8),
        ("测试3", (90, 180, 270), 4, 6, 8),
        ("测试4", (45, 90, 45), 4, 6, 8),
        ("测试5", (0, 45, 0), 4, 6, 8),
        ("测试6", (30, 0, 0), 4, 6, 8),
    ]
    
    all_passed = True
    
    for name, rotations, length, width, height in test_cases:
        print(f"\n--- {name} ---")
        
        # 创建原始 BBox
        original = SimpleBBox(10, 20, 30, length, width, height)
        original.set_rotations(*rotations)
        
        original_vertices = original.get_vertices()
        original_center = original.get_center()
        
        # 计算中心点
        centroid = tuple(np.add(np.subtract(original_vertices[4], original_vertices[2]) / 2, 
                                 original_vertices[2]))
        
        # 恢复旋转
        recovered_rot = vertices2rotations_original(original_vertices.tolist(), centroid)
        
        print(f"  原始旋转: {rotations}")
        print(f"  恢复旋转: {recovered_rot}")
        
        # 创建恢复的 BBox
        recovered = SimpleBBox(*centroid, length, width, height)
        recovered.set_rotations(*recovered_rot)
        
        recovered_vertices = recovered.get_vertices()
        
        # 比较顶点
        vertices_match = np.allclose(original_vertices, recovered_vertices, atol=1e-6)
        max_diff = np.max(np.abs(original_vertices - recovered_vertices))
        
        print(f"  顶点匹配: {vertices_match} (最大差异: {max_diff:.2e})")
        
        # 验证旋转矩阵是否相同
        def get_rotation_matrix(x, y, z, degrees=True):
            if degrees:
                x = degrees_to_radians(x)
                y = degrees_to_radians(y)
                z = degrees_to_radians(z)
            
            Rx = np.array([
                [1, 0, 0],
                [0, np.cos(x), -np.sin(x)],
                [0, np.sin(x), np.cos(x)],
            ])
            
            Ry = np.array([
                [np.cos(y), 0, np.sin(y)],
                [0, 1, 0],
                [-np.sin(y), 0, np.cos(y)],
            ])
            
            Rz = np.array([
                [np.cos(z), -np.sin(z), 0],
                [np.sin(z), np.cos(z), 0],
                [0, 0, 1],
            ])
            
            return Rz @ Ry @ Rx
        
        R_original = get_rotation_matrix(*rotations)
        R_recovered = get_rotation_matrix(*recovered_rot)
        
        matrices_match = np.allclose(R_original, R_recovered, atol=1e-6)
        
        print(f"  旋转矩阵匹配: {matrices_match}")
        
        if not (vertices_match and matrices_match):
            all_passed = False
            print(f"  ✗ 测试失败!")
            print(f"    原始矩阵:\n{R_original}")
            print(f"    恢复矩阵:\n{R_recovered}")
        else:
            print(f"  ✓ 测试通过")
    
    print(f"\n{'=' * 80}")
    print(f"欧拉角歧义性测试全部通过: {all_passed}")
    print(f"{'=' * 80}")
    
    return all_passed


def test_precision_effect():
    """测试导出精度对 round-trip 的影响"""
    print("\n" + "=" * 80)
    print("测试导出精度对 round-trip 的影响")
    print("=" * 80)
    
    precisions = [2, 4, 6, 8]
    
    test_rotations = [
        (0, 0, 0),
        (30, 45, 60),
        (90, 180, 270),
    ]
    
    for rotations in test_rotations:
        print(f"\n--- 旋转: {rotations} ---")
        
        bbox = SimpleBBox(10.123456, 20.654321, 5.987654, 2.12345, 1.54321, 1.87654)
        bbox.set_rotations(*rotations)
        
        original_vertices = bbox.get_vertices()
        
        for precision in precisions:
            # 模拟导出（四舍五入）
            exported_vertices = np.round(original_vertices, precision)
            
            # 计算中心点
            centroid = tuple(np.add(np.subtract(exported_vertices[4], exported_vertices[2]) / 2, 
                                     exported_vertices[2]))
            
            # 恢复旋转
            recovered_rot = vertices2rotations_original(exported_vertices.tolist(), centroid)
            
            # 创建恢复的 BBox
            length = vector_length(np.subtract(exported_vertices[3], exported_vertices[0]))
            width = vector_length(np.subtract(exported_vertices[1], exported_vertices[0]))
            height = vector_length(np.subtract(exported_vertices[4], exported_vertices[0]))
            
            recovered = SimpleBBox(*centroid, length, width, height)
            recovered.set_rotations(*recovered_rot)
            
            recovered_vertices = recovered.get_vertices()
            
            max_diff = np.max(np.abs(original_vertices - recovered_vertices))
            
            print(f"  精度 {precision}: 最大顶点差异 = {max_diff:.2e}")


if __name__ == "__main__":
    test_float_comparison_issue()
    test_euler_angle_ambiguity()
    test_precision_effect()
