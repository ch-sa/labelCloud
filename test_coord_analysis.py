#!/usr/bin/env python3
"""不依赖OpenGL的坐标转换分析"""

import math
import numpy as np


# ============================================================================ #
#                          从源码复制的关键函数                                #
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
    """注意：函数内部实际调用顺序是 x -> y -> z（从内到外）"""
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
    """从顶点计算旋转角度（这是VerticesFormat导入时使用的函数）"""
    x_rotation, y_rotation, z_rotation = (0.0, 0.0, 0.0)
    vertices_trans = np.subtract(vertices, centroid)
    
    # 计算 z_rotation - 使用顶点3-顶点0的向量
    x_vec = vertices_trans[3] - vertices_trans[0]  # length向量
    z_rotation = radians_to_degrees(np.arctan2(x_vec[1], x_vec[0])) % 360
    
    # 计算 y_rotation
    if vertices[3][2] != vertices[0][2]:
        x_vec_rot = rotate_around_z(x_vec, -z_rotation, degrees=True)
        y_rotation = -radians_to_degrees(np.arctan2(x_vec_rot[2], x_vec_rot[0])) % 360
    
    # 计算 x_rotation
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
    """简化的BBox类，不依赖OpenGL"""
    
    def __init__(self, cx: float, cy: float, cz: float, 
                 length: float, width: float, height: float):
        self.center = (cx, cy, cz)
        self.length = length
        self.width = width
        self.height = height
        self.x_rotation = 0.0
        self.y_rotation = 0.0
        self.z_rotation = 0.0
        
        self.verticies = np.zeros((8, 3))
        self.set_axis_aligned_verticies()
    
    def set_axis_aligned_verticies(self):
        """轴对齐顶点定义（从源码复制）"""
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
    
    def get_rotations(self):
        return self.x_rotation, self.y_rotation, self.z_rotation
    
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
        """获取旋转后的顶点（从源码复制的逻辑）"""
        self.set_axis_aligned_verticies()
        rotated_vertices = rotate_bbox_around_center(
            self.get_axis_aligned_vertices(),
            self.center,
            self.get_rotations(),
        )
        return np.array(rotated_vertices)


# ============================================================================ #
#                                 测试函数                                     #
# ============================================================================ #

def analyze_vertex_order():
    """分析顶点顺序和尺寸计算"""
    print("=" * 70)
    print("分析1: 顶点顺序与尺寸向量")
    print("=" * 70)
    
    # 创建一个简单的轴对齐BBox
    bbox = SimpleBBox(0, 0, 0, 4, 6, 8)  # length=4, width=6, height=8
    vertices = bbox.get_vertices()
    
    print(f"轴对齐BBox的8个顶点 (length=4, width=6, height=8):")
    for i, v in enumerate(vertices):
        print(f"  顶点 {i}: {v}")
    
    print(f"\nVerticesFormat导入时使用的向量:")
    
    # 用于计算length的向量: vertices[3] - vertices[0]
    length_vec = vertices[3] - vertices[0]
    length_calc = vector_length(length_vec)
    print(f"  length向量 (顶点3-顶点0): {length_vec}")
    print(f"  计算出的length: {length_calc}, 预期: {bbox.length}")
    
    # 用于计算width的向量: vertices[1] - vertices[0]
    width_vec = vertices[1] - vertices[0]
    width_calc = vector_length(width_vec)
    print(f"  width向量 (顶点1-顶点0): {width_vec}")
    print(f"  计算出的width: {width_calc}, 预期: {bbox.width}")
    
    # 用于计算height的向量: vertices[4] - vertices[0]
    height_vec = vertices[4] - vertices[0]
    height_calc = vector_length(height_vec)
    print(f"  height向量 (顶点4-顶点0): {height_vec}")
    print(f"  计算出的height: {height_calc}, 预期: {bbox.height}")
    
    print(f"\nBBox定义的各边对应向量:")
    print(f"  顶点0: [-l/2, -w/2, -h/2] = {vertices[0]}")
    print(f"  顶点1: [-l/2, +w/2, -h/2] = {vertices[1]} (沿width方向)")
    print(f"  顶点3: [+l/2, -w/2, -h/2] = {vertices[3]} (沿length方向)")
    print(f"  顶点4: [-l/2, -w/2, +h/2] = {vertices[4]} (沿height方向)")
    
    # 验证
    assert np.isclose(length_calc, bbox.length), "Length计算错误！"
    assert np.isclose(width_calc, bbox.width), "Width计算错误！"
    assert np.isclose(height_calc, bbox.height), "Height计算错误！"
    
    print("\n✓ 轴对齐状态下，顶点顺序和尺寸计算正确")
    


