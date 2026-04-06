import socket
import sys
import pygame

from firebase_logger import FirebaseLogger
from games import apple, maze, racing

HOST = "127.0.0.1"
PORT = 5005

pygame.init()
pygame.font.init()
pygame.display.set_caption("ESP32 3 GAMES")

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
clock = pygame.time.Clock()

font_title = pygame.font.SysFont("Arial", 74, bold=True)
font_big = pygame.font.SysFont("Arial", 42, bold=True)
font_med = pygame.font.SysFont("Arial", 28, bold=True)
font_small = pygame.font.SysFont("Arial", 20)

STATE_MENU = 0
STATE_APPLE = 1
STATE_MAZE = 2
STATE_RACING = 3
STATE_PAUSE = 4
STATE_GAMEOVER = 5
STATE_WIN = 6

game_state = STATE_MENU
previous_game_state = STATE_MENU
selected_game = 0
current_game_name = ""
last_result_score = 0

roll = 0.0
pitch = 0.0
yaw = 0.0

roll_offset = 0.0
pitch_offset = 0.0
yaw_offset = 0.0

sock = None
data = ""
connected = False
last_reconnect_ms = 0
reconnect_interval_ms = 2000

logger = FirebaseLogger()

stars = []
button_w = 360
button_h = 76

menu_buttons = []
control_button = None
overlay_buttons = {}
show_overlay_menu = False


def init_stars():
    stars.clear()
    for i in range(240):
        stars.append([float((i * 11) % WIDTH), float((i * 17) % HEIGHT), 1 + (i % 3)])


def draw_background():
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

    for s in stars:
        pygame.draw.circle(screen, (255, 255, 255), (int(s[0]), int(s[1])), 1)
        s[1] += s[2]
        if s[1] > HEIGHT:
            s[1] = 0


def connect_bridge():
    global sock, connected
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        s.setblocking(False)
        sock = s
        connected = True
    except Exception:
        sock = None
        connected = False


def try_reconnect_bridge():
    global last_reconnect_ms
    now = pygame.time.get_ticks()
    if connected:
        return
    if now - last_reconnect_ms >= reconnect_interval_ms:
        last_reconnect_ms = now
        connect_bridge()


def read_sensor():
    global data, roll, pitch, yaw, connected, sock

    if sock is None:
        return

    try:
        while True:
            chunk = sock.recv(4096).decode("utf-8", errors="ignore")
            if not chunk:
                connected = False
                try:
                    sock.close()
                except Exception:
                    pass
                sock = None
                return
            data += chunk
    except BlockingIOError:
        pass
    except Exception:
        connected = False
        try:
            sock.close()
        except Exception:
            pass
        sock = None
        return

    while "\n" in data:
        line, data = data.split("\n", 1)
        line = line.strip()

        if not line:
            continue

        if line in ("READY", "MPU_NOT_FOUND", "OTA_READY", "OTA_START", "OTA_END", "WIFI_FAIL"):
            continue

        if line.startswith("OTA_ERROR_"):
            continue

        parts = line.split(",")
        if len(parts) == 3:
            try:
                roll = float(parts[0])
                pitch = float(parts[1])
                yaw = float(parts[2])
            except Exception:
                pass


def draw_center_text(text, font, color, y):
    surf = font.render(text, True, color)
    screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))


def draw_button_rect(rect, text, selected=False, active_color=(0, 180, 100)):
    mouse_pos = pygame.mouse.get_pos()
    hover = rect.collidepoint(mouse_pos)

    if selected:
        fill = active_color
    elif hover:
        fill = (85, 85, 85)
    else:
        fill = (40, 40, 40)

    pygame.draw.rect(screen, fill, rect, border_radius=18)
    pygame.draw.rect(screen, (255, 255, 255), rect, 3 if selected else 2, border_radius=18)

    txt = font_med.render(text, True, (255, 255, 255))
    screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))


