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
        self.rot_x = 0  # Pitch (vertical)
        self.rot_z = 0  # Yaw (horizontal)
        self.distance = 10.0  # Camera distance from target
        # self.target = np.array([0, 0, 0])  # Orbit target
        self.target = np.array([0, 0, -1])  # Orbit target

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

        # Set camera position
        glTranslatef(0, 0, -self.distance)
        
        # Rotate vertically (pitch) first, then horizontally (yaw)
        glRotatef(self.rot_x, 1, 0, 0)
        glRotatef(self.rot_z, 0, 0, 1)
        
        # Focus on target
        glTranslatef(-self.target[0], -self.target[1], -self.target[2])

        # Draw a red cube (using raw OpenGL, no GLUT)
        self.draw_cube_at(self.target, size=0.5)

        # Draw grid
        self.draw_ground_grid()

    def draw_cube_at(self, pos, size=1.0):
        vertices = [
            [1, 1, -1], [-1, 1, -1], [-1, 1, 1], [1, 1, 1],
            [1, -1, 1], [-1, -1, 1], [-1, -1, -1], [1, -1, -1]
        ]
        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 7), (1, 6), (2, 5), (3, 4)
        ]

        glPushMatrix()
        glTranslatef(pos[0], pos[1], pos[2])
        glScalef(size, size, size)
        
        glColor3f(1, 0, 0)  # Red
        glBegin(GL_LINES)
        for edge in edges:
            for vertex in edge:
                glVertex3fv(vertices[vertex])
        glEnd()
        glPopMatrix()

    def draw_ground_grid(self, size=10, step=1):
        glBegin(GL_LINES)
        glColor3f(0.5, 0.5, 0.5)  # Gray
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
            self.rot_z += dx * 0.5  # Horizontal (always full 360)
            self.rot_x += dy * 0.5  # Vertical (now unlimited!)
            # Remove the clipping: self.rot_x = np.clip(self.rot_x, -90, 90)
            
        self.last_pos = event.pos()
        self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = OrbitViewer()
    viewer.resize(800, 600)
    viewer.setWindowTitle("OpenGL Orbit Camera Demo (No GLUT)")
    viewer.show()
    sys.exit(app.exec_())