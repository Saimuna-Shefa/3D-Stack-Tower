"""
3D Stack Tower (Python + PyOpenGL + pygame)

Install:  pip install pygame PyOpenGL
Run:      python stack_3d.py

How to play
  A block slides back and forth above the tower. Drop it so it lands on the
  block below. Any part that hangs over is cut off and falls away, so the
  tower gets thinner. Land it almost perfectly to keep the full size.
  Miss completely and the game is over.

Controls
  SPACE / Left click : drop the block
  R                  : restart
  ESC                : quit
"""
import math
import colorsys
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

START_SIZE = 6.0       # width of the first block
RANGE = 11.0           # how far the moving block slides each way
PERFECT_TOL = 0.25     # drop closer than this = perfect (snaps in place)

# ---------- box drawing ----------
FACES = [
    ((0, 0, 1),  [(-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]),
    ((0, 0, -1), [(-.5, -.5, -.5), (-.5, .5, -.5), (.5, .5, -.5), (.5, -.5, -.5)]),
    ((0, 1, 0),  [(-.5, .5, -.5), (-.5, .5, .5), (.5, .5, .5), (.5, .5, -.5)]),
    ((0, -1, 0), [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, -.5, .5), (-.5, -.5, .5)]),
    ((1, 0, 0),  [(.5, -.5, -.5), (.5, .5, -.5), (.5, .5, .5), (.5, -.5, .5)]),
    ((-1, 0, 0), [(-.5, -.5, -.5), (-.5, -.5, .5), (-.5, .5, .5), (-.5, .5, -.5)]),
]

def draw_box(x, y, z, sx, sy, sz, color):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    glColor3f(*color)
    glBegin(GL_QUADS)
    for normal, corners in FACES:
        glNormal3f(*normal)
        for c in corners:
            glVertex3f(*c)
    glEnd()
    glPopMatrix()

def level_color(level, bright=0.0):
    h = (0.55 + level * 0.035) % 1.0
    return colorsys.hsv_to_rgb(h, max(0.0, 0.6 - bright), min(1.0, 0.85 + bright))

# ---------- game state ----------
class Game:
    def __init__(self):
        self.best = 0
        self.reset()

    def reset(self):
        # each layer: center x/z and size sx/sz. Layer i sits at height i.
        self.layers = [dict(x=0.0, z=0.0, sx=START_SIZE, sz=START_SIZE)]
        self.debris = []
        self.score = 0
        self.combo = 0
        self.flash = 0.0
        self.over = False
        self.spawn()

    def spawn(self):
        n = len(self.layers)
        self.axis = "x" if n % 2 == 1 else "z"   # alternate direction
        self.pos = -RANGE
        self.dir = 1
        self.speed = min(16.0, 6.0 + n * 0.3)    # gets faster as you climb

    def current(self):
        """The block that is currently sliding."""
        prev = self.layers[-1]
        if self.axis == "x":
            return dict(x=self.pos, z=prev["z"], sx=prev["sx"], sz=prev["sz"])
        return dict(x=prev["x"], z=self.pos, sx=prev["sx"], sz=prev["sz"])

    def drop(self):
        if self.over:
            return
        prev = self.layers[-1]
        cur = self.current()
        level = len(self.layers)

        if self.axis == "x":
            c, s, pc, ps = cur["x"], cur["sx"], prev["x"], prev["sx"]
        else:
            c, s, pc, ps = cur["z"], cur["sz"], prev["z"], prev["sz"]

        lo = max(c - s / 2, pc - ps / 2)
        hi = min(c + s / 2, pc + ps / 2)
        overlap = hi - lo

        if overlap <= 0:
            # complete miss: the whole block falls and the game ends
            self.add_debris(cur, level)
            self.over = True
            self.best = max(self.best, self.score)
            return

        delta = c - pc
        if abs(delta) < PERFECT_TOL:
            new_c, new_s = pc, ps          # perfect: snap, no cutting
            self.combo += 1
            self.flash = 0.35
        else:
            self.combo = 0
            new_c, new_s = (lo + hi) / 2, overlap
            # the overhanging piece falls off
            cur_min, cur_max = c - s / 2, c + s / 2
            d_lo, d_hi = (hi, cur_max) if delta > 0 else (cur_min, lo)
            piece = dict(cur)
            if self.axis == "x":
                piece["x"], piece["sx"] = (d_lo + d_hi) / 2, d_hi - d_lo
            else:
                piece["z"], piece["sz"] = (d_lo + d_hi) / 2, d_hi - d_lo
            self.add_debris(piece, level)

        if self.axis == "x":
            layer = dict(x=new_c, z=prev["z"], sx=new_s, sz=prev["sz"])
        else:
            layer = dict(x=prev["x"], z=new_c, sx=prev["sx"], sz=new_s)
        self.layers.append(layer)
        self.score += 1
        self.best = max(self.best, self.score)
        self.spawn()

    def add_debris(self, block, level):
        self.debris.append(dict(block, y=level + 0.5, vy=0.0, level=level))

    def update(self, dt):
        if not self.over:
            self.pos += self.dir * self.speed * dt
            if self.pos > RANGE:
                self.pos, self.dir = RANGE, -1
            elif self.pos < -RANGE:
                self.pos, self.dir = -RANGE, 1
        self.flash = max(0.0, self.flash - dt)
        for d in self.debris:
            d["vy"] -= 25 * dt
            d["y"] += d["vy"] * dt
        self.debris = [d for d in self.debris if d["y"] > -40]

