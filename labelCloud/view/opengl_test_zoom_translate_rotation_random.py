import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtCore import Qt, QPoint
from OpenGL.GL import *
from OpenGL.GLU import *

class OrbitViewer(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.last_pos = QPoint()
        
        # Camera parameters
        self.rot_x = 0          # Pitch (vertical, unlimited)
        self.rot_z = 0          # Yaw (horizontal)
        self.distance = 50.0     # Start with larger distance for big scene
        self.target = np.array([0, 0, 0])  # Orbit target (x,y,0)
        self.pan_offset = np.array([0.0, 0.0])  # X/Y translation
        
        # Environment parameters
        self.world_size = {'x': 200, 'y': 100, 'z_min': -1, 'z_max': 5}
        
        # Generate random boxes
        self.boxes = self.generate_random_boxes(50)

    def generate_random_boxes(self, count):
        boxes = []
        for _ in range(count):
            # Random position within world bounds
            x = np.random.uniform(-self.world_size['x']/2, self.world_size['x']/2)
            y = np.random.uniform(-self.world_size['y']/2, self.world_size['y']/2)
            z = np.random.uniform(self.world_size['z_min'], self.world_size['z_max'] - 1)
            
            # Random size (width, length, height)
            width = np.random.uniform(1, 10)
            length = np.random.uniform(1, 10)
            height = np.random.uniform(0.5, 5)
            
            # Random color
            color = (np.random.uniform(0.2, 1), 
                     np.random.uniform(0.2, 1), 
                     np.random.uniform(0.2, 1))
            
            boxes.append({
                'position': [x, y, z],
                'size': [width, length, height],
                'color': color
            })
        return boxes

    def initializeGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glEnable(GL_DEPTH_TEST)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h, 0.1, 1000.0)  # Increased far plane
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # 1. Zoom (camera distance)
        glTranslatef(0, 0, -self.distance)
        
        # 2. Orbit rotation
        glRotatef(self.rot_x, 1, 0, 0)
        glRotatef(self.rot_z, 0, 0, 1)
        
        # 3. Pan (X/Y translation)
        glTranslatef(-self.target[0] + self.pan_offset[0], 
                     -self.target[1] + self.pan_offset[1], 
                     -self.target[2])

        # Draw environment
        self.draw_ground_grid()
        self.draw_axes()
        
        # Draw all boxes
        for box in self.boxes:
            self.draw_box(box['position'], box['size'], box['color'])

    def draw_box(self, pos, size, color):
        """Draw a box with given position, size (width, length, height), and color"""
        w, l, h = size[0]/2, size[1]/2, size[2]  # Half extents
        
        vertices = [
            # Bottom face
            [ w,  l, 0], [-w,  l, 0], [-w, -l, 0], [ w, -l, 0],
            # Top face
            [ w,  l, h], [-w,  l, h], [-w, -l, h], [ w, -l, h]
        ]
        
        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),  # Bottom
            (4, 5), (5, 6), (6, 7), (7, 4),  # Top
            (0, 4), (1, 5), (2, 6), (3, 7)  # Sides
        ]
        
        glPushMatrix()
        glTranslatef(pos[0], pos[1], pos[2])
        glColor3f(*color)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for edge in edges:
            for vertex in edge:
                glVertex3fv(vertices[vertex])
        glEnd()
        glPopMatrix()

    def draw_ground_grid(self, step=5):
        """Draw a large grid on the ground plane"""
        size_x = self.world_size['x']
        size_y = self.world_size['y']
        
        glBegin(GL_LINES)
        glColor3f(0.3, 0.3, 0.3)
        for i in range(-size_x, size_x + 1, step):
            glVertex3f(i, -size_y, 0)
            glVertex3f(i, size_y, 0)
        for i in range(-size_y, size_y + 1, step):
            glVertex3f(-size_x, i, 0)
            glVertex3f(size_x, i, 0)
        glEnd()

    def draw_axes(self, length=10):
        """Draw XYZ axes for orientation"""
        glLineWidth(2.0)
        glBegin(GL_LINES)
        # X axis (red)
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(length, 0, 0)
        # Y axis (green)
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, length, 0)
        # Z axis (blue)
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, length)
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
            
        elif event.buttons() == Qt.MiddleButton:
            # Pan (translate X/Y)
            self.pan_offset[0] += dx * 0.01 * (self.distance / 50)  # Scale by zoom level
            self.pan_offset[1] -= dy * 0.01 * (self.distance / 50)
            
        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        # Zoom (adjust distance)
        zoom_factor = max(0.1, self.distance / 50)  # Slower zoom when far away
        self.distance = max(5.0, self.distance - event.angleDelta().y() * 0.01 * zoom_factor)
        self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = OrbitViewer()
    viewer.resize(1200, 800)
    viewer.setWindowTitle("Large-Scale Environment Viewer (200m x 100m)")
    viewer.show()
    sys.exit(app.exec_())