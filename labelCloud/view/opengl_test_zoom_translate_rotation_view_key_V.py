import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtCore import Qt, QPoint
from OpenGL.GL import *
from OpenGL.GLU import *
import random
import math

class OrbitViewer(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.last_pos = QPoint()
        
        # Camera parameters
        self.rot_x = -30          # Pitch (vertical)
        self.rot_z = 0            # Yaw (horizontal)
        self.distance = 5.0       # Camera distance (zoom)
        self.target = np.array([0, 0, 0])  # Orbit target
        self.pan_offset = np.array([0.0, 0.0])  # X/Y translation

        # Generate random cube
        self.cube_pos, self.cube_size, self.cube_rot_z = self.generate_random_cube()
        self.cube_color = (0.8, 0.2, 0.2)

        # View control
        self.view_modes = ["perspective", "top", "front", "right", "left", "back"]
        self.current_view = "perspective"
        self.current_view_index = 0
        self.original_view_state = None
        
        # Debug visualization
        self.debug_camera_pos = None
        self.debug_sphere = None
        self.show_debug = True  # Always show debug visuals
        
    def generate_random_cube(self):
        """Generate random cube with position, size and rotation"""
        pos = np.array([1.5, 1.5, 0.5])  # Fixed position for debugging
        size = np.array([4.0, 2.0, 2.0])  # Fixed size for debugging
        rot_z = 0  # Fixed rotation for debugging
        return pos, size, rot_z

    def initializeGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glEnable(GL_DEPTH_TEST)
        self.debug_sphere = self.create_sphere(0.5, 16, 16)

    def create_sphere(self, radius, slices, stacks):
        quad = gluNewQuadric()
        return quad

    def draw_sphere(self, quad, pos, color):
        glPushMatrix()
        glTranslatef(pos[0], pos[1], pos[2])
        glColor3f(*color)
        gluSphere(quad, 0.5, 16, 16)
        glPopMatrix()

    def draw_axes(self, length=1.5):
        """Draw XYZ axes at cube position (red=X/front, green=Y/left, blue=Z/up)"""
        glPushMatrix()
        glTranslatef(self.cube_pos[0], self.cube_pos[1], self.cube_pos[2])
        glRotatef(self.cube_rot_z, 0, 0, 1)  # Apply cube rotation
        
        glBegin(GL_LINES)
        # X axis (front) - Red
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(length, 0, 0)
        
        # Y axis (left) - Green
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, length, 0)
        
        # Z axis (up) - Blue
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, length)
        glEnd()
        
        glPopMatrix()

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h, 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Camera transformations
        glTranslatef(0, 0, -self.distance)
        glRotatef(self.rot_x, 1, 0, 0)
        glRotatef(self.rot_z, 0, 0, 1)
        glTranslatef(-self.target[0] + self.pan_offset[0], 
                    -self.target[1] + self.pan_offset[1], 
                    -self.target[2])

        # Draw objects
        self.draw_ground_grid()
        self.draw_cube()
        self.draw_axes()
        
        # Draw debug camera position if set
        if self.show_debug and self.debug_camera_pos is not None:
            self.draw_sphere(self.debug_sphere, self.debug_camera_pos, (0, 1, 0))
            # Draw line from camera to target
            glBegin(GL_LINES)
            glColor3f(0, 1, 1)
            glVertex3fv(self.debug_camera_pos)
            glVertex3fv(self.target)
            glEnd()

    def draw_cube(self):
        half_size = self.cube_size / 2
        vertices = [
            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],  # Bottom
            [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]       # Top
        ]
        edges = [
            (0,1), (1,2), (2,3), (3,0),  # Bottom
            (4,5), (5,6), (6,7), (7,4),  # Top
            (0,4), (1,5), (2,6), (3,7)   # Sides
        ]

        glPushMatrix()
        glTranslatef(self.cube_pos[0], self.cube_pos[1], self.cube_pos[2])
        glRotatef(self.cube_rot_z, 0, 0, 1)
        glScalef(half_size[0], half_size[1], half_size[2])
        
        glColor3f(*self.cube_color)
        glBegin(GL_LINES)
        for edge in edges:
            for vertex in edge:
                glVertex3fv(vertices[vertex])
        glEnd()
        glPopMatrix()

    def draw_ground_grid(self, size=10, step=1):
        glBegin(GL_LINES)
        glColor3f(0.3, 0.3, 0.3)
        for i in range(-size, size+1, step):
            glVertex3f(i, -size, 0)
            glVertex3f(i, size, 0)
            glVertex3f(-size, i, 0)
            glVertex3f(size, i, 0)
        glEnd()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_V:
            self.cycle_view()
        else:
            super().keyPressEvent(event)

    def cycle_view(self):
        if self.original_view_state is None:
            self.original_view_state = {
                'rot_x': self.rot_x,
                'rot_z': self.rot_z,
                'distance': self.distance,
                'target': self.target.copy(),
                'pan_offset': self.pan_offset.copy()
            }

        if not hasattr(self, 'view_modes'):
            self.view_modes = ["perspective", "top", "front", "right", "left", "back"]
            self.current_view_index = -1
            
        self.current_view_index = (self.current_view_index + 1) % len(self.view_modes)
        self.current_view = self.view_modes[self.current_view_index]

        print(f"\nSwitching to view: {self.current_view}")
        print(f"Cube position: {self.cube_pos}")
        print(f"Cube rotation: {self.cube_rot_z}°")
        print(f"Cube size: {self.cube_size}")

        if self.current_view == "perspective":
            if self.original_view_state:
                self.rot_x = self.original_view_state['rot_x']
                self.rot_z = self.original_view_state['rot_z']
                self.distance = self.original_view_state['distance']
                self.target = self.original_view_state['target'].copy()
                self.pan_offset = self.original_view_state['pan_offset'].copy()
        else:
            self.set_bbox_view(self.current_view)

        self.update()

    def set_bbox_view(self, view_type):
        """Set camera to specific view relative to the cube"""
        # Calculate view distance based on cube size
        view_distance = max(self.cube_size) * 2.5
        angle_rad = math.radians(self.cube_rot_z)
        
        # Set target to cube center
        self.target = self.cube_pos.copy()
        self.pan_offset = np.array([0.0, 0.0])

        if view_type == "top":
            # Camera directly above looking down
            self.debug_camera_pos = self.cube_pos + np.array([0, 0, view_distance])
            self.rot_x = 0
            self.rot_z = 90
            self.distance = view_distance
        elif view_type == "front":
            # Camera in front looking at cube
            offset_x = math.cos(angle_rad) * view_distance
            offset_y = math.sin(angle_rad) * view_distance
            self.debug_camera_pos = self.cube_pos + np.array([offset_x, offset_y, self.cube_size[2]/2])
            self.set_camera_to_look_at(self.debug_camera_pos)
        elif view_type == "right":
            # Camera to right looking at cube
            offset_x = -math.sin(angle_rad) * view_distance
            offset_y = math.cos(angle_rad) * view_distance
            self.debug_camera_pos = self.cube_pos + np.array([offset_x, offset_y, self.cube_size[2]/2])
            self.set_camera_to_look_at(self.debug_camera_pos)
        elif view_type == "left":
            # Camera to left looking at cube
            offset_x = math.sin(angle_rad) * view_distance
            offset_y = -math.cos(angle_rad) * view_distance
            self.debug_camera_pos = self.cube_pos + np.array([offset_x, offset_y, self.cube_size[2]/2])
            self.set_camera_to_look_at(self.debug_camera_pos)
        elif view_type == "back":
            # Camera behind looking at cube
            offset_x = -math.cos(angle_rad) * view_distance
            offset_y = -math.sin(angle_rad) * view_distance
            self.debug_camera_pos = self.cube_pos + np.array([offset_x, offset_y, self.cube_size[2]/2])
            self.set_camera_to_look_at(self.debug_camera_pos)

        print(f"Camera target: {self.target}")
        print(f"Camera position: {self.debug_camera_pos}")
        print(f"Camera distance: {self.distance}")
        print(f"Camera rotations - X: {self.rot_x}°, Z: {self.rot_z}°")

    def set_camera_to_look_at(self, camera_pos):
        """Calculate camera rotations to look at target from given position"""
        direction = self.target - camera_pos
        self.distance = np.linalg.norm(direction)
        dir_normalized = direction / self.distance
        
        # OpenGL coordinates:
        # X = right, Y = up, Z = backward (negative is forward)
        
        # Pitch (X rotation) - look up/down
        # Calculate angle between direction vector and XZ plane
        self.rot_x = math.degrees(math.asin(dir_normalized[1]))  # Using Y component
        
        # Yaw (Z rotation) - look left/right
        # Calculate angle in XZ plane (ignore Y)
        self.rot_z = math.degrees(math.atan2(-dir_normalized[0], -dir_normalized[2]))

    def mousePressEvent(self, event):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        
        if event.buttons() == Qt.LeftButton:
            self.rot_z += dx * 0.5
            self.rot_x += dy * 0.5
            self.current_view = "perspective"
            
        elif event.buttons() == Qt.MiddleButton:
            self.pan_offset[0] += dx * 0.01
            self.pan_offset[1] -= dy * 0.01
            self.current_view = "perspective"
            
        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        self.distance = max(1.0, self.distance - event.angleDelta().y() * 0.01)
        self.current_view = "perspective"
        self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = OrbitViewer()
    viewer.resize(800, 600)
    viewer.setWindowTitle("3D Viewer Debug - Press V to cycle views")
    viewer.show()
    sys.exit(app.exec_())