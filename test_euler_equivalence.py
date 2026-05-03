#!/usr/bin/env python3
"""验证欧拉角等价性 - 检查不同欧拉角是否产生相同的顶点和朝向"""

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
    
    def get_orientation_vector(self):
        """获取方向箭头向量（模拟 draw_orientation）"""
        arrow_length = self.length * 0.4
        bp2 = np.array([arrow_length, 0, 0])
        
        center = np.array(self.get_center())
        rotations = self.get_rotations()
        
        v = rotate_around_x(bp2, rotations[0], degrees=True)
        v = rotate_around_y(v, rotations[1], degrees=True)
        v = rotate_around_z(v, rotations[2], degrees=True)
        
        return center + v


# ============================================================================ #
#                              测试函数                                        #
# ============================================================================ #

def test_euler_equivalence():
    """测试欧拉角等价性 - 检查不同欧拉角是否产生相同的结果"""
    print("=" * 80)
    print("测试欧拉角等价性")
    print("=" * 80)
    
    test_cases = [
        ("简单旋转", (0, 0, 45)),
        ("复合旋转", (30, 45, 60)),
        ("问题旋转1", (90, 180, 270)),
        ("问题旋转2", (120, 240, 300)),
        ("万向锁情况", (0, 90, 0)),
        ("万向锁情况2", (45, 90, 45)),
    ]
    
    all_passed = True
    
    for name, original_rot in test_cases:
        print(f"\n--- {name}: {original_rot} ---")
        
        # 创建原始BBox
        original = SimpleBBox(0, 0, 0, 4, 6, 8)
        original.set_rotations(*original_rot)
        original_vertices = original.get_vertices()
        original_orientation = original.get_orientation_vector()
        
        # 导出顶点
        exported_vertices = original_vertices.tolist()
        
        # 计算中心点
        center = tuple(np.add(np.subtract(exported_vertices[4], exported_vertices[2]) / 2, 
                               exported_vertices[2]))
        
        # 恢复旋转
        recovered_rot = vertices2rotations(exported_vertices, center)
        
        print(f"  原始旋转: {original_rot}")
        print(f"  恢复旋转: {recovered_rot}")
        
        # 创建恢复后的BBox
        recovered = SimpleBBox(*center, 4, 6, 8)
        recovered.set_rotations(*recovered_rot)
        recovered_vertices = recovered.get_vertices()
        recovered_orientation = recovered.get_orientation_vector()
        
        # 比较
        vertices_match = np.allclose(original_vertices, recovered_vertices, atol=1e-6)
        orientation_match = np.allclose(original_orientation, recovered_orientation, atol=1e-6)
        
        max_vertex_diff = np.max(np.abs(original_vertices - recovered_vertices))
        max_orient_diff = np.max(np.abs(original_orientation - recovered_orientation))
        
        print(f"  顶点匹配: {vertices_match} (最大差异: {max_vertex_diff})")
        print(f"  方向匹配: {orientation_match} (最大差异: {max_orient_diff})")
        
        if not (vertices_match and orientation_match):
            all_passed = False
            print(f"  ✗ 测试失败!")
            print(f"    原始方向: {original_orientation}")
            print(f"    恢复方向: {recovered_orientation}")
        else:
            print(f"  ✓ 测试通过")
    
    print(f"\n" + "=" * 80)
    print(f"欧拉角等价性测试全部通过: {all_passed}")
    print("=" * 80)
    return all_passed


