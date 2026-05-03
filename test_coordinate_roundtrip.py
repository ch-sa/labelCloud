#!/usr/bin/env python3
"""验证坐标转换的round-trip一致性测试"""

import json
import math
import tempfile
from pathlib import Path

import numpy as np

# 添加 labelCloud 到路径
import sys
sys.path.insert(0, str(Path(__file__).parent))

from labelCloud.model.bbox import BBox
from labelCloud.io.labels.centroid import CentroidFormat
from labelCloud.io.labels.vertices import VerticesFormat
from labelCloud.io.labels.kitti import KittiFormat
from labelCloud.utils import math3d


def test_bbox_vertices_consistency():
    """验证BBox顶点计算的一致性"""
    print("=" * 60)
    print("测试1: BBox顶点计算一致性")
    print("=" * 60)
    
    # 创建一个测试bbox
    bbox = BBox(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)  # cx, cy, cz, length, width, height
    bbox.set_rotations(0, 0, 0)  # 无旋转
    
    # 获取顶点
    vertices = bbox.get_vertices()
    print(f"轴对齐BBox的8个顶点:")
    for i, v in enumerate(vertices):
        print(f"  顶点 {i}: {v}")
    
    # 预期的轴对齐顶点（基于BBox.verticies定义）
    expected_vertices = np.array([
        [-2.0, -2.5, -3.0],  # 0: -l/2, -w/2, -h/2
        [-2.0, 2.5, -3.0],   # 1: -l/2, +w/2, -h/2
        [2.0, 2.5, -3.0],    # 2: +l/2, +w/2, -h/2
        [2.0, -2.5, -3.0],   # 3: +l/2, -w/2, -h/2
        [-2.0, -2.5, 3.0],   # 4: -l/2, -w/2, +h/2
        [-2.0, 2.5, 3.0],    # 5: -l/2, +w/2, +h/2
        [2.0, 2.5, 3.0],     # 6: +l/2, +w/2, +h/2
        [2.0, -2.5, 3.0],    # 7: +l/2, -w/2, +h/2
    ])
    # 加上中心点 (1, 2, 3)
    expected_vertices += np.array([1.0, 2.0, 3.0])
    
    print(f"\n预期顶点:")
    for i, v in enumerate(expected_vertices):
        print(f"  顶点 {i}: {v}")
    
    # 检查是否匹配
    np.testing.assert_allclose(vertices, expected_vertices, atol=1e-6)
    print("\n✓ 轴对齐顶点计算正确")
    


def test_rotation_roundtrip():
    """测试旋转的round-trip"""
    print("\n" + "=" * 60)
    print("测试2: 旋转Round-Trip测试")
    print("=" * 60)
    
    # 创建带旋转的BBox
    original_center = (1.0, 2.0, 3.0)
    original_dims = (4.0, 5.0, 6.0)  # length, width, height
    original_rotations = (30.0, 45.0, 60.0)  # x, y, z rotations in degrees
    
    bbox = BBox(*original_center, *original_dims)
    bbox.set_rotations(*original_rotations)
    
    print(f"原始BBox:")
    print(f"  中心点: {bbox.get_center()}")
    print(f"  尺寸: {bbox.get_dimensions()}")
    print(f"  旋转: {bbox.get_rotations()}")
    
    # 获取顶点
    original_vertices = bbox.get_vertices()
    print(f"\n原始顶点（前4个）:")
    for i, v in enumerate(original_vertices[:4]):
        print(f"  顶点 {i}: {v}")
    
    # 现在尝试从顶点重新计算
    # 使用vertices2rotations
    computed_center = tuple(np.add(np.subtract(original_vertices[4], original_vertices[2]) / 2, original_vertices[2]))
    print(f"\n从顶点计算的中心点: {computed_center}")
    
    # 计算尺寸
    length = math3d.vector_length(np.subtract(original_vertices[0], original_vertices[3]))
    width = math3d.vector_length(np.subtract(original_vertices[0], original_vertices[1]))
    height = math3d.vector_length(np.subtract(original_vertices[0], original_vertices[4]))
    print(f"从顶点计算的尺寸: length={length}, width={width}, height={height}")
    
    # 计算旋转
    computed_rotations = math3d.vertices2rotations(original_vertices.tolist(), computed_center)
    print(f"从顶点计算的旋转: {computed_rotations}")
    
    # 验证
    print(f"\n验证:")
    print(f"  中心点匹配: {np.allclose(original_center, computed_center)}")
    print(f"  尺寸匹配: {np.allclose(original_dims, (length, width, height))}")
    print(f"  旋转匹配: {np.allclose(original_rotations, computed_rotations)}")
    
    # 创建新BBox并比较顶点
    new_bbox = BBox(*computed_center, length, width, height)
    new_bbox.set_rotations(*computed_rotations)
    new_vertices = new_bbox.get_vertices()
    
    print(f"\n顶点差异:")
    vertex_diff = np.max(np.abs(original_vertices - new_vertices))
    print(f"  最大顶点差异: {vertex_diff}")
    
    np.testing.assert_allclose(original_vertices, new_vertices, atol=1e-6, 
                                 err_msg="顶点在round-trip后不一致！")
    print("✓ 旋转Round-Trip通过")
    


