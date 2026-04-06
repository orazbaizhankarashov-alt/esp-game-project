import math
import random
import socket
import sys
import pygame

# =========================
# TCP / PYTHON BRIDGE
# =========================
HOST = "127.0.0.1"
PORT = 5005

client_sock = None
current_source = ""
data_buffer = ""

serial_connected = False
serial_searching = True

scan_interval_ms = 2000
last_scan_time = 0
last_data_time = 0
connection_timeout_ms = 4000

# =========================
# SENSOR
# =========================
roll = 0.0
pitch = 0.0
yaw = 0.0

roll_offset = 0.0
pitch_offset = 0.0
yaw_offset = 0.0

# =========================
# STATES
# =========================
STATE_MAIN_MENU = 0
STATE_APPLE = 1
STATE_MAZE = 2
STATE_SPACE = 3
STATE_PAUSE = 4
STATE_SETTINGS = 5
STATE_GAMEOVER = 6
STATE_WIN = 7

game_state = STATE_MAIN_MENU
previous_game_state = STATE_MAIN_MENU
selected_game = 0
current_game_name = ""

# =========================
# SETTINGS
# =========================
sound_enabled = True
sensor_sensitivity = 1.0
brightness_mode = 2
apple_difficulty = 1.0
maze_speed_factor = 1.0
space_speed_factor = 1.0

settings_index = 0
settings_names = [
    "SOUND",
    "SENSITIVITY",
    "BRIGHTNESS",
    "APPLE DIFFICULTY",
    "MAZE SPEED",
    "SPACE SPEED",
]

# =========================
# UI
# =========================
btn_w = 300
btn_h = 70

# =========================
# BACKGROUND
# =========================
star_x = []
star_y = []
star_speed = []

# =========================
# APPLE CATCHER
# =========================
player_x = 0.0
smooth_x = 0.0
apple_lives = 3
trail = []

apple_count = 8
apple_x = [0.0] * apple_count
apple_y = [0.0] * apple_count

obstacle_count = 6
obs_x = [0.0] * obstacle_count
obs_y = [0.0] * obstacle_count
obs_speed = [0.0] * obstacle_count
obs_angle = [0.0] * obstacle_count

apple_total_time = 60
apple_time_left = 60
apple_score = 0
apple_best_score = 0

apple_speed = 4.0
apple_timer_start = 0
last_apple_speed_update = 0

# =========================
# MAZE RUNNER
# =========================
maze_player_x = 0.0
maze_player_y = 0.0
maze_player_r = 14
maze_lives = 3
maze_time_total = 60
maze_time_left = 60
maze_timer_start = 0

finish_x = 0.0
finish_y = 0.0
finish_w = 0.0
finish_h = 0.0
walls = []
traps = []
maze_last_trap_hit_time = -9999
maze_trap_cooldown_ms = 900

# =========================
# SPACE DODGER
# =========================
ship_x = 0.0
ship_y = 0.0
ship_size = 34
space_lives = 3
space_time_total = 60
space_time_left = 60
space_timer_start = 0
space_score = 0
space_best_score = 0

asteroids = []
coins = []

# =========================
# COMMON
# =========================
explosions = []

# =========================
# PYGAME INIT
# =========================
pygame.init()
pygame.font.init()
pygame.display.set_caption("3 GAMES MENU")

WIDTH, HEIGHT = 1366, 768
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

font_cache = {}


def get_font(size, bold=False):
    key = (size, bold)
    if key not in font_cache:
        font_cache[key] = pygame.font.SysFont("Arial", size, bold=bold)
    return font_cache[key]


def millis():
    return pygame.time.get_ticks()


def play_beep():
    if sound_enabled:
        pass


def play_double_beep():
    if sound_enabled:
        pass


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def map_value(value, start1, stop1, start2, stop2):
    if stop1 == start1:
        return start2
    return start2 + (stop2 - start2) * ((value - start1) / (stop1 - start1))


def draw_text(text, size, color, x, y, align="center", bold=False):
    surf = get_font(size, bold).render(text, True, color)
    rect = surf.get_rect()
    if align == "center":
        rect.center = (x, y)
    elif align == "left":
        rect.midleft = (x, y)
    elif align == "right":
        rect.midright = (x, y)
    screen.blit(surf, rect)


# =========================
# BRIDGE
# =========================
def try_connect_to_bridge():
    global client_sock, current_source, serial_connected, serial_searching
    global last_data_time, last_scan_time, data_buffer

    last_scan_time = millis()
    serial_searching = True

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        s.connect((HOST, PORT))
        s.setblocking(False)

        client_sock = s
        current_source = f"{HOST}:{PORT}"
        serial_connected = True
        serial_searching = False
        last_data_time = millis()
        data_buffer = ""
    except Exception:
        client_sock = None
        current_source = ""
        serial_connected = False
        serial_searching = True


