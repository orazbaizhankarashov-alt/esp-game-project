import random
import pygame

NAME = "APPLE CATCHER"

player_x = 0.0
smooth_x = 0.0
lives = 3
score = 0
best_score = 0
time_total = 60
time_left = 60
apple_speed = 4.0
timer_start = 0
last_speed_update = 0

trail = []
apples = []
obstacles = []


def millis():
    return pygame.time.get_ticks()


def reset(width, height):
    global player_x, smooth_x, lives, score, time_left, apple_speed, timer_start, last_speed_update
    global apples, obstacles, trail

    player_x = width / 2
    smooth_x = width / 2
    lives = 3
    score = 0
    time_left = time_total
    apple_speed = 4.0
    timer_start = millis()
    last_speed_update = 0
    trail = []

    apples = []
    obstacles = []

    for _ in range(8):
        apples.append([random.uniform(50, width - 50), random.uniform(-height, -50)])

    for _ in range(6):
        obstacles.append([random.uniform(50, width - 50), random.uniform(-height, -100), random.uniform(3, 6), random.uniform(0, 360)])


def update(width, height, roll_value):
    global player_x, smooth_x, lives, score, time_left, apple_speed, timer_start, last_speed_update, best_score

    player_x = ((roll_value + 25) / 50.0) * (width - 120)
    player_x = max(0, min(width - 120, player_x))
    smooth_x += (player_x - smooth_x) * 0.2

    trail.append((smooth_x + 60, height - 40))
    if len(trail) > 18:
        trail.pop(0)

    if time_total - time_left > last_speed_update + 5:
        apple_speed += 0.3
        last_speed_update += 5

    for a in apples:
        a[1] += apple_speed

        if a[1] > height - 70 and smooth_x < a[0] < smooth_x + 120:
            score += 1
            a[1] = -50
            a[0] = random.uniform(50, width - 50)

        if a[1] > height:
            a[1] = -50
            a[0] = random.uniform(50, width - 50)

    for o in obstacles:
        o[1] += o[2] + apple_speed * 0.2
        o[3] += 5

        if o[1] > height:
            o[1] = random.uniform(-800, -100)
            o[0] = random.uniform(50, width - 50)

        dx = (smooth_x + 60) - o[0]
        dy = (height - 35) - o[1]
        if (dx * dx + dy * dy) ** 0.5 < 60:
            lives -= 1
            o[1] = random.uniform(-800, -100)

            if lives <= 0:
                best_score = max(best_score, score)
                return "GAME_OVER", score

    if millis() - timer_start >= 1000:
        timer_start = millis()
        time_left -= 1
        if time_left <= 0:
            best_score = max(best_score, score)
            return "GAME_OVER", score

    return "RUNNING", score


def draw(screen, width, height, font_small, font_med):
    screen.fill((10, 20, 35))

    if len(trail) > 1:
        pygame.draw.lines(screen, (0, 255, 200), False, [(int(x), int(y)) for x, y in trail], 4)

    pygame.draw.rect(screen, (0, 250, 150), pygame.Rect(smooth_x, height - 50, 120, 25), border_radius=15)

    for a in apples:
        pygame.draw.circle(screen, (255, 50, 50), (int(a[0]), int(a[1])), 15)

    for o in obstacles:
        pygame.draw.circle(screen, (255, 140, 0), (int(o[0]), int(o[1])), 22)

    screen.blit(font_med.render(NAME, True, (255, 255, 255)), (30, 20))
    screen.blit(font_small.render(f"Score: {score}", True, (255, 255, 255)), (30, 70))
    screen.blit(font_small.render(f"Lives: {lives}", True, (255, 255, 255)), (30, 105))
    screen.blit(font_small.render(f"Time: {time_left}", True, (255, 255, 255)), (30, 140))