def test_centroid_format_roundtrip():
    """测试Centroid格式的round-trip"""
    print("\n" + "=" * 60)
    print("测试3: Centroid格式Round-Trip")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # 创建测试BBox
        original_center = (10.0, 20.0, 30.0)
        original_dims = (4.0, 5.0, 6.0)
        original_rotations = (10.0, 20.0, 30.0)  # 绝对角度
        
        bbox = BBox(*original_center, *original_dims)
        bbox.set_rotations(*original_rotations)
        bbox.set_classname("test_object")
        
        print(f"原始BBox:")
        print(f"  中心点: {bbox.get_center()}")
        print(f"  尺寸: {bbox.get_dimensions()}")
        print(f"  旋转: {bbox.get_rotations()}")
        print(f"  类别: {bbox.get_classname()}")
        
        # 导出（绝对角度）
        pcd_path = Path("test.ply")
        fmt_abs = CentroidFormat(tmpdir_path, 8, relative_rotation=False)
        fmt_abs.export_labels([bbox], pcd_path)
        
        # 读取导出的文件
        with open(tmpdir_path / "test.json") as f:
            exported = json.load(f)
        print(f"\n导出的数据:")
        print(f"  centroid: {exported['objects'][0]['centroid']}")
        print(f"  dimensions: {exported['objects'][0]['dimensions']}")
        print(f"  rotations (abs): {exported['objects'][0]['rotations']}")
        
        # 重新导入
        imported_bboxes = fmt_abs.import_labels(pcd_path)
        imported = imported_bboxes[0]
        
        print(f"\n重新导入的BBox:")
        print(f"  中心点: {imported.get_center()}")
        print(f"  尺寸: {imported.get_dimensions()}")
        print(f"  旋转: {imported.get_rotations()}")
        print(f"  类别: {imported.get_classname()}")
        
        # 验证
        assert imported.get_center() == pytest.approx(original_center)
        assert imported.get_dimensions() == pytest.approx(original_dims)
        assert imported.get_rotations() == pytest.approx(original_rotations)
        assert imported.get_classname() == "test_object"
        
        print("\n✓ Centroid格式（绝对角度）Round-Trip通过")
        