def analyze_rotation_direction():
    """分析旋转方向和顺序"""
    print("\n" + "=" * 70)
    print("分析2: 旋转方向和顺序")
    print("=" * 70)
    
    # 测试点: (1, 0, 0) - 在x轴正方向
    test_point = np.array([1.0, 0.0, 0.0])
    print(f"测试点: {test_point}")
    print(f"预期: 绕z轴逆时针旋转90°后应指向 (0, 1, 0)")
    
    # 测试绕z轴旋转
    rotated_90 = rotate_around_z(test_point, 90, degrees=True)
    print(f"实际旋转90°后: {rotated_90}")
    
    # 检查这是顺时针还是逆时针
    # 标准右手坐标系：逆时针旋转(从z轴正方向看)
    # (1,0,0) -> (0,1,0) 是逆时针90°
    # (1,0,0) -> (0,-1,0) 是顺时针90°
    
    expected_ccw_90 = np.array([0.0, 1.0, 0.0])  # 逆时针
    expected_cw_90 = np.array([0.0, -1.0, 0.0])   # 顺时针
    
    if np.allclose(rotated_90, expected_ccw_90):
        print("  -> 这是逆时针旋转（右手坐标系标准）")
    elif np.allclose(rotated_90, expected_cw_90):
        print("  -> 这是顺时针旋转（与右手坐标系相反）")
    else:
        print(f"  -> 意外结果: {rotated_90}")
    
    # 现在测试旋转顺序
    print(f"\n测试旋转顺序 (rotate_around_zyx):")
    print(f"函数签名: rotate_around_zyx(point, x_angle, y_angle, z_angle)")
    print(f"函数内部调用: z(y(x(point))) - 即先x,再y,再z")
    
    # 用简单旋转测试
    point = np.array([1.0, 0.0, 0.0])
    
    # 只绕z轴旋转90°
    result1 = rotate_around_zyx(point, 0, 0, 90, degrees=True)
    direct_z = rotate_around_z(point, 90, degrees=True)
    print(f"\n只绕z轴旋转90°:")
    print(f"  rotate_around_zyx(0,0,90): {result1}")
    print(f"  直接rotate_around_z(90): {direct_z}")
    
    # 测试旋转顺序的影响
    print(f"\n测试旋转顺序的影响:")
    point2 = np.array([1.0, 0.0, 0.0])
    
    # 顺序1: 先x(90°), 再z(90°)
    step1 = rotate_around_x(point2, 90, degrees=True)
    step2 = rotate_around_z(step1, 90, degrees=True)
    print(f"先x(90°), 再z(90°): {step2}")
    
    # 使用rotate_around_zyx
    result2 = rotate_around_zyx(point2, 90, 0, 90, degrees=True)
    print(f"rotate_around_zyx(90, 0, 90): {result2}")
    
    # 顺序2: 先z(90°), 再x(90°)
    step1_v2 = rotate_around_z(point2, 90, degrees=True)
    step2_v2 = rotate_around_x(step1_v2, 90, degrees=True)
    print(f"先z(90°), 再x(90°): {step2_v2}")
    
    print(f"\n结论: rotate_around_zyx的实际旋转顺序是 x -> y -> z")
    


