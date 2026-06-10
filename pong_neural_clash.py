import pygame
import sys
import math
import random
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
W, H       = 800, 600
FPS        = 60
WIN_SCORE  = 7
WINS_TO_MATCH = 2   # first to 2 game-wins takes the match (best of 3)

# Colours
CYAN     = (0,   255, 255)
PINK     = (255, 0,   136)
WHITE    = (255, 255, 255)
BLACK    = (0,   0,   5  )
DIM_CYAN = (0,   80,  100)
DARK_BG  = (0,   12,  34 )
GOLD     = (255, 200,  50)

# Paddle dims
PW, PH, PM = 12, 90, 20
PADDLE_SPD = 7

# AI configs  {spd, offset, error_chance, prediction}
AI_CFG = {
    "easy":   dict(spd=2.8, offset=45, err=0.38, pred=0.35),
    "medium": dict(spd=5.0, offset=14, err=0.10, pred=0.78),
    "hard":   dict(spd=7.8, offset=4,  err=0.02, pred=1.00),
}

LEADERBOARD_FILE = os.path.join(os.path.dirname(__file__), "pong_leaderboard.json")


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def clamp(v, lo, hi): return max(lo, min(hi, v))
def sign(v): return (1 if v > 0 else -1) if v != 0 else 0


def load_lb():
    try:
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_lb(entries):
    try:
        with open(LEADERBOARD_FILE, "w") as f:
            json.dump(entries[:50], f, indent=2)
    except Exception:
        pass


# ─────────────────────────────────────────────
#  LOADING SCREEN
# ─────────────────────────────────────────────
BOOT_STEPS = [
    (0.08,  "INITIALIZING NEURAL ENGINE..."),
    (0.18,  "LOADING PHYSICS MODULE..."),
    (0.30,  "CALIBRATING AI REFLEXES..."),
    (0.44,  "COMPILING PARTICLE SYSTEM..."),
    (0.57,  "SYNCING LEADERBOARD DATA..."),
    (0.70,  "WARMING UP RENDERER..."),
    (0.82,  "ARMING PADDLE CONTROLLERS..."),
    (0.92,  "RUNNING SELF-DIAGNOSTICS..."),
    (1.00,  "SYSTEM READY // NEURAL CLASH ONLINE"),
]

