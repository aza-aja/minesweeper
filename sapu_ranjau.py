import pygame
import random
import sys
import math

pygame.init()

# ── Level config ─────────────────────────────────────────────────────────────
LEVELS = {
    "mudah":  (9,  9,  10),
    "sedang": (16, 16, 40),
    "sulit":  (16, 30, 99),
}
LEVEL_LABELS = {
    "mudah": "EASY",
    "sedang": "MEDIUM",
    "sulit": "HARD",
}

UKURAN_SEL_AWAL = 30
TINGGI_PANEL    = 90

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "bg":            (11,  15,  23),
    "panel":         (22,  30,  46),
    "panel_border":  (50,  70,  110),
    "grid":          (40,  54,  76),
    "closed":        (58,  78,  108),
    "closed_hi":     (72,  96,  130),
    "open":          (190, 200, 218),
    "open_zero":     (170, 182, 202),
    "mine":          (220, 55,  75),
    "mine_bg":       (80,  20,  28),
    "flag":          (255, 195, 60),
    "flag_pole":     (220, 160, 40),
    "cursor":        (80,  210, 255),
    "cursor_dim":    (40,  110, 140),
    "btn":           (42,  90,  170),
    "btn_hi":        (60,  120, 210),
    "btn_danger":    (160, 40,  55),
    "btn_danger_hi": (200, 60,  75),
    "white":         (245, 248, 255),
    "dim":           (140, 160, 195),
    "gold":          (255, 205, 70),
    "green":         (55,  200, 110),
    "red":           (220, 70,  70),
}
NUM_COLORS = {
    1: (80,  130, 255),
    2: (55,  195, 100),
    3: (230, 80,  70),
    4: (80,  100, 220),
    5: (200, 70,  70),
    6: (55,  190, 200),
    7: (200, 200, 200),
    8: (150, 160, 175),
}

# Best time storage (per session)
best_times = {"mudah": None, "sedang": None, "sulit": None}


# ── Particle ──────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color, vx=None, vy=None, life=None, size=None):
        self.x        = x
        self.y        = y
        self.vx       = vx   if vx   is not None else random.uniform(-3, 3)
        self.vy       = vy   if vy   is not None else random.uniform(-5, -1)
        self.life     = life if life is not None else random.randint(30, 60)
        self.max_life = self.life
        self.size     = size if size is not None else random.uniform(2, 5)
        self.color    = color
        self.gravity  = 0.15

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += self.gravity
        self.life -= 1

    def draw(self, surf):
        alpha = self.life / self.max_life
        r, g, b = self.color
        s = max(1, int(self.size * alpha))
        pygame.draw.circle(surf,
                           (int(r * alpha), int(g * alpha), int(b * alpha)),
                           (int(self.x), int(self.y)), s)

    @property
    def alive(self):
        return self.life > 0


# ── Cell open animation (ripple) ──────────────────────────────────────────────
class CellAnim:
    def __init__(self, row, col, delay):
        self.row, self.col = row, col
        self.delay = delay
        self.t, self.dur  = 0, 12

    def progress(self):
        return 0.0 if self.delay > 0 else min(1.0, self.t / self.dur)

    def update(self):
        if self.delay > 0:
            self.delay -= 1
        else:
            self.t += 1

    @property
    def done(self):
        return self.delay <= 0 and self.t >= self.dur


# ── Flag plant animation ───────────────────────────────────────────────────────
class FlagAnim:
    def __init__(self, row, col):
        self.row, self.col = row, col
        self.t, self.dur   = 0, 18

    def scale(self):
        p = self.t / self.dur
        return 1.0 + 0.4 * math.sin(p * math.pi) * (1 - p)

    def update(self):
        self.t += 1

    @property
    def done(self):
        return self.t >= self.dur