def analyze_vertices_roundtrip():
    """分析Vertices格式的round-trip问题"""
    print("\n" + "=" * 70)
    print("分析3: Vertices格式Round-Trip (关键测试)")
    print("=" * 70)
    
    # 测试案例1: 只有z旋转
    print("\n案例1: 只有Z轴旋转 (45°)")
    print("-" * 50)
    
    original_center = (0.0, 0.0, 0.0)
    original_dims = (4.0, 6.0, 8.0)  # length, width, height
    original_rotations = (0.0, 0.0, 45.0)  # x, y, z
    
    bbox = SimpleBBox(*original_center, *original_dims)
    bbox.set_rotations(*original_rotations)
    
    original_vertices = bbox.get_vertices()
    print(f"原始BBox:")
    print(f"  中心点: {original_center}")
    print(f"  尺寸: {original_dims} (length, width, height)")
    print(f"  旋转: {original_rotations}")
    
    # 模拟VerticesFormat导出: 直接保存顶点
    exported_vertices = original_vertices.tolist()
    
    # 模拟VerticesFormat导入
    # 1. 计算中心点: (vertices[4] - vertices[2])/2 + vertices[2]
    imported_center = tuple(np.add(np.subtract(exported_vertices[4], exported_vertices[2]) / 2, 
                                    exported_vertices[2]))
    print(f"\n导入计算:")
    print(f"  计算出的中心点: {imported_center}")
    
    # 2. 计算尺寸
    length = vector_length(np.subtract(exported_vertices[0], exported_vertices[3]))
    width = vector_length(np.subtract(exported_vertices[0], exported_vertices[1]))
    height = vector_length(np.subtract(exported_vertices[0], exported_vertices[4]))
    print(f"  计算出的尺寸: length={length}, width={width}, height={height}")
    
    # 3. 计算旋转
    imported_rotations = vertices2rotations(exported_vertices, imported_center)
    print(f"  计算出的旋转: {imported_rotations}")
    
    # 4. 创建新BBox并获取顶点
    new_bbox = SimpleBBox(*imported_center, length, width, height)
    new_bbox.set_rotations(*imported_rotations)
    new_vertices = new_bbox.get_vertices()
    
    # 比较顶点
    print(f"\n顶点比较:")
    max_diff = np.max(np.abs(original_vertices - new_vertices))
    print(f"  最大顶点差异: {max_diff}")
    
    if max_diff > 1e-6:
        print(f"\n✗ 发现问题！详细比较:")
        for i in range(8):
            diff = np.abs(original_vertices[i] - new_vertices[i])
            print(f"  顶点 {i}: 原始={original_vertices[i]}, 导入={new_vertices[i]}, 差异={diff}")
    else:
        print("\n✓ 顶点匹配")
    
    # 测试案例2: 更复杂的旋转
    print("\n" + "=" * 70)
    print("案例2: 复杂旋转 (x=30°, y=45°, z=60°)")
    print("=" * 70)
    
    original_rotations2 = (30.0, 45.0, 60.0)
    
    bbox2 = SimpleBBox(*original_center, *original_dims)
    bbox2.set_rotations(*original_rotations2)
    
    original_vertices2 = bbox2.get_vertices()
    print(f"原始旋转: {original_rotations2}")
    
    # 导入
    imported_center2 = tuple(np.add(np.subtract(original_vertices2[4], original_vertices2[2]) / 2, 
                                     original_vertices2[2]))
    length2 = vector_length(np.subtract(original_vertices2[0], original_vertices2[3]))
    width2 = vector_length(np.subtract(original_vertices2[0], original_vertices2[1]))
    height2 = vector_length(np.subtract(original_vertices2[0], original_vertices2[4]))
    imported_rotations2 = vertices2rotations(original_vertices2.tolist(), imported_center2)
    
    print(f"导入计算:")
    print(f"  中心点: {imported_center2}")
    print(f"  尺寸: length={length2}, width={width2}, height={height2}")
    print(f"  旋转: {imported_rotations2}")
    
    # 比较
    print(f"\n验证:")
    print(f"  中心点匹配: {np.allclose(original_center, imported_center2)}")
    print(f"  尺寸匹配: {np.allclose(original_dims, (length2, width2, height2))}")
    print(f"  旋转匹配: {np.allclose(original_rotations2, imported_rotations2)}")
    
    # 创建新BBox比较顶点
    new_bbox2 = SimpleBBox(*imported_center2, length2, width2, height2)
    new_bbox2.set_rotations(*imported_rotations2)
    new_vertices2 = new_bbox2.get_vertices()
    
    max_diff2 = np.max(np.abs(original_vertices2 - new_vertices2))
    print(f"\n  最大顶点差异: {max_diff2}")
    
    if max_diff2 > 1e-6:
        print(f"\n✗ 顶点不匹配！")
        for i in range(8):
            print(f"  顶点 {i}: 原始={original_vertices2[i]}, 导入={new_vertices2[i]}")
    


