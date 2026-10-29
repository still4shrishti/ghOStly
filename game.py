
import os, sys, math, random, time, ctypes
import numpy as np
import cv2
import mss
import pygame


MAX_MONSTERS = 30
MONSTER_HP = 3
HERO_SPEED = 280
HERO_HP = 5
ORB_SPEED = 900
FIRE_DELAY = 0.13
GHOST_W, GHOST_H = 300, 360
HOLE_COLOR = (12, 6, 18)

BASE = os.path.dirname(os.path.abspath(__file__))


# ---------------- sound helpers ----------------
def load_sound(name, volume=1.0):
    """Looks for name.mp3 / name.wav / name.ogg next to this file."""
    for ext in (".mp3", ".wav", ".ogg"):
        path = os.path.join(BASE, name + ext)
        if os.path.exists(path):
            try:
                s = pygame.mixer.Sound(path)
                s.set_volume(volume)
                return s
            except Exception as e:
                print(f"Could not load {path}: {e}")
    print(f"[sound] {name} not found - playing without it")
    return None


def play(snd):
    if snd:
        snd.play()


def start_music(name="bgm", volume=0.4):
    for ext in (".mp3", ".wav", ".ogg"):
        path = os.path.join(BASE, name + ext)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(volume)
                pygame.mixer.music.play(-1)  # loop forever
            except Exception as e:
                print(f"Could not play music: {e}")
            return


# ---------------- windows helpers ----------------
def make_dpi_aware():
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def set_topmost():
    """Keep the small ghost window above all other windows (Windows only)."""
    if sys.platform == "win32":
        try:
            hwnd = pygame.display.get_wm_info()["window"]
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
        except Exception:
            pass


# ---------------- 1. GHOST MENU ----------------
def draw_ghost(surf, cx, cy, t):
    glow = pygame.Surface((220, 220), pygame.SRCALPHA)
    for r in range(100, 0, -10):
        pygame.draw.circle(glow, (150, 255, 220, 6), (110, 110), r)
    surf.blit(glow, (cx - 110, cy - 110))
    body = (225, 255, 245)
    pygame.draw.circle(surf, body, (cx, cy - 15), 45)
    pygame.draw.rect(surf, body, (cx - 45, cy - 15, 90, 55))
    for i in range(4):  # wavy bottom
        off = math.sin(t * 6 + i) * 4
        pygame.draw.circle(surf, body, (int(cx - 34 + i * 23), int(cy + 40 + off)), 12)
    pygame.draw.circle(surf, (20, 20, 40), (cx - 16, cy - 20), 7)
    pygame.draw.circle(surf, (20, 20, 40), (cx + 16, cy - 20), 7)
    pygame.draw.ellipse(surf, (20, 20, 40), (cx - 8, cy - 2, 16, 20))


