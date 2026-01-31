#pgzero
import random

# ========== ПОЛЕ ==========
cell = Actor('border')
road = Actor('floor')
size_w = 5
size_h = 10
WIDTH = cell.width * size_w
HEIGHT = cell.height * size_h

TITLE = "Погоня от полиции"
FPS = 30

# ========== КАРТА ==========
my_map = [[0, 0, 0, 0, 0],
          [0, 1, 1, 1, 0],
          [0, 1, 1, 1, 0],
          [0, 1, 1, 1, 0],
          [0, 1, 1, 1, 0],
          [0, 1, 1, 1, 0],
          [0, 1, 1, 1, 0],
          [0, 1, 1, 1, 0],
          [0, 0, 0, 0, 0],
          [-1, -1, -1, -1, -1]]

# ========== ГЕРОЙ ==========
car = Actor('car')
car.x = cell.width * 2
car.y = HEIGHT - cell.height * 2
car.health = 100
car.speed_boost = 1

# ========== ПОЛИЦЕЙСКИЕ МАШИНЫ ==========
police_cars = []

def spawn_police():
    lane = random.randint(1, 3)
    x = cell.width * lane
    y = -cell.height
    police = Actor('police', topleft=(x, y))
    police.health = 20
    police.attack = 10
    police.bonus = random.randint(1, 3)
    police_cars.append(police)

for _ in range(5):
    spawn_police()

# ========== БОНУСЫ ==========
boosts = []
armors = []

# ========== УРОВЕНЬ ==========
level = 1

# ========== ОТРИСОВКА КАРТЫ ==========
def map_draw():
    for i in range(8):
        for j in range(5):
            if my_map[i][j] == 0:
                cell.left = j * cell.width
                cell.top = i * cell.height
                cell.draw()
            elif my_map[i][j] == 1:
                road.left = j * cell.width
                road.top = i * cell.height
                road.draw()

# ========== ОТРИСОВКА ==========
def draw():
    screen.fill("#2f3542")
    map_draw()
    car.draw()
    
    screen.draw.text("HP:", (25, 475), color="white", fontsize=20)
    screen.draw.text(str(car.health), (75, 475), color="white", fontsize=20)
    screen.draw.text("Уровень: " + str(level), (350, 475), color="yellow", fontsize=20)

    for p in police_cars:
        p.draw()
    for b in boosts:
        b.draw()
    for a in armors:
        a.draw()

# ========== УПРАВЛЕНИЕ ==========
def on_key_down(key):
    old_x = car.x

    if keyboard.left and car.x > cell.width:
        car.x -= cell.width
    elif keyboard.right and car.x < cell.width * 3:
        car.x += cell.width

    idx = car.collidelist(police_cars)
    if idx != -1:
        car.x = old_x
        police = police_cars[idx]
        car.health -= police.attack
        police.health -= 10
        if police.health <= 0:
            if police.bonus == 1:
                b = Actor("star")
                b.pos = police.pos
                boosts.append(b)
            elif police.bonus == 2:
                a = Actor("shield")
                a.pos = police.pos
                armors.append(a)
            police_cars.pop(idx)

# ========== ДВИЖЕНИЕ ==========
def update():
    global level

    for p in police_cars:
        p.y += 5

    for p in police_cars[:]:
        if p.y > HEIGHT:
            police_cars.remove(p)
            spawn_police()

    for b in boosts[:]:
        if car.colliderect(b):
            boosts.remove(b)
            car.speed_boost += 0.5

    for a in armors[:]:
        if car.colliderect(a):
            armors.remove(a)
            car.health += 30

    if car.health <= 0:
        screen.fill("black")
        screen.draw.text("ПОРАЖЕНИЕ", center=(WIDTH//2, HEIGHT//2), color="red", fontsize=60)
        screen.draw.text("Нажми R", center=(WIDTH//2, HEIGHT//2 + 50), color="white", fontsize=30)