def disconnect_bridge():
    global client_sock, current_source, serial_connected, serial_searching, data_buffer
    try:
        if client_sock is not None:
            client_sock.close()
    except Exception:
        pass

    client_sock = None
    current_source = ""
    serial_connected = False
    serial_searching = True
    data_buffer = ""


def handle_bridge_connection():
    if serial_connected:
        if millis() - last_data_time > connection_timeout_ms:
            disconnect_bridge()

    if not serial_connected and millis() - last_scan_time >= scan_interval_ms:
        try_connect_to_bridge()


def read_mpu():
    global data_buffer, roll, pitch, yaw, last_data_time
    global player_x, smooth_x

    if client_sock is not None:
        try:
            while True:
                chunk = client_sock.recv(4096)
                if not chunk:
                    disconnect_bridge()
                    break
                data_buffer += chunk.decode("utf-8", errors="ignore")
                if len(chunk) < 4096:
                    break
        except BlockingIOError:
            pass
        except Exception:
            disconnect_bridge()

    while "\n" in data_buffer:
        line, data_buffer = data_buffer.split("\n", 1)
        line = line.strip()

        if not line:
            continue
        if line == "READY":
            last_data_time = millis()
            continue
        if line in ("MPU_NOT_FOUND", "OTA_READY", "OTA_START", "OTA_END", "WIFI_FAIL"):
            continue
        if line.startswith("OTA_ERROR_"):
            continue

        parts = line.split(",")
        if len(parts) == 3:
            try:
                roll = float(parts[0])
                pitch = float(parts[1])
                yaw = float(parts[2])
                last_data_time = millis()
            except Exception:
                pass

    player_x = map_value((roll - roll_offset) * sensor_sensitivity, -25, 25, 0, WIDTH - 120)
    player_x = clamp(player_x, 0, WIDTH - 120)
    smooth_x = lerp(smooth_x, player_x, 0.2)

    trail.append((smooth_x + 60, HEIGHT - 40))
    if len(trail) > 15:
        trail.pop(0)


# =========================
# BACKGROUND
# =========================
def init_stars():
    star_x.clear()
    star_y.clear()
    star_speed.clear()
    for _ in range(300):
        star_x.append(random.uniform(0, WIDTH))
        star_y.append(random.uniform(0, HEIGHT))
        star_speed.append(random.uniform(0.5, 3.0))


def draw_gradient_background():
    top = (20, 10, 40)
    bottom = (0, 0, 5)
    for y in range(HEIGHT):
        t = y / max(1, HEIGHT - 1)
        c = (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        )
        pygame.draw.line(screen, c, (0, y), (WIDTH, y))


def draw_stars():
    count_to_draw = 80
    if brightness_mode == 1:
        count_to_draw = 150
    if brightness_mode == 2:
        count_to_draw = 220

    for i in range(count_to_draw):
        pygame.draw.circle(screen, (255, 255, 255), (int(star_x[i]), int(star_y[i])), 1)
        star_y[i] += star_speed[i]
        if star_y[i] > HEIGHT:
            star_y[i] = 0
            star_x[i] = random.uniform(0, WIDTH)


