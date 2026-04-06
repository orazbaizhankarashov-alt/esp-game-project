import math
import pygame

NAME = "MAZE FRUIT"

player_x = 0.0
player_y = 0.0
player_r = 20

score = 0
record = 0
time_total = 45
time_left = 45
timer_start = 0

walls = []
fruits = []
start_pos = (0, 0)

panel_w = 210
maze_left = 20
maze_top = 20
maze_right = 0
maze_bottom = 0
maze_width = 0
maze_height = 0


def millis():
    return pygame.time.get_ticks()


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
    return math.sqrt((dist_x * dist_x) + (dist_y * dist_y)) <= cr


def sx(x):
    return maze_left + int(x * maze_width)


def sy(y):
    return maze_top + int(y * maze_height)


def sw(w):
    return int(w * maze_width)


def sh(h):
    return int(h * maze_height)


def build_maze():
    line = max(10, int(min(maze_width, maze_height) * 0.012))
    result = []

    # outer frame
    result.append((maze_left, maze_top, maze_width, line))
    result.append((maze_left, maze_bottom - line, maze_width, line))
    result.append((maze_left, maze_top, line, maze_height))
    result.append((maze_right - line, maze_top, line, maze_height))

    # inner maze
    result.extend([
        (sx(0.08), sy(0.07), sw(0.28), line),
        (sx(0.36), sy(0.07), line, sh(0.16)),

        (sx(0.56), sy(0.07), sw(0.24), line),
        (sx(0.78), sy(0.07), line, sh(0.12)),

        (sx(0.12), sy(0.18), sw(0.14), line),
        (sx(0.25), sy(0.18), line, sh(0.23)),

        (sx(0.40), sy(0.18), sw(0.36), line),
        (sx(0.74), sy(0.18), line, sh(0.16)),

        (sx(0.08), sy(0.33), sw(0.18), line),
        (sx(0.08), sy(0.33), line, sh(0.12)),

        (sx(0.40), sy(0.33), sw(0.35), line),
        (sx(0.75), sy(0.33), sw(0.18), line),

        (sx(0.41), sy(0.42), line, sh(0.22)),
        (sx(0.69), sy(0.42), sw(0.18), line),
        (sx(0.87), sy(0.33), line, sh(0.20)),

        (sx(0.12), sy(0.45), sw(0.30), line),
        (sx(0.12), sy(0.45), line, sh(0.21)),
        (sx(0.41), sy(0.33), line, sh(0.25)),

        (sx(0.22), sy(0.55), sw(0.20), line),
        (sx(0.69), sy(0.55), sw(0.22), line),
        (sx(0.90), sy(0.55), line, sh(0.18)),

        (sx(0.28), sy(0.66), line, sh(0.14)),
        (sx(0.55), sy(0.63), sw(0.34), line),

        (sx(0.43), sy(0.63), line, sh(0.15)),
        (sx(0.14), sy(0.72), sw(0.12), line),

        (sx(0.10), sy(0.83), sw(0.36), line),
        (sx(0.46), sy(0.83), line, sh(0.11)),

        (sx(0.60), sy(0.86), sw(0.26), line),
    ])

    return result


def build_fruits():
    return [
        [sx(0.28), sy(0.11), True],
        [sx(0.62), sy(0.11), True],
        [sx(0.80), sy(0.24), True],
        [sx(0.12), sy(0.34), True],
        [sx(0.18), sy(0.58), True],
        [sx(0.80), sy(0.63), True],
        [sx(0.50), sy(0.73), True],
    ]


def reset(width, height):
    global player_x, player_y, score, time_left, timer_start
    global walls, fruits, start_pos
    global maze_left, maze_top, maze_right, maze_bottom, maze_width, maze_height

    score = 0
    time_left = time_total
    timer_start = millis()

    maze_left = 20
    maze_top = 20
    maze_right = width - panel_w - 20
    maze_bottom = height - 20
    maze_width = maze_right - maze_left
    maze_height = maze_bottom - maze_top

    walls = build_maze()

    start_pos = (sx(0.86), sy(0.67))
    player_x, player_y = start_pos

    fruits = build_fruits()


