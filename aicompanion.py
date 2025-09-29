import pygame, sys

# Config
SPRITE_FILE = "woman.jpg"
NUM_FRAMES = 10   # number of faces/mouths
WINDOW_SIZE = (800, 800)  # keep big enough for clarity

class SpriteAnimator:
    def __init__(self, sprite_path, num_frames):
        self.sheet = pygame.image.load(sprite_path).convert_alpha()
        self.frames = []
        sheet_width, sheet_height = self.sheet.get_size()

        frame_width = sheet_width // num_frames
        frame_height = sheet_height  # use full height (don't resize vertically)

        for i in range(num_frames):
            rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
            frame = self.sheet.subsurface(rect)
            self.frames.append(frame)

        self.current_frame = 0
        self.timer = 0
        self.frame_delay = 500  # ms per frame

    def update(self, dt):
        self.timer += dt
        if self.timer > self.frame_delay:
            self.timer = 0
            self.current_frame = (self.current_frame + 1) % len(self.frames)

    def draw(self, surface):
        frame = self.frames[self.current_frame]
        # Scale proportionally to fit into window
        frame_aspect = frame.get_width() / frame.get_height()
        new_height = WINDOW_SIZE[1]
        new_width = int(new_height * frame_aspect)

        scaled = pygame.transform.smoothscale(frame, (new_width, new_height))
        surface.blit(scaled, ((WINDOW_SIZE[0] - new_width) // 2, 0))

def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Anime Avatar Test")

    clock = pygame.time.Clock()
    avatar = SpriteAnimator(SPRITE_FILE, NUM_FRAMES)

    running = True
    while running:
        dt = clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        avatar.update(dt)
        screen.fill((255, 255, 255))
        avatar.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