def draw_menu():
    global menu_buttons
    draw_background()
    menu_buttons = []

    draw_center_text("GAME MENU", font_title, (255, 255, 255), 100)

    status = "Sensor connected" if connected else "Bridge / ESP32 waiting..."
    draw_center_text(status, font_small, (230, 230, 230), 205)

    labels = ["APPLE CATCHER", "MAZE RUNNER", "TILT RACING"]
    colors = [(0, 180, 100), (0, 120, 220), (180, 100, 255)]
    ys = [290, 390, 490]

    for i, label in enumerate(labels):
        rect = pygame.Rect(WIDTH // 2 - button_w // 2, ys[i], button_w, button_h)
        draw_button_rect(rect, label, selected_game == i, colors[i])
        menu_buttons.append(rect)

    exit_rect = pygame.Rect(WIDTH // 2 - 120, 610, 240, 65)
    draw_button_rect(exit_rect, "EXIT", False, (200, 50, 50))
    menu_buttons.append(exit_rect)

    draw_center_text("UP / DOWN - choose    ENTER - start", font_small, (220, 220, 220), HEIGHT - 110)
    draw_center_text("Mouse-пен де басуға болады", font_small, (220, 220, 220), HEIGHT - 75)

    screen.blit(font_small.render(f"ROLL: {roll:.2f}", True, (255, 255, 255)), (30, 30))
    screen.blit(font_small.render(f"PITCH: {pitch:.2f}", True, (255, 255, 255)), (30, 60))
    screen.blit(font_small.render(f"YAW: {yaw:.2f}", True, (255, 255, 255)), (30, 90))


def draw_top_control_button():
    global control_button
    rect = pygame.Rect(WIDTH - 190, 25, 150, 48)
    control_button = rect
    draw_button_rect(rect, "OPTIONS")


def draw_overlay_menu():
    global overlay_buttons
    overlay_buttons = {}

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))

    box = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 170, 440, 340)
    pygame.draw.rect(screen, (30, 30, 30), box, border_radius=24)
    pygame.draw.rect(screen, (255, 255, 255), box, 2, border_radius=24)

    draw_center_text("OPTIONS", font_big, (255, 255, 255), HEIGHT // 2 - 125)

    resume_rect = pygame.Rect(WIDTH // 2 - 140, HEIGHT // 2 - 40, 280, 58)
    menu_rect = pygame.Rect(WIDTH // 2 - 140, HEIGHT // 2 + 35, 280, 58)
    exit_rect = pygame.Rect(WIDTH // 2 - 140, HEIGHT // 2 + 110, 280, 58)

    draw_button_rect(resume_rect, "RESUME")
    draw_button_rect(menu_rect, "MENU")
    draw_button_rect(exit_rect, "EXIT")

    overlay_buttons["resume"] = resume_rect
    overlay_buttons["menu"] = menu_rect
    overlay_buttons["exit"] = exit_rect


def calibrate_sensor():
    global roll_offset, pitch_offset, yaw_offset
    roll_offset = roll
    pitch_offset = pitch
    yaw_offset = yaw


def start_game(idx):
    global game_state, current_game_name, last_result_score, show_overlay_menu

    calibrate_sensor()
    last_result_score = 0
    show_overlay_menu = False

    if idx == 0:
        current_game_name = apple.NAME
        apple.reset(WIDTH, HEIGHT)
        game_state = STATE_APPLE
    elif idx == 1:
        current_game_name = maze.NAME
        maze.reset(WIDTH, HEIGHT)
        game_state = STATE_MAZE
    elif idx == 2:
        current_game_name = racing.NAME
        racing.reset(WIDTH, HEIGHT)
        game_state = STATE_RACING

    logger.start_game(current_game_name)


def handle_result(status, value):
    global game_state, last_result_score, show_overlay_menu

    if status == "GAME_OVER":
        last_result_score = value
        logger.save_score(current_game_name, value)
        logger.end_game("game_over")
        show_overlay_menu = False
        game_state = STATE_GAMEOVER

    elif status == "WIN":
        last_result_score = value
        logger.save_score(current_game_name, value)
        logger.end_game("win")
        show_overlay_menu = False
        game_state = STATE_WIN


def draw_pause():
    draw_background()
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))

    draw_center_text("PAUSED", font_title, (255, 255, 255), 180)
    draw_center_text("Press P to resume", font_big, (255, 255, 255), 340)
    draw_center_text("ESC - exit", font_big, (255, 255, 255), 410)


def draw_result(title_text):
    draw_background()
    draw_center_text(title_text, font_title, (255, 255, 255), 150)
    draw_center_text(f"Game: {current_game_name}", font_big, (255, 255, 255), 320)
    draw_center_text(f"Result: {last_result_score}", font_big, (255, 255, 255), 390)
    draw_center_text("R - restart    M - menu    ESC - exit", font_small, (220, 220, 220), 520)


def end_to_menu():
    global game_state, show_overlay_menu
    logger.end_game("menu")
    show_overlay_menu = False
    game_state = STATE_MENU


def restart_current_game():
    if current_game_name == apple.NAME:
        start_game(0)
    elif current_game_name == maze.NAME:
        start_game(1)
    elif current_game_name == racing.NAME:
        start_game(2)


def shutdown():
    try:
        logger.app_close()
    except Exception:
        pass

    try:
        if sock is not None:
            sock.close()
    except Exception:
        pass

    pygame.quit()
    sys.exit()


def handle_mouse_click(pos):
    global selected_game, game_state, show_overlay_menu

    if game_state == STATE_MENU:
        if len(menu_buttons) >= 4:
            if menu_buttons[0].collidepoint(pos):
                selected_game = 0
                start_game(0)
            elif menu_buttons[1].collidepoint(pos):
                selected_game = 1
                start_game(1)
            elif menu_buttons[2].collidepoint(pos):
                selected_game = 2
                start_game(2)
            elif menu_buttons[3].collidepoint(pos):
                shutdown()

    elif game_state in (STATE_APPLE, STATE_MAZE, STATE_RACING):
        if show_overlay_menu:
            if overlay_buttons.get("resume") and overlay_buttons["resume"].collidepoint(pos):
                show_overlay_menu = False
            elif overlay_buttons.get("menu") and overlay_buttons["menu"].collidepoint(pos):
                show_overlay_menu = False
                end_to_menu()
            elif overlay_buttons.get("exit") and overlay_buttons["exit"].collidepoint(pos):
                shutdown()
        else:
            if control_button and control_button.collidepoint(pos):
                show_overlay_menu = True

    elif game_state == STATE_PAUSE:
        pass

    elif game_state in (STATE_GAMEOVER, STATE_WIN):
        pass


def main():
    global selected_game, game_state, previous_game_state, show_overlay_menu

    init_stars()
    connect_bridge()
    logger.app_open()

    while True:
        try_reconnect_bridge()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_mouse_click(event.pos)

            if event.type == pygame.KEYDOWN:
                if game_state == STATE_MENU:
                    if event.key == pygame.K_UP:
                        selected_game = max(0, selected_game - 1)
                    elif event.key == pygame.K_DOWN:
                        selected_game = min(2, selected_game + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        start_game(selected_game)
                    elif event.key == pygame.K_ESCAPE:
                        shutdown()

                elif game_state in (STATE_APPLE, STATE_MAZE, STATE_RACING):
                    if event.key == pygame.K_p:
                        previous_game_state = game_state
                        game_state = STATE_PAUSE
                        show_overlay_menu = False
                    elif event.key == pygame.K_m:
                        show_overlay_menu = False
                        end_to_menu()
                    elif event.key == pygame.K_ESCAPE:
                        shutdown()

                elif game_state == STATE_PAUSE:
                    if event.key == pygame.K_p:
                        game_state = previous_game_state
                    elif event.key == pygame.K_m:
                        end_to_menu()
                    elif event.key == pygame.K_ESCAPE:
                        shutdown()

                elif game_state in (STATE_GAMEOVER, STATE_WIN):
                    if event.key == pygame.K_r:
                        restart_current_game()
                    elif event.key == pygame.K_m:
                        game_state = STATE_MENU
                    elif event.key == pygame.K_ESCAPE:
                        shutdown()

        read_sensor()

        if game_state == STATE_MENU:
            draw_menu()

        elif game_state == STATE_APPLE:
            status, value = apple.update(WIDTH, HEIGHT, roll - roll_offset)
            apple.draw(screen, WIDTH, HEIGHT, font_small, font_med)
            draw_top_control_button()
            if show_overlay_menu:
                draw_overlay_menu()
            handle_result(status, value)

        elif game_state == STATE_MAZE:
            status, value = maze.update(WIDTH, HEIGHT, roll - roll_offset, pitch - pitch_offset)
            maze.draw(screen, WIDTH, HEIGHT, font_small, font_med)
            draw_top_control_button()
            if show_overlay_menu:
                draw_overlay_menu()
            handle_result(status, value)

        elif game_state == STATE_RACING:
            status, value = racing.update(WIDTH, HEIGHT, roll - roll_offset)
            racing.draw(screen, WIDTH, HEIGHT, font_small, font_med)
            draw_top_control_button()
            if show_overlay_menu:
                draw_overlay_menu()
            handle_result(status, value)

        elif game_state == STATE_PAUSE:
            draw_pause()

        elif game_state == STATE_GAMEOVER:
            draw_result("GAME OVER")

        elif game_state == STATE_WIN:
            draw_result("YOU WIN")

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()