def test_kitti_untransformed_roundtrip():
    """测试KITTI未转换格式的round-trip"""
    print("\n" + "=" * 60)
    print("测试4: KITTI Untransformed格式Round-Trip")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # 创建测试BBox（注意KITTI中的尺寸对应关系）
        original_center = (10.0, 20.0, 30.0)
        # KITTI格式: dimensions = [height, width, length]
        # BBox中: (length, width, height)
        original_dims = (4.0, 5.0, 6.0)  # length, width, height for BBox
        # 这在KITTI中会变成: height=6.0, width=5.0, length=4.0
        
        # 只测试z旋转（KITTI只支持绕垂直轴的旋转）
        z_rotation_deg = 45.0
        z_rotation_rad = math.radians(z_rotation_deg)
        
        bbox = BBox(*original_center, *original_dims)
        bbox.set_rotations(0, 0, z_rotation_deg)
        bbox.set_classname("Car")
        
        print(f"原始BBox:")
        print(f"  中心点: {bbox.get_center()}")
        print(f"  尺寸: {bbox.get_dimensions()} (length, width, height)")
        print(f"  z旋转: {bbox.get_z_rotation()}度 = {math.radians(bbox.get_z_rotation()):.4f}弧度")
        
        # 导出
        pcd_path = Path("test.ply")
        fmt = KittiFormat(tmpdir_path, 8, transformed=False)
        fmt.export_labels([bbox], pcd_path)
        
        # 读取导出的文件
        with open(tmpdir_path / "test.txt") as f:
            exported = f.read().strip()
        print(f"\n导出的KITTI格式: {exported}")
        
        parts = exported.split()
        kitti_height = float(parts[8])
        kitti_width = float(parts[9])
        kitti_length = float(parts[10])
        kitti_rotation = float(parts[14])
        
        print(f"  KITTI dimensions: height={kitti_height}, width={kitti_width}, length={kitti_length}")
        print(f"  KITTI rotation_y: {kitti_rotation}弧度")
        
        # 重新导入
        imported_bboxes = fmt.import_labels(pcd_path)
        imported = imported_bboxes[0]
        
        print(f"\n重新导入的BBox:")
        print(f"  中心点: {imported.get_center()}")
        print(f"  尺寸: {imported.get_dimensions()}")
        print(f"  旋转: {imported.get_rotations()}")
        print(f"  类别: {imported.get_classname()}")
        
        # 验证
        print(f"\n验证:")
        print(f"  中心点匹配: {np.allclose(original_center, imported.get_center())}")
        print(f"  尺寸匹配: {np.allclose(original_dims, imported.get_dimensions())}")
        print(f"  z旋转匹配: {np.isclose(z_rotation_deg, imported.get_z_rotation(), atol=0.1)}")
        
        np.testing.assert_allclose(original_center, imported.get_center(), atol=1e-6)
        np.testing.assert_allclose(original_dims, imported.get_dimensions(), atol=1e-6)
        np.testing.assert_allclose([z_rotation_deg], [imported.get_z_rotation()], atol=1e-6)
        
        print("\n✓ KITTI Untransformed格式Round-Trip通过")
        


def test_vertices_format_roundtrip():
    """测试Vertices格式的round-trip"""
    print("\n" + "=" * 60)
    print("测试5: Vertices格式Round-Trip")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # 创建带旋转的测试BBox
        original_center = (1.0, 2.0, 3.0)
        original_dims = (4.0, 5.0, 6.0)
        original_rotations = (0.0, 0.0, 45.0)  # 只z旋转，简化测试
        
        bbox = BBox(*original_center, *original_dims)
        bbox.set_rotations(*original_rotations)
        bbox.set_classname("test_object")
        
        original_vertices = bbox.get_vertices()
        print(f"原始BBox:")
        print(f"  中心点: {bbox.get_center()}")
        print(f"  尺寸: {bbox.get_dimensions()}")
        print(f"  旋转: {bbox.get_rotations()}")
        print(f"  顶点（前2个）: {original_vertices[0]}, {original_vertices[1]}")
        
        # 导出
        pcd_path = Path("test.ply")
        fmt = VerticesFormat(tmpdir_path, 8)
        fmt.export_labels([bbox], pcd_path)
        
        # 重新导入
        imported_bboxes = fmt.import_labels(pcd_path)
        imported = imported_bboxes[0]
        
        imported_vertices = imported.get_vertices()
        print(f"\n重新导入的BBox:")
        print(f"  中心点: {imported.get_center()}")
        print(f"  尺寸: {imported.get_dimensions()}")
        print(f"  旋转: {imported.get_rotations()}")
        print(f"  顶点（前2个）: {imported_vertices[0]}, {imported_vertices[1]}")
        
        # 比较顶点
        print(f"\n顶点差异:")
        max_diff = np.max(np.abs(original_vertices - imported_vertices))
        print(f"  最大顶点差异: {max_diff}")
        
        # 详细比较
        for i in range(8):
            diff = np.abs(original_vertices[i] - imported_vertices[i])
            if np.max(diff) > 1e-6:
                print(f"  顶点 {i}: 原始={original_vertices[i]}, 导入={imported_vertices[i]}, 差异={diff}")
        
        np.testing.assert_allclose(original_vertices, imported_vertices, atol=1e-4,
                                     err_msg="Vertices格式Round-Trip失败！")
        print("\n✓ Vertices格式Round-Trip通过")
        


if __name__ == "__main__":
    import pytest
    
    print("\n" + "=" * 60)
    print("坐标转换Round-Trip测试套件")
    print("=" * 60)
    
    try:
        test_bbox_vertices_consistency()
        test_rotation_roundtrip()
        test_centroid_format_roundtrip()
        test_kitti_untransformed_roundtrip()
        test_vertices_format_roundtrip()
        
        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
