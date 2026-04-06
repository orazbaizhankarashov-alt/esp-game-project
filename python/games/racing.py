import random
import pygame

NAME = "HIGHWAY RACING"

car_x = 0
car_y = 0
car_w = 52
car_h = 96

road_left = 0
road_right = 0
road_width = 0

lane_centers = []
obstacles = []

score = 0
best_score = 0
road_offset = 0
spawn_timer = 0
game_over_flash = 0


def reset(width, height):
    global car_x, car_y, road_left, road_right, road_width
    global lane_centers, obstacles, score, road_offset, spawn_timer, game_over_flash

    road_width = int(width * 0.56)
    road_left = (width - road_width) // 2
    road_right = road_left + road_width

    lane_count = 4
    lane_w = road_width / lane_count
    lane_centers = [road_left + lane_w * (i + 0.5) for i in range(lane_count)]

    car_x = lane_centers[1]
    car_y = height - 140

    obstacles = []
    score = 0
    road_offset = 0
    spawn_timer = 0
    game_over_flash = 0


def spawn_vehicle(height):
    lane = random.choice(lane_centers)
    kind = random.choice(["car", "truck", "bike"])

    if kind == "car":
        w, h = 48, 92
        speed = random.uniform(9.0, 12.0)
        color = random.choice([(210, 40, 40), (40, 120, 220), (240, 180, 40)])
    elif kind == "truck":
        w, h = 56, 150
        speed = random.uniform(7.0, 9.0)
        color = random.choice([(220, 220, 220), (180, 180, 200), (230, 230, 255)])
    else:
        w, h = 28, 62
        speed = random.uniform(11.0, 14.0)
        color = random.choice([(80, 80, 80), (30, 30, 30), (160, 0, 0)])

    obstacles.append({
        "x": lane,
        "y": -h,
        "w": w,
        "h": h,
        "speed": speed,
        "kind": kind,
        "color": color,
    })


def rect_hit(ax, ay, aw, ah, bx, by, bw, bh):
    return (
        ax - aw / 2 < bx + bw / 2 and
        ax + aw / 2 > bx - bw / 2 and
        ay - ah / 2 < by + bh / 2 and
        ay + ah / 2 > by - bh / 2
    )


def update(width, height, roll_value):
    global car_x, obstacles, score, best_score, road_offset, spawn_timer, game_over_flash

    target_x = ((roll_value + 25) / 50.0) * (road_width - 100) + road_left + 50
    car_x += (target_x - car_x) * 0.18
    car_x = max(road_left + 35, min(road_right - 35, car_x))

    road_offset += 14
    if road_offset >= 70:
        road_offset = 0

    spawn_timer += 1
    if spawn_timer >= 22:
        spawn_timer = 0
        if len(obstacles) < 8:
            spawn_vehicle(height)

    for obj in obstacles:
        obj["y"] += obj["speed"]

        if rect_hit(
            car_x, car_y, car_w, car_h,
            obj["x"], obj["y"], obj["w"], obj["h"]
        ):
            best_score = max(best_score, score)
            game_over_flash = 10
            return "GAME_OVER", score

    obstacles = [o for o in obstacles if o["y"] < height + 200]

    score += 1
    return "RUNNING", score


def draw_player_car(screen, x, y):
    body = pygame.Rect(0, 0, car_w, car_h)
    body.center = (int(x), int(y))

    pygame.draw.rect(screen, (245, 245, 245), body, border_radius=14)

    glass = pygame.Rect(body.x + 10, body.y + 16, body.w - 20, 26)
    pygame.draw.rect(screen, (120, 170, 255), glass, border_radius=8)

    roof = pygame.Rect(body.x + 8, body.y + 46, body.w - 16, 24)
    pygame.draw.rect(screen, (210, 210, 210), roof, border_radius=8)

    pygame.draw.rect(screen, (25, 25, 25), (body.x + 4, body.y + 12, 8, 18), border_radius=4)
    pygame.draw.rect(screen, (25, 25, 25), (body.right - 12, body.y + 12, 8, 18), border_radius=4)
    pygame.draw.rect(screen, (25, 25, 25), (body.x + 4, body.bottom - 30, 8, 18), border_radius=4)
    pygame.draw.rect(screen, (25, 25, 25), (body.right - 12, body.bottom - 30, 8, 18), border_radius=4)