def analyze_problematic_rotation():
    """分析问题旋转 (90, 180, 270)"""
    print("\n" + "=" * 80)
    print("详细分析问题旋转 (90, 180, 270)")
    print("=" * 80)
    
    original_rot = (90, 180, 270)
    
    # 创建原始BBox
    original = SimpleBBox(0, 0, 0, 4, 6, 8)
    original.set_rotations(*original_rot)
    original_vertices = original.get_vertices()
    original_orientation = original.get_orientation_vector()
    
    print(f"原始旋转: {original_rot}")
    print(f"原始顶点（前4个）:")
    for i in range(4):
        print(f"  顶点 {i}: {original_vertices[i]}")
    
    # 导出顶点
    exported_vertices = original_vertices.tolist()
    
    # 计算中心点
    center = tuple(np.add(np.subtract(exported_vertices[4], exported_vertices[2]) / 2, 
                           exported_vertices[2]))
    
    # 恢复旋转
    recovered_rot = vertices2rotations(exported_vertices, center)
    
    print(f"\n恢复旋转: {recovered_rot}")
    
    # 创建恢复后的BBox
    recovered = SimpleBBox(*center, 4, 6, 8)
    recovered.set_rotations(*recovered_rot)
    recovered_vertices = recovered.get_vertices()
    recovered_orientation = recovered.get_orientation_vector()
    
    print(f"\n顶点比较:")
    for i in range(8):
        match = np.allclose(original_vertices[i], recovered_vertices[i], atol=1e-6)
        diff = np.max(np.abs(original_vertices[i] - recovered_vertices[i]))
        status = "✓" if match else "✗"
        print(f"  顶点 {i}: {status} (差异: {diff})")
    
    print(f"\n方向比较:")
    print(f"  原始方向: {original_orientation}")
    print(f"  恢复方向: {recovered_orientation}")
    print(f"  差异: {np.abs(original_orientation - recovered_orientation)}")
    print(f"  匹配: {np.allclose(original_orientation, recovered_orientation, atol=1e-6)}")
    
    # 验证这两组旋转是否真的等价
    print(f"\n验证旋转矩阵是否等价:")
    
    # 测试几个关键点
    test_points = [
        np.array([1, 0, 0]),  # x轴方向
        np.array([0, 1, 0]),  # y轴方向
        np.array([0, 0, 1]),  # z轴方向
        np.array([1, 1, 1]),  # 任意点
    ]
    
    all_points_match = True
    for p in test_points:
        r1 = rotate_around_zyx(p, *original_rot, degrees=True)
        r2 = rotate_around_zyx(p, *recovered_rot, degrees=True)
        match = np.allclose(r1, r2, atol=1e-6)
        diff = np.max(np.abs(r1 - r2))
        status = "✓" if match else "✗"
        print(f"  点 {p}: {status} (原始旋转后: {r1}, 恢复旋转后: {r2}, 差异: {diff})")
        if not match:
            all_points_match = False
    
    print(f"\n结论:")
    if all_points_match:
        print("  这两组旋转是等价的！它们产生相同的旋转效果。")
        print("  这是欧拉角表示的正常行为（万向锁或多对一映射）。")
    else:
        print("  这两组旋转不等价！存在bug。")
    
    return all_points_match


def check_rotation_matrix():
    """检查旋转矩阵的构成"""
    print("\n" + "=" * 80)
    print("检查旋转矩阵的构成")
    print("=" * 80)
    
    def get_rotation_matrix(x_angle, y_angle, z_angle, degrees=True):
        """获取组合旋转矩阵"""
        if degrees:
            x_angle = degrees_to_radians(x_angle)
            y_angle = degrees_to_radians(y_angle)
            z_angle = degrees_to_radians(z_angle)
        
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(x_angle), -np.sin(x_angle)],
            [0, np.sin(x_angle), np.cos(x_angle)],
        ])
        
        Ry = np.array([
            [np.cos(y_angle), 0, np.sin(y_angle)],
            [0, 1, 0],
            [-np.sin(y_angle), 0, np.cos(y_angle)],
        ])
        
        Rz = np.array([
            [np.cos(z_angle), -np.sin(z_angle), 0],
            [np.sin(z_angle), np.cos(z_angle), 0],
            [0, 0, 1],
        ])
        
        # R = Rz * Ry * Rx (顺序: x -> y -> z)
        return Rz @ Ry @ Rx
    
    rot1 = (90, 180, 270)
    rot2 = (270, 0, 90)
    
    R1 = get_rotation_matrix(*rot1)
    R2 = get_rotation_matrix(*rot2)
    
    print(f"旋转1: {rot1}")
    print(f"旋转矩阵 R1:\n{R1}")
    
    print(f"\n旋转2: {rot2}")
    print(f"旋转矩阵 R2:\n{R2}")
    
    print(f"\n矩阵差异:\n{np.abs(R1 - R2)}")
    print(f"\n矩阵是否等价: {np.allclose(R1, R2, atol=1e-6)}")
    
    # 检查 R1 * R2^T 是否接近单位矩阵
    if np.allclose(R1, R2, atol=1e-6):
        print("\n这两个旋转矩阵相同，表示相同的旋转。")
        print("这是欧拉角表示的正常行为。")
    else:
        print("\n这两个旋转矩阵不同。")
        
        # 检查是否相差符号
        print(f"\n检查 R1 = -R2? {np.allclose(R1, -R2, atol=1e-6)}")
        
        # 检查行列式（应该为1）
        print(f"\nR1 行列式: {np.linalg.det(R1)}")
        print(f"R2 行列式: {np.linalg.det(R2)}")


if __name__ == "__main__":
    print("=" * 80)
    print("欧拉角等价性分析")
    print("=" * 80)
    
    test_euler_equivalence()
    analyze_problematic_rotation()
    check_rotation_matrix()