# =========================
# CLASSES
# =========================
class Explosion:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.r = 10
        self.a = 255

    def update(self):
        self.r += 5
        self.a -= 10

    def draw(self):
        if self.a <= 0:
            return
        surf = pygame.Surface((int(self.r * 2 + 12), int(self.r * 2 + 12)), pygame.SRCALPHA)
        pygame.draw.circle(
            surf,
            (255, 100, 0, max(0, self.a)),
            (surf.get_width() // 2, surf.get_height() // 2),
            int(self.r),
            4,
        )
        screen.blit(surf, (self.x - surf.get_width() / 2, self.y - surf.get_height() / 2))

    def finished(self):
        return self.a <= 0


class Wall:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def show(self):
        pygame.draw.rect(
            screen,
            (180, 80, 220),
            pygame.Rect(self.x, self.y, self.w, self.h),
            border_radius=6,
        )


class Trap:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def show(self):
        surf = pygame.Surface((int(self.w), int(self.h)), pygame.SRCALPHA)
        pygame.draw.rect(surf, (255, 0, 0, 160), pygame.Rect(0, 0, self.w, self.h), border_radius=10)
        screen.blit(surf, (self.x, self.y))


class Asteroid:
    def __init__(self, x, y, size, speed):
        self.x = x
        self.y = y
        self.size = size
        self.speed = speed

    def update(self):
        self.y += self.speed * space_speed_factor
        if self.y > HEIGHT + self.size:
            self.reset()

    def reset(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(-HEIGHT, -50)
        self.size = random.uniform(28, 60)
        self.speed = random.uniform(3, 7)

    def show(self):
        pygame.draw.circle(screen, (140, 140, 140), (int(self.x), int(self.y)), int(self.size / 2))
        pygame.draw.circle(screen, (100, 100, 100), (int(self.x - self.size * 0.15), int(self.y - self.size * 0.1)), int(self.size * 0.13))
        pygame.draw.circle(screen, (100, 100, 100), (int(self.x + self.size * 0.2), int(self.y + self.size * 0.1)), int(self.size * 0.09))


class StarCoin:
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.speed = speed

    def update(self):
        self.y += self.speed * space_speed_factor
        if self.y > HEIGHT + 20:
            self.reset()

    def reset(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(-HEIGHT, -50)
        self.speed = random.uniform(2, 4)

    def show(self):
        pts = []
        for i in range(10):
            r = 14 if i % 2 == 0 else 6
            a = math.tau * i / 10.0
            pts.append((self.x + math.cos(a) * r, self.y + math.sin(a) * r))
        pygame.draw.polygon(screen, (255, 220, 0), pts)


def draw_explosions():
    for i in range(len(explosions) - 1, -1, -1):
        e = explosions[i]
        e.update()
        e.draw()
        if e.finished():
            explosions.pop(i)


# =========================
# BUTTONS / MENU
# =========================
def draw_button(label, x, y, active_color):
    rect = pygame.Rect(x, y, btn_w, btn_h)
    hover = rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(screen, active_color if hover else (40, 40, 40), rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=15)
    draw_text(label, 30, (255, 255, 255), x + btn_w / 2, y + btn_h / 2)
    return rect


def draw_menu_button(label, x, y, active_color, selected):
    rect = pygame.Rect(x, y, btn_w, btn_h)
    hover = rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(screen, active_color if (hover or selected) else (40, 40, 40), rect, border_radius=18)
    pygame.draw.rect(screen, (255, 255, 255), rect, 4 if selected else 2, border_radius=18)
    draw_text(label, 28, (255, 255, 255), x + btn_w / 2, y + btn_h / 2)
    return rect


def draw_main_menu():
    draw_text("GAME MENU", 74, (255, 255, 255), WIDTH / 2, HEIGHT / 2 - 230)

    if serial_connected:
        status = "Sensor connected"
    elif serial_searching:
        status = "Python bridge / ESP32 waiting..."
    else:
        status = "No connection"

    draw_text(status, 24, (255, 255, 255), WIDTH / 2, HEIGHT / 2 - 160)

    draw_menu_button("APPLE CATCHER", WIDTH / 2 - btn_w / 2, HEIGHT / 2 - 40, (0, 180, 100), selected_game == 0)
    draw_menu_button("MAZE RUNNER", WIDTH / 2 - btn_w / 2, HEIGHT / 2 + 60, (0, 120, 220), selected_game == 1)
    draw_menu_button("SPACE DODGER", WIDTH / 2 - btn_w / 2, HEIGHT / 2 + 160, (180, 100, 255), selected_game == 2)

    draw_button("SETTINGS", WIDTH / 2 - btn_w / 2, HEIGHT / 2 + 280, (220, 160, 0))
    draw_button("EXIT", WIDTH / 2 - btn_w / 2, HEIGHT / 2 + 380, (200, 50, 50))

    draw_text("Bridge: " + (current_source if serial_connected else "DISCONNECTED"), 18, (255, 255, 255), 40, 50, align="left")
    draw_text(f"Roll: {roll:.2f}", 18, (255, 255, 255), 40, 80, align="left")
    draw_text(f"Pitch: {pitch:.2f}", 18, (255, 255, 255), 40, 110, align="left")


def get_setting_value(i):
    if i == 0:
        return "ON" if sound_enabled else "OFF"
    if i == 1:
        return f"{sensor_sensitivity:.1f}"
    if i == 2:
        return "LOW" if brightness_mode == 0 else "MEDIUM" if brightness_mode == 1 else "HIGH"
    if i == 3:
        return f"{apple_difficulty:.1f}"
    if i == 4:
        return f"{maze_speed_factor:.1f}"
    if i == 5:
        return f"{space_speed_factor:.1f}"
    return ""


def change_setting(direction):
    global sound_enabled, sensor_sensitivity, brightness_mode
    global apple_difficulty, maze_speed_factor, space_speed_factor

    if settings_index == 0:
        if direction != 0:
            sound_enabled = not sound_enabled
            play_beep()
    elif settings_index == 1:
        sensor_sensitivity = clamp(sensor_sensitivity + 0.1 * direction, 0.5, 2.0)
        play_beep()
    elif settings_index == 2:
        brightness_mode = int(clamp(brightness_mode + direction, 0, 2))
        play_beep()
    elif settings_index == 3:
        apple_difficulty = clamp(apple_difficulty + 0.1 * direction, 0.7, 2.0)
        play_beep()
    elif settings_index == 4:
        maze_speed_factor = clamp(maze_speed_factor + 0.1 * direction, 0.7, 2.0)
        play_beep()
    elif settings_index == 5:
        space_speed_factor = clamp(space_speed_factor + 0.1 * direction, 0.7, 2.0)
        play_beep()


def draw_settings_menu():
    draw_text("SETTINGS", 68, (255, 255, 255), WIDTH / 2, 120)

    start_y = 240
    gap = 80

    for i in range(len(settings_names)):
        col = (0, 180, 255) if i == settings_index else (255, 255, 255)
        draw_text(settings_names[i], 28, col, WIDTH / 2 - 220, start_y + i * gap)
        draw_text(get_setting_value(i), 28, (255, 255, 255), WIDTH / 2 + 40, start_y + i * gap, align="left")

    draw_text("LEFT / RIGHT - change value", 22, (255, 255, 255), WIDTH / 2, HEIGHT - 150)
    draw_text("UP / DOWN - choose", 22, (255, 255, 255), WIDTH / 2, HEIGHT - 115)
    draw_text("ESC or M - back", 22, (255, 255, 255), WIDTH / 2, HEIGHT - 80)


def draw_pause_menu():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    draw_text("PAUSED", 78, (255, 255, 255), WIDTH / 2, HEIGHT / 2 - 170)

    draw_button("RESUME", WIDTH / 2 - btn_w / 2, HEIGHT / 2 - 40, (0, 200, 100))
    draw_button("SETTINGS", WIDTH / 2 - btn_w / 2, HEIGHT / 2 + 60, (220, 160, 0))
    draw_button("MENU", WIDTH / 2 - btn_w / 2, HEIGHT / 2 + 160, (0, 120, 220))


# =========================
# APPLE CATCHER
# =========================
def reset_apple_game():
    global apple_score, apple_lives, apple_time_left, apple_speed
    global last_apple_speed_update, apple_timer_start, smooth_x

    apple_score = 0
    apple_lives = 3
    apple_time_left = apple_total_time
    apple_speed = 4.0
    last_apple_speed_update = 0
    apple_timer_start = millis()
    smooth_x = WIDTH / 2

    trail.clear()
    explosions.clear()

    for i in range(apple_count):
        apple_x[i] = random.uniform(50, WIDTH - 50)
        apple_y[i] = random.uniform(-HEIGHT, -50)

    for i in range(obstacle_count):
        obs_x[i] = random.uniform(50, WIDTH - 50)
        obs_y[i] = random.uniform(-HEIGHT, -100)
        obs_speed[i] = random.uniform(3, 6)
        obs_angle[i] = random.uniform(0, math.tau)


def start_apple_game():
    global current_game_name, roll_offset, pitch_offset, yaw_offset, game_state
    current_game_name = "APPLE CATCHER"
    roll_offset = roll
    pitch_offset = pitch
    yaw_offset = yaw
    reset_apple_game()
    game_state = STATE_APPLE
    play_beep()


def update_apple_game():
    global apple_speed, last_apple_speed_update
    global apple_score, apple_lives, game_state, apple_best_score

    if apple_total_time - apple_time_left > last_apple_speed_update + 5:
        apple_speed += 0.3 * apple_difficulty
        last_apple_speed_update += 5

    for i in range(apple_count):
        apple_y[i] += apple_speed

        if apple_y[i] > HEIGHT - 70 and smooth_x < apple_x[i] < smooth_x + 120:
            apple_score += 1
            play_beep()
            apple_y[i] = -50
            apple_x[i] = random.uniform(50, WIDTH - 50)

        if apple_y[i] > HEIGHT:
            apple_y[i] = -50
            apple_x[i] = random.uniform(50, WIDTH - 50)

    for i in range(obstacle_count):
        obs_y[i] += obs_speed[i] + (apple_speed * 0.2)
        obs_angle[i] += 0.05

        if obs_y[i] > HEIGHT:
            obs_y[i] = random.uniform(-800, -100)
            obs_x[i] = random.uniform(50, WIDTH - 50)

        if math.dist((smooth_x + 60, HEIGHT - 35), (obs_x[i], obs_y[i])) < 60:
            apple_lives -= 1
            play_double_beep()
            explosions.append(Explosion(obs_x[i], obs_y[i]))
            obs_y[i] = random.uniform(-800, -100)

            if apple_lives <= 0:
                game_state = STATE_GAMEOVER
                if apple_score > apple_best_score:
                    apple_best_score = apple_score


def draw_apple_game():
    if len(trail) > 1:
        pygame.draw.lines(screen, (0, 255, 200), False, [(int(x), int(y)) for x, y in trail], 4)

    pygame.draw.rect(screen, (0, 250, 150), pygame.Rect(smooth_x, HEIGHT - 50, 120, 25), border_radius=15)

    for i in range(apple_count):
        pygame.draw.circle(screen, (255, 50, 50), (int(apple_x[i]), int(apple_y[i])), 15)

    for i in range(obstacle_count):
        pts = []
        for j in range(6):
            r = 30 if j % 2 == 0 else 15
            a = math.tau * j / 6 + obs_angle[i]
            pts.append((obs_x[i] + math.cos(a) * r, obs_y[i] + math.sin(a) * r))
        pygame.draw.polygon(screen, (255, 100, 0), pts)
        pygame.draw.polygon(screen, (255, 200, 0), pts, 2)

    draw_text("APPLE CATCHER", 25, (255, 255, 255), 40, 40, align="left")
    draw_text(f"Score: {apple_score}", 25, (255, 255, 255), 40, 80, align="left")
    draw_text(f"Speed: {apple_speed:.1f}", 25, (255, 255, 255), 40, 115, align="left")
    draw_text(f"Lives: {apple_lives}", 25, (255, 255, 255), 40, 150, align="left")
    draw_text(f"Time: {apple_time_left}", 25, (255, 255, 255), WIDTH - 40, 50, align="right")
    draw_text("P = Pause | M = Menu", 18, (255, 255, 255), 40, 190, align="left")
    draw_text("Sound: " + ("ON" if sound_enabled else "OFF"), 18, (255, 255, 255), 40, 220, align="left")


def update_apple_timer():
    global apple_timer_start, apple_time_left, game_state, apple_best_score
    if millis() - apple_timer_start >= 1000:
        apple_timer_start = millis()
        apple_time_left -= 1
        if apple_time_left <= 0:
            game_state = STATE_GAMEOVER
            if apple_score > apple_best_score:
                apple_best_score = apple_score


# =========================
# MAZE RUNNER
# =========================
def circle_rect_collision(cx, cy, cr, rx, ry, rw, rh):
    test_x = cx
    test_y = cy

    if cx < rx:
        test_x = rx
    elif cx > rx + rw:
        test_x = rx + rw

    if cy < ry:
        test_y = ry
    elif cy > ry + rh:
        test_y = ry + rh

    dist_x = cx - test_x
    dist_y = cy - test_y
    distance = math.sqrt((dist_x * dist_x) + (dist_y * dist_y))
    return distance <= cr


def reset_maze_game():
    global maze_lives, maze_time_left, maze_timer_start
    global maze_player_x, maze_player_y, maze_last_trap_hit_time
    global finish_x, finish_y, finish_w, finish_h, walls, traps

    maze_lives = 3
    maze_time_left = maze_time_total
    maze_timer_start = millis()
    maze_player_x = 90
    maze_player_y = 120
    maze_last_trap_hit_time = -maze_trap_cooldown_ms

    finish_x = WIDTH - 170
    finish_y = HEIGHT - 160
    finish_w = 100
    finish_h = 80

    walls.clear()
    traps.clear()

    walls.append(Wall(50, 80, WIDTH - 100, 20))
    walls.append(Wall(50, HEIGHT - 80, WIDTH - 100, 20))
    walls.append(Wall(50, 80, 20, HEIGHT - 160))
    walls.append(Wall(WIDTH - 70, 80, 20, HEIGHT - 160))

    walls.append(Wall(140, 140, 500, 20))
    walls.append(Wall(140, 140, 20, 220))
    walls.append(Wall(260, 240, 20, 300))
    walls.append(Wall(260, 520, 350, 20))
    walls.append(Wall(420, 140, 20, 260))
    walls.append(Wall(420, 380, 300, 20))
    walls.append(Wall(620, 220, 20, 300))
    walls.append(Wall(760, 140, 20, 220))
    walls.append(Wall(860, 280, 240, 20))
    walls.append(Wall(980, 280, 20, 240))
    walls.append(Wall(760, 560, 260, 20))
    walls.append(Wall(1080, 420, 20, 160))
    walls.append(Wall(180, 660, 240, 20))
    walls.append(Wall(180, 660, 20, 150))
    walls.append(Wall(500, 680, 20, 140))
    walls.append(Wall(620, 640, 260, 20))

    traps.append(Trap(180, 180, 70, 70))
    traps.append(Trap(300, 560, 120, 60))
    traps.append(Trap(470, 250, 80, 80))
    traps.append(Trap(690, 430, 90, 90))
    traps.append(Trap(885, 330, 85, 85))
    traps.append(Trap(820, 600, 120, 50))


def start_maze_game():
    global current_game_name, roll_offset, pitch_offset, yaw_offset, game_state
    current_game_name = "MAZE RUNNER"
    roll_offset = roll
    pitch_offset = pitch
    yaw_offset = yaw
    reset_maze_game()
    game_state = STATE_MAZE
    play_beep()


def update_maze_game():
    global maze_player_x, maze_player_y
    global maze_lives, maze_last_trap_hit_time, game_state
    global maze_timer_start, maze_time_left

    move_x = map_value((roll - roll_offset) * sensor_sensitivity, -25, 25, -5, 5) * maze_speed_factor
    move_y = map_value((pitch - pitch_offset) * sensor_sensitivity, -25, 25, -5, 5) * maze_speed_factor

    new_x = maze_player_x + move_x
    new_y = maze_player_y + move_y

    hit_x = any(circle_rect_collision(new_x, maze_player_y, maze_player_r, w.x, w.y, w.w, w.h) for w in walls)
    hit_y = any(circle_rect_collision(maze_player_x, new_y, maze_player_r, w.x, w.y, w.w, w.h) for w in walls)

    if not hit_x:
        maze_player_x = new_x
    if not hit_y:
        maze_player_y = new_y

    maze_player_x = clamp(maze_player_x, maze_player_r, WIDTH - maze_player_r)
    maze_player_y = clamp(maze_player_y, maze_player_r, HEIGHT - maze_player_r)

    for t in traps:
        if circle_rect_collision(maze_player_x, maze_player_y, maze_player_r, t.x, t.y, t.w, t.h):
            if millis() - maze_last_trap_hit_time > maze_trap_cooldown_ms:
                maze_lives -= 1
                maze_last_trap_hit_time = millis()
                play_double_beep()
                maze_player_x = 90
                maze_player_y = 120

                if maze_lives <= 0:
                    game_state = STATE_GAMEOVER

    if finish_x < maze_player_x < finish_x + finish_w and finish_y < maze_player_y < finish_y + finish_h:
        play_double_beep()
        game_state = STATE_WIN

    if millis() - maze_timer_start >= 1000:
        maze_timer_start = millis()
        maze_time_left -= 1
        if maze_time_left <= 0:
            game_state = STATE_GAMEOVER


def draw_maze_game():
    draw_text("MAZE RUNNER", 26, (255, 255, 255), 40, 40, align="left")
    draw_text(f"Lives: {maze_lives}", 26, (255, 255, 255), 40, 80, align="left")
    draw_text(f"Time: {maze_time_left}", 26, (255, 255, 255), 40, 115, align="left")
    draw_text("P = Pause | M = Menu", 22, (255, 255, 255), 40, 150, align="left")

    pygame.draw.rect(screen, (0, 220, 120), pygame.Rect(finish_x, finish_y, finish_w, finish_h), border_radius=16)
    draw_text("FINISH", 24, (255, 255, 255), finish_x + finish_w / 2, finish_y + finish_h / 2)
    draw_text("START", 22, (255, 255, 255), 80, 110, align="left")

    for w in walls:
        w.show()
    for t in traps:
        t.show()

    pygame.draw.circle(screen, (80, 180, 255), (int(maze_player_x), int(maze_player_y)), maze_player_r)

    if millis() - maze_last_trap_hit_time < 250:
        pygame.draw.circle(screen, (255, 80, 80), (int(maze_player_x), int(maze_player_y)), int(maze_player_r * 1.5), 4)


# =========================
# SPACE DODGER
# =========================
def reset_space_game():
    global ship_x, ship_y, space_lives, space_time_left, space_timer_start, space_score
    global asteroids, coins

    ship_x = WIDTH / 2
    ship_y = HEIGHT - 120
    space_lives = 3
    space_time_left = space_time_total
    space_timer_start = millis()
    space_score = 0

    asteroids.clear()
    coins.clear()

    for _ in range(8):
        asteroids.append(
            Asteroid(
                random.uniform(0, WIDTH),
                random.uniform(-HEIGHT, 0),
                random.uniform(28, 60),
                random.uniform(3, 7),
            )
        )

    for _ in range(4):
        coins.append(
            StarCoin(
                random.uniform(0, WIDTH),
                random.uniform(-HEIGHT, 0),
                random.uniform(2, 4),
            )
        )


def start_space_game():
    global current_game_name, roll_offset, pitch_offset, yaw_offset, game_state
    current_game_name = "SPACE DODGER"
    roll_offset = roll
    pitch_offset = pitch
    yaw_offset = yaw
    reset_space_game()
    game_state = STATE_SPACE
    play_beep()


def update_space_game():
    global ship_x, ship_y, space_lives, game_state, space_score

    move_x = map_value((roll - roll_offset) * sensor_sensitivity, -25, 25, -7, 7) * space_speed_factor
    move_y = map_value((pitch - pitch_offset) * sensor_sensitivity, -25, 25, -7, 7) * space_speed_factor

    ship_x += move_x
    ship_y += move_y

    ship_x = clamp(ship_x, 40, WIDTH - 40)
    ship_y = clamp(ship_y, 80, HEIGHT - 40)

    for a in asteroids:
        a.update()
        if math.dist((ship_x, ship_y), (a.x, a.y)) < (ship_size / 2 + a.size / 2):
            explosions.append(Explosion(a.x, a.y))
            play_double_beep()
            space_lives -= 1
            a.reset()

            if space_lives <= 0:
                game_state = STATE_GAMEOVER

    for c in coins:
        c.update()
        if math.dist((ship_x, ship_y), (c.x, c.y)) < 28:
            play_beep()
            space_score += 1
            c.reset()


def draw_ship(x, y):
    pts = [
        (x, y - ship_size / 2),
        (x - ship_size / 2, y + ship_size / 2),
        (x + ship_size / 2, y + ship_size / 2),
    ]
    flame = [
        (x, y + ship_size / 2 + 6),
        (x - 8, y + ship_size / 2 - 8),
        (x + 8, y + ship_size / 2 - 8),
    ]

    pygame.draw.polygon(screen, (100, 200, 255), pts)
    pygame.draw.polygon(screen, (255, 180, 0), flame)


def draw_space_game():
    draw_text("SPACE DODGER", 26, (255, 255, 255), 40, 40, align="left")
    draw_text(f"Score: {space_score}", 26, (255, 255, 255), 40, 80, align="left")
    draw_text(f"Lives: {space_lives}", 26, (255, 255, 255), 40, 115, align="left")
    draw_text(f"Time: {space_time_left}", 26, (255, 255, 255), 40, 150, align="left")
    draw_text("P = Pause | M = Menu", 22, (255, 255, 255), 40, 185, align="left")

    for a in asteroids:
        a.show()
    for c in coins:
        c.show()

    draw_ship(ship_x, ship_y)


def update_space_timer():
    global space_timer_start, space_time_left, game_state, space_best_score
    if millis() - space_timer_start >= 1000:
        space_timer_start = millis()
        space_time_left -= 1
        if space_time_left <= 0:
            if space_score > space_best_score:
                space_best_score = space_score
            game_state = STATE_WIN


# =========================
# RESULT SCREENS
# =========================
def draw_game_over_screen():
    draw_text("GAME OVER", 82, (255, 0, 0), WIDTH / 2, HEIGHT / 2 - 180)
    draw_text("Game: " + current_game_name, 34, (255, 255, 255), WIDTH / 2, HEIGHT / 2 - 95)

    if current_game_name == "APPLE CATCHER":
        draw_text(f"Score: {apple_score}", 34, (255, 255, 255), WIDTH / 2, HEIGHT / 2 - 35)
        draw_text(f"Best: {apple_best_score}", 34, (255, 255, 255), WIDTH / 2, HEIGHT / 2 + 10)
    elif current_game_name == "SPACE DODGER":
        draw_text(f"Score: {space_score}", 34, (255, 255, 255), WIDTH / 2, HEIGHT / 2 - 35)
        draw_text(f"Best: {space_best_score}", 34, (255, 255, 255), WIDTH / 2, HEIGHT / 2 + 10)
    else:
        draw_text("You ran out of lives or time", 34, (255, 255, 255), WIDTH / 2, HEIGHT / 2 - 10)

    draw_button("RESTART", WIDTH / 2 - btn_w / 2, HEIGHT / 2 + 100, (0, 200, 100))
    draw_button("MENU", WIDTH / 2 - btn_w / 2, HEIGHT / 2 + 200, (0, 120, 220))


def draw_win_screen():
    global space_best_score
    draw_text("YOU WIN!", 82, (0, 255, 120), WIDTH / 2, HEIGHT / 2 - 180)
    draw_text("Game: " + current_game_name, 34, (255, 255, 255), WIDTH / 2, HEIGHT / 2 - 95)

    if current_game_name == "MAZE RUNNER":
        draw_text(f"Time Left: {maze_time_left}", 34, (255, 255, 255), WIDTH / 2, HEIGHT / 2 - 25)
    elif current_game_name == "SPACE DODGER":
        if space_score > space_best_score:
            space_best_score = space_score
        draw_text(f"Final Score: {space_score}", 34, (255, 255, 255), WIDTH / 2, HEIGHT / 2 - 25)

    draw_button("RESTART", WIDTH / 2 - btn_w / 2, HEIGHT / 2 + 110, (0, 200, 100))
    draw_button("MENU", WIDTH / 2 - btn_w / 2, HEIGHT / 2 + 210, (0, 120, 220))


# =========================
# INPUT
# =========================
def restart_current_game():
    if current_game_name == "APPLE CATCHER":
        start_apple_game()
    elif current_game_name == "MAZE RUNNER":
        start_maze_game()
    elif current_game_name == "SPACE DODGER":
        start_space_game()


def handle_mouse_pressed(pos):
    global game_state, previous_game_state, selected_game

    x = WIDTH / 2 - btn_w / 2

    if game_state == STATE_MAIN_MENU:
        if pygame.Rect(x, HEIGHT / 2 - 40, btn_w, btn_h).collidepoint(pos):
            selected_game = 0
            if serial_connected:
                start_apple_game()
        elif pygame.Rect(x, HEIGHT / 2 + 60, btn_w, btn_h).collidepoint(pos):
            selected_game = 1
            if serial_connected:
                start_maze_game()
        elif pygame.Rect(x, HEIGHT / 2 + 160, btn_w, btn_h).collidepoint(pos):
            selected_game = 2
            if serial_connected:
                start_space_game()
        elif pygame.Rect(x, HEIGHT / 2 + 280, btn_w, btn_h).collidepoint(pos):
            previous_game_state = STATE_MAIN_MENU
            game_state = STATE_SETTINGS
            play_beep()
        elif pygame.Rect(x, HEIGHT / 2 + 380, btn_w, btn_h).collidepoint(pos):
            shutdown()

    elif game_state == STATE_PAUSE:
        if pygame.Rect(x, HEIGHT / 2 - 40, btn_w, btn_h).collidepoint(pos):
            game_state = previous_game_state
            play_beep()
        elif pygame.Rect(x, HEIGHT / 2 + 60, btn_w, btn_h).collidepoint(pos):
            game_state = STATE_SETTINGS
            play_beep()
        elif pygame.Rect(x, HEIGHT / 2 + 160, btn_w, btn_h).collidepoint(pos):
            game_state = STATE_MAIN_MENU
            play_beep()

    elif game_state in (STATE_GAMEOVER, STATE_WIN):
        restart_y = HEIGHT / 2 + 100 if game_state == STATE_GAMEOVER else HEIGHT / 2 + 110
        menu_y = HEIGHT / 2 + 200 if game_state == STATE_GAMEOVER else HEIGHT / 2 + 210

        if pygame.Rect(x, restart_y, btn_w, btn_h).collidepoint(pos):
            restart_current_game()
        elif pygame.Rect(x, menu_y, btn_w, btn_h).collidepoint(pos):
            game_state = STATE_MAIN_MENU
            play_beep()


def handle_key_pressed(event):
    global game_state, previous_game_state, selected_game, settings_index

    if event.key == pygame.K_p:
        if game_state in (STATE_APPLE, STATE_MAZE, STATE_SPACE):
            previous_game_state = game_state
            game_state = STATE_PAUSE
            play_beep()
            return
        elif game_state == STATE_PAUSE:
            game_state = previous_game_state
            play_beep()
            return

    if event.key == pygame.K_m:
        if game_state == STATE_SETTINGS:
            game_state = previous_game_state
            play_beep()
        elif game_state in (STATE_APPLE, STATE_MAZE, STATE_SPACE, STATE_PAUSE, STATE_GAMEOVER, STATE_WIN):
            game_state = STATE_MAIN_MENU
            play_beep()

    if game_state == STATE_MAIN_MENU:
        if event.key == pygame.K_UP:
            selected_game = max(0, selected_game - 1)
            play_beep()
        if event.key == pygame.K_DOWN:
            selected_game = min(2, selected_game + 1)
            play_beep()
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if not serial_connected:
                return
            if selected_game == 0:
                start_apple_game()
            elif selected_game == 1:
                start_maze_game()
            elif selected_game == 2:
                start_space_game()
        if event.key == pygame.K_s:
            previous_game_state = STATE_MAIN_MENU
            game_state = STATE_SETTINGS
            play_beep()

    elif game_state == STATE_SETTINGS:
        if event.key == pygame.K_UP:
            settings_index = max(0, settings_index - 1)
            play_beep()
        if event.key == pygame.K_DOWN:
            settings_index = min(len(settings_names) - 1, settings_index + 1)
            play_beep()
        if event.key == pygame.K_LEFT:
            change_setting(-1)
        if event.key == pygame.K_RIGHT:
            change_setting(1)
        if event.key == pygame.K_ESCAPE:
            game_state = previous_game_state
            play_beep()
            return

    if event.key == pygame.K_ESCAPE and game_state != STATE_SETTINGS:
        shutdown()


# =========================
# MAIN LOOP
# =========================
def shutdown():
    disconnect_bridge()
    pygame.quit()
    sys.exit()


def setup():
    init_stars()
    reset_apple_game()
    reset_maze_game()
    reset_space_game()
    try_connect_to_bridge()


def draw():
    draw_gradient_background()
    draw_stars()

    handle_bridge_connection()
    read_mpu()

    if game_state == STATE_MAIN_MENU:
        draw_main_menu()
    elif game_state == STATE_APPLE:
        update_apple_game()
        draw_apple_game()
        update_apple_timer()
        draw_explosions()
    elif game_state == STATE_MAZE:
        update_maze_game()
        draw_maze_game()
    elif game_state == STATE_SPACE:
        update_space_game()
        draw_space_game()
        update_space_timer()
        draw_explosions()
    elif game_state == STATE_PAUSE:
        draw_pause_menu()
    elif game_state == STATE_SETTINGS:
        draw_settings_menu()
    elif game_state == STATE_GAMEOVER:
        draw_game_over_screen()
    elif game_state == STATE_WIN:
        draw_win_screen()


def main():
    setup()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown()
            elif event.type == pygame.KEYDOWN:
                handle_key_pressed(event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_mouse_pressed(event.pos)

        draw()
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()