# ---------- drawing ----------
def draw_game(game):
    # pillar under the first block so the tower looks like it stands on something
    draw_box(0, -5.5, 0, START_SIZE, 10, START_SIZE, (0.12, 0.12, 0.18))

    top = len(game.layers) - 1
    for i, L in enumerate(game.layers):
        bright = 0.25 if (i == top and game.flash > 0) else 0.0
        draw_box(L["x"], i + 0.5, L["z"], L["sx"], 0.96, L["sz"], level_color(i, bright))

    if not game.over:
        c = game.current()
        n = len(game.layers)
        draw_box(c["x"], n + 0.5, c["z"], c["sx"], 0.96, c["sz"], level_color(n))

    for d in game.debris:
        draw_box(d["x"], d["y"], d["z"], d["sx"], 0.96, d["sz"], level_color(d["level"]))

# ---------- main ----------
def main():
    pygame.init()
    W, H = 1000, 700
    pygame.display.set_mode((W, H), DOUBLEBUF | OPENGL)
    clock = pygame.time.Clock()

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_NORMALIZE)
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.45, 0.45, 0.45, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.9, 0.9, 0.9, 1))

    glMatrixMode(GL_PROJECTION)
    gluPerspective(50, W / H, 0.1, 300)
    glMatrixMode(GL_MODELVIEW)

    game = Game()
    cam_y = 1.0

    running = True
    while running:
        dt = min(clock.tick(60) / 1000, 0.05)

        for e in pygame.event.get():
            if e.type == QUIT:
                running = False
            elif e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    running = False
                elif e.key == K_r:
                    game.reset()
                elif e.key == K_SPACE:
                    game.drop()
            elif e.type == MOUSEBUTTONDOWN and e.button == 1:
                game.drop()

        game.update(dt)

        # camera climbs smoothly with the tower
        cam_y += (len(game.layers) - cam_y) * min(1.0, 3 * dt)

        # background color slowly shifts as you go higher
        bg = colorsys.hsv_to_rgb((0.6 + len(game.layers) * 0.01) % 1.0, 0.6, 0.12)
        glClearColor(*bg, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(17, cam_y + 15, 17,   0, cam_y, 0,   0, 1, 0)
        glLightfv(GL_LIGHT0, GL_POSITION, (10, cam_y + 30, 10, 1))

        draw_game(game)

        status = "GAME OVER - press R" if game.over else "SPACE to drop"
        combo = f" | Perfect x{game.combo}" if game.combo > 1 else ""
        pygame.display.set_caption(
            f"3D Stack | Score: {game.score} | Best: {game.best}{combo} | {status}")
        pygame.display.flip()

    pygame.quit()

main()