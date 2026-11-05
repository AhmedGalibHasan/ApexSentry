from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from math import sin, cos, radians, degrees, atan2, sqrt
import random, time, sys

W, H = 1000, 800

STATE_MENU = -1
STATE_PLAYING = 0
STATE_PAUSED = 1
STATE_OVER = 2
game_state = STATE_MENU

# Command pad / lives / score
pad_pos = [0.0, 0.0, 0.0]
pad_radius = 1.2
lives = 5
score = 0
wave = 1

pad_shake = [0.0, 0.0, 0.0]
pad_flash = 0.0
pad_hit_time = 0.0

# Cannon (player unit on pad surface)
cannon_pos = [0.0, 0.0, 0.0]
cannon_yaw = 0.0
cannon_pitch = 12.0
cannon_pitch_min = -10.0
cannon_pitch_max = 60.0
cannon_move_speed = 0.15

# Camera
CAM_THIRD = 0
CAM_FIRST = 1
cam_mode = CAM_THIRD
cam_orbit_x = 35.0
cam_orbit_y = 22.0
cam_dist = 13.0
fovY = 58.0
fp_fovY = 44.0

auto_aim = False
rapid_fire = False

projectiles = []
proj_speed = 0.55
proj_range = 60.0
fire_cooldown = 0.25
last_fire_time = 0.0

stats_shots = 0
stats_hits = 0
stats_kills = 0
game_start_time = 0.0

# Hostiles: SWARM, ROCKET, GLIDER
enemies = []
base_spawn_interval = 1.25
last_spawn_time = 0.0
difficulty_start_time = time.time()

sky_drift = 0.0
is_dusk_mode = True

mega_shot_ready = False
mega_shot_used = False
last_wave_for_mega = 0
mega_projectiles = []

prev_time = time.time()


def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def vec_len(x, y, z):
    return sqrt(x * x + y * y + z * z)


def norm_vec(x, y, z):
    d = vec_len(x, y, z)
    if d == 0:
        return 0.0, 0.0, 0.0
    return x / d, y / d, z / d


def cannon_target():
    return cannon_pos[0], 0.68, cannon_pos[2]


def velocity_face_angles(vx, vy, vz):
    yaw = degrees(atan2(vx, vz))
    horiz = sqrt(vx * vx + vz * vz)
    pitch = -degrees(atan2(vy, horiz))
    return yaw, pitch


def now():
    return time.time()


def new_quadric():
    return gluNewQuadric()


def draw_solid_cylinder(base_r, top_r, height, slices, stacks):
    glPushMatrix()
    glRotatef(90, 1, 0, 0)
    gluCylinder(new_quadric(), base_r, top_r, height, slices, stacks)
    glPopMatrix()


def draw_solid_sphere(radius, slices, stacks):
    gluSphere(new_quadric(), radius, slices, stacks)


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, W, 0, H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def hud_begin():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, W, 0, H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()


def hud_end():
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def hud_text(x, y, text):
    glColor3f(1, 1, 1)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))


def hud_quad(x, y, w, h):
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x, y + h)
    glEnd()


def draw_fp_scope():
    hud_begin()
    cx = W // 2
    cy = H // 2

    glColor3f(0.02, 0.03, 0.04)
    border = 28
    hud_quad(0, 0, W, border)
    hud_quad(0, H - border, W, border)
    hud_quad(0, border, border, H - border * 2)
    hud_quad(W - border, border, border, H - border * 2)

    glColor3f(0.12, 0.75, 0.38)
    arm = 42
    thick = 2
    gap = 14
    hud_quad(cx - gap - arm, cy - gap, thick, arm)
    hud_quad(cx - gap - arm, cy - gap - thick, arm, thick)
    hud_quad(cx + gap, cy - gap, thick, arm)
    hud_quad(cx + gap, cy - gap - thick, arm, thick)
    hud_quad(cx - gap - arm, cy + gap - arm, thick, arm)
    hud_quad(cx - gap - arm, cy + gap, arm, thick)
    hud_quad(cx + gap, cy + gap - arm, thick, arm)
    hud_quad(cx + gap, cy + gap, arm, thick)

    glColor3f(0.18, 0.90, 0.45)
    hud_quad(cx - 16, cy - 1, 11, 2)
    hud_quad(cx + 5, cy - 1, 11, 2)
    hud_quad(cx - 1, cy - 16, 2, 11)
    hud_quad(cx - 1, cy + 5, 2, 11)

    glColor3f(0.25, 1.0, 0.50)
    glPointSize(5.0)
    glBegin(GL_POINTS)
    glVertex2f(cx, cy)
    glEnd()

    glColor3f(0.10, 0.55, 0.28)
    for i in range(-2, 3):
        if i == 0:
            continue
        hud_quad(cx - 1, cy + i * 22 - 1, 2, 6)
        hud_quad(cx + i * 22 - 1, cy - 1, 6, 2)

    glColor3f(0.55, 0.85, 0.65)
    hud_text(cx - 34, cy + 52, "RNG")
    hud_text(cx + 24, cy + 52, "AIM")

    hud_end()


def first_person_camera():
    yaw_r = radians(cannon_yaw)
    pitch_r = radians(cannon_pitch)
    fx = sin(yaw_r) * cos(pitch_r)
    fy = sin(pitch_r)
    fz = cos(yaw_r) * cos(pitch_r)
    rx = cos(yaw_r)
    rz = -sin(yaw_r)

    pivot_y = 0.58
    eye_x = cannon_pos[0] + rx * 0.10 - fx * 0.08
    eye_y = pivot_y + 0.16
    eye_z = cannon_pos[2] + rz * 0.10 - fz * 0.08

    look_x = eye_x + fx * 120.0
    look_y = eye_y + fy * 120.0
    look_z = eye_z + fz * 120.0
    return eye_x, eye_y, eye_z, look_x, look_y, look_z


