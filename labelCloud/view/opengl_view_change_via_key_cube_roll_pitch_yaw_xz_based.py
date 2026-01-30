import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QOpenGLWidget, 
                             QVBoxLayout, QWidget, QLabel)
from PyQt5.QtCore import Qt, QPoint
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtGui import QQuaternion, QVector3D
import math

class OpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view = "perspective"
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Cube dimensions (X=4m, Y=3m, Z=2m)
        self.cube_length = 4.0  # X-axis (red)
        self.cube_width = 3.0   # Y-axis (green)
        self.cube_height = 2.0   # Z-axis (blue)
        
        # Mouse control variables - NOW USING X+Z SYSTEM
        self.last_pos = QPoint()
        self.x_rot = 20    # Pitch (X rotation)
        self.z_rot = 0   # Roll (Z rotation) replaces y_rot
        self.x_trans = 0
        self.y_trans = 0
        self.zoom = -15.0

        # Cube rotation (unchanged)
        self.cube_rot_x = 0   # Pitch
        self.cube_rot_y = 0   # Roll
        self.cube_rot_z = 30  # Yaw

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
        
        # Apply camera transformations - NOW USING X+Z
        glTranslatef(self.x_trans, self.y_trans, self.zoom)
        glRotatef(self.x_rot, 1.0, 0.0, 0.0)  # Pitch (X)
        glRotatef(self.z_rot, 0.0, 0.0, 1.0)  # Roll (Z) - replaces Y rotation
        
        # Fixed world rotation (Z-up)
        glRotatef(-90, 1.0, 0.0, 0.0)
        
        # Draw scene (unchanged)
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
        glLineWidth(3.0)
        
        # Apply cube rotation to axes
        glPushMatrix()
        glRotatef(self.cube_rot_z, 0.0, 0.0, 1.0)  # Yaw
        glRotatef(self.cube_rot_y, 0.0, 1.0, 0.0)  # Roll
        glRotatef(self.cube_rot_x, 1.0, 0.0, 0.0)  # Pitch
        
        glBegin(GL_LINES)
        # X axis (red)
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(self.cube_length, 0, 0)
        # Y axis (green)
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, self.cube_width, 0)
        # Z axis (blue)
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, self.cube_height)
        glEnd()
        
        glPopMatrix()
        glLineWidth(1.0)

    def draw_cube(self):
        half_l = self.cube_length / 2
        half_w = self.cube_width  / 2
        half_h = self.cube_height / 2

        glPushMatrix()
        # Apply all cube rotations (order matters: Z -> Y -> X)
        glRotatef(self.cube_rot_z, 0, 0, 1)  # Yaw first
        glRotatef(self.cube_rot_y, 0, 1, 0)  # Then Roll
        glRotatef(self.cube_rot_x, 1, 0, 0)  # Finally Pitch

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
        glBegin(GL_LINES)
        glColor3f(1, 1, 1)  # White
        for edge in edges:
            for vertex in edge:
                glVertex3fv(vertices[vertex])
        glEnd()
        glPopMatrix()  # Restore matrix state

    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        self.setFocus()

    def mouseMoveEvent(self, event):
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        
        if event.buttons() & Qt.LeftButton:
            # Now rotating around X and Z instead of X and Y
            self.x_rot += dy * 0.5  # Pitch (up/down)
            self.z_rot += dx * 0.5  # Roll (left/right tilt)
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

        # Cube rotation controls (unchanged)
        if event.key() == Qt.Key_Q:
            self.cube_rot_z += 5
        elif event.key() == Qt.Key_E:
            self.cube_rot_z -= 5
        elif event.key() == Qt.Key_A:
            self.cube_rot_x += 5
        elif event.key() == Qt.Key_D:
            self.cube_rot_x -= 5
        elif event.key() == Qt.Key_W:
            self.cube_rot_y += 5
        elif event.key() == Qt.Key_S:
            self.cube_rot_y -= 5
        else:
            super().keyPressEvent(event)
        self.update()

    def reset_view(self, view_type):
        self.current_view = view_type
        self.x_trans = 0
        self.y_trans = 0
        self.zoom = -15.0
        
        # Create rotation quaternion (ZYX order)
        z_rot = QQuaternion.fromAxisAndAngle(0, 0, 1, self.cube_rot_z)
        y_rot = QQuaternion.fromAxisAndAngle(0, 1, 0, self.cube_rot_y)
        x_rot = QQuaternion.fromAxisAndAngle(1, 0, 0, self.cube_rot_x)
        cube_rotation = z_rot * y_rot * x_rot
        
        # Base view directions (in cube's local coordinates)
        if view_type == 'left':
            view_dir = QVector3D(0, -1, 0)  # -Y
        elif view_type == 'right':
            view_dir = QVector3D(0, 1, 0)   # +Y
        elif view_type == 'top':
            view_dir = QVector3D(0, 0, -1)  # -Z
        elif view_type == 'bottom':
            view_dir = QVector3D(0, 0, 1)   # +Z
        elif view_type == 'back':
            view_dir = QVector3D(1, 0, 0)   # +X
        elif view_type == 'front':
            view_dir = QVector3D(-1, 0, 0)  # -X
        elif view_type == 'isometric':
            view_dir = QVector3D(-1, -1, -1).normalized()
        else:  # perspective
            view_dir = QVector3D(-0.5, -1, -0.5).normalized()
        
        # Rotate view direction by cube's rotation
        adjusted_dir = cube_rotation.rotatedVector(view_dir)
        
        azimuth = math.atan2(adjusted_dir.y(), adjusted_dir.x())
        
        # 2. Calculate elevation angle
        xy_length = math.sqrt(adjusted_dir.x()**2 + adjusted_dir.y()**2)
        elevation = math.atan2(adjusted_dir.z(), xy_length)
        
        # 3. Convert to X+Z rotations
        self.z_rot = math.degrees(azimuth - math.pi/2)  # Offset by 90° for correct facing
        self.x_rot = math.degrees(elevation)
        
        # Apply standard downward tilt for better viewing
        if view_type not in ['isometric', 'perspective']:
            self.x_rot = max(self.x_rot, -30)  # Limit to 30° downward tilt

        # Special adjustments
        if view_type in ['isometric', 'perspective']:
            self.z_rot -= 45  # Adjust for better angle
            self.x_rot += 30
        
        self.update()

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