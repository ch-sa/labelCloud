import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QOpenGLWidget, QFileDialog
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QSurfaceFormat
from OpenGL.GL import *
from OpenGL.GLU import *
from typing import TYPE_CHECKING, Optional, Set, Tuple
import struct
import numpy.typing as npt

class PointCloud:
    def __init__(self):
        self.vertices = None
        self.colors = None
        self.center = np.array([0, 0, 0])
        self.scale = 1.0
        self.point_size = 3.0  # Increased default point size

    def calculate_scale_and_distance(self):
        """More aggressive scaling for better visibility"""
        if self.vertices is None:
            return 1.0, 50.0
            
        min_vals = np.min(self.vertices, axis=0)
        max_vals = np.max(self.vertices, axis=0)
        dimensions = max_vals - min_vals
        max_dim = np.max(dimensions)
        
        # More aggressive scaling (target 50 units instead of 20)
        self.scale = 50.0 / max_dim if max_dim > 0 else 1.0
        
        # Closer viewing distance (1.5x scaled size instead of 3x)
        self.distance = max(10.0, max_dim * self.scale * 1.5)
        
        return self.scale, self.distance

    def read_ply(self, file_name) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Read both binary and ASCII PLY files"""
        try:
            with open(file_name, 'rb') as f:
                # Check if file is binary
                line = f.readline().decode('ascii').strip()
                if not line == 'ply':
                    raise ValueError("Not a valid PLY file")
                    
                format = 'ascii'
                vertex_count = 0
                properties = []
                has_color = False
                
                # Parse header
                while True:
                    line = f.readline().decode('ascii').strip()
                    if line.startswith('format'):
                        if 'binary' in line:
                            format = 'binary_' + line.split()[1]  # binary_little_endian or binary_big_endian
                    elif line.startswith('element vertex'):
                        vertex_count = int(line.split()[-1])
                    elif line.startswith('property'):
                        properties.append(line)
                        if 'red' in line or 'green' in line or 'blue' in line:
                            has_color = True
                    elif line == 'end_header':
                        break
                
                # Prepare data structures
                vertices = []
                colors = [] if has_color else None
                
                # Read vertex data
                if format == 'ascii':
                    for _ in range(vertex_count):
                        line = f.readline().decode('ascii').strip().split()
                        vertices.append([float(line[0]), float(line[1]), float(line[2])])
                        if has_color and len(line) >= 6:
                            colors.append([
                                float(line[3])/255.0, 
                                float(line[4])/255.0, 
                                float(line[5])/255.0
                            ])
                else:  # binary format
                    # Determine byte order
                    endian = '<' if 'little' in format else '>'
                    
                    # Create format string for struct
                    fmt = endian
                    color_props = 0
                    for prop in properties:
                        if 'float' in prop or 'double' in prop:
                            fmt += 'f' if 'float' in prop else 'd'
                        elif 'uchar' in prop:
                            fmt += 'B'
                            if 'red' in prop or 'green' in prop or 'blue' in prop:
                                color_props += 1
                        elif 'int' in prop:
                            fmt += 'i'
                    
                    # Read binary data
                    vertex_size = struct.calcsize(fmt)
                    for _ in range(vertex_count):
                        data = struct.unpack(fmt, f.read(vertex_size))
                        vertices.append([data[0], data[1], data[2]])
                        if has_color and color_props >= 3:
                            colors.append([
                                data[-color_props]/255.0,    # red
                                data[-color_props+1]/255.0,  # green
                                data[-color_props+2]/255.0   # blue
                            ])
                
                self.vertices = np.array(vertices, dtype=np.float32)
                if colors:
                    self.colors = np.array(colors, dtype=np.float32)
                
                # Calculate center and scale
                if self.vertices is not None:
                    self.center = np.mean(self.vertices, axis=0)
                    max_dim = np.max(np.ptp(self.vertices, axis=0))
                    self.scale = 10.0 / max_dim if max_dim > 0 else 1.0
                    
                return self.vertices, self.colors
                
        except Exception as e:
            print(f"Error loading PLY file: {e}")
            return None, None

    def load_ply(self, filename):
        """Wrapper for compatibility with existing code"""
        vertices, colors = self.read_ply(filename)
        return vertices is not None
    
    def draw(self):
        if self.vertices is None:
            return
            
        glPointSize(self.point_size)  # Use configured point size
        glBegin(GL_POINTS)
        
        if self.colors is not None:
            for v, c in zip(self.vertices, self.colors):
                glColor3f(c[0], c[1], c[2])
                glVertex3f(v[0], v[1], v[2])
        else:
            # Brighter default color
            glColor3f(0.9, 0.9, 0.9)  # Almost white
            for v in self.vertices:
                glVertex3f(v[0], v[1], v[2])
                
        glEnd()

class OrbitViewer(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.last_pos = QPoint()
        
        # Initialize point cloud FIRST (this was missing)
        self.point_cloud = PointCloud()  # <-- THIS IS THE CRITICAL LINE
        
        # Then initialize other attributes
        self.rot_x = -30
        self.rot_z = 0
        self.distance = 100.0
        self.axes_length = 10
        self.target = np.array([0, 0, 0])
        self.pan_offset = np.array([0.0, 0.0])
        self.boxes = [{'position': [60, 8, -1], 'size': [5, 5, 5], 'color': (1, 0, 0)}]

    def _initialize_view_to_point_cloud(self):
        """Initialize view with proper scaling"""
        if self.point_cloud.vertices is None:
            return
            
        # Calculate the bounding box of the point cloud
        min_coords = np.min(self.point_cloud.vertices, axis=0)
        max_coords = np.max(self.point_cloud.vertices, axis=0)
        bbox_size = max_coords - min_coords
        
        # Set the grid and axes to match the point cloud scale
        self.grid_size = max(bbox_size[0], bbox_size[1]) * 1.2  # 20% larger than point cloud
        self.grid_step = self.grid_size / 10  # Automatic step size
        self.axes_length = max(bbox_size) * 0.5  # Half of max dimension
        
        # Center the view
        self.target = self.point_cloud.center.copy()
        self.distance = max(bbox_size) * 1.5  # Start 1.5x the size away
        self.rot_x = -30  # Slight downward angle
        self.rot_z = 0    # No rotation

    def initializeGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)  # Pure black background
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        # Wider depth range
        gluPerspective(45, w/h, 0.1, 10000.0)  # Increased far plane
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Apply camera transformations
        glTranslatef(0, 0, -self.distance)
        glRotatef(self.rot_x, 1, 0, 0)
        glRotatef(self.rot_z, 0, 0, 1)
        glTranslatef(-self.target[0] + self.pan_offset[0], 
                    -self.target[1] + self.pan_offset[1], 
                    -self.target[2])

        # Draw references (now properly scaled)
        self.draw_ground_grid()
        self.draw_axes()
        
        # Draw point cloud (without additional scaling)
        glPushMatrix()
        glTranslatef(-self.point_cloud.center[0], -self.point_cloud.center[1], -self.point_cloud.center[2])
        self.point_cloud.draw()
        glPopMatrix()

    def draw_ground_grid(self):
        """Draw grid matching point cloud scale"""
        glBegin(GL_LINES)
        glColor3f(0.4, 0.4, 0.4)  # Medium gray
        for i in np.arange(-self.grid_size, self.grid_size + self.grid_step, self.grid_step):
            # X lines
            glVertex3f(i, -self.grid_size, 0)
            glVertex3f(i, self.grid_size, 0)
            # Y lines
            glVertex3f(-self.grid_size, i, 0)
            glVertex3f(self.grid_size, i, 0)
        glEnd()

    def draw_axes(self):
        """Draw proportional reference axes"""
        glLineWidth(2.0)
        glBegin(GL_LINES)
        # X axis (red)
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(self.axes_length, 0, 0)
        # Y axis (green)
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, self.axes_length, 0)
        # Z axis (blue)
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, self.axes_length)
        glEnd()

    def mousePressEvent(self, event):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        
        if event.buttons() == Qt.LeftButton:
            # Orbit rotation
            self.rot_z += dx * 0.5
            self.rot_x += dy * 0.5
            
        elif event.buttons() == Qt.MiddleButton:  # Fixed middle-click drag
            # Pan (translate X/Y)
            self.pan_offset[0] += dx * 0.01 * (self.distance / 50)
            self.pan_offset[1] -= dy * 0.01 * (self.distance / 50)
            
        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        # Zoom (adjust distance)
        zoom_factor = max(0.1, self.distance / 50)
        self.distance = max(-20.0, self.distance - event.angleDelta().y() * 0.01 * zoom_factor)
        self.update()

    def draw_ground_grid(self, size=50, step=5):
        """Draw a finite grid centered at origin"""
        glBegin(GL_LINES)
        glColor3f(0.5, 0.5, 0.5)  # Gray grid color
        for i in range(-size, size + 1, step):
            # X-axis lines
            glVertex3f(i, -size, 0)
            glVertex3f(i, size, 0)
            # Y-axis lines
            glVertex3f(-size, i, 0)
            glVertex3f(size, i, 0)
        glEnd()

if __name__ == "__main__":
    filename = "/home/yiming/wads/data/11/velodyne_dsor_ply/039498_dsor.ply"
    app = QApplication(sys.argv)
    viewer = OrbitViewer()
    viewer.resize(1200, 800)
    viewer.point_cloud.load_ply(filename)
    viewer.setWindowTitle("Point Cloud + Bounding Box Viewer (Right-click to load PLY)")
    viewer.show()
    sys.exit(app.exec_())