from settings import *

class Scoreboard:
    def __init__(self, players):
        self.players = players  # List of players
        self.font = pygame.font.SysFont('Arial', 30)  # Use a default system font

    def draw(self, surface):
        # Draw the scoreboard at the top-left corner
        x, y = 10, 10
        surface.blit(self.font.render("SCOREBOARD:", True, (0, 0, 0)), (x, y))
        for i, player in enumerate(self.players, start=1):
            score_text = f"Player {i} = {player.score}"
            surface.blit(self.font.render(score_text, True, (0, 0, 0)), (x, y + i * 30))