# ── Main game ─────────────────────────────────────────────────────────────────
class SapuRanjau:
    def __init__(self, level):
        self.nama_level        = level
        self.BARIS, self.KOLOM, self.RANJAU = LEVELS[level]
        self.ukuran_sel        = UKURAN_SEL_AWAL
        self.is_fullscreen     = False

        info = pygame.display.Info()
        self.LEBAR  = self.KOLOM * UKURAN_SEL_AWAL
        self.TINGGI = self.BARIS * UKURAN_SEL_AWAL + TINGGI_PANEL

        self.layar = pygame.display.set_mode((self.LEBAR, self.TINGGI), pygame.RESIZABLE)
        pygame.display.set_caption("Sapu Ranjau")
        self._load_fonts()
        self.reset()

    def _load_fonts(self):
        self.font       = pygame.font.SysFont("consolas",  18, bold=True)
        self.font_besar = pygame.font.SysFont("consolas",  38, bold=True)
        self.font_kecil = pygame.font.SysFont("segoe ui",  14)
        self.font_label = pygame.font.SysFont("segoe ui",  13)
        self.font_huge  = pygame.font.SysFont("consolas",  54, bold=True)

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.layar = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.layar = pygame.display.set_mode((self.LEBAR, self.TINGGI), pygame.RESIZABLE)
        w, h = self.layar.get_size()
        self.LEBAR, self.TINGGI = w, h

    def reset(self):
        self.papan         = [[0]     * self.KOLOM for _ in range(self.BARIS)]
        self.terbuka       = [[False] * self.KOLOM for _ in range(self.BARIS)]
        self.ditandai      = [[False] * self.KOLOM for _ in range(self.BARIS)]
        self.klik_pertama  = True
        self.game_over     = False
        self.menang        = False
        self.tampilkan_menu= False
        self.mode_menu     = "akhir"
        self.waktu_mulai   = pygame.time.get_ticks()
        self.waktu_jeda    = 0       # accumulated paused ms
        self.sedang_jeda   = False
        self.waktu_selesai = None
        self.kursor_baris  = 0
        self.kursor_kolom  = 0
        self.hovered_cell  = None
        self.particles     = []
        self.cell_anims    = []
        self.flag_anims    = {}
        self.flash_timer   = 0
        self.win_timer     = 0
        self.menu_rects    = []

    # ── Board logic ───────────────────────────────────────────────────────────
    def _tempatkan_ranjau(self, aman_b, aman_k):
        zona_aman = {
            (aman_b + db, aman_k + dk)
            for db in (-1, 0, 1)
            for dk in (-1, 0, 1)
            if 0 <= aman_b + db < self.BARIS and 0 <= aman_k + dk < self.KOLOM
        }
        count = 0
        while count < self.RANJAU:
            b = random.randint(0, self.BARIS - 1)
            k = random.randint(0, self.KOLOM - 1)
            if (b, k) not in zona_aman and self.papan[b][k] != "*":
                self.papan[b][k] = "*"
                count += 1

    def _hitung_tetangga(self, b, k):
        return sum(
            1 for db, dk in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
            if 0 <= b+db < self.BARIS and 0 <= k+dk < self.KOLOM
            and self.papan[b+db][k+dk] == "*"
        )

    def _isi_angka(self):
        for b in range(self.BARIS):
            for k in range(self.KOLOM):
                if self.papan[b][k] != "*":
                    self.papan[b][k] = self._hitung_tetangga(b, k)

    def _flood_fill(self, start_b, start_k):
        """Iterative flood fill — avoids recursion limit on large grids."""
        stack = [(start_b, start_k, 0)]
        visited = set()
        while stack:
            b, k, depth = stack.pop()
            if (b, k) in visited:
                continue
            if not (0 <= b < self.BARIS and 0 <= k < self.KOLOM):
                continue
            if self.terbuka[b][k] or self.ditandai[b][k]:
                continue
            visited.add((b, k))
            self.terbuka[b][k] = True
            self.cell_anims.append(CellAnim(b, k, delay=depth * 2))
            if self.papan[b][k] == 0:
                for db, dk in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                    stack.append((b+db, k+dk, depth+1))

    def _cek_menang(self):
        return all(
            self.terbuka[b][k] or self.papan[b][k] == "*"
            for b in range(self.BARIS)
            for k in range(self.KOLOM)
        )

    def buka_sel(self, b, k):
        if self.game_over or self.ditandai[b][k] or self.terbuka[b][k]:
            return
        if self.klik_pertama:
            self._tempatkan_ranjau(b, k)
            self._isi_angka()
            self.klik_pertama = False
        if self.papan[b][k] == "*":
            self.terbuka[b][k] = True
            self.game_over      = True
            self.menang         = False
            self.mode_menu      = "akhir"
            self.tampilkan_menu = True
            self.flash_timer    = 30
            cx, cy = self._cell_center(b, k)
            self._spawn_explosion(cx, cy)
        else:
            self._flood_fill(b, k)
            if self._cek_menang():
                self.game_over      = True
                self.menang         = True
                self.mode_menu      = "akhir"
                self.tampilkan_menu = True
                self.waktu_selesai  = self._elapsed()
                lv = self.nama_level
                if best_times[lv] is None or self.waktu_selesai < best_times[lv]:
                    best_times[lv] = self.waktu_selesai
                self.win_timer = 60
                self._spawn_win_particles()

    def toggle_bendera(self, b, k):
        if self.terbuka[b][k] or self.game_over:
            return
        self.ditandai[b][k] = not self.ditandai[b][k]
        if self.ditandai[b][k]:
            self.flag_anims[(b, k)] = FlagAnim(b, k)

    # ── Timer helpers ─────────────────────────────────────────────────────────
    def _elapsed(self):
        """Elapsed seconds, excluding paused time."""
        return (pygame.time.get_ticks() - self.waktu_mulai - self.waktu_jeda) // 1000

    def pause(self):
        if not self.game_over and not self.sedang_jeda:
            self.sedang_jeda   = True
            self._jeda_mulai   = pygame.time.get_ticks()
            self.mode_menu     = "pause"
            self.tampilkan_menu= True

    def resume(self):
        if self.sedang_jeda:
            self.waktu_jeda += pygame.time.get_ticks() - self._jeda_mulai
            self.sedang_jeda  = False
        self.tampilkan_menu = False

    # ── Particle helpers ──────────────────────────────────────────────────────
    def _cell_center(self, b, k):
        px, py = self._asal_papan()
        s = self.ukuran_sel
        return px + k * s + s // 2, py + b * s + s // 2

    def _spawn_explosion(self, cx, cy):
        for _ in range(40):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(2, 8)
            self.particles.append(Particle(
                cx, cy, C["mine"],
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(25, 50),
                size=random.uniform(3, 7),
            ))

    def _spawn_win_particles(self):
        for _ in range(80):
            col = random.choice([C["gold"], C["green"], C["white"]])
            self.particles.append(Particle(
                random.randint(0, self.LEBAR),
                random.randint(-50, self.TINGGI // 2),
                col,
                vx=random.uniform(-2, 2),
                vy=random.uniform(1, 4),
                life=random.randint(60, 120),
                size=random.uniform(3, 7),
            ))

    # ── Layout ────────────────────────────────────────────────────────────────
    def _hitung_ukuran_sel(self):
        area_w = max(8, self.LEBAR  - 120)
        area_h = max(8, self.TINGGI - TINGGI_PANEL - 60)
        self.ukuran_sel = max(20, min(50, area_w // self.KOLOM, area_h // self.BARIS))

    def _asal_papan(self):
        self._hitung_ukuran_sel()
        lebar  = self.KOLOM * self.ukuran_sel
        tinggi = self.BARIS * self.ukuran_sel
        x = (self.LEBAR  - lebar)  // 2
        y = TINGGI_PANEL + max(10, (self.TINGGI - TINGGI_PANEL - tinggi) // 2)
        return x, y

    def _cell_at_mouse(self, mx, my):
        px, py = self._asal_papan()
        s = self.ukuran_sel
        b = (my - py) // s
        k = (mx - px) // s
        if 0 <= b < self.BARIS and 0 <= k < self.KOLOM:
            return b, k
        return None

    # ── Draw ──────────────────────────────────────────────────────────────────
    def gambar(self, mouse_pos):
        w, h = self.layar.get_size()
        self.LEBAR, self.TINGGI = w, h

        self.hovered_cell = (
            self._cell_at_mouse(*mouse_pos)
            if not self.tampilkan_menu else None
        )

        # update animations
        self.cell_anims = [ca for ca in self.cell_anims if not ca.done]
        for ca in self.cell_anims:
            ca.update()

        for key in list(self.flag_anims):
            fa = self.flag_anims[key]
            fa.update()
            if fa.done:
                del self.flag_anims[key]

        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update()

        if self.flash_timer > 0:
            self.flash_timer -= 1
        if self.win_timer > 0:
            self.win_timer -= 1
            if self.win_timer % 8 == 0:
                self._spawn_win_particles()

        # background
        self.layar.fill(C["bg"])
        self._draw_bg_grid()

        # flash overlays
        if self.flash_timer > 0:
            self._draw_overlay_color((200, 30, 30), int(160 * self.flash_timer / 30))
        if self.win_timer > 0:
            self._draw_overlay_color((255, 215, 0), int(80 * self.win_timer / 60))

        detik = (self.waktu_selesai if self.waktu_selesai is not None
                 else self._elapsed())
        sisa  = self.RANJAU - sum(sum(row) for row in self.ditandai)

        self._draw_panel(sisa, detik)
        self._draw_board()

        for p in self.particles:
            p.draw(self.layar)

        if self.tampilkan_menu:
            self._draw_overlay_menu()

        pygame.display.flip()

    def _draw_overlay_color(self, rgb, alpha):
        fl = pygame.Surface((self.LEBAR, self.TINGGI), pygame.SRCALPHA)
        fl.fill((*rgb, alpha))
        self.layar.blit(fl, (0, 0))

    def _draw_bg_grid(self):
        dot_col = (22, 30, 44)
        for x in range(0, self.LEBAR, 28):
            for y in range(0, self.TINGGI, 28):
                pygame.draw.circle(self.layar, dot_col, (x, y), 1)

    def _draw_panel(self, sisa, detik):
        pad  = 12
        h    = TINGGI_PANEL - pad
        cx   = self.LEBAR // 2
        panel = pygame.Rect(pad, pad, self.LEBAR - pad * 2, h)
        pygame.draw.rect(self.layar, C["panel"], panel, border_radius=14)
        pygame.draw.rect(self.layar, C["panel_border"], panel, 2, border_radius=14)

        # mine counter
        mine_col = C["red"] if sisa <= 0 else C["white"]
        self._draw_seg(pad + 20, pad + 6, sisa, mine_col)
        self.layar.blit(
            self.font_label.render("MINES", True, C["dim"]),
            (pad + 20, pad + h - 18))

        # timer
        timer_col = C["red"] if detik >= 999 else (C["gold"] if detik > 180 else C["white"])
        self._draw_seg(self.LEBAR - pad - 20 - 90, pad + 6, detik, timer_col, right_align=True)
        self.layar.blit(
            self.font_label.render("TIME", True, C["dim"]),
            (self.LEBAR - pad - 20 - 90, pad + h - 18))

        # smiley reset button
        btn_r  = 22
        btn_cy = pad + h // 2
        self._smiley_rect = pygame.Rect(cx - btn_r, btn_cy - btn_r, btn_r * 2, btn_r * 2)
        face_col = C["gold"] if (self.menang or not self.game_over) else C["red"]
        pygame.draw.circle(self.layar, face_col, (cx, btn_cy), btn_r)
        pygame.draw.circle(self.layar, C["bg"],  (cx, btn_cy), btn_r, 2)

        if self.game_over and not self.menang:   # X eyes
            for ex in (-8, 8):
                for dx, dy in ((-3,-3),(3,3),(-3,3),(3,-3)):
                    pygame.draw.line(self.layar, C["bg"],
                                     (cx+ex+dx-2, btn_cy-6+dy-2),
                                     (cx+ex-dx+2, btn_cy-6-dy+2), 2)
        else:
            pygame.draw.circle(self.layar, C["bg"], (cx - 8, btn_cy - 6), 3)
            pygame.draw.circle(self.layar, C["bg"], (cx + 8, btn_cy - 6), 3)

        # mouth
        if self.menang:
            pygame.draw.arc(self.layar, C["bg"],
                            pygame.Rect(cx-9, btn_cy-2, 18, 14), math.pi, math.tau, 2)
        elif self.game_over:
            pygame.draw.arc(self.layar, C["bg"],
                            pygame.Rect(cx-9, btn_cy+4, 18, 10), 0, math.pi, 2)
        else:
            pygame.draw.arc(self.layar, C["bg"],
                            pygame.Rect(cx-9, btn_cy-2, 18, 14), math.pi, math.tau, 2)

        lv_txt = self.font_label.render(
            f"{LEVEL_LABELS[self.nama_level]}  ·  F11 Fullscreen  ·  ESC Pause",
            True, C["dim"])
        self.layar.blit(lv_txt, lv_txt.get_rect(center=(cx, pad + h - 9)))

    def _draw_seg(self, x, y, value, color, right_align=False):
        txt = self.font_besar.render(f"{min(max(value, 0), 999):03d}", True, color)
        self.layar.blit(txt, (x + 90 - txt.get_width() if right_align else x, y))

    def _draw_board(self):
        px, py = self._asal_papan()
        s      = self.ukuran_sel
        margin = 2
        anim_map = {(ca.row, ca.col): ca.progress() for ca in self.cell_anims}

        for b in range(self.BARIS):
            for k in range(self.KOLOM):
                rx   = px + k * s + margin
                ry   = py + b * s + margin
                rs   = s - margin * 2
                rect = pygame.Rect(rx, ry, rs, rs)
                hovered = self.hovered_cell == (b, k) and not self.terbuka[b][k]

                if self.terbuka[b][k]:
                    prog = anim_map.get((b, k), 1.0)
                    if prog < 1.0:
                        sz = max(1, int(rs * prog))
                        cx_ = rx + rs // 2
                        cy_ = ry + rs // 2
                        draw_rect = pygame.Rect(cx_ - sz//2, cy_ - sz//2, sz, sz)
                    else:
                        draw_rect = rect

                    bg = (C["mine_bg"] if self.papan[b][k] == "*"
                          else (C["open_zero"] if self.papan[b][k] == 0 else C["open"]))
                    pygame.draw.rect(self.layar, bg, draw_rect, border_radius=4)

                    if prog >= 0.7:
                        val = self.papan[b][k]
                        if val == "*":
                            r = max(5, s // 3)
                            pygame.draw.circle(self.layar, C["mine"], rect.center, r)
                            for ang in range(0, 360, 45):
                                rad = math.radians(ang)
                                ex  = rect.centerx + math.cos(rad) * s // 2.2
                                ey  = rect.centery + math.sin(rad) * s // 2.2
                                pygame.draw.line(self.layar, C["mine"],
                                                 rect.center, (int(ex), int(ey)), 2)
                        elif val > 0:
                            txt = self.font.render(str(val), True, NUM_COLORS[val])
                            self.layar.blit(txt, txt.get_rect(center=rect.center))
                else:
                    pygame.draw.rect(self.layar,
                                     C["closed_hi"] if hovered else C["closed"],
                                     rect, border_radius=4)
                    hl = pygame.Surface((rs, rs), pygame.SRCALPHA)
                    pygame.draw.rect(hl, (255, 255, 255, 18), hl.get_rect(), border_radius=4)
                    self.layar.blit(hl, (rx, ry))
                    if self.ditandai[b][k]:
                        self._draw_flag(rect, b, k)

                pygame.draw.rect(self.layar, C["grid"], rect, 1, border_radius=4)

        # keyboard cursor
        t     = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(t / 250)
        cc    = tuple(int(C["cursor"][i] * pulse + C["cursor_dim"][i] * (1-pulse))
                      for i in range(3))
        cr = pygame.Rect(px + self.kursor_kolom * s + margin,
                         py + self.kursor_baris  * s + margin,
                         s - margin * 2, s - margin * 2)
        pygame.draw.rect(self.layar, cc, cr, 2, border_radius=5)

    def _draw_flag(self, cell_rect, b, k):
        fa   = self.flag_anims.get((b, k))
        sc   = fa.scale() if fa else 1.0
        cx, cy = cell_rect.center
        s = cell_rect.width
        pole_h   = int(s * 0.55 * sc)
        pole_x   = cx - int(s * 0.06)
        pole_top = cy - pole_h // 2
        pygame.draw.line(self.layar, C["flag_pole"],
                         (pole_x, cy + pole_h // 2), (pole_x, pole_top),
                         max(1, int(2 * sc)))
        flag_w = int(s * 0.32 * sc)
        flag_h = int(s * 0.22 * sc)
        pygame.draw.polygon(self.layar, C["flag"], [
            (pole_x,           pole_top),
            (pole_x + flag_w,  pole_top + flag_h // 2),
            (pole_x,           pole_top + flag_h),
        ])

    def _draw_overlay_menu(self):
        ov = pygame.Surface((self.LEBAR, self.TINGGI), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 180))
        self.layar.blit(ov, (0, 0))

        card_w, card_h = 380, 320
        cx = self.LEBAR  // 2
        cy = self.TINGGI // 2
        card = pygame.Rect(cx - card_w//2, cy - card_h//2, card_w, card_h)

        # card shadow
        sh = pygame.Surface((card_w + 20, card_h + 20), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 100), sh.get_rect(), border_radius=20)
        self.layar.blit(sh, (card.x - 10, card.y - 10))
        pygame.draw.rect(self.layar, C["panel"], card, border_radius=18)
        pygame.draw.rect(self.layar, C["panel_border"], card, 2, border_radius=18)

        if self.mode_menu == "pause":
            title_txt = "PAUSED"
            title_col = C["white"]
            opsi      = ["Lanjut", "Ganti Level", "Keluar"]
        elif self.menang:
            title_txt = "YOU WIN!"
            title_col = C["gold"]
            opsi      = ["Main Lagi", "Ganti Level", "Keluar"]
        else:
            title_txt = "GAME OVER"
            title_col = C["red"]
            opsi      = ["Main Lagi", "Ganti Level", "Keluar"]

        title = self.font_huge.render(title_txt, True, title_col)
        self.layar.blit(title, title.get_rect(center=(cx, card.y + 52)))

        if self.mode_menu == "akhir" and self.waktu_selesai is not None:
            bt  = best_times[self.nama_level]
            sub = f"Time: {self.waktu_selesai}s" + (f"  ·  Best: {bt}s" if bt else "")
            s   = self.font_kecil.render(sub, True, C["dim"])
            self.layar.blit(s, s.get_rect(center=(cx, card.y + 100)))

        self.menu_rects = []
        btn_w, btn_h = 260, 48
        mouse = pygame.mouse.get_pos()
        for i, teks in enumerate(opsi):
            bx   = cx - btn_w // 2
            by   = card.y + 130 + i * 62
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            hover = rect.collidepoint(mouse)
            col   = (C["btn_danger_hi"] if hover else C["btn_danger"]) \
                    if teks == "Keluar" else (C["btn_hi"] if hover else C["btn"])
            pygame.draw.rect(self.layar, col, rect, border_radius=12)
            lbl = self.font.render(teks, True, C["white"])
            self.layar.blit(lbl, lbl.get_rect(center=rect.center))
            self.menu_rects.append((teks, rect))


# ── Level select screen ───────────────────────────────────────────────────────
def menu_level():
    W, H  = 500, 420
    layar = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Sapu Ranjau")

    font_title  = pygame.font.SysFont("consolas", 42, bold=True)
    font_sub    = pygame.font.SysFont("segoe ui",  15)
    font_btn    = pygame.font.SysFont("consolas",  22, bold=True)
    font_detail = pygame.font.SysFont("segoe ui",  13)

    bg_particles = [
        {
            "x": random.randint(0, W), "y": random.randint(0, H),
            "r": random.uniform(1, 3),
            "vx": random.uniform(-0.3, 0.3), "vy": random.uniform(-0.3, 0.3),
            "col": random.choice([C["cursor"], C["gold"], C["btn"]]),
            "alpha": random.randint(60, 160),
        }
        for _ in range(35)
    ]

    clock = pygame.time.Clock()
    while True:
        layar.fill(C["bg"])
        for x in range(0, W, 28):
            for y in range(0, H, 28):
                pygame.draw.circle(layar, (22, 30, 44), (x, y), 1)

        for p in bg_particles:
            p["x"] = (p["x"] + p["vx"]) % W
            p["y"] = (p["y"] + p["vy"]) % H
            r_, g_, b_ = p["col"]
            s = pygame.Surface((int(p["r"]*2+1), int(p["r"]*2+1)), pygame.SRCALPHA)
            pygame.draw.circle(s, (r_, g_, b_, p["alpha"]),
                               (int(p["r"]), int(p["r"])), int(p["r"]))
            layar.blit(s, (int(p["x"] - p["r"]), int(p["y"] - p["r"])))

        # title panel
        title_panel = pygame.Rect(30, 22, W - 60, 80)
        pygame.draw.rect(layar, C["panel"], title_panel, border_radius=14)
        pygame.draw.rect(layar, C["panel_border"], title_panel, 2, border_radius=14)
        layar.blit(font_title.render("SAPU RANJAU", True, C["gold"]),
                   font_title.render("SAPU RANJAU", True, C["gold"]).get_rect(center=(W//2, 62)))
        layar.blit(font_sub.render("Select difficulty to start", True, C["dim"]),
                   font_sub.render("Select difficulty to start", True, C["dim"]).get_rect(center=(W//2, 88)))

        mouse  = pygame.mouse.get_pos()
        tombol = {}
        for i, (lvl, (rows, cols, mines)) in enumerate(LEVELS.items()):
            by   = 130 + i * 86
            rect = pygame.Rect(60, by, W - 120, 72)
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(layar, (28, 40, 62) if hover else C["panel"], rect, border_radius=14)
            pygame.draw.rect(layar, C["cursor"] if hover else C["panel_border"], rect, 2, border_radius=14)
            layar.blit(font_btn.render(LEVEL_LABELS[lvl], True, C["gold"] if hover else C["white"]),
                       (rect.x + 20, rect.y + 10))
            layar.blit(font_detail.render(f"{cols}×{rows} grid  ·  {mines} mines", True, C["dim"]),
                       (rect.x + 20, rect.y + 42))
            bt = best_times[lvl]
            if bt is not None:
                bt_txt = font_detail.render(f"Best: {bt}s", True, C["gold"])
                layar.blit(bt_txt, bt_txt.get_rect(midright=(rect.right - 20, rect.centery)))
            tombol[lvl] = rect

        hint = font_detail.render("F11 fullscreen  ·  ESC quit", True, (50, 65, 90))
        layar.blit(hint, hint.get_rect(center=(W//2, H - 16)))

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for lvl, rect in tombol.items():
                    if rect.collidepoint(event.pos):
                        return lvl


# ── Main loop ─────────────────────────────────────────────────────────────────
clock = pygame.time.Clock()

while True:
    level_terpilih = menu_level()
    game = SapuRanjau(level_terpilih)
    ganti_level = False

    while True:
        game.gambar(pygame.mouse.get_pos())
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                k = event.key
                if k == pygame.K_F11:
                    game.toggle_fullscreen()
                elif k == pygame.K_ESCAPE:
                    if game.sedang_jeda:
                        game.resume()
                    else:
                        game.pause()

                if game.tampilkan_menu:
                    continue

                if k in (pygame.K_w, pygame.K_UP):
                    game.kursor_baris = max(0, game.kursor_baris - 1)
                elif k in (pygame.K_s, pygame.K_DOWN):
                    game.kursor_baris = min(game.BARIS - 1, game.kursor_baris + 1)
                elif k in (pygame.K_a, pygame.K_LEFT):
                    game.kursor_kolom = max(0, game.kursor_kolom - 1)
                elif k in (pygame.K_d, pygame.K_RIGHT):
                    game.kursor_kolom = min(game.KOLOM - 1, game.kursor_kolom + 1)
                elif k in (pygame.K_RETURN, pygame.K_SPACE):
                    game.buka_sel(game.kursor_baris, game.kursor_kolom)
                elif k == pygame.K_f:
                    game.toggle_bendera(game.kursor_baris, game.kursor_kolom)
                elif k == pygame.K_r:
                    game.reset()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if hasattr(game, "_smiley_rect") and game._smiley_rect.collidepoint(event.pos):
                    game.reset()
                    continue

                if game.tampilkan_menu:
                    for teks, rect in game.menu_rects:
                        if rect.collidepoint(event.pos):
                            if teks == "Main Lagi":
                                game.reset()
                                game.tampilkan_menu = False
                            elif teks == "Lanjut":
                                game.resume()
                            elif teks == "Ganti Level":
                                ganti_level = True
                            elif teks == "Keluar":
                                pygame.quit(); sys.exit()
                    if ganti_level:
                        break
                    continue

                if not game.game_over:
                    cell = game._cell_at_mouse(*event.pos)
                    if cell:
                        b, k = cell
                        if event.button == 1:
                            game.buka_sel(b, k)
                        elif event.button == 3:
                            game.toggle_bendera(b, k)

            elif event.type == pygame.VIDEORESIZE and not game.is_fullscreen:
                game.LEBAR, game.TINGGI = event.w, event.h

        if ganti_level:
            break
