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
        self.distance = 5.0      # Camera distance (zoom)
        self.target = np.array([0, 0, 0])  # Orbit target (x,y,0)
        self.pan_offset = np.array([0.0, 0.0])  # X/Y translation

    def initializeGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glEnable(GL_DEPTH_TEST)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h, 0.1, 50.0)
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

        # Draw objects
        self.draw_ground_grid()
        self.draw_cube_at([1, 1, 0], size=0.3, color=(1, 0, 0))  # Example object 1
        self.draw_cube_at([-1, -1, 0], size=0.4, color=(0, 1, 0)) # Example object 2

    def draw_cube_at(self, pos, size=1.0, color=(1, 1, 1)):
        vertices = [  # Cube vertices (Z=0 for "ground-level" objects)
            [1, 1, 0], [-1, 1, 0], [-1, -1, 0], [1, -1, 0],
            [1, 1, 1], [-1, 1, 1], [-1, -1, 1], [1, -1, 1]
        ]
        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),  # Bottom
            (4, 5), (5, 6), (6, 7), (7, 4),  # Top
            (0, 4), (1, 5), (2, 6), (3, 7)   # Sides
        ]
        glPushMatrix()
        glTranslatef(pos[0], pos[1], pos[2])
        glScalef(size, size, size)
        glColor3f(*color)
        glBegin(GL_LINES)
        for edge in edges:
            for vertex in edge:
                glVertex3fv(vertices[vertex])
        glEnd()
        glPopMatrix()

    def draw_ground_grid(self, size=10, step=1):
        glBegin(GL_LINES)
        glColor3f(0.3, 0.3, 0.3)
        for i in range(-size, size + 1, step):
            glVertex3f(i, -size, 0)
            glVertex3f(i, size, 0)
            glVertex3f(-size, i, 0)
            glVertex3f(size, i, 0)
        glEnd()

    def mousePressEvent(self, event):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        
        if event.buttons() == Qt.LeftButton:
            # Orbit rotation
            self.rot_z += dx * 0.5
            self.rot_x += dy * 0.5  # Full 360° vertical
            
        elif event.buttons() == Qt.MiddleButton:  # Changed from RightButton
            # Pan (translate X/Y)
            self.pan_offset[0] += dx * 0.01
            self.pan_offset[1] -= dy * 0.01
            
        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        # Zoom (adjust distance)
        self.distance = max(1.0, self.distance - event.angleDelta().y() * 0.01)
        self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = OrbitViewer()
    viewer.resize(800, 600)
    viewer.setWindowTitle("Orbit + Zoom + Middle-Mouse-Translate Demo")
    viewer.show()
    sys.exit(app.exec_())