def draw_scanner():
    radar_size = 110
    radar_x = W - radar_size - 15
    radar_y = H - radar_size - 15

    hud_begin()

    glColor3f(0.08, 0.12, 0.18)
    glBegin(GL_QUADS)
    glVertex2f(radar_x, radar_y)
    glVertex2f(radar_x + radar_size, radar_y)
    glVertex2f(radar_x + radar_size, radar_y + radar_size)
    glVertex2f(radar_x, radar_y + radar_size)
    glEnd()

    glColor3f(0.2, 0.55, 0.75)
    glBegin(GL_QUADS)
    glVertex2f(radar_x + 2, radar_y + 2)
    glVertex2f(radar_x + radar_size - 2, radar_y + 2)
    glVertex2f(radar_x + radar_size - 2, radar_y + radar_size - 2)
    glVertex2f(radar_x + 2, radar_y + radar_size - 2)
    glEnd()

    cx = radar_x + radar_size // 2
    cy = radar_y + radar_size // 2
    glColor3f(0.1, 0.95, 0.7)
    glPointSize(5.0)
    glBegin(GL_POINTS)
    glVertex2f(cx, cy)
    glEnd()

    scan_range = 20.0
    for e in enemies:
        rel_x = (e["x"] - cannon_pos[0]) / scan_range
        rel_z = (e["z"] - cannon_pos[2]) / scan_range
        if abs(rel_x) <= 1.0 and abs(rel_z) <= 1.0:
            px = cx + rel_x * (radar_size // 2 - 8)
            py = cy + rel_z * (radar_size // 2 - 8)
            r, g, b = hostile_color(e)
            glColor3f(r, g, b)
            glPointSize(4.0)
            glBegin(GL_POINTS)
            glVertex2f(px, py)
            glEnd()

    glColor3f(0.85, 0.95, 1.0)
    hud_text(radar_x + 8, radar_y + radar_size - 18, "SCANNER")

    hud_end()


def draw_pause_overlay():
    hud_begin()

    glColor3f(0.05, 0.05, 0.12)
    glBegin(GL_QUADS)
    glVertex2f(0, 0)
    glVertex2f(W, 0)
    glVertex2f(W, H)
    glVertex2f(0, H)
    glEnd()

    cx = W // 2
    cy = H // 2
    glColor3f(0.95, 0.55, 0.15)
    hud_text(cx - 55, cy + 70, "PAUSED")
    glColor3f(1.0, 1.0, 1.0)
    hud_text(cx - 150, cy + 30, "I/K - Pitch   J/L - Yaw")
    hud_text(cx - 150, cy + 10, "W/A/S/D - Move Cannon")
    hud_text(cx - 150, cy - 10, "Mouse - Fire   V - Camera")
    hud_text(cx - 150, cy - 30, "C - Auto-Aim   F - Rapid Fire")
    hud_text(cx - 150, cy - 50, "Z/X - Zoom   P - Dusk/Dawn")
    hud_text(cx - 150, cy - 80, "SPACE - Resume")

    hud_end()


def draw_outpost_props():
    ground_y = -0.1

    glColor3f(0.62, 0.52, 0.38)
    glPushMatrix()
    glTranslatef(0, ground_y, -22)
    glScalef(5.0, 0.06, 22.0)
    glutSolidCube(1)
    glPopMatrix()

    glColor3f(0.95, 0.85, 0.55)
    for i in range(-18, 18, 4):
        glPushMatrix()
        glTranslatef(0, ground_y + 0.04, i)
        glScalef(0.12, 0.02, 1.0)
        glutSolidCube(1)
        glPopMatrix()

    rock_spots = [(-14, -10), (12, -8), (-9, 14), (16, 11), (-18, 5)]
    for rx, rz in rock_spots:
        glColor3f(0.45, 0.40, 0.35)
        glPushMatrix()
        glTranslatef(rx, ground_y + 0.35, rz)
        glScalef(1.2, 0.7, 1.0)
        glutSolidCube(1)
        glPopMatrix()
        glColor3f(0.38, 0.34, 0.30)
        glPushMatrix()
        glTranslatef(rx + 0.4, ground_y + 0.55, rz - 0.3)
        draw_solid_sphere(0.35, 10, 10)
        glPopMatrix()

    beacon_spots = [(-16, -16), (16, -16), (-17, 16), (17, 16)]
    for bx, bz in beacon_spots:
        glColor3f(0.55, 0.48, 0.42)
        glPushMatrix()
        glTranslatef(bx, ground_y + 1.4, bz)
        glScalef(0.35, 2.8, 0.35)
        glutSolidCube(1)
        glPopMatrix()

        glColor3f(0.85, 0.35, 0.12)
        glPushMatrix()
        glTranslatef(bx, ground_y + 3.0, bz)
        draw_solid_cylinder(0.55, 0.15, 0.9, 12, 6)
        glPopMatrix()

        glColor3f(1.0, 0.75, 0.2)
        glPushMatrix()
        glTranslatef(bx, ground_y + 3.55, bz)
        glScalef(0.25, 0.25, 0.25)
        glutSolidCube(1)
        glPopMatrix()

    fence_posts = [(-11, -12), (-11, 0), (-11, 12), (11, -12), (11, 0), (11, 12)]
    for fx, fz in fence_posts:
        glColor3f(0.50, 0.42, 0.36)
        glPushMatrix()
        glTranslatef(fx, ground_y + 0.5, fz)
        glScalef(0.15, 1.0, 0.15)
        glutSolidCube(1)
        glPopMatrix()

    shelter_spots = [(-21, 0), (21, 0)]
    for sx, sz in shelter_spots:
        glColor3f(0.42, 0.38, 0.55)
        glPushMatrix()
        glTranslatef(sx, ground_y + 1.0, sz)
        glScalef(2.8, 2.0, 3.5)
        glutSolidCube(1)
        glPopMatrix()

        glColor3f(0.35, 0.32, 0.48)
        glPushMatrix()
        glTranslatef(sx, ground_y + 2.4, sz)
        glRotatef(90, 0, 0, 1)
        draw_solid_cylinder(1.2, 1.2, 2.8, 14, 4)
        glPopMatrix()


def draw_horizon():
    global sky_drift
    size = 80.0
    top = 42.0
    bot = -2.0

    if is_dusk_mode:
        sky_bottom = (0.55, 0.28, 0.18)
        sky_top = (0.25, 0.12, 0.35)
        cloud_color = (0.95, 0.55, 0.35)
    else:
        sky_bottom = (0.35, 0.55, 0.82)
        sky_top = (0.55, 0.75, 0.95)
        cloud_color = (0.92, 0.94, 0.98)

    glBegin(GL_QUADS)
    glColor3f(*sky_bottom)
    glVertex3f(-size, bot, -size)
    glVertex3f(size, bot, -size)
    glColor3f(*sky_top)
    glVertex3f(size, top, -size)
    glVertex3f(-size, top, -size)
    glEnd()

    glBegin(GL_QUADS)
    glColor3f(*sky_bottom)
    glVertex3f(-size, bot, size)
    glVertex3f(size, bot, size)
    glColor3f(*sky_top)
    glVertex3f(size, top, size)
    glVertex3f(-size, top, size)
    glEnd()

    glBegin(GL_QUADS)
    glColor3f(*sky_bottom)
    glVertex3f(-size, bot, -size)
    glVertex3f(-size, bot, size)
    glColor3f(*sky_top)
    glVertex3f(-size, top, size)
    glVertex3f(-size, top, -size)
    glEnd()

    glBegin(GL_QUADS)
    glColor3f(*sky_bottom)
    glVertex3f(size, bot, -size)
    glVertex3f(size, bot, size)
    glColor3f(*sky_top)
    glVertex3f(size, top, size)
    glVertex3f(size, top, -size)
    glEnd()

    glBegin(GL_QUADS)
    glColor3f(sky_top[0] * 0.75, sky_top[1] * 0.75, sky_top[2] * 0.75)
    glVertex3f(-size, top, -size)
    glVertex3f(size, top, -size)
    glColor3f(*sky_top)
    glVertex3f(size, top, size)
    glVertex3f(-size, top, size)
    glEnd()

    glColor3f(*cloud_color)
    for i in range(5):
        y = 11 + i * 4.5
        z0 = -40 + ((sky_drift * 2.2 + i * 9.0) % 80.0)
        z1 = z0 + 16.0
        x0, x1 = -42, 42
        glBegin(GL_QUADS)
        glVertex3f(x0, y, z0)
        glVertex3f(x1, y, z0)
        glVertex3f(x1, y, z1)
        glVertex3f(x0, y, z1)
        glEnd()


def draw_command_pad():
    glPushMatrix()
    glTranslatef(
        pad_pos[0] + pad_shake[0],
        pad_pos[1] + pad_shake[1],
        pad_pos[2] + pad_shake[2],
    )

    base = (0.18, 0.32, 0.48)
    flash = (1.0, 0.35, 0.15)
    r = base[0] + (flash[0] - base[0]) * pad_flash
    g = base[1] + (flash[1] - base[1]) * pad_flash
    b = base[2] + (flash[2] - base[2]) * pad_flash

    glColor3f(clamp(r, 0, 1), clamp(g, 0, 1), clamp(b, 0, 1))
    glPushMatrix()
    glTranslatef(0, 0.18, 0)
    glScalef(3.0, 0.35, 3.0)
    glutSolidCube(1)
    glPopMatrix()

    glColor3f(0.85, 0.55, 0.12)
    glPushMatrix()
    glTranslatef(0, 0.38, 0)
    draw_solid_cylinder(1.35, 1.35, 0.12, 20, 2)
    glPopMatrix()

    for ang in range(0, 360, 60):
        glPushMatrix()
        glRotatef(ang, 0, 1, 0)
        glTranslatef(1.15, 0.42, 0)
        glColor3f(0.12, 0.55, 0.72)
        glScalef(0.18, 0.22, 0.18)
        glutSolidCube(1)
        glPopMatrix()

    glPopMatrix()

    if is_dusk_mode:
        glColor3f(0.48, 0.38, 0.28)
    else:
        glColor3f(0.58, 0.62, 0.45)
    glPushMatrix()
    glTranslatef(0, -0.1, 0)
    glScalef(50.0, 0.1, 50.0)
    glutSolidCube(1)
    glPopMatrix()


def draw_cannon_full():
    glPushMatrix()
    glTranslatef(cannon_pos[0], 0.0, cannon_pos[2])

    glColor3f(0.18, 0.20, 0.16)
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(side * 0.55, 0.14, 0)
        glScalef(0.22, 0.16, 1.35)
        glutSolidCube(1)
        glPopMatrix()
        for wheel in (-0.45, 0.0, 0.45):
            glPushMatrix()
            glTranslatef(side * 0.55, 0.08, wheel)
            glRotatef(90, 0, 0, 1)
            draw_solid_cylinder(0.11, 0.11, 0.08, 12, 3)
            glPopMatrix()

    glColor3f(0.28, 0.32, 0.22)
    glPushMatrix()
    glTranslatef(0, 0.28, 0)
    glScalef(1.05, 0.32, 1.45)
    glutSolidCube(1)
    glPopMatrix()

    glColor3f(0.22, 0.25, 0.18)
    glPushMatrix()
    glTranslatef(0, 0.44, -0.55)
    glScalef(0.85, 0.22, 0.35)
    glutSolidCube(1)
    glPopMatrix()

    draw_cannon_turret()
    glPopMatrix()


def draw_cannon_turret():
    glRotatef(cannon_yaw, 0, 1, 0)

    glColor3f(0.24, 0.27, 0.20)
    glPushMatrix()
    glTranslatef(0, 0.52, 0)
    draw_solid_cylinder(0.48, 0.48, 0.18, 18, 3)
    glPopMatrix()

    glColor3f(0.32, 0.35, 0.26)
    glPushMatrix()
    glTranslatef(0, 0.62, 0)
    glScalef(0.72, 0.28, 0.82)
    glutSolidCube(1)
    glPopMatrix()

    for side in (-1, 1):
        glColor3f(0.26, 0.29, 0.21)
        glPushMatrix()
        glTranslatef(side * 0.42, 0.62, 0.05)
        glScalef(0.08, 0.38, 0.55)
        glutSolidCube(1)
        glPopMatrix()

    glTranslatef(0, 0.62, 0)
    glRotatef(-cannon_pitch, 1, 0, 0)

    glColor3f(0.14, 0.14, 0.15)
    glPushMatrix()
    glTranslatef(0, 0.0, 0.35)
    glRotatef(90, 1, 0, 0)
    draw_solid_cylinder(0.11, 0.11, 0.55, 14, 4)
    glPopMatrix()

    glColor3f(0.10, 0.10, 0.11)
    glPushMatrix()
    glTranslatef(0, 0.0, 0.72)
    glRotatef(90, 1, 0, 0)
    draw_solid_cylinder(0.07, 0.05, 0.85, 14, 4)
    glPopMatrix()

    glColor3f(0.08, 0.08, 0.09)
    glPushMatrix()
    glTranslatef(0, 0.0, 1.18)
    glRotatef(90, 1, 0, 0)
    draw_solid_cylinder(0.09, 0.09, 0.12, 12, 2)
    glPopMatrix()

    glColor3f(0.55, 0.48, 0.18)
    glPushMatrix()
    glTranslatef(0, 0.0, 1.28)
    glScalef(0.14, 0.14, 0.10)
    glutSolidCube(1)
    glPopMatrix()


def draw_cannon_fp_view():
    glPushMatrix()
    glTranslatef(cannon_pos[0], 0.0, cannon_pos[2])
    glRotatef(cannon_yaw, 0, 1, 0)

    glColor3f(0.20, 0.23, 0.17)
    glPushMatrix()
    glTranslatef(0, 0.50, -0.18)
    glScalef(0.95, 0.14, 0.72)
    glutSolidCube(1)
    glPopMatrix()

    for side in (-1, 1):
        glColor3f(0.18, 0.21, 0.15)
        glPushMatrix()
        glTranslatef(side * 0.48, 0.48, 0.02)
        glScalef(0.10, 0.22, 0.62)
        glutSolidCube(1)
        glPopMatrix()

    glColor3f(0.30, 0.33, 0.25)
    glPushMatrix()
    glTranslatef(0, 0.56, 0.05)
    glScalef(0.58, 0.12, 0.48)
    glutSolidCube(1)
    glPopMatrix()

    glTranslatef(0, 0.58, 0.08)
    glRotatef(-cannon_pitch, 1, 0, 0)

    glColor3f(0.12, 0.12, 0.13)
    glPushMatrix()
    glTranslatef(0, 0.02, 0.22)
    glScalef(0.28, 0.18, 0.38)
    glutSolidCube(1)
    glPopMatrix()

    glColor3f(0.09, 0.09, 0.10)
    glPushMatrix()
    glTranslatef(0, 0.04, 0.55)
    glRotatef(90, 1, 0, 0)
    draw_solid_cylinder(0.09, 0.07, 0.95, 14, 4)
    glPopMatrix()

    glColor3f(0.07, 0.07, 0.08)
    glPushMatrix()
    glTranslatef(0, 0.04, 1.05)
    glRotatef(90, 1, 0, 0)
    draw_solid_cylinder(0.10, 0.10, 0.14, 12, 2)
    glPopMatrix()

    glPopMatrix()


def draw_cannon():
    if cam_mode == CAM_FIRST and game_state == STATE_PLAYING:
        draw_cannon_fp_view()
    else:
        draw_cannon_full()


def cannon_muzzle_world():
    base_y = 0.62
    yaw_r = radians(cannon_yaw)
    pitch_r = radians(cannon_pitch)
    fx = sin(yaw_r) * cos(pitch_r)
    fy = sin(pitch_r)
    fz = cos(yaw_r) * cos(pitch_r)
    mx = cannon_pos[0] + fx * 1.35
    my = base_y + fy * 1.35
    mz = cannon_pos[2] + fz * 1.35
    return mx, my, mz, fx, fy, fz


def hostile_template(t):
    if t == 0:
        return ("SWARM", 0.06, 1, 0.32, (0.65, 0.20, 0.85))
    if t == 1:
        return ("ROCKET", 0.05, 1, 0.26, (0.95, 0.25, 0.15))
    return ("GLIDER", 0.03, 3, 0.52, (0.15, 0.75, 0.55))


def hostile_color(e):
    max_hp = e.get("max_hp", 1)
    if max_hp == 0:
        max_hp = 1
    ratio = e["hp"] / max_hp
    if ratio > 0.66:
        return (0.2, 0.85, 0.95)
    if ratio > 0.33:
        return (0.95, 0.85, 0.20)
    return (0.95, 0.25, 0.30)


def spawn_hostile():
    r = random.uniform(10.0, 16.0)
    ang = random.uniform(0, 360)
    x = r * sin(radians(ang))
    z = r * cos(radians(ang))
    y = random.uniform(5.0, 12.0)

    p = random.random()
    if p < 0.55:
        t = 0
    elif p < 0.80:
        t = 1
    else:
        t = 2

    name, spd, hp, size, col = hostile_template(t)
    tx, ty, tz = cannon_target()
    dx, dy, dz = tx - x, ty - y, tz - z
    nx, ny, nz = norm_vec(dx, dy, dz)

    enemies.append(
        {
            "type": name,
            "x": x,
            "y": y,
            "z": z,
            "vx": nx * spd,
            "vy": ny * spd,
            "vz": nz * spd,
            "speed": spd,
            "hp": hp,
            "max_hp": hp,
            "size": size,
            "col": col,
            "spawn_t": now(),
            "rot": random.uniform(0, 360),
        }
    )


def spawn_controller():
    global last_spawn_time, wave, mega_shot_ready, mega_shot_used, last_wave_for_mega
    t = now()
    elapsed = t - difficulty_start_time

    new_wave = 1 + int(elapsed / 20.0)
    if new_wave != wave:
        wave = new_wave
        if new_wave > last_wave_for_mega:
            mega_shot_ready = True
            mega_shot_used = False
            last_wave_for_mega = new_wave

    interval = clamp(base_spawn_interval - (wave - 1) * 0.10, 0.35, 2.0)
    if t - last_spawn_time >= interval:
        last_spawn_time = t
        spawn_hostile()


def update_hostiles(dt):
    global lives, game_state, pad_shake, pad_flash, pad_hit_time
    speed_boost = 1.0 + (wave - 1) * 0.08

    tx, ty, tz = cannon_target()

    for e in enemies[:]:
        dx, dy, dz = tx - e["x"], ty - e["y"], tz - e["z"]
        nx, ny, nz = norm_vec(dx, dy, dz)
        spd = e["speed"] * speed_boost

        if e["type"] == "ROCKET":
            blend = 0.18
            e["vx"] = e["vx"] * (1.0 - blend) + nx * spd * blend
            e["vy"] = e["vy"] * (1.0 - blend) + ny * spd * blend
            e["vz"] = e["vz"] * (1.0 - blend) + nz * spd * blend
            cur = vec_len(e["vx"], e["vy"], e["vz"])
            if cur > 0:
                e["vx"] = e["vx"] / cur * spd
                e["vy"] = e["vy"] / cur * spd
                e["vz"] = e["vz"] / cur * spd
        else:
            e["vx"], e["vy"], e["vz"] = nx * spd, ny * spd, nz * spd

        e["x"] += e["vx"] * dt * 60.0
        e["y"] += e["vy"] * dt * 60.0
        e["z"] += e["vz"] * dt * 60.0

        if e["type"] == "SWARM":
            e["rot"] = (e["rot"] + 120.0 * dt) % 360.0
        else:
            e["rot"] = velocity_face_angles(e["vx"], e["vy"], e["vz"])[0]

        d = vec_len(e["x"] - tx, e["y"] - ty, e["z"] - tz)
        if d <= 0.85 + e["size"]:
            enemies.remove(e)
            lives -= 1
            pad_hit_time = now()
            pad_flash = 1.0
            pad_shake = [
                random.uniform(-0.15, 0.15),
                random.uniform(-0.15, 0.15),
                random.uniform(-0.15, 0.15),
            ]
            if lives <= 0:
                game_state = STATE_OVER

        if abs(e["x"]) > 80 or abs(e["z"]) > 80 or e["y"] < -5 or e["y"] > 60:
            if e in enemies:
                enemies.remove(e)

    t = now()
    if t - pad_hit_time < 0.5:
        decay = 1.0 - (t - pad_hit_time) / 0.5
        pad_shake = [s * decay * 0.5 for s in pad_shake]
        pad_flash = max(0.0, 1.0 - (t - pad_hit_time) / 0.3)
    else:
        pad_shake = [0.0, 0.0, 0.0]
        pad_flash = 0.0


def draw_hostile(e):
    r, g, b = hostile_color(e)
    s = e["size"]

    glPushMatrix()
    glTranslatef(e["x"], e["y"], e["z"])

    if e["type"] == "SWARM":
        glRotatef(e["rot"], 0, 1, 0)

        glColor3f(0.14, 0.14, 0.16)
        glPushMatrix()
        glScalef(0.55, 0.18, 0.75)
        glutSolidCube(s * 2.0)
        glPopMatrix()

        glColor3f(r, g, b)
        glPushMatrix()
        glTranslatef(0, s * 0.18, 0)
        draw_solid_sphere(s * 0.28, 10, 10)
        glPopMatrix()

        glColor3f(0.92, 0.18, 0.12)
        glPushMatrix()
        glTranslatef(0, s * 0.12, s * 0.55)
        draw_solid_sphere(s * 0.08, 8, 8)
        glPopMatrix()

        for ang in (45, 135, 225, 315):
            glPushMatrix()
            glRotatef(ang, 0, 1, 0)
            glTranslatef(0, 0, s * 1.05)
            glColor3f(0.12, 0.12, 0.14)
            glScalef(0.06, 0.04, 0.55)
            glutSolidCube(s * 2)
            glPopMatrix()
            glPushMatrix()
            glRotatef(ang + e["rot"] * 3.0, 0, 1, 0)
            glTranslatef(0, s * 0.22, s * 1.05)
            glColor3f(0.35, 0.35, 0.38)
            draw_solid_cylinder(s * 0.22, s * 0.22, 0.03, 8, 2)
            glPopMatrix()

    elif e["type"] == "ROCKET":
        yaw, pitch = velocity_face_angles(e["vx"], e["vy"], e["vz"])
        glRotatef(yaw, 0, 1, 0)
        glRotatef(pitch, 1, 0, 0)

        glColor3f(0.75, 0.75, 0.78)
        glPushMatrix()
        glTranslatef(0, 0, s * 1.55)
        glRotatef(90, 1, 0, 0)
        draw_solid_cylinder(0.01, s * 0.22, s * 0.55, 10, 4)
        glPopMatrix()

        glColor3f(r, g, b)
        glPushMatrix()
        glTranslatef(0, 0, s * 0.35)
        glRotatef(90, 1, 0, 0)
        draw_solid_cylinder(s * 0.18, s * 0.18, s * 2.2, 12, 6)
        glPopMatrix()

        glColor3f(0.20, 0.20, 0.22)
        for side in (-1, 1):
            glPushMatrix()
            glTranslatef(side * s * 0.28, 0, -s * 0.55)
            glScalef(0.05, 0.35, 0.55)
            glutSolidCube(s * 2)
            glPopMatrix()

        glColor3f(0.95, 0.55, 0.12)
        glPushMatrix()
        glTranslatef(0, 0, -s * 0.75)
        glRotatef(90, 1, 0, 0)
        draw_solid_cylinder(s * 0.08, s * 0.20, s * 0.35, 10, 4)
        glPopMatrix()

        glColor3f(1.0, 0.65, 0.15)
        glPushMatrix()
        glTranslatef(0, 0, -s * 1.05)
        draw_solid_sphere(s * 0.12, 8, 8)
        glPopMatrix()

    else:
        yaw, pitch = velocity_face_angles(e["vx"], e["vy"], e["vz"])
        glRotatef(yaw, 0, 1, 0)
        glRotatef(pitch, 1, 0, 0)

        glColor3f(r, g, b)
        glPushMatrix()
        glTranslatef(0, 0, s * 0.15)
        glScalef(0.42, 0.42, 2.10)
        glutSolidCube(s * 2.0)
        glPopMatrix()

        glColor3f(0.55, 0.62, 0.68)
        glPushMatrix()
        glTranslatef(0, 0, s * 1.05)
        glRotatef(90, 1, 0, 0)
        draw_solid_cylinder(0.01, s * 0.20, s * 0.45, 10, 4)
        glPopMatrix()

        glColor3f(0.18, 0.55, 0.72)
        glPushMatrix()
        glTranslatef(0, s * 0.08, s * 0.55)
        draw_solid_sphere(s * 0.14, 10, 10)
        glPopMatrix()

        for side in (-1, 1):
            glColor3f(0.22, 0.28, 0.32)
            glPushMatrix()
            glTranslatef(side * s * 1.05, 0, s * 0.05)
            glScalef(0.85, 0.05, 0.55)
            glutSolidCube(s * 2)
            glPopMatrix()

        glColor3f(0.20, 0.24, 0.28)
        glPushMatrix()
        glTranslatef(0, s * 0.42, -s * 0.95)
        glScalef(0.08, 0.55, 0.42)
        glutSolidCube(s * 2)
        glPopMatrix()

        for side in (-1, 1):
            glPushMatrix()
            glTranslatef(side * s * 0.35, 0, -s * 1.05)
            glScalef(0.35, 0.04, 0.22)
            glutSolidCube(s * 2)
            glPopMatrix()

        glColor3f(0.12, 0.12, 0.14)
        glPushMatrix()
        glTranslatef(0, 0, -s * 1.15)
        draw_solid_cylinder(s * 0.06, s * 0.06, s * 0.35, 8, 3)
        glPopMatrix()

    glPopMatrix()


def fire_projectile(is_mega=False):
    global last_fire_time, stats_shots, mega_shot_used, mega_shot_ready
    t = now()
    cd = 0.05 if rapid_fire else fire_cooldown
    if t - last_fire_time < cd:
        return
    last_fire_time = t
    stats_shots += 1

    mx, my, mz, fx, fy, fz = cannon_muzzle_world()

    if is_mega and mega_shot_ready and not mega_shot_used:
        vx, vy, vz = fx * proj_speed * 2.0, fy * proj_speed * 2.0, fz * proj_speed * 2.0
        mega_projectiles.append([mx, my, mz, vx, vy, vz, t])
        mega_shot_used = True
        mega_shot_ready = False
    elif not is_mega:
        vx, vy, vz = fx * proj_speed, fy * proj_speed, fz * proj_speed
        projectiles.append([mx, my, mz, vx, vy, vz, t])


def update_projectiles(dt):
    t = now()
    keep = []
    for p in projectiles:
        p[0] += p[3] * dt * 60.0
        p[1] += p[4] * dt * 60.0
        p[2] += p[5] * dt * 60.0
        if vec_len(p[0], p[1], p[2]) > proj_range or (t - p[6]) > 4.0:
            continue
        keep.append(p)
    projectiles[:] = keep

    keep_mega = []
    for p in mega_projectiles:
        p[0] += p[3] * dt * 60.0
        p[1] += p[4] * dt * 60.0
        p[2] += p[5] * dt * 60.0
        dx, dy, dz = p[0] - cannon_pos[0], p[1], p[2] - cannon_pos[2]
        if vec_len(dx, dy, dz) > proj_range * 2.0 or (t - p[6]) > 8.0:
            continue
        keep_mega.append(p)
    mega_projectiles[:] = keep_mega


def draw_projectiles():
    for p in projectiles:
        glColor3f(0.85, 0.15, 0.75)
        glPushMatrix()
        glTranslatef(p[0], p[1], p[2])
        glRotatef(45, 0, 1, 0)
        glScalef(0.14, 0.14, 0.14)
        glutSolidCube(1)
        glPopMatrix()

    for p in mega_projectiles:
        glColor3f(1.0, 0.55, 0.05)
        glPushMatrix()
        glTranslatef(p[0], p[1], p[2])
        glScalef(0.32, 0.32, 0.32)
        glutSolidCube(1)
        glPopMatrix()
        glColor3f(1.0, 0.85, 0.25)
        glPushMatrix()
        glTranslatef(p[0], p[1], p[2])
        draw_solid_sphere(0.28, 10, 10)
        glPopMatrix()


def projectile_hits():
    global score, stats_hits, stats_kills

    for p in projectiles[:]:
        for e in enemies[:]:
            d = vec_len(p[0] - e["x"], p[1] - e["y"], p[2] - e["z"])
            if d <= e["size"] + 0.18:
                if p in projectiles:
                    projectiles.remove(p)
                stats_hits += 1
                e["hp"] -= 1
                if e["hp"] <= 0:
                    if e in enemies:
                        enemies.remove(e)
                    stats_kills += 1
                    if e["type"] == "SWARM":
                        score += 10
                    elif e["type"] == "ROCKET":
                        score += 12
                    else:
                        score += 25
                break

    for p in mega_projectiles[:]:
        for e in enemies[:]:
            d = vec_len(p[0] - e["x"], p[1] - e["y"], p[2] - e["z"])
            if d <= e["size"] + 0.35:
                if p in mega_projectiles:
                    mega_projectiles.remove(p)
                stats_hits += 1
                if e in enemies:
                    enemies.remove(e)
                stats_kills += 1
                if e["type"] == "SWARM":
                    score += 20
                elif e["type"] == "ROCKET":
                    score += 25
                else:
                    score += 50
                break


def auto_aim_update():
    global cannon_yaw, cannon_pitch
    if not auto_aim or len(enemies) == 0:
        return

    best = None
    bestd = 10**9
    cx, cy, cz = cannon_target()
    for e in enemies:
        d = vec_len(e["x"] - cx, e["y"] - cy, e["z"] - cz)
        if d < bestd:
            bestd = d
            best = e

    if best is None:
        return

    dx = best["x"] - cannon_pos[0]
    dz = best["z"] - cannon_pos[2]
    dyaw = (degrees(atan2(dx, dz)) + 360.0) % 360.0
    horiz = sqrt(dx * dx + dz * dz)
    dpitch = degrees(atan2(best["y"] - 0.62, horiz))

    diff = (dyaw - cannon_yaw + 540.0) % 360.0 - 180.0
    cannon_yaw = (cannon_yaw + diff * 0.12) % 360.0
    cannon_pitch = clamp(cannon_pitch + (dpitch - cannon_pitch) * 0.12, cannon_pitch_min, cannon_pitch_max)


def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    if cam_mode == CAM_FIRST and game_state not in (STATE_OVER, STATE_MENU):
        gluPerspective(fp_fovY, W / H, 0.08, 1500)
    else:
        gluPerspective(fovY, W / H, 0.1, 1500)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if cam_mode == CAM_FIRST and game_state not in (STATE_OVER, STATE_MENU):
        ex, ey, ez, lx, ly, lz = first_person_camera()
        gluLookAt(ex, ey, ez, lx, ly, lz, 0, 1, 0)
    else:
        ex = cannon_pos[0] + cam_dist * cos(radians(cam_orbit_x)) * cos(radians(cam_orbit_y))
        ey = cam_dist * sin(radians(cam_orbit_y))
        ez = cannon_pos[2] + cam_dist * sin(radians(cam_orbit_x)) * cos(radians(cam_orbit_y))
        cx, cy, cz = cannon_target()
        gluLookAt(ex, ey, ez, cx, cy, cz, 0, 1, 0)


def draw_menu():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, W, H)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, W / H, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(0, 11, 22, 0, 1, 0, 0, 1, 0)

    draw_horizon()

    if is_dusk_mode:
        glColor3f(0.48, 0.38, 0.28)
    else:
        glColor3f(0.58, 0.62, 0.45)
    glPushMatrix()
    glTranslatef(0, -0.1, 0)
    glScalef(50.0, 0.1, 50.0)
    glutSolidCube(1)
    glPopMatrix()

    glPushMatrix()
    glScalef(3.5, 3.5, 3.5)
    draw_cannon()
    glPopMatrix()

    hud_begin()
    glColor3f(0.08, 0.06, 0.14)
    glBegin(GL_QUADS)
    glVertex2f(0, 0)
    glVertex2f(W, 0)
    glVertex2f(W, H)
    glVertex2f(0, H)
    glEnd()

    cx = W // 2
    cy = H // 2
    glColor3f(0.95, 0.45, 0.12)
    hud_text(cx - 95, cy + 180, "APEX SENTRY")
    glColor3f(0.75, 0.90, 1.0)
    hud_text(cx - 175, cy + 120, "Coastal Defense Simulation")
    glColor3f(1.0, 1.0, 1.0)
    hud_text(cx - 155, cy + 70, "Press SPACE to Deploy Cannon")
    hud_end()

    glutSwapBuffers()


def showScreen():
    if game_state == STATE_MENU:
        draw_menu()
        return

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, W, H)
    setupCamera()

    draw_horizon()
    draw_outpost_props()
    draw_command_pad()
    draw_cannon()

    if mega_shot_ready and not mega_shot_used:
        glPushMatrix()
        glTranslatef(cannon_pos[0], 2.2, cannon_pos[2])
        glColor3f(1.0, 0.65, 0.10)
        draw_solid_sphere(0.32, 10, 10)
        glPopMatrix()

    for e in enemies:
        draw_hostile(e)
    draw_projectiles()

    if game_state == STATE_OVER:
        hud_begin()
        glColor3f(0.04, 0.04, 0.10)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(W, 0)
        glVertex2f(W, H)
        glVertex2f(0, H)
        glEnd()

        cx = W // 2
        cy = H // 2
        game_time = now() - game_start_time
        minutes = int(game_time // 60)
        seconds = int(game_time % 60)
        accuracy = (stats_hits / stats_shots * 100) if stats_shots > 0 else 0.0

        glColor3f(0.95, 0.35, 0.20)
        hud_text(cx - 85, cy + 100, "MISSION FAILED")
        glColor3f(1.0, 1.0, 1.0)
        hud_text(cx - 120, cy + 60, "=== AFTER ACTION ===")
        hud_text(cx - 120, cy + 30, f"Time: {minutes:02d}:{seconds:02d}")
        hud_text(cx - 120, cy + 10, f"Eliminated: {stats_kills}")
        hud_text(cx - 120, cy - 10, f"Rounds: {stats_shots}")
        hud_text(cx - 120, cy - 30, f"Hits: {stats_hits}")
        hud_text(cx - 120, cy - 50, f"Accuracy: {accuracy:.1f}%")
        hud_text(cx - 120, cy - 70, f"Score: {score}")
        hud_text(cx - 120, cy - 100, "R - Retry   ESC - Exit")
        hud_end()
    elif game_state == STATE_PAUSED:
        draw_pause_overlay()

    if game_state == STATE_PLAYING:
        draw_scanner()

    if cam_mode == CAM_FIRST and game_state == STATE_PLAYING:
        draw_fp_scope()

    draw_text(15, H - 35, f"SCORE: {score}")
    draw_text(15, H - 60, f"Lives: {lives}/5   Wave: {wave}")
    draw_text(15, H - 85, "Camera: " + ("FIRST" if cam_mode == CAM_FIRST else "THIRD"))
    draw_text(
        15,
        H - 110,
        "AutoAim(C): "
        + ("ON" if auto_aim else "OFF")
        + "   Rapid(F): "
        + ("ON" if rapid_fire else "OFF"),
    )
    draw_text(15, H - 135, f"FOV(Z/X): {int(fovY)}")
    draw_text(15, H - 160, "Theme: " + ("DUSK" if is_dusk_mode else "DAWN") + " (P)")
    if mega_shot_ready and not mega_shot_used:
        draw_text(15, H - 185, "MEGA SHOT READY (T)")
    elif mega_shot_used:
        draw_text(15, H - 185, "Mega Shot: spent")

    glutSwapBuffers()


def idle():
    global prev_time, sky_drift
    t = now()
    dt = t - prev_time
    prev_time = t
    sky_drift += dt * 0.25

    if game_state == STATE_PLAYING:
        spawn_controller()
        auto_aim_update()
        update_projectiles(dt)
        update_hostiles(dt)
        projectile_hits()

    glutPostRedisplay()


def keyboardListener(key, x, y):
    global cannon_yaw, cannon_pitch, game_state, cam_mode, auto_aim, rapid_fire, fovY
    global cannon_pos, is_dusk_mode, mega_shot_ready, mega_shot_used

    if key == b"\x1b":
        if game_state == STATE_MENU:
            sys.exit(0)
        elif game_state in (STATE_PLAYING, STATE_PAUSED):
            game_state = STATE_MENU
        else:
            sys.exit(0)
        return

    if game_state == STATE_MENU:
        if key == b" ":
            reset_game()
            game_state = STATE_PLAYING
        return

    if game_state == STATE_OVER:
        if key in (b"r", b"R"):
            reset_game()
            game_state = STATE_PLAYING
        return

    if key == b" ":
        if game_state == STATE_PLAYING:
            game_state = STATE_PAUSED
        elif game_state == STATE_PAUSED:
            game_state = STATE_PLAYING

    if key in (b"p", b"P"):
        is_dusk_mode = not is_dusk_mode

    if key in (b"v", b"V"):
        cam_mode = CAM_FIRST if cam_mode == CAM_THIRD else CAM_THIRD

    if key in (b"c", b"C"):
        auto_aim = not auto_aim

    if key in (b"f", b"F"):
        rapid_fire = not rapid_fire

    if key in (b"t", b"T") and game_state == STATE_PLAYING:
        if mega_shot_ready and not mega_shot_used:
            fire_projectile(is_mega=True)

    if key in (b"z", b"Z"):
        fovY = clamp(fovY - 3.0, 25.0, 90.0)
    if key in (b"x", b"X"):
        fovY = clamp(fovY + 3.0, 25.0, 90.0)

    if key in (b"w", b"W"):
        cannon_pos[2] = clamp(cannon_pos[2] - cannon_move_speed, -20.0, 20.0)
    if key in (b"s", b"S"):
        cannon_pos[2] = clamp(cannon_pos[2] + cannon_move_speed, -20.0, 20.0)
    if key in (b"a", b"A"):
        cannon_pos[0] = clamp(cannon_pos[0] - cannon_move_speed, -20.0, 20.0)
    if key in (b"d", b"D"):
        cannon_pos[0] = clamp(cannon_pos[0] + cannon_move_speed, -20.0, 20.0)

    if key in (b"i", b"I"):
        cannon_pitch = clamp(cannon_pitch + 2.0, cannon_pitch_min, cannon_pitch_max)
    if key in (b"k", b"K"):
        cannon_pitch = clamp(cannon_pitch - 2.0, cannon_pitch_min, cannon_pitch_max)

    if key in (b"j", b"J"):
        cannon_yaw = (cannon_yaw + 3.0) % 360.0
    if key in (b"l", b"L"):
        cannon_yaw = (cannon_yaw - 3.0) % 360.0


def specialKeyListener(key, x, y):
    global cam_orbit_x, cam_orbit_y
    if cam_mode != CAM_THIRD:
        return
    if key == GLUT_KEY_LEFT:
        cam_orbit_x += 4.0
    if key == GLUT_KEY_RIGHT:
        cam_orbit_x -= 4.0
    if key == GLUT_KEY_UP:
        cam_orbit_y = clamp(cam_orbit_y + 3.0, -5.0, 70.0)
    if key == GLUT_KEY_DOWN:
        cam_orbit_y = clamp(cam_orbit_y - 3.0, -5.0, 70.0)


def mouseListener(button, state, x, y):
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if game_state == STATE_PLAYING:
            fire_projectile(is_mega=False)


def reset_game():
    global lives, score, wave, enemies, projectiles
    global cannon_yaw, cannon_pitch, cam_mode, cam_orbit_x, cam_orbit_y, cam_dist, fovY
    global auto_aim, rapid_fire, last_spawn_time, last_fire_time, difficulty_start_time
    global stats_shots, stats_hits, stats_kills, game_start_time
    global pad_shake, pad_flash, pad_hit_time
    global cannon_pos, mega_shot_ready, mega_shot_used, last_wave_for_mega, mega_projectiles

    lives = 5
    score = 0
    wave = 1
    enemies[:] = []
    projectiles[:] = []
    mega_projectiles[:] = []

    cannon_yaw = 0.0
    cannon_pitch = 12.0
    cannon_pos = [0.0, 0.0, 0.0]

    cam_mode = CAM_THIRD
    cam_orbit_x, cam_orbit_y, cam_dist = 35.0, 22.0, 13.0
    fovY = 58.0

    auto_aim = False
    rapid_fire = False

    last_spawn_time = now()
    last_fire_time = 0.0
    difficulty_start_time = now()
    game_start_time = now()

    stats_shots = 0
    stats_hits = 0
    stats_kills = 0

    pad_shake = [0.0, 0.0, 0.0]
    pad_flash = 0.0
    pad_hit_time = 0.0

    mega_shot_ready = False
    mega_shot_used = False
    last_wave_for_mega = 0


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(W, H)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"ApexSentry - Coastal Defense")

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    reset_game()
    glutMainLoop()


if __name__ == "__main__":
    main()