def update(width, height, roll_value, pitch_value):
    global player_x, player_y, score, record, time_left, timer_start

    move_x = max(-6, min(6, roll_value * 0.26))
    move_y = max(-6, min(6, pitch_value * 0.26))

    new_x = player_x + move_x
    new_y = player_y + move_y

    hit_x = any(circle_rect_collision(new_x, player_y, player_r, *w) for w in walls)
    hit_y = any(circle_rect_collision(player_x, new_y, player_r, *w) for w in walls)

    if not hit_x:
        player_x = new_x
    if not hit_y:
        player_y = new_y

    player_x = max(maze_left + player_r, min(maze_right - player_r, player_x))
    player_y = max(maze_top + player_r, min(maze_bottom - player_r, player_y))

    for fruit in fruits:
        fx, fy, alive = fruit
        if alive:
            dx = player_x - fx
            dy = player_y - fy
            if math.sqrt(dx * dx + dy * dy) < 28:
                fruit[2] = False
                score += 1
                if score > record:
                    record = score

    if all(not f[2] for f in fruits):
        return "WIN", score

    if millis() - timer_start >= 1000:
        timer_start = millis()
        time_left -= 1
        if time_left <= 0:
            return "GAME_OVER", score

    return "RUNNING", score


def draw_fruit(screen, x, y):
    pygame.draw.circle(screen, (235, 35, 75), (x - 8, y), 10)
    pygame.draw.circle(screen, (235, 35, 75), (x + 8, y), 10)
    pygame.draw.line(screen, (40, 180, 50), (x, y - 10), (x, y - 22), 3)
    pygame.draw.line(screen, (40, 180, 50), (x - 8, y - 8), (x - 2, y - 16), 2)
    pygame.draw.line(screen, (40, 180, 50), (x + 8, y - 8), (x + 2, y - 16), 2)


def draw_player(screen, x, y):
    pygame.draw.circle(screen, (255, 215, 70), (int(x), int(y)), player_r)
    pygame.draw.circle(screen, (25, 25, 25), (int(x - 7), int(y - 5)), 3)
    pygame.draw.circle(screen, (25, 25, 25), (int(x + 7), int(y - 5)), 3)

    pygame.draw.arc(
        screen,
        (25, 25, 25),
        pygame.Rect(int(x - 10), int(y - 2), 20, 12),
        math.radians(20),
        math.radians(160),
        2,
    )


def draw_panel(screen, width, height):
    panel_x = width - panel_w
    pygame.draw.rect(screen, (55, 55, 70), (panel_x, 0, panel_w, height))
    pygame.draw.rect(screen, (120, 220, 255), (panel_x, 0, 4, height))

    title_font = pygame.font.SysFont("Arial", 34, bold=True)
    num_font = pygame.font.SysFont("Arial", 56, bold=True)

    screen.blit(title_font.render("TIME", True, (90, 255, 255)), (panel_x + 42, 28))
    screen.blit(num_font.render(str(time_left), True, (90, 255, 255)), (panel_x + 70, 78))

    screen.blit(title_font.render("score:", True, (70, 220, 70)), (panel_x + 28, 190))
    screen.blit(num_font.render(str(score), True, (70, 220, 70)), (panel_x + 74, 240))

    screen.blit(title_font.render("record:", True, (255, 60, 255)), (panel_x + 22, 370))
    screen.blit(num_font.render(str(record), True, (255, 60, 255)), (panel_x + 74, 420))

    for syy in [26, 150, 340, 530]:
        pygame.draw.circle(screen, (255, 255, 255), (panel_x + 165, syy), 3)
        pygame.draw.circle(screen, (255, 255, 255), (panel_x + 144, syy + 17), 2)
        pygame.draw.circle(screen, (255, 255, 255), (panel_x + 124, syy + 32), 2)


def draw(screen, width, height, font_small, font_med):
    screen.fill((6, 6, 70))

    # maze background block
    pygame.draw.rect(
        screen,
        (8, 8, 78),
        (maze_left, maze_top, maze_width, maze_height)
    )

    for wall in walls:
        pygame.draw.rect(screen, (240, 175, 35), pygame.Rect(*wall), border_radius=3)

    for fruit in fruits:
        if fruit[2]:
            draw_fruit(screen, int(fruit[0]), int(fruit[1]))

    draw_player(screen, player_x, player_y)
    draw_panel(screen, width, height)

    screen.blit(font_med.render(NAME, True, (255, 255, 255)), (24, height - 42))