import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QOpenGLWidget, 
                             QVBoxLayout, QWidget, QLabel)
from PyQt5.QtCore import Qt, QPoint
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtGui import QQuaternion, QVector3D

class OpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view = "perspective"
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Cube dimensions (X=4m, Y=3m, Z=2m)
        self.cube_length = 4.0  # X-axis (red)
        self.cube_width = 3.0   # Y-axis (green)
        self.cube_height = 2.0   # Z-axis (blue)
        
        # Mouse control variables
        self.last_pos = QPoint()
        self.x_rot = 20  # Slightly tilted initial view
        self.y_rot = -30
        self.z_rot = 0
        self.x_trans = 0
        self.y_trans = 0
        self.zoom = -15.0

        # World rotation (converts from Y-up to Z-up)
        # self.world_rotation = QQuaternion.fromEulerAngles(-90, 0, 0)

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.2, 0.2, 0.2, 1.0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / h if h != 0 else 1.0
        gluPerspective(45, aspect, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Apply camera transformations
        glTranslatef(self.x_trans, self.y_trans, self.zoom)
        glRotatef(self.x_rot, 1.0, 0.0, 0.0)  # Pitch
        glRotatef(self.y_rot, 0.0, 1.0, 0.0)  # Yaw
        
        # Apply fixed world rotation (X by -90° to make Z up)
        glRotatef(-90, 1.0, 0.0, 0.0)
        
        # Draw scene
        self.draw_grid()
        self.draw_axes()
        self.draw_cube()

    def draw_grid(self):
        glBegin(GL_LINES)
        glColor3f(0.5, 0.5, 0.5)  # Gray grid
        size = 20
        step = 1
        for i in range(-size, size+1, step):
            glVertex3f(i, -size, 0)
            glVertex3f(i, size, 0)
            glVertex3f(-size, i, 0)
            glVertex3f(size, i, 0)
        glEnd()

    def draw_axes(self):
        glLineWidth(3.0)  # Thicker lines for axes
        glBegin(GL_LINES)
        # X axis (red) - cube length
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(self.cube_length, 0, 0)
        # Y axis (green) - cube width
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, self.cube_width, 0)
        # Z axis (blue) - cube height
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, self.cube_height)
        glEnd()
        glLineWidth(1.0)  # Reset to default

    def draw_cube(self):
        half_l = self.cube_length / 2
        half_w = self.cube_width / 2
        half_h = self.cube_height / 2
        
        vertices = (
            (half_l, -half_w, -half_h), (half_l, half_w, -half_h), 
            (-half_l, half_w, -half_h), (-half_l, -half_w, -half_h),
            (half_l, -half_w, half_h), (half_l, half_w, half_h), 
            (-half_l, -half_w, half_h), (-half_l, half_w, half_h)
        )
        
        edges = (
            (0,1), (1,2), (2,3), (3,0),  # Bottom face
            (4,5), (5,7), (7,6), (6,4),  # Top face
            (0,4), (1,5), (2,7), (3,6)   # Vertical edges
        )
        
        # Draw white wireframe only
        glBegin(GL_LINES)
        glColor3f(1, 1, 1)  # White
        for edge in edges:
            for vertex in edge:
                glVertex3fv(vertices[vertex])
        glEnd()

    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        self.setFocus()  # Ensure keyboard focus

    def mouseMoveEvent(self, event):
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        
        if event.buttons() & Qt.LeftButton:
            self.x_rot += dy * 0.5
            self.y_rot += dx * 0.5
        elif event.buttons() & Qt.RightButton:
            self.x_trans += dx * 0.02
            self.y_trans -= dy * 0.02
        
        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        self.zoom += event.angleDelta().y() * 0.01
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_0:
            self.reset_view('perspective')
        elif event.key() == Qt.Key_1:
            self.reset_view('front')
        elif event.key() == Qt.Key_2:
            self.reset_view('back')
        elif event.key() == Qt.Key_3:
            self.reset_view('top')
        elif event.key() == Qt.Key_4:
            self.reset_view('bottom')
        elif event.key() == Qt.Key_5:
            self.reset_view('left')
        elif event.key() == Qt.Key_6:
            self.reset_view('right')
        elif event.key() == Qt.Key_7:
            self.reset_view('isometric')
        
        self.update()

    def reset_view(self, view_type):
        self.current_view = view_type
        self.x_rot = 0
        self.y_rot = 0
        self.x_trans = 0
        self.y_trans = 0
        self.zoom = -15.0
        
        if view_type == 'right':
            self.y_rot = 0    # Looking down -Y (engineering front)
        elif view_type == 'left':
            self.y_rot = 180  # Looking down +Y
        elif view_type == 'top':
            self.x_rot = 90  # Looking down -Z (note sign change)
        elif view_type == 'bottom':
            self.x_rot = -90 # Looking down +Z
        elif view_type == 'front':
            self.y_rot = -90  # Looking down +X
        elif view_type == 'back':
            self.y_rot = 90   # Looking down -X
        elif view_type == 'isometric':
            self.x_rot = 35.264  # arctan(1/sqrt(2))
            self.y_rot = -45
        else:  # perspective
            self.x_rot = 20
            self.y_rot = -30

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cube Viewer - Clear Coordinate Axes")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Help label
        help_text = (
            "Keyboard Views: 0(Persp) 1(Front) 2(Back) 3(Top)\n"
            "4(Bottom) 5(Left) 6(Right) 7(Iso)\n\n"
            "Mouse Controls:\n"
            "Left Drag: Rotate | Right Drag: Pan | Wheel: Zoom\n\n"
            "Axes: Red=X(4m) Green=Y(3m) Blue=Z(2m)"
        )
        help_label = QLabel(help_text)
        layout.addWidget(help_label)
        
        self.opengl_widget = OpenGLWidget()
        layout.addWidget(self.opengl_widget, 1)

    def showEvent(self, event):
        """Ensure widget gets focus when window appears"""
        super().showEvent(event)
        self.opengl_widget.setFocus()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())