def ghost_menu():
    screen = pygame.display.set_mode((GHOST_W, GHOST_H))
    pygame.display.set_caption("Boo...")
    set_topmost()
    font = pygame.font.SysFont("consolas", 18, bold=True)
    big = pygame.font.SysFont("consolas", 28, bold=True)
    btn = pygame.Rect(GHOST_W // 2 - 70, GHOST_H - 70, 140, 46)
    clock = pygame.time.Clock()
    while True:
        t = time.time()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and btn.collidepoint(e.pos):
                return
        screen.fill((10, 8, 20))
        draw_ghost(screen, GHOST_W // 2, 130 + int(math.sin(t * 2) * 8), t)
        txt = font.render("Go to any screen...", True, (190, 255, 230))
        screen.blit(txt, txt.get_rect(center=(GHOST_W // 2, 235)))
        hover = btn.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (200, 40, 60) if hover else (140, 20, 40), btn, border_radius=10)
        s = big.render("START", True, (255, 255, 255))
        screen.blit(s, s.get_rect(center=btn.center))
        pygame.display.flip()
        clock.tick(60)


# ---------------- 2. SCREENSHOT -> MONSTER BOXES ----------------
def grab_screen():
    with mss.mss() as sct:
        mon = sct.monitors[1]
        shot = sct.grab(mon)
    bgr = np.array(shot)[:, :, :3]          # BGRA -> BGR
    return bgr, shot.width, shot.height


def find_blobs(bgr, w, h):
    """Find icon / text shaped blobs using edges + dilation."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 160)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (23, 9))
    edges = cv2.dilate(edges, kernel, iterations=1)  # merges letters into words
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in cnts:
        x, y, bw, bh = cv2.boundingRect(c)
        if bw < 24 or bh < 16:
            continue
        if bw > 420 or bh > 260:
            continue
        boxes.append((x, y, bw, bh))
    random.shuffle(boxes)
    boxes = boxes[:MAX_MONSTERS]
    # fallback: empty desktop -> random chunks so the game still works
    while len(boxes) < 6:
        bw, bh = random.randint(60, 140), random.randint(40, 100)
        boxes.append((random.randint(0, w - bw), random.randint(0, h - bh), bw, bh))
    return boxes


def make_monster_img(img):
    """Use the exact captured desktop crop; don't redraw or distort the icon."""
    return img.copy()


# ---------------- 3. GAME OBJECTS ----------------
class Monster:
    def __init__(self, original, rect, now):
        self.orig = original
        self.img = make_monster_img(original)
        self.home = pygame.Rect(rect)
        self.pos = pygame.Vector2(self.home.center)
        self.hp = MONSTER_HP
        self.speed = random.uniform(45, 95)
        self.phase = random.random() * 6.28
        self.wake_at = now + random.uniform(1.5, 5.0)
        self.flash = 0.0
        self.woke = False          # for the wake sound (plays once)

    def awake(self, now):
        return now >= self.wake_at

    def hitbox(self):
        w, h = self.img.get_size()
        r = pygame.Rect(0, 0, int(w * 0.7), int(h * 0.7))
        r.center = self.pos
        return r

    def update(self, dt, now, hero_pos):
        self.flash = max(0, self.flash - dt)
        if self.awake(now):
            d = hero_pos - self.pos
            if d.length() > 1:
                self.pos += d.normalize() * self.speed * dt

    def draw(self, screen, now):
        jitter = pygame.Vector2(0, 0)
        if not self.awake(now):   # about to wake up -> twitch
            if self.wake_at - now < 1.2:
                jitter = pygame.Vector2(random.uniform(-2, 2), random.uniform(-2, 2))
            img = self.orig if self.wake_at - now > 0.6 else self.img
            screen.blit(img, img.get_rect(center=self.pos + jitter))
            return
        ang = math.sin(now * 5 + self.phase) * 8
        sc = 1 + math.sin(now * 7 + self.phase) * 0.06
        img = pygame.transform.rotozoom(self.img, ang, sc)
        if self.flash > 0:
            white = pygame.Surface(img.get_size()); white.fill((120, 120, 120))
            img.blit(white, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        screen.blit(img, img.get_rect(center=self.pos))


class FinalBoss:
    """Two-legged desktop beast with two arms; the original icons form its hide."""
    def __init__(self, fragments, w, h):
        self.pos = pygame.Vector2(w / 2, h / 2)
        self.w, self.h = w, h
        self.radius = max(105, min(w, h) * 0.17)
        self.max_hp = 65
        self.hp = self.max_hp
        self.speed = 118
        self.flash = 0.0
        self.phase = random.random() * math.tau
        self.fragments = fragments[:]
        self.attack_clock = 0.0

    def hit_test(self, point, projectile_radius=12):
        # Point hit test kept for compatibility with other game objects.
        dx = (point[0] - self.pos.x) / (self.radius * 0.92 + projectile_radius)
        dy = (point[1] - (self.pos.y - self.radius * 0.05)) / (self.radius * 1.05 + projectile_radius)
        return dx * dx + dy * dy <= 1.0

    def hit_segment(self, start, end, projectile_radius=10):
        # Swept collision: checks the whole bullet path between frames, not just
        # the final point, so fast bullets cannot pass through the moving boss.
        rx = self.radius * 0.92 + projectile_radius
        ry = self.radius * 1.05 + projectile_radius
        cx, cy = self.pos.x, self.pos.y - self.radius * 0.05
        ax = (start.x - cx) / rx
        ay = (start.y - cy) / ry
        bx = (end.x - cx) / rx
        by = (end.y - cy) / ry
        vx, vy = bx - ax, by - ay
        denom = vx * vx + vy * vy
        if denom <= 1e-9:
            t = 0.0
        else:
            t = max(0.0, min(1.0, -(ax * vx + ay * vy) / denom))
        px, py = ax + t * vx, ay + t * vy
        return px * px + py * py <= 1.0

    def hitbox(self):
        r = self.radius * 0.9
        return pygame.Rect(int(self.pos.x-r), int(self.pos.y-r), int(r*2), int(r*2))

    def update(self, dt, hero_pos):
        self.flash = max(0.0, self.flash - dt)
        d = hero_pos - self.pos
        if d.length() > 1:
            self.pos += d.normalize() * self.speed * dt
        self.attack_clock += dt

    def draw(self, screen, now):
        # A towering humanoid beast, not a circular blob. Limbs animate independently.
        x, y = self.pos.x, self.pos.y
        r = self.radius
        bob = math.sin(now * 5.5 + self.phase) * r * 0.035
        stride = math.sin(now * 7.0 + self.phase) * r * 0.10
        I = int
        # Ground shadow
        shadow = pygame.Surface((I(r*2.2), I(r*.48)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 145), shadow.get_rect())
        screen.blit(shadow, shadow.get_rect(center=(I(x), I(y+r*.78))))

        # Two separate legs and clawed feet
        for side, swing in ((-1, stride), (1, -stride)):
            hip = (I(x + side*r*.28), I(y+r*.30+bob))
            knee = (I(x + side*r*.34+swing*.35), I(y+r*.67+bob))
            ankle = (I(x + side*r*.38+swing), I(y+r*.91))
            pygame.draw.line(screen, (43, 12, 23), hip, knee, max(8, I(r*.22)))
            pygame.draw.line(screen, (95, 22, 37), knee, ankle, max(7, I(r*.17)))
            pygame.draw.circle(screen, (125, 28, 43), knee, max(5, I(r*.10)))
            foot = [(ankle[0]-I(r*.13), ankle[1]-I(r*.03)), (ankle[0]+I(r*.12), ankle[1]-I(r*.04)),
                    (ankle[0]+I(r*.24), ankle[1]+I(r*.05)), (ankle[0]+I(r*.08), ankle[1]+I(r*.09)),
                    (ankle[0]-I(r*.18), ankle[1]+I(r*.08))]
            pygame.draw.polygon(screen, (38, 8, 17), foot)
            for claw in range(3):
                cx = ankle[0] + I((claw-1)*r*.10)
                pygame.draw.line(screen, (220, 190, 170), (cx, ankle[1]+I(r*.05)), (cx+I(r*.035), ankle[1]+I(r*.13)), max(2, I(r*.018)))

        # Long arms reaching outward, ending in hooked claws
        for side in (-1, 1):
            shoulder = (I(x + side*r*.52), I(y-r*.20+bob))
            elbow = (I(x + side*r*.82), I(y+r*.02 + math.sin(now*4+side)*r*.06))
            wrist = (I(x + side*r*.91), I(y+r*.31 + math.sin(now*5+side)*r*.05))
            pygame.draw.line(screen, (48, 9, 24), shoulder, elbow, max(9, I(r*.20)))
            pygame.draw.line(screen, (115, 24, 40), elbow, wrist, max(7, I(r*.14)))
            pygame.draw.circle(screen, (145, 32, 46), elbow, max(5, I(r*.10)))
            pygame.draw.circle(screen, (70, 9, 20), wrist, max(6, I(r*.09)))
            for claw in range(3):
                startp = (wrist[0]+I(side*claw*r*.025), wrist[1]+I(claw*r*.025))
                endp = (wrist[0]+I(side*(.11+claw*.025)*r), wrist[1]+I((.12+claw*.025)*r))
                pygame.draw.line(screen, (225, 205, 180), startp, endp, max(2, I(r*.025)))

        # Muscular torso with jagged silhouette
        torso = [(I(x-r*.43), I(y-r*.35+bob)), (I(x-r*.30), I(y-r*.58+bob)),
                 (I(x-r*.12), I(y-r*.66+bob)), (I(x+r*.13), I(y-r*.63+bob)),
                 (I(x+r*.34), I(y-r*.48+bob)), (I(x+r*.43), I(y+r*.20+bob)),
                 (I(x+r*.25), I(y+r*.43+bob)), (I(x-r*.27), I(y+r*.42+bob)),
                 (I(x-r*.43), I(y+r*.12+bob))]
        pygame.draw.polygon(screen, (42, 7, 21), torso)
        pygame.draw.polygon(screen, (120, 23, 43), torso, max(3, I(r*.035)))
        # Desktop icons remain recognizable as embedded plates across the beast's chest.
        for i, original in enumerate(self.fragments[:7]):
            iw = max(18, I(r*.28)); ih = max(16, I(r*.20))
            tile = pygame.transform.smoothscale(original, (iw, ih))
            tint = pygame.Surface((iw, ih), pygame.SRCALPHA); tint.fill((95, 0, 20, 48)); tile.blit(tint, (0, 0))
            col = i % 3; row = i // 3
            tx = I(x + (col-1)*r*.25 - iw/2)
            ty = I(y - r*.25 + row*r*.22 + bob - ih/2)
            screen.blit(tile, (tx, ty))
            pygame.draw.rect(screen, (220, 40, 55), (tx, ty, iw, ih), max(1, I(r*.008)))

        # Neck and beast head
        neck = pygame.Rect(I(x-r*.20), I(y-r*.72+bob), I(r*.40), I(r*.24))
        pygame.draw.rect(screen, (70, 12, 29), neck, border_radius=max(4, I(r*.06)))
        head_y = y-r*.82+bob
        head = [(I(x-r*.32), I(head_y+r*.05)), (I(x-r*.28), I(head_y-r*.16)),
                (I(x-r*.10), I(head_y-r*.30)), (I(x+r*.13), I(head_y-r*.26)),
                (I(x+r*.32), I(head_y-r*.04)), (I(x+r*.27), I(head_y+r*.20)),
                (I(x+r*.12), I(head_y+r*.33)), (I(x-r*.13), I(head_y+r*.30)),
                (I(x-r*.30), I(head_y+r*.16))]
        pygame.draw.polygon(screen, (65, 9, 25), head)
        pygame.draw.polygon(screen, (165, 34, 49), head, max(3, I(r*.025)))
        # Horns
        pygame.draw.polygon(screen, (30, 7, 15), [(I(x-r*.24), I(head_y-r*.08)), (I(x-r*.42), I(head_y-r*.40)), (I(x-r*.12), I(head_y-r*.22))])
        pygame.draw.polygon(screen, (30, 7, 15), [(I(x+r*.20), I(head_y-r*.12)), (I(x+r*.40), I(head_y-r*.42)), (I(x+r*.12), I(head_y-r*.23))])
        # Eyes, muzzle and teeth
        for ex in (x-r*.13, x+r*.13):
            pygame.draw.ellipse(screen, (255, 30, 15), (I(ex-r*.065), I(head_y-r*.02), I(r*.13), I(r*.075)))
            pygame.draw.circle(screen, (255, 235, 170), (I(ex), I(head_y+r*.015)), max(2, I(r*.018)))
        muzzle = [(I(x-r*.18), I(head_y+r*.13)), (I(x), I(head_y+r*.08)), (I(x+r*.18), I(head_y+r*.13)), (I(x+r*.10), I(head_y+r*.25)), (I(x-r*.10), I(head_y+r*.25))]
        pygame.draw.polygon(screen, (12, 2, 8), muzzle)
        for tooth in range(5):
            tx = I(x-r*.12+tooth*r*.06)
            pygame.draw.polygon(screen, (245, 225, 205), [(tx, I(head_y+r*.14)), (tx+I(r*.035), I(head_y+r*.14)), (tx+I(r*.018), I(head_y+r*.21))])

        if self.flash > 0:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (255, 255, 255, 65), (I(x), I(y)), I(r*.9))
            screen.blit(overlay, (0, 0))

    def draw_health(self, screen, font):
        bar_w = min(620, self.w - 80)
        bar_h = 24
        x = (self.w - bar_w) // 2
        y = 58
        pygame.draw.rect(screen, (30, 0, 10), (x, y, bar_w, bar_h), border_radius=8)
        fill_w = int(bar_w * max(0, self.hp) / self.max_hp)
        if fill_w > 0:
            pygame.draw.rect(screen, (220, 20, 45), (x, y, fill_w, bar_h), border_radius=8)
        pygame.draw.rect(screen, (255, 210, 210), (x, y, bar_w, bar_h), 2, border_radius=8)
        label = font.render("THE DESKTOP BEAST", True, (255, 225, 225))
        screen.blit(label, label.get_rect(center=(self.w // 2, y - 17)))


class Orb:
    def __init__(self, pos, direction):
        self.pos = pygame.Vector2(pos)
        self.vel = direction * ORB_SPEED
        self.life = 1.8
        self.radius = 10
        self.previous = self.pos.copy()

    def update(self, dt):
        self.previous = self.pos.copy()
        self.pos += self.vel * dt
        self.life -= dt

    def draw(self, screen):
        p = (int(self.pos.x), int(self.pos.y))
        prev = (int(self.previous.x), int(self.previous.y))
        pygame.draw.line(screen, (35, 105, 190), prev, p, 8)
        pygame.draw.line(screen, (105, 220, 255), prev, p, 4)
        pygame.draw.circle(screen, (45, 150, 255), p, self.radius + 3)
        pygame.draw.circle(screen, (225, 250, 255), p, self.radius)
        pygame.draw.circle(screen, (255, 255, 255), p, 4)


class Spark:
    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        a = random.uniform(0, 6.28)
        self.vel = pygame.Vector2(math.cos(a), math.sin(a)) * random.uniform(60, 260)
        self.life = random.uniform(0.3, 0.8)

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt

    def draw(self, screen):
        pygame.draw.circle(screen, (180, 240, 255), (int(self.pos.x), int(self.pos.y)), 3)


def make_vignette(w, h):
    small = pygame.Surface((w // 8, h // 8), pygame.SRCALPHA)
    sw, sh = small.get_size()
    for y in range(sh):
        for x in range(sw):
            dx, dy = (x - sw / 2) / (sw / 2), (y - sh / 2) / (sh / 2)
            a = min(1.0, (dx * dx + dy * dy) ** 0.5)
            small.set_at((x, y), (0, 0, 15, int(40 + 150 * a * a)))
    return pygame.transform.smoothscale(small, (w, h))


def make_glow(radius):
    g = pygame.Surface((radius * 2, radius * 2))
    for r in range(radius, 0, -6):
        c = int(60 * (1 - r / radius))
        pygame.draw.circle(g, (c, c, int(c * 1.3)), (radius, radius), r)
    return g


# ---------------- HERO DRAWING ----------------
def draw_hero(screen, pos, aim, now, moving, s=1.6, red=0.0, look=None):
    """Little Exorcist: purple hat, blue cloak, walking legs, glowing lantern."""
    x, y = pos.x, pos.y
    I = int
    bob = math.sin(now * 12) * 2 * s if moving else math.sin(now * 3) * 1.2 * s
    swing = math.sin(now * 12) * 6 * s if moving else 0

    # shadow
    sh = pygame.Surface((I(36 * s), I(12 * s)), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 110), sh.get_rect())
    screen.blit(sh, sh.get_rect(center=(I(x), I(y + 19 * s))))

    # legs + boots
    for side, sw in ((-1, swing), (1, -swing)):
        hip = (x + side * 4 * s, y + 8 * s + bob / 2)
        foot = (x + side * 4 * s + sw, y + 18 * s)
        pygame.draw.line(screen, (40, 30, 70), hip, foot, I(4 * s))
        pygame.draw.circle(screen, (25, 18, 40), (I(foot[0]), I(foot[1])), I(3 * s))

    # cloak
    cloak = [(x - 12 * s, y + 13 * s + bob), (x + 12 * s, y + 13 * s + bob),
             (x + 7 * s, y - 8 * s + bob), (x - 7 * s, y - 8 * s + bob)]
    pygame.draw.polygon(screen, (55, 95, 200), cloak)
    pygame.draw.polygon(screen, (140, 190, 255), cloak, max(1, I(1.5 * s)))
    pygame.draw.line(screen, (255, 220, 120),                      # golden belt
                     (x - 9 * s, y + 3 * s + bob), (x + 9 * s, y + 3 * s + bob), I(2.5 * s))

    # head
    hy = y - 16 * s + bob
    pygame.draw.circle(screen, (255, 222, 190), (I(x), I(hy)), I(9 * s))
    # eyes look toward the aim direction (or straight at the viewer when `look` is given)
    gaze = look if look is not None else aim
    sclera = (255, I(255 - 215 * red), I(255 - 215 * red))
    pupil = (I(10 + 50 * red), I(10 * (1 - red)), I(30 * (1 - red)))
    for dx in (-3.5, 3.5):
        ex, ey = x + dx * s, hy + 1 * s
        if red > 0.05:                                   # red glow around the eyes
            g = pygame.Surface((I(40 * s), I(40 * s)), pygame.SRCALPHA)
            for r in range(I(18 * s), 0, -3):
                pygame.draw.circle(g, (255, 0, 0, I(8 + 16 * red)), (I(20 * s), I(20 * s)), r)
            screen.blit(g, g.get_rect(center=(I(ex), I(ey))))
        pygame.draw.circle(screen, sclera, (I(ex), I(ey)), I(2.8 * s))
        pygame.draw.circle(screen, pupil,
                           (I(ex + gaze.x * 1.4 * s), I(ey + gaze.y * 1.2 * s)), I(1.4 * s))
    # pointed hat with star
    hat = [(x - 12 * s, hy - 4 * s), (x + 12 * s, hy - 4 * s), (x + 3 * s, hy - 26 * s)]
    pygame.draw.polygon(screen, (115, 60, 190), hat)
    pygame.draw.line(screen, (80, 40, 150),
                     (x - 13 * s, hy - 4 * s), (x + 13 * s, hy - 4 * s), I(3 * s))
    pygame.draw.circle(screen, (255, 235, 120), (I(x + 1 * s), I(hy - 12 * s)), I(2 * s))

    # arm + lantern pointing at the mouse
    shoulder = pygame.Vector2(x, y - 4 * s + bob)
    hand = shoulder + aim * 17 * s
    pygame.draw.line(screen, (255, 222, 190), shoulder, hand, I(4 * s))
    lan = hand + aim * 7 * s
    halo = pygame.Surface((I(70 * s), I(70 * s)), pygame.SRCALPHA)
    for r in range(I(34 * s), 0, -4):
        pygame.draw.circle(halo, (255, 220, 100, 14), (I(35 * s), I(35 * s)), r)
    screen.blit(halo, halo.get_rect(center=(I(lan.x), I(lan.y))))
    frame = pygame.Rect(0, 0, I(11 * s), I(15 * s)); frame.center = (I(lan.x), I(lan.y))
    pygame.draw.rect(screen, (255, 235, 140), frame.inflate(-4, -4))
    pygame.draw.rect(screen, (150, 100, 40), frame, max(1, I(1.8 * s)))
    pygame.draw.line(screen, (150, 100, 40), (frame.centerx, frame.top),
                     (frame.centerx, frame.top - I(4 * s)), 2)


# ---------------- ENDING SEQUENCE ----------------
def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def fade(e, t0, t1, d=0.6):
    """Opacity curve 0 -> 1 -> 0 between time t0 and t1."""
    return max(0.0, min(smooth((e - t0) / d), smooth((t1 - e) / d)))


def draw_story_text(screen, font, text, alpha, w, h):
    surf = font.render(text, True, (235, 235, 235))
    band = pygame.Surface((w, surf.get_height() + 50), pygame.SRCALPHA)
    band.fill((0, 0, 0, int(170 * alpha)))
    screen.blit(band, (0, h // 2 - band.get_height() // 2))
    surf.set_alpha(int(255 * alpha))
    screen.blit(surf, surf.get_rect(center=(w // 2, h // 2)))


_ending_once = {"black": False}


def on_black_screen():
    """Called ONCE, the moment the screen turns black at the very end.

    >>> PUT YOUR SUSPENSE SOUND HERE. Example:
            snd = load_sound("suspense")    # looks for suspense.mp3 next to this file
            play(snd)
    """
    pass


def run_ending(screen, bg, hero0, sparks, vignette, story, e, w, h):
    """Draws one frame of the ending. e = seconds since the last monster died.
    Returns True when the ending is over (the program should close)."""
    now = time.time()
    I = int
    screen.blit(bg, (0, 0))
    for sp in sparks:
        sp.draw(screen)
    screen.blit(vignette, (0, 0))

    # 1) story text
    a1 = fade(e, 1.0, 4.0)
    if a1 > 0:
        draw_story_text(screen, story, "You killed all these monsters...", a1, w, h)
    a2 = fade(e, 4.5, 8.0)
    if a2 > 0:
        draw_story_text(screen, story, "But how will you kill the monster inside you?", a2, w, h)

    # 2) the room gets dark
    dark = smooth((e - 8.0) / 2.5)
    if dark > 0:
        ov = pygame.Surface((w, h)); ov.set_alpha(I(215 * dark)); ov.fill((0, 0, 0))
        screen.blit(ov, (0, 0))

    # 3) the hero walks to the middle, grows, stares at YOU, eyes turn red
    k = smooth((e - 8.0) / 2.5)
    s_end = h / 130
    end_pos = pygame.Vector2(w / 2, h * 0.45 + 16 * s_end)
    pos = hero0.lerp(end_pos, k)
    s = 1.6 + (s_end - 1.6) * k
    red = smooth((e - 10.5) / 3.0)
    if e >= 13.5:                                            # trembling
        pos = pos + pygame.Vector2(random.uniform(-4, 4), random.uniform(-4, 4))
    aim = pygame.Vector2(0.35, 0.9).normalize()
    draw_hero(screen, pos, aim, now, 0 < k < 1, s, red, pygame.Vector2(0, 0))
    lan = pygame.Vector2(pos.x, pos.y - 4 * s) + aim * 24 * s   # lantern position

    # 4) he shoots at you -> white flash -> black
    if 15.0 <= e < 15.6:
        r = I((e - 15.0) * 2.4 * max(w, h))
        pygame.draw.circle(screen, (255, 235, 235), (I(lan.x), I(lan.y)), r)
    if e >= 15.6:
        screen.fill((0, 0, 0))
        if not _ending_once["black"]:
            _ending_once["black"] = True
            on_black_screen()
    return e >= 19.0


# ---------------- 4. MAIN GAME ----------------
def run_game(bgr, w, h):
    screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)      # we draw our own crosshair
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    bg = pygame.image.frombuffer(rgb.tobytes(), (w, h), "RGB").convert()

    # sounds
    snd_wake = load_sound("wake", 0.5)
    snd_purify = load_sound("purify", 0.8)
    snd_hurt = load_sound("hurt", 1.0)
    snd_shoot = load_sound("shoot", 0.4)
    snd_lose = load_sound("lose", 1.0)    # optional extras
    start_music("bgm", 0.4)

    now = time.time()
    monsters = []
    for r in find_blobs(bgr, w, h):
        crop = bg.subsurface(pygame.Rect(r)).copy()
        monsters.append(Monster(crop, r, now))
    icon_fragments = [(m.orig.copy(), m.home.copy()) for m in monsters]
    for m in monsters:                       # leave dark holes behind
        bg.fill(HOLE_COLOR, m.home)

    hero = pygame.Vector2(w / 2, h / 2)
    hero_hp, invul, last_shot = HERO_HP, 0.0, 0.0
    orbs, sparks = [], []
    vignette, glow = make_vignette(w, h), make_glow(180)
    font = pygame.font.SysFont("consolas", 26, bold=True)
    huge = pygame.font.SysFont("consolas", 80, bold=True)
    story = pygame.font.SysFont("consolas", max(26, h // 24), bold=True)
    total = len(monsters)
    state = "play"
    respawn_start = 0.0
    boss = None
    boss_font = pygame.font.SysFont("consolas", 28, bold=True)
    clock = pygame.time.Clock()
    flicker_until = 0.0
    last_wake_sound = 0.0
    moving = False
    hero0 = hero.copy()
    ending_start = 0.0

    while True:
        dt = clock.tick(60) / 1000
        now = time.time()
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit(); sys.exit()

        keys = pygame.key.get_pressed()
        mouse = pygame.Vector2(pygame.mouse.get_pos())

        if state in ("play", "boss"):
            mv = pygame.Vector2(
                (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
                (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]))
            moving = mv.length() > 0
            if moving:
                hero += mv.normalize() * HERO_SPEED * dt
            hero.x = max(15, min(w - 15, hero.x)); hero.y = max(15, min(h - 15, hero.y))

            shooting = keys[pygame.K_SPACE] or pygame.mouse.get_pressed()[0]
            if shooting and now - last_shot > FIRE_DELAY:
                d = mouse - hero
                if d.length() > 1:
                    orbs.append(Orb(hero + d.normalize() * 34, d.normalize())); last_shot = now
                    play(snd_shoot)

            if state == "play":
                for m in monsters:
                    m.update(dt, now, hero)
                    if m.awake(now) and not m.woke:
                        m.woke = True
                        if now - last_wake_sound > 0.4:
                            play(snd_wake)
                            last_wake_sound = now
                for o in orbs:
                    o.update(dt)
                    for m in monsters:
                        if o.life > 0 and m.hitbox().collidepoint(o.pos):
                            o.life = 0
                            m.hp -= 1; m.flash = 0.12
                            if m.awake(now) and (m.pos - hero).length() > 0:
                                m.pos += (m.pos - hero).normalize() * 25
                            if m.hp <= 0:
                                bg.blit(m.orig, m.home)
                                sparks += [Spark(m.pos) for _ in range(25)]
                                play(snd_purify)
                                m.hp = -99
                            break
                monsters = [m for m in monsters if m.hp > -99]
                orbs = [o for o in orbs if o.life > 0]
                if not monsters:
                    # The icons return, then get pulled together to create the final boss.
                    for original, home in icon_fragments:
                        bg.fill(HOLE_COLOR, home)
                    state = "respawn"
                    respawn_start = now
                    orbs.clear()
                    pygame.mixer.music.stop()
            elif state == "boss":
                boss.update(dt, hero)
                for o in orbs:
                    if o.life <= 0:
                        continue
                    # CRITICAL FIX: bullets must advance during the boss fight too.
                    o.update(dt)
                    if boss.hit_segment(o.previous, o.pos, o.radius):
                        o.life = 0
                        boss.hp -= 1
                        boss.flash = 0.12
                        sparks += [Spark(o.pos) for _ in range(4)]
                orbs = [o for o in orbs if o.life > 0]
                if boss.hp <= 0:
                    sparks += [Spark(boss.pos) for _ in range(100)]
                    play(snd_purify)
                    state = "ending"
                    ending_start = now
                    hero0 = hero.copy()
                    orbs.clear()
                    pygame.mixer.music.stop()

            invul = max(0, invul - dt)
            touching_enemy = any(m.awake(now) and m.hitbox().collidepoint(hero) for m in monsters) if state == "play" else False
            if state == "boss" and boss and boss.hitbox().collidepoint(hero):
                touching_enemy = True
            if touching_enemy and invul == 0:
                hero_hp -= 1; invul = 1.0
                flicker_until = now + 0.15
                play(snd_hurt)
            if hero_hp <= 0 and state not in ("ending", "respawn"):
                state = "lose"
                pygame.mixer.music.stop()
                play(snd_lose)
        if state == "respawn":
            # Bring every desktop fragment back, then collapse them into the boss.
            elapsed = now - respawn_start
            if elapsed >= 4.8:
                boss = FinalBoss([item[0] for item in icon_fragments], w, h)
                boss.pos = pygame.Vector2(w / 2, h / 2)
                state = "boss"
                start_music("bgm", 0.28)
            # The icon animation is drawn after the background each frame.

        for s in sparks:
            s.update(dt)
        sparks = [s for s in sparks if s.life > 0]

        if state == "ending":
            if run_ending(screen, bg, hero0, sparks, vignette, story, now - ending_start, w, h):
                pygame.quit(); sys.exit()          # the game file ends here
            pygame.display.flip()
            continue

        # ---- draw ----
        screen.blit(bg, (0, 0))
        if state == "respawn":
            elapsed = now - respawn_start
            for idx, (original, home) in enumerate(icon_fragments):
                delay = idx * 0.055
                t = max(0.0, min(1.0, (elapsed - delay) / 2.8))
                if t <= 0:
                    continue
                home_pos = pygame.Vector2(home.center)
                center_pos = pygame.Vector2(w / 2, h / 2)
                # First respawn at the original desktop location, then fly into the beast.
                converge = smooth(max(0.0, min(1.0, (elapsed - 2.2) / 2.2)))
                pos = home_pos.lerp(center_pos, converge)
                scale = 1.0 - 0.88 * converge
                iw = max(2, int(original.get_width() * scale))
                ih = max(2, int(original.get_height() * scale))
                icon = pygame.transform.smoothscale(original, (iw, ih))
                icon.set_alpha(max(0, int(255 * (1.0 - converge * 0.9))))
                screen.blit(icon, icon.get_rect(center=(int(pos.x), int(pos.y))))
        if state == "play":
            for m in monsters:
                m.draw(screen, now)
        if state == "boss" and boss:
            # Subtle screen shake when the boss stomps.
            shake = 5 if math.sin(now * 5) > 0.94 else 0
            if shake:
                screen.scroll(random.randint(-shake, shake), random.randint(-shake, shake))
            boss.draw(screen, now)
            boss.draw_health(screen, boss_font)
        screen.blit(glow, (hero.x - 180, hero.y - 180), special_flags=pygame.BLEND_RGB_ADD)
        for o in orbs:
            o.draw(screen)
        for s in sparks:
            s.draw(screen)
        # hero
        if invul == 0 or int(now * 20) % 2:
            aim = mouse - hero
            aim = aim.normalize() if aim.length() > 1 else pygame.Vector2(1, 0)
            draw_hero(screen, hero, aim, now, moving)
        screen.blit(vignette, (0, 0))
        if now < flicker_until or random.random() < 0.004:
            dark = pygame.Surface((w, h)); dark.set_alpha(140 if now < flicker_until else 90)
            dark.fill((40 if now < flicker_until else 0, 0, 0))
            screen.blit(dark, (0, 0))

        if state in ("play", "boss"):             # crosshair at the mouse / touchpad pointer
            mx, my = int(mouse.x), int(mouse.y)
            pygame.draw.circle(screen, (255, 80, 80), (mx, my), 14, 2)
            for a, b in (((-22, 0), (-8, 0)), ((8, 0), (22, 0)), ((0, -22), (0, -8)), ((0, 8), (0, 22))):
                pygame.draw.line(screen, (255, 255, 255), (mx + a[0], my + a[1]), (mx + b[0], my + b[1]), 2)
        if state == "boss":
            hud_text = f"HP {'<3 ' * max(0, hero_hp)}  FINAL BOSS   (ESC = exit)"
        elif state == "respawn":
            hud_text = f"HP {'<3 ' * max(0, hero_hp)}  THE ICONS ARE COMING BACK..."
        else:
            hud_text = f"HP {'<3 ' * max(0, hero_hp)}  Monsters left: {len(monsters)}/{total}   (ESC = exit)"
        hud = font.render(hud_text, True, (255, 220, 220))
        screen.blit(hud, (20, 15))
        if state == "lose":
            t = huge.render("YOU DIED...", True, (255, 50, 50))
            screen.blit(t, t.get_rect(center=(w // 2, h // 2)))
        pygame.display.flip()


def main():
    make_dpi_aware()
    pygame.init()
    pygame.mixer.init()
    ghost_menu()                  # player moves the ghost window anywhere, clicks START
    pygame.display.quit()         # closes the ghost window so it isn't in the screenshot
    time.sleep(0.5)               # let the desktop repaint
    bgr, w, h = grab_screen()
    pygame.display.init()
    run_game(bgr, w, h)


if __name__ == "__main__":
    main()