def run_loading_screen(screen, clock):
    """Blocking loading screen. Returns when animation finishes."""
    pygame.font.init()
    font_title = None
    font_med   = None
    font_sm    = None
    for name in ("Orbitron", "Share Tech Mono", "Courier New", "monospace"):
        try:
            font_title = pygame.font.SysFont(name, 64, bold=True)
            font_med   = pygame.font.SysFont(name, 18, bold=True)
            font_sm    = pygame.font.SysFont(name, 13)
            break
        except Exception:
            pass
    if font_title is None:
        font_title = pygame.font.Font(None, 64)
        font_med   = pygame.font.Font(None, 22)
        font_sm    = pygame.font.Font(None, 16)

    DURATION   = 2.8   # seconds total
    elapsed    = 0.0
    glitch_t   = 0.0
    glitch_chars = "!@#$%^&*<>/\\|~█▓▒░"

    def draw_bg_grid(surf):
        surf.fill((0, 3, 18))
        for x in range(0, W, 40):
            pygame.draw.line(surf, (0, 14, 22), (x, 0), (x, H))
        for y in range(0, H, 40):
            pygame.draw.line(surf, (0, 14, 22), (0, y), (W, y))
        pygame.draw.line(surf, CYAN, (0, 1),    (W, 1),    2)
        pygame.draw.line(surf, CYAN, (0, H-2),  (W, H-2),  2)

    def glitch_text(text, t, intensity=0.18):
        if random.random() > intensity:
            return text
        out = list(text)
        for i in random.sample(range(len(out)), max(1, int(len(out) * 0.12))):
            if out[i] != " ":
                out[i] = random.choice(glitch_chars)
        return "".join(out)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        elapsed  += dt
        glitch_t += dt
        progress  = min(elapsed / DURATION, 1.0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if elapsed > 0.5:
                if event.type == pygame.KEYDOWN or (
                        event.type == pygame.MOUSEBUTTONDOWN):
                    running = False

        draw_bg_grid(screen)

        # ── title with glow ──────────────────────────────────────
        title_alpha = min(255, int(progress * 3.5 * 255))
        glow_col = (0, int(180 * progress), int(220 * progress))
        title_str = glitch_text("PONG", glitch_t, intensity=max(0, 0.5 - progress * 0.6))
        title_surf = font_title.render(title_str, True, (0, 230, 230))
        title_surf.set_alpha(title_alpha)
        screen.blit(title_surf, title_surf.get_rect(center=(W // 2, 155)))

        sub_surf = font_sm.render("// NEURAL CLASH //", True, (0, 130, 140))
        sub_surf.set_alpha(min(255, int((progress - 0.1) * 4 * 255)))
        screen.blit(sub_surf, sub_surf.get_rect(center=(W // 2, 208)))

        # ── scanline overlay ─────────────────────────────────────
        scan_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 4):
            pygame.draw.line(scan_surf, (0, 0, 0, 28), (0, y), (W, y))
        screen.blit(scan_surf, (0, 0))

        # ── boot log lines ───────────────────────────────────────
        log_x  = W // 2 - 220
        log_y0 = 270
        visible_steps = [s for s in BOOT_STEPS if progress >= s[0]]
        for idx, (_, msg) in enumerate(visible_steps[-6:]):   # show last 6
            y = log_y0 + idx * 18
            is_last = (idx == len(visible_steps[-6:]) - 1)
            col = CYAN if is_last else (0, 100, 110)
            disp = glitch_text(msg, glitch_t, 0.25) if is_last else msg
            prefix = "> " if is_last else "  "
            line_surf = font_sm.render(prefix + disp, True, col)
            screen.blit(line_surf, (log_x, y))

        # ── progress bar ─────────────────────────────────────────
        bar_w  = 420
        bar_h  = 14
        bar_x  = W // 2 - bar_w // 2
        bar_y  = 400
        filled = int(bar_w * progress)

        pygame.draw.rect(screen, (0, 30, 45),  (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        pygame.draw.rect(screen, (0, 60, 80),  (bar_x, bar_y, bar_w, bar_h), 1, border_radius=3)

        if filled > 0:
            pygame.draw.rect(screen, (0, 180, 200), (bar_x, bar_y, filled, bar_h), border_radius=3)
            edge_x = bar_x + filled - 4
            if edge_x > bar_x:
                pygame.draw.rect(screen, CYAN, (edge_x, bar_y, 4, bar_h), border_radius=2)

        pct_surf = font_sm.render(f"{int(progress * 100):3d}%", True, (0, 160, 170))
        screen.blit(pct_surf, (bar_x + bar_w + 10, bar_y))

        # ── skip hint ────────────────────────────────────────────
        if elapsed > 0.5:
            hint_alpha = min(180, int((elapsed - 0.5) * 300))
            hint_surf = font_sm.render("PRESS ANY KEY TO SKIP", True, (0, 70, 80))
            hint_surf.set_alpha(hint_alpha)
            screen.blit(hint_surf, hint_surf.get_rect(center=(W // 2, H - 28)))

        # ── corner brackets ──────────────────────────────────────
        bc, sz = (0, 160, 160), 18
        for px, py, dx, dy in [(4,4,1,1),(W-4,4,-1,1),(4,H-4,1,-1),(W-4,H-4,-1,-1)]:
            pygame.draw.line(screen, bc, (px, py), (px + dx * sz, py), 2)
            pygame.draw.line(screen, bc, (px, py), (px, py + dy * sz), 2)

        pygame.display.flip()

        if progress >= 1.0 and elapsed > DURATION + 0.3:
            running = False


# ─────────────────────────────────────────────
#  SOUND
# ─────────────────────────────────────────────
def make_beep(freq=440, duration=0.05, waveform="square", volume=0.25, sample_rate=22050):
    import numpy as np
    frames = int(sample_rate * duration)
    t = np.linspace(0, duration, frames, endpoint=False)
    if waveform == "sine":
        wave = np.sin(2 * math.pi * freq * t)
    elif waveform == "sawtooth":
        wave = 2 * (t * freq - np.floor(t * freq + 0.5))
    else:
        wave = np.sign(np.sin(2 * math.pi * freq * t))
    envelope = np.exp(-t / (duration * 0.6))
    wave = (wave * envelope * volume * 32767).astype(np.int16)
    stereo = np.column_stack([wave, wave])
    return pygame.sndarray.make_sound(stereo)


class SFX:
    def __init__(self):
        self.enabled = True
        self._cache  = {}
        try:
            import numpy
            self._np = True
        except ImportError:
            self._np = False

    def _get(self, key, freq, dur, wave="square", vol=0.25):
        if not self._np or not self.enabled:
            return
        if key not in self._cache:
            try:
                self._cache[key] = make_beep(freq, dur, wave, vol)
            except Exception:
                self._cache[key] = None
        s = self._cache[key]
        if s:
            try: s.play()
            except Exception: pass

    def hit(self):   self._get("hit",   460, 0.05, "square",   0.2)
    def wall(self):  self._get("wall",  280, 0.05, "square",   0.15)
    def score(self): self._get("score", 200, 0.1,  "sawtooth", 0.3)
    def go(self):    self._get("go",    900, 0.25, "sine",     0.45)
    def win(self):
        for i, f in enumerate([440, 550, 660, 880]):
            pygame.time.set_timer(pygame.USEREVENT + i, (i + 1) * 110)
    def lose(self):  self._get("lose",  180, 0.4,  "sawtooth", 0.4)
    def count(self, n): self._get(f"c{n}", 440 + n * 90, 0.18, "sine", 0.4)
    def game_win(self): self._get("gwin", 660, 0.3, "sine", 0.45)


# ─────────────────────────────────────────────
#  PARTICLE
# ─────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        spd   = random.uniform(1, 5)
        self.x, self.y  = float(x), float(y)
        self.dx, self.dy = math.cos(angle) * spd, math.sin(angle) * spd
        self.life        = 1.0
        self.decay       = random.uniform(0.03, 0.08)
        self.r           = random.uniform(1, 4)
        self.color       = color

    def update(self):
        self.x    += self.dx
        self.y    += self.dy
        self.dx   *= 0.94
        self.dy   *= 0.94
        self.life -= self.decay

    def draw(self, surface):
        if self.life <= 0: return
        alpha = max(0, min(255, int(self.life * 255)))
        r = max(1, int(self.r))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        c = (*self.color, alpha)
        pygame.draw.circle(s, c, (r, r), r)
        surface.blit(s, (int(self.x) - r, int(self.y) - r))


def spawn_particles(particles, x, y, color, n=8):
    for _ in range(n):
        particles.append(Particle(x, y, color))


# ─────────────────────────────────────────────
#  DRAWING UTILITIES
# ─────────────────────────────────────────────
class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self._glow_cache = {}
        pygame.font.init()
        self.font_title  = self._load_font(68, bold=True)
        self.font_score  = self._load_font(52, bold=True)
        self.font_med    = self._load_font(26, bold=True)
        self.font_sm     = self._load_font(16)
        self.font_xs     = self._load_font(13)

    @staticmethod
    def _load_font(size, bold=False):
        for name in ("Orbitron", "Share Tech Mono", "Courier New", "monospace"):
            try:
                f = pygame.font.SysFont(name, size, bold=bold)
                return f
            except Exception:
                pass
        return pygame.font.Font(None, size)

    def text(self, txt, font, color, cx, cy, alpha=255):
        surf = font.render(str(txt), True, color)
        if alpha < 255:
            surf.set_alpha(alpha)
        r = surf.get_rect(center=(cx, cy))
        self.screen.blit(surf, r)
        return r

    def glow_text(self, txt, font, color, cx, cy, glow_r=12):
        surf = font.render(str(txt), True, color)
        r    = surf.get_rect(center=(cx, cy))
        try:
            for offset in range(max(2, glow_r), 0, -3):
                dim = tuple(max(0, min(255, int(c * 0.35))) for c in color[:3])
                glow_surf = font.render(str(txt), True, dim)
                new_w = glow_surf.get_width() + offset * 2
                new_h = glow_surf.get_height() + offset * 2
                if new_w > 0 and new_h > 0:
                    gs = pygame.transform.smoothscale(glow_surf, (new_w, new_h))
                    gs.set_alpha(max(0, 80 - offset * 8))
                    self.screen.blit(gs, (cx - gs.get_width() // 2, cy - gs.get_height() // 2))
        except Exception:
            pass
        self.screen.blit(surf, r)

    def draw_bg(self):
        self.screen.fill((0, 3, 18))
        for x in range(0, W, 40):
            pygame.draw.line(self.screen, (0, 18, 28), (x, 0), (x, H))
        for y in range(0, H, 40):
            pygame.draw.line(self.screen, (0, 18, 28), (0, y), (W, y))
        for y in range(0, H, 26):
            pygame.draw.rect(self.screen, (0, 60, 80), (W // 2 - 1, y, 2, 10))
        pygame.draw.line(self.screen, (0, 255, 255), (0, 1), (W, 1), 2)
        pygame.draw.line(self.screen, (0, 255, 255), (0, H - 2), (W, H - 2), 2)
        bc = (0, 200, 200)
        sz = 18
        for px, py, dx, dy in [(4,4,1,1),(W-4,4,-1,1),(4,H-4,1,-1),(W-4,H-4,-1,-1)]:
            pygame.draw.line(self.screen, bc, (px, py), (px + dx * sz, py), 2)
            pygame.draw.line(self.screen, bc, (px, py), (px, py + dy * sz), 2)

    def draw_paddle(self, paddle, color, glow):
        x, y, pw, ph = int(paddle.x), int(paddle.y), PW, PH
        gs = pygame.Surface((pw + 20, ph + 20), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*glow, 40), (6, 6, pw + 8, ph + 8), border_radius=4)
        self.screen.blit(gs, (x - 10, y - 10))
        pygame.draw.rect(self.screen, color, (x, y, pw, ph), border_radius=2)
        pygame.draw.rect(self.screen, (255, 255, 255, 80), (x, y, 2, ph))

    def draw_ball(self, ball):
        bx, by, br = int(ball.x), int(ball.y), ball.r
        for rad in range(br * 4, br, -2):
            alpha = max(0, 60 - (rad - br) * 8)
            s = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (0, 255, 255, alpha), (rad, rad), rad)
            self.screen.blit(s, (bx - rad, by - rad))
        pygame.draw.circle(self.screen, WHITE, (bx, by), max(2, br - 2))

    def draw_hud(self, p_score, a_score, mode, difficulty, rallies, p_wins, a_wins):
        # point scores
        self.glow_text(f"{p_score:02d}", self.font_score, CYAN, 160, 38)
        self.glow_text(f"{a_score:02d}", self.font_score, PINK, W - 160, 38)

        # labels
        p1_lbl = "PLAYER 1"
        p2_lbl = "PLAYER 2" if mode == "pvp" else "NEURAL AI"
        self.text(p1_lbl, self.font_xs, (0, 180, 180), 160, 68)
        self.text(p2_lbl, self.font_xs, (180, 0, 80), W - 160, 68)

        # game-win dots — draw under the scores on each side
        self._draw_win_pips(p_wins, 160, 82, CYAN)
        self._draw_win_pips(a_wins, W - 160, 82, PINK)

        # centre tags
        diff_str = "VS PLAYER" if mode == "pvp" else difficulty.upper()
        self.text(diff_str, self.font_xs, (0, 120, 130), W // 2, 25)
        self.text(f"RALLY {rallies}", self.font_xs, (0, 120, 130), W // 2, 45)

        # best-of label
        total = p_wins + a_wins
        game_num = total + 1
        self.text(f"GAME {game_num}  |  BO3", self.font_xs, (0, 150, 150), W // 2, H - 16)

    def _draw_win_pips(self, wins, cx, cy, color):
        """Draw up to WINS_TO_MATCH small diamond pips indicating game wins."""
        spacing = 18
        total = WINS_TO_MATCH
        start_x = cx - (total - 1) * spacing // 2
        for i in range(total):
            px = start_x + i * spacing
            filled = i < wins
            c = color if filled else (30, 60, 70)
            pts = [(px, cy - 5), (px + 5, cy), (px, cy + 5), (px - 5, cy)]
            if filled:
                pygame.draw.polygon(self.screen, c, pts)
                gs = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.polygon(gs, (*c, 60),
                    [(10, 3), (17, 10), (10, 17), (3, 10)])
                self.screen.blit(gs, (px - 10, cy - 10))
            else:
                pygame.draw.polygon(self.screen, c, pts, 1)


# ─────────────────────────────────────────────
#  BALL
# ─────────────────────────────────────────────
class Ball:
    def __init__(self):
        self.x = self.y = 0.0
        self.dx = self.dy = 0.0
        self.r   = 8
        self.spd = 5.0

    def reset(self, mode, difficulty):
        self.x = W / 2
        self.y = H / 2
        if mode == "pvp":
            self.spd = 5.0
        else:
            self.spd = {"easy": 4.0, "medium": 6.5, "hard": 9.5}[difficulty]
        self.spd_cap = {"easy": 9.0, "medium": 13.0, "hard": 18.0}.get(difficulty, 14.0)
        angle = math.radians(random.uniform(-27.5, 27.5))
        direction = random.choice([-1, 1])
        self.dx = math.cos(angle) * self.spd * direction
        self.dy = math.sin(angle) * self.spd


# ─────────────────────────────────────────────
#  PADDLE
# ─────────────────────────────────────────────
class Paddle:
    def __init__(self, x):
        self.x = float(x)
        self.y = H / 2 - PH / 2


# ─────────────────────────────────────────────
#  MENU / LEADERBOARD SCREENS
# ─────────────────────────────────────────────
class MenuScreen:
    def __init__(self, renderer, sfx):
        self.R   = renderer
        self.sfx = sfx
        self.mode       = "ai"
        self.difficulty = "medium"
        self.pulse_t    = 0.0

    def update(self, dt): self.pulse_t += dt

    def draw(self):
        self.R.draw_bg()
        glow = abs(math.sin(self.pulse_t * 1.2))
        col  = (int(0 + glow * 0), int(200 + glow * 55), int(200 + glow * 55))
        self.R.glow_text("PONG", self.R.font_title, col, W // 2, 90, glow_r=max(4, int(glow * 18)))
        self.R.text("//NEURAL CLASH//", self.R.font_xs, (0, 130, 130), W // 2, 148)
        self.R.text("BEST OF 3 GAMES", self.R.font_xs, GOLD, W // 2, 162)

        pygame.draw.line(self.R.screen, (0, 120, 120), (W // 2 - 110, 175), (W // 2 + 110, 175))

        self.R.text("SELECT MODE", self.R.font_xs, (0, 140, 140), W // 2, 196)
        for i, (lbl, key) in enumerate([("VS NEURAL AI", "ai"), ("VS PLAYER", "pvp")]):
            bx = W // 2 - 160 + i * 162
            active = self.mode == key
            bc = (0, 255, 255) if active else (0, 70, 90)
            tc = WHITE if active else (0, 160, 160)
            pygame.draw.rect(self.R.screen, bc, (bx, 207, 155, 36), 1 if not active else 0, border_radius=3)
            if active: pygame.draw.rect(self.R.screen, (0, 40, 60), (bx, 207, 155, 36), border_radius=3)
            self.R.text(lbl, self.R.font_xs, tc, bx + 77, 225)

        alpha_diff = 60 if self.mode == "pvp" else 255
        self.R.text("DIFFICULTY", self.R.font_xs, (0, 140, 140, alpha_diff), W // 2, 263)
        for i, diff in enumerate(["EASY", "MEDIUM", "HARD"]):
            bx = W // 2 - 160 + i * 108
            active = self.mode == "ai" and self.difficulty == diff.lower()
            bc = CYAN if active else (0, 70, 90)
            tc = WHITE if active else (0, 140, 140)
            pygame.draw.rect(self.R.screen, bc, (bx, 275, 100, 32), 0 if active else 1, border_radius=3)
            if active: pygame.draw.rect(self.R.screen, (0, 40, 60), (bx, 275, 100, 32), border_radius=3)
            surf = self.R.font_xs.render(diff, True, tc)
            self.R.screen.blit(surf, surf.get_rect(center=(bx + 50, 291)))

        sound_txt = f"SFX: {'ON' if self.sfx.enabled else 'OFF'}  [M to toggle]"
        self.R.text(sound_txt, self.R.font_xs, (0, 120, 130), W // 2, 325)

        pygame.draw.rect(self.R.screen, (0, 40, 60), (W // 2 - 120, 345, 240, 46), border_radius=4)
        pygame.draw.rect(self.R.screen, CYAN, (W // 2 - 120, 345, 240, 46), 1, border_radius=4)
        self.R.text("INITIALIZE", self.R.font_med, CYAN, W // 2, 368)

        pygame.draw.rect(self.R.screen, (0, 25, 40), (W // 2 - 90, 402, 180, 34), border_radius=3)
        pygame.draw.rect(self.R.screen, (0, 140, 140), (W // 2 - 90, 402, 180, 34), 1, border_radius=3)
        self.R.text("LEADERBOARD", self.R.font_xs, (0, 200, 200), W // 2, 419)

        if self.mode == "pvp":
            hint = "P1 = W / S     |     P2 = UP / DOWN"
        else:
            hint = "W / S  or  MOUSE  to move"
        self.R.text(hint, self.R.font_xs, (0, 100, 110), W // 2, 455)

        self.R.text("SYS:READY // NEURAL ENGINE ONLINE // AWAITING INPUT",
                    self.R.font_xs, (0, 80, 90), W // 2, H - 16)

    def handle_click(self, pos):
        mx, my = pos
        for i, key in enumerate(["ai", "pvp"]):
            bx = W // 2 - 160 + i * 162
            if bx <= mx <= bx + 155 and 207 <= my <= 243:
                self.mode = key
                return None
        if self.mode == "ai":
            for i, diff in enumerate(["easy", "medium", "hard"]):
                bx = W // 2 - 160 + i * 108
                if bx <= mx <= bx + 100 and 275 <= my <= 307:
                    self.difficulty = diff
                    return None
        if W // 2 - 120 <= mx <= W // 2 + 120 and 345 <= my <= 391:
            return "start"
        if W // 2 - 90 <= mx <= W // 2 + 90 and 402 <= my <= 436:
            return "leaderboard"
        return None


# ─────────────────────────────────────────────
#   correct xs, total games column added
# ─────────────────────────────────────────────
class LeaderboardScreen:
    def __init__(self, renderer):
        self.R = renderer

    def draw(self, entries):
        self.R.draw_bg()
        self.R.glow_text("LEADERBOARD", self.R.font_med, CYAN, W // 2, 42)
        self.R.text("// MATCH HISTORY — BEST OF 3 GAMES //", self.R.font_xs, (0, 130, 130), W // 2, 72)

        headers = ["#",  "WINNER",  "MATCH",  "SCORE",    "TOTAL", "MODE", "DIFF",  "DATE"      ]
        xs      = [22,   80,        190,       310,         405,     470,    535,     650         ]

        pygame.draw.line(self.R.screen, (0, 100, 110), (14, 97), (W - 14, 97))
        for hdr, hx in zip(headers, xs):
            self.R.text(hdr, self.R.font_xs, (0, 180, 180), hx, 88)

        if not entries:
            self.R.text("NO MATCHES YET — PLAY A GAME FIRST",
                        self.R.font_xs, (0, 120, 130), W // 2, 280)
        else:
            for i, e in enumerate(entries[:20]):
                y = 113 + i * 20
                if y > H - 80: break

                score_str = e.get("score", f"{e.get('p1','?')}–{e.get('p2','?')}")

                total_games = e.get("total_games", "?")

                row = [
                    f"{i+1:02d}",
                    e.get("winner", "?"),           
                    e.get("games", "?"),             
                    score_str,                       
                    str(total_games),                
                    e.get("mode", "?"),              
                    e.get("diff", "—"),              
                    e.get("date", "?"),             
                ]
                for val, rx in zip(row, xs):
                    color = CYAN if i == 0 else (0, 160, 160)
                    self.R.text(val, self.R.font_xs, color, rx, y)

        pygame.draw.rect(self.R.screen, (0, 30, 50), (W // 2 - 80, H - 52, 160, 34), border_radius=3)
        pygame.draw.rect(self.R.screen, CYAN, (W // 2 - 80, H - 52, 160, 34), 1, border_radius=3)
        self.R.text("BACK", self.R.font_xs, CYAN, W // 2, H - 35)

    def handle_click(self, pos):
        mx, my = pos
        if W // 2 - 80 <= mx <= W // 2 + 80 and H - 52 <= my <= H - 18:
            return "back"
        return None


# ─────────────────────────────────────────────
#  GAME-WIN SCREEN
# ─────────────────────────────────────────────
class GameWinScreen:
    """Shown after each individual game (not the whole match)."""
    def __init__(self, renderer, sfx):
        self.R   = renderer
        self.sfx = sfx
        self.pulse_t  = 0.0
        self.winner   = ""
        self.color    = CYAN
        self.p_score  = 0
        self.a_score  = 0
        self.p_wins   = 0
        self.a_wins   = 0
        self.mode     = "ai"

    def setup(self, winner, color, p_score, a_score, p_wins, a_wins, mode):
        self.winner  = winner
        self.color   = color
        self.p_score = p_score
        self.a_score = a_score
        self.p_wins  = p_wins
        self.a_wins  = a_wins
        self.mode    = mode
        self.pulse_t = 0.0

    def update(self, dt):
        self.pulse_t += dt

    def draw(self):
        self.R.draw_bg()

        total = self.p_wins + self.a_wins
        self.R.text(f"// GAME {total} COMPLETE //", self.R.font_xs, (0, 130, 130), W // 2, 90)

        glow = abs(math.sin(self.pulse_t * 1.8))
        gc = tuple(int(c * (0.7 + 0.3 * glow)) for c in self.color)
        self.R.glow_text(f"{self.winner}", self.R.font_title, gc, W // 2, 180, glow_r=int(6 + glow * 16))
        self.R.text("WINS THIS GAME", self.R.font_med, self.color, W // 2, 240)

        self.R.text(f"{self.p_score:02d}  —  {self.a_score:02d}", self.R.font_score, (0, 200, 200), W // 2, 290)

        pygame.draw.line(self.R.screen, (0, 120, 120), (W // 2 - 130, 325), (W // 2 + 130, 325))

        p2_lbl = "PLAYER 2" if self.mode == "pvp" else "NEURAL AI"
        self.R.text("MATCH SCORE", self.R.font_xs, (0, 150, 150), W // 2, 345)
        self.R.text(f"PLAYER 1    {self.p_wins} — {self.a_wins}    {p2_lbl}",
                    self.R.font_med, CYAN, W // 2, 368)

        self._draw_match_pips()

        pygame.draw.rect(self.R.screen, (0, 40, 60), (W // 2 - 130, 440, 260, 46), border_radius=4)
        pygame.draw.rect(self.R.screen, CYAN, (W // 2 - 130, 440, 260, 46), 1, border_radius=4)
        self.R.text("NEXT GAME ▶", self.R.font_med, CYAN, W // 2, 463)

        self.R.text("ESC = MAIN MENU", self.R.font_xs, (0, 80, 90), W // 2, H - 16)

    def _draw_match_pips(self):
        cy = 408
        spacing = 28
        for i in range(WINS_TO_MATCH):
            px = W // 2 - 80 - i * spacing
            filled = (WINS_TO_MATCH - 1 - i) < self.p_wins
            c = CYAN if filled else (30, 60, 70)
            pts = [(px, cy - 7), (px + 7, cy), (px, cy + 7), (px - 7, cy)]
            if filled:
                pygame.draw.polygon(self.R.screen, c, pts)
            else:
                pygame.draw.polygon(self.R.screen, c, pts, 1)
        for i in range(WINS_TO_MATCH):
            px = W // 2 + 80 + i * spacing
            filled = i < self.a_wins
            c = PINK if filled else (30, 60, 70)
            pts = [(px, cy - 7), (px + 7, cy), (px, cy + 7), (px - 7, cy)]
            if filled:
                pygame.draw.polygon(self.R.screen, c, pts)
            else:
                pygame.draw.polygon(self.R.screen, c, pts, 1)

    def handle_click(self, pos):
        mx, my = pos
        if W // 2 - 130 <= mx <= W // 2 + 130 and 440 <= my <= 486:
            return "next"
        return None


# ─────────────────────────────────────────────
#  MATCH-OVER SCREEN
# ─────────────────────────────────────────────
class GameOverScreen:
    def __init__(self, renderer, sfx):
        self.R   = renderer
        self.sfx = sfx
        self.pulse_t = 0.0

    def update(self, dt): self.pulse_t += dt

    def draw(self, p_score, a_score, mode, difficulty, rallies, ai_bonus, p_wins, a_wins):
        self.R.draw_bg()
        self.R.text("// MATCH TERMINATED //", self.R.font_xs, (0, 130, 130), W // 2, 72)

        if p_wins > a_wins:
            winner_txt, col = "PLAYER 1 WINS", CYAN
        elif a_wins > p_wins:
            winner_txt = "PLAYER 2 WINS" if mode == "pvp" else "NEURAL AI WINS"
            col = PINK
        else:
            winner_txt, col = "DRAW", (255, 170, 0)

        glow = abs(math.sin(self.pulse_t * 1.5))
        gc   = tuple(int(c * (0.7 + 0.3 * glow)) for c in col)
        self.R.glow_text("THE MATCH", self.R.font_med, (0, 180, 180), W // 2, 120)
        self.R.glow_text(winner_txt, self.R.font_title, gc, W // 2, 185, glow_r=int(6 + glow * 16))

        p2_lbl = "PLAYER 2" if mode == "pvp" else "NEURAL AI"
        self.R.text(f"PLAYER 1  {p_wins} — {a_wins}  {p2_lbl}", self.R.font_med, (0, 200, 200), W // 2, 255)
        self.R.text(f"last game: {p_score} — {a_score}", self.R.font_xs, (0, 120, 130), W // 2, 285)

        pygame.draw.line(self.R.screen, (0, 120, 120), (W // 2 - 110, 305), (W // 2 + 110, 305))

        if mode == "ai":
            info = f"NEURAL AI ADAPTED {rallies} TIMES  |  SPEED BONUS +{ai_bonus:.1f}"
        else:
            info = f"TOTAL RALLIES: {rallies}"
        self.R.text(info, self.R.font_xs, (0, 140, 140), W // 2, 322)

        btns = [("REMATCH", W // 2 - 210, 345), ("LEADERBOARD", W // 2 - 50, 345), ("MAIN MENU", W // 2 + 110, 345)]
        for lbl, bx, by in btns:
            w = 140
            pygame.draw.rect(self.R.screen, (0, 25, 40), (bx - w // 2, by, w, 36), border_radius=3)
            pygame.draw.rect(self.R.screen, CYAN, (bx - w // 2, by, w, 36), 1, border_radius=3)
            self.R.text(lbl, self.R.font_xs, CYAN, bx, by + 18)

        if p_wins > a_wins:
            status = "SYSTEM: NEURAL AI DEFEATED // RECALIBRATING..." if mode == "ai" else "PLAYER 1 VICTORIOUS"
        else:
            status = "SYSTEM: PLAYER ELIMINATED // AI DOMINANT" if mode == "ai" else "PLAYER 2 VICTORIOUS"
        self.R.text(status, self.R.font_xs, (0, 90, 100), W // 2, H - 16)

    def handle_click(self, pos):
        mx, my = pos
        btns = [("rematch", W // 2 - 210), ("leaderboard", W // 2 - 50), ("menu", W // 2 + 110)]
        for action, bx in btns:
            if bx - 70 <= mx <= bx + 70 and 345 <= my <= 381:
                return action
        return None


# ─────────────────────────────────────────────
#  MAIN GAME
# ─────────────────────────────────────────────
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("PONG // NEURAL CLASH  |  BEST OF 3")
        self.screen   = pygame.display.set_mode((W, H))
        self.clock    = pygame.time.Clock()

        # ── loading screen  ────────────
        run_loading_screen(self.screen, self.clock)

        self.renderer = Renderer(self.screen)
        self.sfx      = SFX()

        self.menu_screen     = MenuScreen(self.renderer, self.sfx)
        self.lb_screen       = LeaderboardScreen(self.renderer)
        self.go_screen       = GameOverScreen(self.renderer, self.sfx)
        self.game_win_screen = GameWinScreen(self.renderer, self.sfx)

        self.state   = "menu"
        self.lb_from = "menu"

        self.mode       = "ai"
        self.difficulty = "medium"
        self.p_wins     = 0
        self.a_wins     = 0
        self.total_rallies = 0
        self.ai_bonus      = 0.0
        self.p_score = 0
        self.a_score = 0
        self.rallies = 0

        self.game_scores = []   
        self.total_games = 0   

        self.player    = Paddle(PM)
        self.ai_p      = Paddle(W - PM - PW)
        self.ball      = Ball()
        self.particles = []

        self.countdown_val   = 0
        self.countdown_timer = 0.0
        self.countdown_phase = "number"

        self.keys = {}
        self._last_mouse_y = -1

    # ── match / game start ─────────────────────────────────────────
    def start_match(self):
        self.mode          = self.menu_screen.mode
        self.difficulty    = self.menu_screen.difficulty
        self.p_wins        = 0
        self.a_wins        = 0
        self.total_rallies = 0
        self.ai_bonus      = 0.0
        self.particles     = []
        self.game_scores   = []   
        self.total_games   = 0    
        self._start_game()

    def _start_game(self):
        self.p_score = 0
        self.a_score = 0
        self.rallies = 0
        self.player.y = H / 2 - PH / 2
        self.ai_p.y   = H / 2 - PH / 2
        self.ball.reset(self.mode, self.difficulty)
        self.ai_bonus = 0.0
        self.begin_countdown(3)

    def begin_countdown(self, n):
        self.state            = "countdown"
        self.countdown_val    = n
        self.countdown_timer  = 0.0
        self.countdown_phase  = "number"
        self.sfx.count(n)

    def short_countdown(self):
        self.state           = "countdown"
        self.countdown_val   = -1
        self.countdown_timer = 0.0
        self.countdown_phase = "number"
        self.sfx.count(1)

    # ── leaderboard ────────────────────────────────────────────────
    def record_match(self):
        """
        FIX 1: difficulty is already locked in self.difficulty at start_match().
        FIX 2: build a readable per-game score string from self.game_scores.
        FIX 3: save self.total_games so leaderboard can display it.
        """
        if self.p_wins > self.a_wins:
            winner = "PLAYER 1"
        elif self.a_wins > self.p_wins:
            winner = "PLAYER 2" if self.mode == "pvp" else "NEURAL AI"
        else:
            winner = "DRAW"

        score_str = ", ".join(f"{ps}-{as_}" for ps, as_ in self.game_scores)

        entry = {
            "winner":      winner,
            "games":       f"{self.p_wins}–{self.a_wins}",  
            "score":       score_str,                        
            "total_games": self.total_games,                  
            "mode":        "PVP" if self.mode == "pvp" else "VS AI",
            "diff":        "—" if self.mode == "pvp" else self.difficulty.upper(),  
            "rallies":     self.total_rallies,
            "date":        datetime.now().strftime("%b %d %H:%M"),
        }
        lb = load_lb()
        lb.insert(0, entry)
        save_lb(lb)

    # ── AI ─────────────────────────────────────────────────────────
    def update_ai(self):
        cfg = AI_CFG[self.difficulty]
        spd = cfg["spd"] + self.ai_bonus
        target_y = H / 2

        if self.ball.dx > 0:
            t = (self.ai_p.x - self.ball.x) / self.ball.dx if self.ball.dx != 0 else 0
            py = self.ball.y + self.ball.dy * t * cfg["pred"]
            while py < 0 or py > H:
                if py < 0:    py = -py
                if py > H:    py = 2 * H - py
            target_y = py
            if random.random() < cfg["err"]:
                target_y += random.uniform(-55, 55)

        center = self.ai_p.y + PH / 2
        diff   = target_y - center
        if abs(diff) > cfg["offset"]:
            self.ai_p.y += sign(diff) * min(spd, abs(diff))
        self.ai_p.y = clamp(self.ai_p.y, 0, H - PH)

    # ── update ─────────────────────────────────────────────────────
    def update(self, dt):
        if self.state == "countdown":
            self.countdown_timer += dt
            if self.countdown_val == -1:
                if self.countdown_timer >= 0.65:
                    self.state = "playing"
            else:
                if self.countdown_phase == "number" and self.countdown_timer >= 0.8:
                    self.countdown_val -= 1
                    self.countdown_timer = 0.0
                    if self.countdown_val > 0:
                        self.sfx.count(self.countdown_val)
                    elif self.countdown_val == 0:
                        self.countdown_phase = "go"
                        self.sfx.go()
                elif self.countdown_phase == "go" and self.countdown_timer >= 0.65:
                    self.state = "playing"
            return

        if self.state == "game_win":
            self.game_win_screen.update(dt)
            return

        if self.state != "playing":
            return

        # ── movement ──────────────────────────────────────────────
        if self.mode == "ai":
            up1   = self.keys.get(pygame.K_w) or self.keys.get(pygame.K_UP)
            down1 = self.keys.get(pygame.K_s) or self.keys.get(pygame.K_DOWN)
        else:
            up1   = self.keys.get(pygame.K_w)
            down1 = self.keys.get(pygame.K_s)

        if up1:   self.player.y -= PADDLE_SPD
        if down1: self.player.y += PADDLE_SPD
        self.player.y = clamp(self.player.y, 0, H - PH)

        if self.mode == "pvp":
            if self.keys.get(pygame.K_UP):   self.ai_p.y -= PADDLE_SPD
            if self.keys.get(pygame.K_DOWN): self.ai_p.y += PADDLE_SPD
            self.ai_p.y = clamp(self.ai_p.y, 0, H - PH)
        else:
            self.update_ai()

        # ── ball ──────────────────────────────────────────────────
        b = self.ball
        b.x += b.dx
        b.y += b.dy

        if b.y - b.r <= 0:
            b.y = b.r; b.dy *= -1
            self.sfx.wall()
            spawn_particles(self.particles, b.x, 0, CYAN, 5)
        if b.y + b.r >= H:
            b.y = H - b.r; b.dy *= -1
            self.sfx.wall()
            spawn_particles(self.particles, b.x, H, CYAN, 5)

        # P1 paddle hit
        pl = self.player
        if (b.dx < 0
                and b.x - b.r <= pl.x + PW
                and b.x - b.r >= pl.x - 2
                and pl.y <= b.y <= pl.y + PH):
            b.x = pl.x + PW + b.r
            hp = (b.y - (pl.y + PH / 2)) / (PH / 2)
            b.spd = min(b.spd + 0.15, b.spd_cap)
            angle = math.radians(hp * 60)
            b.dx = math.cos(angle) * b.spd
            b.dy = math.sin(angle) * b.spd
            self.rallies += 1
            self.total_rallies += 1
            self.ai_bonus = min(self.rallies * 0.09, 2.8)
            self.sfx.hit()
            spawn_particles(self.particles, b.x, b.y, CYAN, 12)

        # P2 / AI paddle hit
        ai = self.ai_p
        if (b.dx > 0
                and b.x + b.r >= ai.x
                and b.x + b.r <= ai.x + PW + 2
                and ai.y <= b.y <= ai.y + PH):
            b.x = ai.x - b.r
            hp = (b.y - (ai.y + PH / 2)) / (PH / 2)
            b.spd = min(b.spd + 0.15, b.spd_cap)
            angle = math.radians(hp * 60)
            b.dx = -math.cos(angle) * b.spd
            b.dy = math.sin(angle) * b.spd
            self.rallies += 1
            self.total_rallies += 1
            self.ai_bonus = min(self.rallies * 0.09, 2.8)
            self.sfx.hit()
            spawn_particles(self.particles, b.x, b.y, PINK, 12)

        # ── scoring ───────────────────────────────────────────────
        if b.x + b.r < 0:
            self.a_score += 1
            self.sfx.score()
            spawn_particles(self.particles, 10, b.y, PINK, 20)
            if not self.check_game_win():
                self.ball.reset(self.mode, self.difficulty)
                self.player.y = H / 2 - PH / 2
                self.ai_p.y   = H / 2 - PH / 2
                self.short_countdown()

        if b.x - b.r > W:
            self.p_score += 1
            self.sfx.score()
            spawn_particles(self.particles, W - 10, b.y, CYAN, 20)
            if not self.check_game_win():
                self.ball.reset(self.mode, self.difficulty)
                self.player.y = H / 2 - PH / 2
                self.ai_p.y   = H / 2 - PH / 2
                self.short_countdown()

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

    def check_game_win(self):
        """Check if either player hit WIN_SCORE points. Returns True if game ended."""
        if self.p_score >= WIN_SCORE or self.a_score >= WIN_SCORE:
            if self.p_score >= WIN_SCORE:
                self.p_wins += 1
                winner, col = "PLAYER 1", CYAN
            else:
                self.a_wins += 1
                winner = "PLAYER 2" if self.mode == "pvp" else "NEURAL AI"
                col = PINK

            self.game_scores.append((self.p_score, self.a_score))
            self.total_games += 1

            for _ in range(3):
                spawn_particles(self.particles, W // 2, H // 2, col, 20)

            if self.p_wins >= WINS_TO_MATCH or self.a_wins >= WINS_TO_MATCH:
                self.state = "gameover"
                self.record_match()
                if self.p_wins > self.a_wins:
                    self.sfx.win()
                else:
                    self.sfx.lose()
            else:
                self.sfx.game_win()
                self.game_win_screen.setup(
                    winner, col,
                    self.p_score, self.a_score,
                    self.p_wins, self.a_wins,
                    self.mode
                )
                self.state = "game_win"
            return True
        return False

    # ── render ─────────────────────────────────────────────────────
    def render(self):
        R = self.renderer

        if self.state == "menu":
            self.menu_screen.draw()

        elif self.state == "leaderboard":
            self.lb_screen.draw(load_lb())

        elif self.state == "game_win":
            self.game_win_screen.draw()

        elif self.state in ("playing", "countdown", "gameover"):
            R.draw_bg()
            R.draw_paddle(self.player, CYAN, CYAN)
            R.draw_paddle(self.ai_p,   PINK, PINK)
            if self.state != "gameover":
                R.draw_ball(self.ball)
            for p in self.particles:
                p.draw(self.screen)
            R.draw_hud(self.p_score, self.a_score, self.mode, self.difficulty,
                       self.rallies, self.p_wins, self.a_wins)

            if self.state == "countdown":
                if self.countdown_val == -1:
                    lbl = "●"
                elif self.countdown_val == 0:
                    lbl = "GO!"
                else:
                    lbl = str(self.countdown_val)
                R.glow_text(lbl, R.font_title, CYAN, W // 2, H // 2, glow_r=20)

            if self.state == "gameover":
                self.go_screen.draw(
                    self.p_score, self.a_score,
                    self.mode, self.difficulty,
                    self.total_rallies, self.ai_bonus,
                    self.p_wins, self.a_wins
                )

        pygame.display.flip()

    # ── events ─────────────────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                self.keys[event.key] = True
                if event.key == pygame.K_ESCAPE:
                    if self.state in ("playing", "countdown", "gameover", "game_win"):
                        self.state = "menu"
                    else:
                        return False
                if event.key == pygame.K_m:
                    self.sfx.enabled = not self.sfx.enabled
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if self.state == "game_win":
                        self._start_game()

            if event.type == pygame.KEYUP:
                self.keys[event.key] = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if self.state == "menu":
                    action = self.menu_screen.handle_click(pos)
                    if action == "start":
                        self.start_match()
                    elif action == "leaderboard":
                        self.lb_from = "menu"
                        self.state   = "leaderboard"

                elif self.state == "leaderboard":
                    action = self.lb_screen.handle_click(pos)
                    if action == "back":
                        self.state = "menu" if self.lb_from == "menu" else "gameover"

                elif self.state == "game_win":
                    action = self.game_win_screen.handle_click(pos)
                    if action == "next":
                        self._start_game()

                elif self.state == "gameover":
                    action = self.go_screen.handle_click(pos)
                    if action == "rematch":
                        self.start_match()
                    elif action == "leaderboard":
                        self.lb_from = "gameover"
                        self.state   = "leaderboard"
                    elif action == "menu":
                        self.state = "menu"

        if self.state == "playing" and self.mode == "ai":
            mx, my = pygame.mouse.get_pos()
            if my != self._last_mouse_y:
                self.player.y = clamp(my - PH / 2, 0, H - PH)
                self._last_mouse_y = my

        return True

    # ── run ────────────────────────────────────────────────────────
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            running = self.handle_events()

            if self.state == "menu":
                self.menu_screen.update(dt)
            elif self.state == "gameover":
                self.go_screen.update(dt)
            elif self.state == "game_win":
                pass
            else:
                self.update(dt)

            self.render()

        pygame.quit()
        sys.exit()


# ─────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()