import pygame

def main():
    pygame.init()
    screen = pygame.display.set_mode((400, 200))
    pygame.display.set_caption("Head Simulator (Use Arrows)")

    yaw = 0.0
    pitch = 0.0
    font = pygame.font.Font(None, 36)

    running = True
    clock = pygame.time.Clock()

    print("Starting Head Simulator...")
    print("Use LEFT/RIGHT for Yaw")
    print("Use UP/DOWN for Pitch")

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            yaw -= 1
        if keys[pygame.K_RIGHT]:
            yaw += 1
        if keys[pygame.K_UP]:
            pitch += 1
        if keys[pygame.K_DOWN]:
            pitch -= 1

        # Clear screen
        screen.fill((0, 0, 0))

        # Render Text
        text_surf = font.render(f"Yaw: {yaw:.1f}, Pitch: {pitch:.1f}", True, (255, 255, 255))
        screen.blit(text_surf, (20, 80))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