def draw_vehicle(screen, obj):
    x = int(obj["x"])
    y = int(obj["y"])
    w = obj["w"]
    h = obj["h"]
    color = obj["color"]

    rect = pygame.Rect(0, 0, w, h)
    rect.center = (x, y)

    if obj["kind"] == "truck":
        trailer = pygame.Rect(rect.x + 6, rect.y + 28, rect.w - 12, rect.h - 34)
        cabin = pygame.Rect(rect.x, rect.y, rect.w, 34)
        pygame.draw.rect(screen, (220, 40, 40), cabin, border_radius=8)
        pygame.draw.rect(screen, color, trailer, border_radius=6)
        pygame.draw.rect(screen, (30, 30, 30), (rect.x + 4, rect.y + 8, 8, 18), border_radius=4)
        pygame.draw.rect(screen, (30, 30, 30), (rect.right - 12, rect.y + 8, 8, 18), border_radius=4)
    elif obj["kind"] == "bike":
        pygame.draw.rect(screen, color, rect, border_radius=10)
        pygame.draw.circle(screen, (20, 20, 20), (x, rect.y + 18), 8)
        pygame.draw.circle(screen, (20, 20, 20), (x, rect.bottom - 18), 8)
    else:
        pygame.draw.rect(screen, color, rect, border_radius=12)
        glass = pygame.Rect(rect.x + 8, rect.y + 12, rect.w - 16, 22)
        pygame.draw.rect(screen, (130, 170, 255), glass, border_radius=6)
        pygame.draw.rect(screen, (20, 20, 20), (rect.x + 4, rect.y + 10, 8, 16), border_radius=4)
        pygame.draw.rect(screen, (20, 20, 20), (rect.right - 12, rect.y + 10, 8, 16), border_radius=4)
        pygame.draw.rect(screen, (20, 20, 20), (rect.x + 4, rect.bottom - 26, 8, 16), border_radius=4)
        pygame.draw.rect(screen, (20, 20, 20), (rect.right - 12, rect.bottom - 26, 8, 16), border_radius=4)


def draw_road(screen, width, height):
    screen.fill((20, 16, 18))

    sidewalk_color = (168, 150, 140)
    border_color = (190, 190, 190)
    road_color = (70, 70, 70)

    pygame.draw.rect(screen, sidewalk_color, (0, 0, road_left, height))
    pygame.draw.rect(screen, sidewalk_color, (road_right, 0, width - road_right, height))
    pygame.draw.rect(screen, road_color, (road_left, 0, road_width, height))

    pygame.draw.rect(screen, border_color, (road_left - 8, 0, 8, height))
    pygame.draw.rect(screen, border_color, (road_right, 0, 8, height))

    for i in range(1, 4):
        x = int(road_left + i * road_width / 4)
        for y in range(-70, height, 70):
            yy = y + road_offset
            pygame.draw.rect(screen, (245, 245, 245), (x - 4, yy, 8, 34), border_radius=3)

    left_yellow = road_left + 42
    right_yellow = road_right - 42

    for y in range(-50, height, 50):
        yy = y + road_offset
        pygame.draw.rect(screen, (240, 210, 50), (left_yellow, yy, 6, 28), border_radius=3)
        pygame.draw.rect(screen, (240, 210, 50), (right_yellow, yy, 6, 28), border_radius=3)

    sign_positions = [120, 260, 420, 580]
    for sy in sign_positions:
        if sy < height - 60:
            pygame.draw.rect(screen, (210, 230, 210), (30, sy, 56, 28), border_radius=4)
            pygame.draw.rect(screen, (210, 230, 210), (width - 86, sy, 56, 28), border_radius=4)
            pygame.draw.rect(screen, (120, 200, 120), (36, sy + 6, 44, 16), border_radius=3)
            pygame.draw.rect(screen, (120, 200, 120), (width - 80, sy + 6, 44, 16), border_radius=3)


def draw(screen, width, height, font_small, font_med):
    draw_road(screen, width, height)

    for obj in obstacles:
        draw_vehicle(screen, obj)

    draw_player_car(screen, car_x, car_y)

    panel = pygame.Rect(width - 170, 20, 140, 74)
    pygame.draw.rect(screen, (0, 0, 0), panel)
    pygame.draw.rect(screen, (255, 255, 255), panel, 2)

    seconds = score // 60
    time_text = f"00:{seconds:02d}"
    txt = pygame.font.SysFont("Arial", 34, bold=True).render(time_text, True, (255, 255, 255))
    screen.blit(txt, (panel.centerx - txt.get_width() // 2, panel.centery - txt.get_height() // 2))

    screen.blit(font_med.render(NAME, True, (255, 255, 255)), (28, 20))
    screen.blit(font_small.render(f"Score: {score}", True, (255, 255, 255)), (28, 62))
    screen.blit(font_small.render(f"Best: {best_score}", True, (255, 255, 255)), (28, 90))