def analyze_z_rotation_specific():
    """专门分析Z轴旋转的问题"""
    print("\n" + "=" * 70)
    print("分析4: 专门分析Z轴旋转计算")
    print("=" * 70)
    
    # 关键点: vertices2rotations中使用 vertices[3] - vertices[0] 来计算z旋转
    # 让我们看看旋转后这个向量如何变化
    
    # 首先，轴对齐状态
    bbox = SimpleBBox(0, 0, 0, 4, 6, 8)
    vertices_0 = bbox.get_vertices()
    
    print(f"轴对齐状态 (旋转=0°):")
    print(f"  顶点0: {vertices_0[0]}")
    print(f"  顶点3: {vertices_0[3]}")
    x_vec_0 = vertices_0[3] - vertices_0[0]
    print(f"  向量(3-0): {x_vec_0}")
    z_rot_0 = radians_to_degrees(np.arctan2(x_vec_0[1], x_vec_0[0])) % 360
    print(f"  计算的z旋转: {z_rot_0}°")
    print(f"  atan2(y={x_vec_0[1]}, x={x_vec_0[0]}) = {np.arctan2(x_vec_0[1], x_vec_0[0])}弧度")
    
    # 旋转45°
    bbox.set_rotations(0, 0, 45)
    vertices_45 = bbox.get_vertices()
    
    print(f"\n旋转45°后:")
    print(f"  顶点0: {vertices_45[0]}")
    print(f"  顶点3: {vertices_45[3]}")
    x_vec_45 = vertices_45[3] - vertices_45[0]
    print(f"  向量(3-0): {x_vec_45}")
    print(f"  向量长度: {vector_length(x_vec_45)} (应该等于length=4)")
    
    z_rot_45 = radians_to_degrees(np.arctan2(x_vec_45[1], x_vec_45[0])) % 360
    print(f"  计算的z旋转: {z_rot_45}°")
    print(f"  atan2(y={x_vec_45[1]}, x={x_vec_45[0]}) = {np.arctan2(x_vec_45[1], x_vec_45[0]):.4f}弧度")
    
    # 验证: 45°的cos和sin
    print(f"\n验证 45°:")
    print(f"  cos(45°) = {np.cos(np.pi/4):.6f}")
    print(f"  sin(45°) = {np.sin(np.pi/4):.6f}")
    
    # 预期的向量旋转: 原始向量 (4, 0, 0) 旋转45°
    original_vec = np.array([4.0, 0.0, 0.0])
    expected_rotated = rotate_around_z(original_vec, 45, degrees=True)
    print(f"\n预期向量旋转:")
    print(f"  原始向量: {original_vec}")
    print(f"  旋转45°后期望: {expected_rotated}")
    print(f"  实际向量: {x_vec_45}")
    
    # 检查是否匹配
    if np.allclose(expected_rotated, x_vec_45):
        print("\n✓ 向量旋转计算正确")
    else:
        print(f"\n✗ 向量不匹配！差异: {expected_rotated - x_vec_45}")
    
    # 测试 vertices2rotations
    print(f"\n测试 vertices2rotations 函数:")
    computed_rotations = vertices2rotations(vertices_45.tolist(), (0, 0, 0))
    print(f"  输入旋转: (0, 0, 45)")
    print(f"  计算旋转: {computed_rotations}")
    
    if np.allclose([45.0], [computed_rotations[2]]):
        print("✓ Z旋转计算正确")
    else:
        print(f"✗ Z旋转计算错误！期望45°，得到{computed_rotations[2]}°")
    


if __name__ == "__main__":
    print("=" * 70)
    print("坐标转换问题深度分析")
    print("=" * 70)
    
    try:
        analyze_vertex_order()
        analyze_rotation_direction()
        analyze_vertices_roundtrip()
        analyze_z_rotation_specific()
        
        print("\n" + "=" * 70)
        print("分析完成")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n断言失败: {e}")
        import traceback
        traceback.print_exc()
