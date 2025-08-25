#!/usr/bin/env python3

import sys
import random
import json
from typing import List
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QInputDialog
from PyQt6.QtGui import QPainter, QPaintEvent, QPixmap, QKeyEvent, QFont, QLinearGradient, QColor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QRect, QUrl
from PyQt6.QtMultimedia import QSoundEffect

# --- Constants ---
WORLD_W = 1000
"""@brief Width of the game world in pixels."""

WORLD_H = 800
"""@brief Height of the game world in pixels."""

PLAYER_WIDTH = 60
"""@brief Width of the player sprite in pixels."""

PLAYER_HEIGHT = 40
"""@brief Height of the player sprite in pixels."""

GROUND_HEIGHT = 50
"""@brief Height of the ground at the bottom of the screen in pixels."""

ALIEN_SPRITE_COUNT = 6
"""@brief Number of different alien sprites available."""

SCORES_FILE = Path(__file__).parent / "scores.json"
#SCORES_FILE = Path.home() / "Library" / "Application Support" / "SpaceInvaders" / "scores.json"
"""@brief Filename used for storing and loading high scores."""

ALIEN_ANIM_SPEED = 30
"""
@brief Controls the speed of alien animation.
@details
Higher values make the aliens animate slower, lower values animate faster.
Example approximate speeds:
- 10 → ~6 FPS (fast)
- 20 → ~3 FPS (medium)
- 30 → ~2 FPS (classic arcade)
- 60 → ~1 FPS (very slow, lumbering aliens)
"""

ASSET_DIR = Path(__file__).parent / "assets"
"""@brief directory with external files."""

# ---------------------------------------------------------------------
# High Scores Management
# ---------------------------------------------------------------------
class HighScores:
    """
    Handles loading, saving, and updating high scores.

    Attributes:
        file (Path): Path to the JSON file storing scores.
        scores (List[dict]): List of high score entries.
    """

    def __init__(self) -> None:
        """
        @brief Initializes the HighScores object.

        @details
        Creates a HighScores instance and loads any existing high scores from
        the file defined by SCORES_FILE. If the file does not exist, initializes
        an empty score list.

        @post
        - `self.file` is a Path object pointing to the high scores JSON file.
        - `self.scores` is a list containing existing high scores or an empty list.
        """
        # Path next to this script
        self.file: Path = Path(__file__).parent / "scores.json"
        # Ensure parent directory exists
        self.file.parent.mkdir(parents=True, exist_ok=True)
        # Load existing scores or initialize empty list
        self.scores: List[dict] = self.load_scores()

    def load_scores(self) -> List[dict]:
        """
        @brief Loads the high scores from a JSON file.

        @details
        Reads the high scores from the file specified by `self.file`. If the file
        exists, it parses the JSON content into a list of dictionaries. Each dictionary
        represents a score entry with keys such as 'initials' (str) and 'score' (int).
        If the file does not exist, an empty list is returned.

        @return List[dict] A list of dictionaries representing the saved high scores.
                         Returns an empty list if the file does not exist or is empty.

        @note Each score entry dictionary contains:
              - 'initials' (str): The player's initials.
              - 'score' (int): The player's score.
        """
        if self.file.exists():
            try:
                with open(self.file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # If file is corrupted, start fresh
                return []
        return []

    def save_scores(self) -> None:
        """
        @brief Saves the current high scores to a JSON file.

        @details
        Writes the list of high score entries stored in `self.scores` to the file
        specified by `self.file`. The scores are saved in JSON format, overwriting
        any existing content in the file.

        @return None

        @note Each entry in `self.scores` is a dictionary with the following keys:
              - 'initials' (str): The player's initials.
              - 'score' (int): The player's score.
        """
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file, "w") as f:
                json.dump(self.scores, f, indent=2)
        except (OSError, IOError) as e:
            print(f"Warning: Could not save high scores to {self.file}: {e}")

    def is_high_score(self, score: int) -> bool:
        """
        @brief Determines whether a given score qualifies as a high score.

        @details
        Checks if the provided `score` is high enough to be included in the high
        scores list. If fewer than 10 scores exist, any new score qualifies.
        Otherwise, it must be higher than at least one existing score.

        @param[in] score The score to check (integer).

        @return True if the score qualifies as a high score, False otherwise.

        @note This method does not modify the list of high scores; it only evaluates
              eligibility.
        """
        if len(self.scores) < 10:
            return True
        return any(score > s['score'] for s in self.scores)

    def add_score(self, initials: str, score: int) -> None:
        """
        @brief Adds a new score to the high scores list and maintains the top 10.

        @details
        Appends the given `score` with the player's `initials` to the high scores
        list. The list is then sorted in descending order by score, and only the
        top 10 entries are retained. Finally, the updated list is saved to file.

        @param[in] initials Player initials (string, up to 3 characters).
        @param[in] score Player score (integer).

        @post The high scores list is updated and persisted to disk.
        """
        self.scores.append({"initials": initials.strip()[:3].upper(), "score": score})
        self.scores.sort(key=lambda x: x['score'], reverse=True)
        self.scores = self.scores[:10]
        self.save_scores()

# ---------------------------------------------------------------------
# Game Logic Worker Thread
# ---------------------------------------------------------------------
class GameWorker(QThread):
    """
    @class GameWorker
    @brief Handles the Space Invaders game logic in a separate thread.

    @details
    This class manages the entire game state including:
      - Player movement and input
      - Alien movement and shooting
      - Bullet updates and collision detection
      - Mystery ship logic
      - Score, lives, level, and game over conditions

    The class runs in its own QThread, periodically updating the game state
    and emitting signals to the main GUI thread for rendering and interaction.

    @signals
    update_signal(dict)
        Emitted whenever the game state changes. The dictionary contains
        positions, sprites, scores, bullets, aliens, and other relevant info.

    request_initials(int)
        Emitted when the game ends, requesting the player to enter their
        initials with the final score as argument.
    """

    update_signal = pyqtSignal(dict)
    request_initials = pyqtSignal(int)

    def __init__(self) -> None:
        """
        @brief Initializes the GameWorker thread and default game state.

        @details
        Sets up the thread for running the game logic in the background, 
        initializes the running flag, the game state dictionary, key tracking 
        for player input, and sets the default difficulty to 'E' (Easy).
        """
        super().__init__()
        self.running = False
        self.state = {}
        self.keys_pressed = {'left': False, 'right': False}
        self.difficulty = 'E'

    def run(self) -> None:
        """
        @brief Main execution loop of the GameWorker thread.

        @details
        Continuously updates the game state while the thread is running.
        Checks if the game is paused; if not, it calls `update_logic()` to
        progress the game state. Sleeps for 50 milliseconds between iterations
        to control update frequency.

        @note
        This method is automatically invoked when `start()` is called on the thread.
        """
        self.running = True
        while self.running:
            if not self.state.get('paused', False):
                self.update_logic()
            self.msleep(50)

    def start_game(self, difficulty: str) -> None:
        """
        @brief Starts a new game at the specified difficulty.

        @param difficulty Difficulty level as a string:
                          'E' = Easy, 'M' = Medium, 'H' = Hard.

        @details
        Resets the game state, initializes the alien animation counter,
        sets the running flag, and starts the GameWorker thread if it
        is not already running.
        """
        self.difficulty = difficulty
        self.reset_state()
        self.state['alien_anim_counter'] = 0
        self.running = True
        if not self.isRunning():
            self.start()

    def reset_state(self) -> None:
        """
        @brief Resets the entire game state to initial values.

        @details
        Initializes player position, bullets, aliens, alien movement direction
        and speed, animation counters, score, lives, level, game over flag,
        key states, alien shooting cooldown, paused state, shots fired counter,
        and mystery ship state. Also calls `create_aliens()` to populate the
        alien formation.
        """
        self.state = {
            'player_x': (WORLD_W - PLAYER_WIDTH) // 2,
            'player_y': WORLD_H - GROUND_HEIGHT - PLAYER_HEIGHT,
            'bullets': [],
            'alien_bullets': [],
            'aliens': [],
            'alien_direction': 1,
            'alien_speed': 10,
            'alien_anim_counter': 0,
            'score': 0,
            'lives': 3,
            'level': 1,
            'game_over': False,
            'keys_pressed': self.keys_pressed.copy(),
            'alien_shoot_cooldown': 0,
            'paused': False,
            'shots_fired': 0,
            'mystery_ship': None,
            'mystery_ship_direction': 1,
            'mystery_ship_cooldown': random.randint(600, 1000)
        }
        self.create_aliens()

    def create_aliens(self) -> None:
        """Populate the alien formation at the start of a level."""
        self.state['aliens'].clear()
        alien_rows = ["squid", "crab", "crab", "octopus", "octopus"]
        for row, alien_type in enumerate(alien_rows):
            for col in range(11):
                color_index = random.randint(0, 5)
                alien = {
                    'x': 50 + col * 50,
                    'y': 50 + row * 40,
                    'type': alien_type,
                    'color_index': color_index,
                    'frame': 0
                }
                self.state['aliens'].append(alien)

    def calculate_mystery_ship_score(self) -> int:
        """
        @brief Populates the alien formation at the start of a level.

        @details
        Creates a 5-row by 11-column grid of alien entities. Each row has a
        predefined alien type: "squid", "crab", or "octopus". Each alien is
        assigned a random color index (0–5) and an initial animation frame of 0.
        The aliens are stored in `self.state['aliens']` as dictionaries with keys:
        - 'x' (int): X-coordinate
        - 'y' (int): Y-coordinate
        - 'type' (str): Alien type
        - 'color_index' (int): Color variation index
        - 'frame' (int): Animation frame index
        """
        self.state['shots_fired'] += 1
        increment = ((self.state['shots_fired'] + 22) % 15) * 50
        return min(50 + increment, 300)

    def update_logic(self) -> None:
        """
        @brief Perform one step of the game logic: movement, collisions, and state updates.

        @details
        This method updates all dynamic elements of the game for one tick.
        It handles:

        - Player movement based on currently pressed keys.
        - Bullet movement and removal when off-screen.
        - Alien movement, edge detection, and animation frame updates.
        - Alien shooting behavior with difficulty-based cooldowns.
        - Mystery ship spawning, movement, and collisions.
        - Collision detection between player bullets and aliens/mystery ship.
        - Alien bullets colliding with the player and life decrement.
        - Level progression when all aliens are destroyed.
        - Game over if aliens reach the player's row or player loses all lives.
        - Emits updated game state via `update_signal`.

        @note Animation is throttled by `ANIM_SPEED` to slow down frame updates.
        @note Collision rectangles use optional padding for more forgiving hit detection.
        """
        if self.state.get('game_over', True):
            return

        # Player movement
        if self.state.get('keys_pressed'):
            if self.state['keys_pressed'].get('left'):
                self.state['player_x'] = max(0, self.state['player_x'] - 10)
            if self.state['keys_pressed'].get('right'):
                self.state['player_x'] = min(WORLD_W - PLAYER_WIDTH, self.state['player_x'] + 10)

        # Move bullets
        self.state['bullets'] = [[bx, by - 20] for bx, by in self.state['bullets'] if by > 0]
        self.state['alien_bullets'] = [[bx, by + 15] for bx, by in self.state['alien_bullets'] if by < WORLD_H]

        # Move aliens & animate
        edge_hit = False
        self.state['alien_anim_counter'] += 1
        for alien in self.state['aliens']:
            alien['x'] += self.state['alien_direction'] * self.state['alien_speed']
            if alien['x'] <= 0 or alien['x'] >= WORLD_W - 40:
                edge_hit = True

        # Animate every N ticks
        ANIM_SPEED = 5  # number of update_logic() calls per frame change
        if self.state['alien_anim_counter'] >= ANIM_SPEED:
            for alien in self.state['aliens']:
                alien['frame'] = (alien.get('frame', 0) + 1) % 2
            self.state['alien_anim_counter'] = 0

        if edge_hit:
            self.state['alien_direction'] *= -1
            for alien in self.state['aliens']:
                alien['y'] += 20

        # Alien shooting logic
        cooldowns = {'E': 15, 'M': 7, 'H': 3}
        if self.state['alien_shoot_cooldown'] <= 0:
            if self.state['aliens'] and random.random() < 0.3:
                shooter = random.choice(self.state['aliens'])
                self.state['alien_bullets'].append([shooter['x'] + 18, shooter['y'] + 30])
                self.state['alien_shoot_cooldown'] = cooldowns.get(self.difficulty, 20)
                self.update_signal.emit({'alien_fire': True})
        else:
            self.state['alien_shoot_cooldown'] -= 1

        # Mystery ship movement
        if self.state['mystery_ship'] is None:
            self.state['mystery_ship_cooldown'] -= 1
            if self.state['mystery_ship_cooldown'] <= 0:
                start_x = 0 if random.choice([True, False]) else WORLD_W - 60
                direction = 1 if start_x == 0 else -1
                self.state['mystery_ship'] = [start_x, 50]
                self.state['mystery_ship_direction'] = direction
        else:
            self.state['mystery_ship'][0] += self.state['mystery_ship_direction'] * 5
            if self.state['mystery_ship'][0] < -60 or self.state['mystery_ship'][0] > WORLD_W:
                self.state['mystery_ship'] = None
                self.state['mystery_ship_cooldown'] = random.randint(600, 1000)

        # Collision detection
        remaining_aliens = []
        for alien in self.state['aliens']:
            hit = False
            for b in self.state['bullets']:
                padding = 5
                if QRect(b[0], b[1], 5, 15).intersects(QRect(alien['x'] - padding, alien['y'] - padding, 40 + padding, 30 + padding)):
                    hit = True
                    self.state['score'] += 10 * (1 if self.difficulty == 'E' else 2 if self.difficulty == 'M' else 3)
                    self.state['bullets'].remove(b)
                    break
            if not hit:
                remaining_aliens.append(alien)
        self.state['aliens'] = remaining_aliens

        # Mystery ship collisions
        if self.state['mystery_ship']:
            for b in self.state['bullets']:
                if QRect(b[0], b[1], 5, 15).intersects(QRect(self.state['mystery_ship'][0], self.state['mystery_ship'][1], 60, 30)):
                    self.state['bullets'].remove(b)
                    self.state['score'] += self.calculate_mystery_ship_score()
                    self.state['mystery_ship'] = None
                    self.state['mystery_ship_cooldown'] = random.randint(600, 1000)
                    break

        # Alien bullets hitting player
        for b in self.state['alien_bullets'].copy():
            if QRect(b[0], b[1], 5, 15).intersects(QRect(self.state['player_x'], self.state['player_y'], PLAYER_WIDTH, PLAYER_HEIGHT)):
                self.state['lives'] -= 1
                self.state['alien_bullets'].remove(b)
                if self.state['lives'] <= 0:
                    self.state['game_over'] = True
                    self.request_initials.emit(self.state['score'])

        # Level completion
        if not self.state['aliens']:
            self.state['level'] += 1
            self.state['alien_speed'] += 2
            self.create_aliens()

        # Aliens reach bottom
        for alien in self.state['aliens']:
            if alien['y'] + 30 >= self.state['player_y']:
                self.state['game_over'] = True
                self.request_initials.emit(self.state['score'])
                break

        # Emit state
        self.update_signal.emit(self.state.copy())

# ---------------------------------------------------------------------
# Main Game Widget
# ---------------------------------------------------------------------
class SpaceInvadersGame(QWidget):
    """
    @brief Main QWidget for the Space Invaders game GUI.

    @details
    This class handles the full game interface, including:

    - Rendering of the player, aliens, bullets, and mystery ship.
    - Managing sprite assets and animations.
    - Processing user input (keyboard events) for movement and firing.
    - Playing sound effects for shooting, explosions, and game events.
    - Tracking game state including score, level, and lives.
    - Interfacing with the GameWorker thread for game logic updates.
    - Managing high scores using the HighScores class.
    
    @note This widget should be instantiated and displayed within a QApplication context.
    """

    def __init__(self, parent=None) -> None:
        """
        @brief Initialize the main game widget.

        @param parent Optional parent widget. Defaults to None.

        @details
        Sets up the main game interface, loads sprites and sounds, 
        initializes the game worker thread, and prepares the GUI timer.

        @attributes
        - worker (GameWorker): Thread handling the game logic.
        - state (dict): Current game state dictionary.
        - keys_pressed (dict): Tracks left/right movement keys.
        - selecting_difficulty (bool): True if the difficulty selection screen is active.
        - highscores (HighScores): Manages high score data.
        - player_sprite (QPixmap): Player character sprite.
        - bullet_sprite (QPixmap): Player bullet sprite.
        - alien_sprites (dict): Alien sprites organized by type, color, and frame.
        - mystery_ship_sprite (QPixmap): Mystery ship sprite.
        - shoot_sound (QSoundEffect): Sound effect for player shooting.
        - alien_shoot_sound (QSoundEffect): Sound effect for alien shooting.
        - timer (QTimer): GUI update timer.
        - space_pressed (bool): Prevents automatic repeated firing when space is held.
        """
        super().__init__(parent)
        self.setFixedSize(WORLD_W, WORLD_H)

        # Game thread
        self.worker = GameWorker()
        self.worker.update_signal.connect(self.receive_state)
        self.worker.request_initials.connect(self.get_initials)

        self.state = {}
        self.keys_pressed = {'left': False, 'right': False}
        self.selecting_difficulty = True
        self.highscores = HighScores()

        # Sprites
        self.player_sprite = QPixmap(str(ASSET_DIR/"player.png")).scaled(PLAYER_WIDTH, PLAYER_HEIGHT)
        self.bullet_sprite = QPixmap(str(ASSET_DIR/"bullet.png")).scaled(5, 15)
        self.mystery_ship_sprite = QPixmap(str(ASSET_DIR/"mystery_ship.png")).scaled(60, 30)

        self.alien_sprites = {
            "squid": [
                [QPixmap(str(ASSET_DIR/f"alien_squid_{color}_{frame}.png")).scaled(40,30)
                 for frame in range(2)] for color in range(6)
            ],
            "crab": [
                [QPixmap(str(ASSET_DIR/f"alien_crab_{color}_{frame}.png")).scaled(40,30)
                 for frame in range(2)] for color in range(6)
            ],
            "octopus": [
                [QPixmap(str(ASSET_DIR/f"alien_octopus_{color}_{frame}.png")).scaled(40,30)
                 for frame in range(2)] for color in range(6)
            ]
        }
        self.init_aliens()

        # Sounds
        self.shoot_sound = QSoundEffect()
        self.shoot_sound.setSource(QUrl.fromLocalFile(str(Path(ASSET_DIR/"shoot.wav").resolve())))   
        self.shoot_sound.setVolume(0.5)

        self.alien_shoot_sound = QSoundEffect()
        self.alien_shoot_sound.setSource(QUrl.fromLocalFile(str(Path(ASSET_DIR/"alien_shoot.wav").resolve())))  
        self.alien_shoot_sound.setVolume(0.5)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # GUI update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(30)

        # Shooting control
        self.space_pressed = False

    def init_aliens(self) -> None:
        """
        @brief Spawn the aliens in the classic Space Invaders formation.

        @details
        Populates the game state with alien dictionaries arranged in 5 rows.
        Each alien dictionary contains position, type, color variant, and animation frame.

        @note
        The formation consists of:
            - Row 0: Squid
            - Row 1-2: Crab
            - Row 3-4: Octopus

        @attributes
        Each alien dictionary has the following keys:
            - "x" (int): X-coordinate on the game canvas.
            - "y" (int): Y-coordinate on the game canvas.
            - "type" (str): Alien type ("squid", "crab", or "octopus").
            - "color_index" (int): Index representing the color variant.
            - "frame" (int): Current animation frame (0 or 1).
        """
        self.state["aliens"] = []
        alien_rows = ["squid", "crab", "crab", "octopus", "octopus"]

        for row, alien_type in enumerate(alien_rows):
            for col in range(11):
                color_index = random.randint(0, 5)
                alien = {
                    "x": 50 + col * 50,
                    "y": 50 + row * 40,
                    "type": alien_type,
                    "color_index": color_index,
                    "frame": 0
                }
                self.state["aliens"].append(alien)

    def receive_state(self, state: dict) -> None:
        """
        @brief Receive the latest game state from the worker thread.

        @details
        Updates the local game state with the dictionary received from `GameWorker`.
        Plays the alien shooting sound if an alien fired in this update and the game
        is neither paused nor over. Refreshes the GUI by calling `update()`.

        @param state dict The current game state dictionary, which may include:
            - 'alien_fire' (bool): True if an alien fired a bullet this frame.
            - 'game_over' (bool): True if the game has ended.
            - 'paused' (bool): True if the game is paused.
            - Other keys reflecting player position, aliens, bullets, score, etc.

        @note This method is connected to the `update_signal` emitted by `GameWorker`.
        """
        if state.get('alien_fire', False) and not state.get('game_over', False) and not state.get('paused', False):
            self.alien_shoot_sound.play()
        self.state = state
        self.update()

    def update_key_state(self) -> None:
        """
        @brief Update the key press state in the game worker.

        @details
        Copies the current key press states (left/right) from the main widget
        and sends them to the `GameWorker` thread. Ensures that the worker thread
        has the latest input from the player for processing movement.

        @note This method should be called whenever the key state changes
        (e.g., on key press or key release events).

        @return None
        """
        self.worker.state['keys_pressed'] = self.keys_pressed.copy()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        @brief Handle key press events for game control and debug commands.

        @details
        Processes user input and updates game state accordingly.
        Supports standard gameplay, difficulty selection, and debug actions.

        Supported keys:
          - Left/Right arrows: Move the player left or right.
          - Space: Shoot a bullet (prevents automatic repeated firing).
          - Q: Quit the application.
          - R: Restart the game and return to difficulty selection.
          - P: Pause/unpause the game.
          - E/M/H: Select difficulty (Easy, Medium, Hard) when in difficulty selection mode.
          - L: Add an extra life (debug).
          - S: Add 100 points to the score (debug).
          - M: Spawn a mystery ship (debug).

        @param event QKeyEvent containing the key press information.

        @note When difficulty selection is active, only E/M/H keys are processed.
        All other key presses are ignored until a difficulty is selected.

        @return None
        """
        key = event.key()

        if key == Qt.Key.Key_Left:
            self.keys_pressed['left'] = True
        elif key == Qt.Key.Key_Right:
            self.keys_pressed['right'] = True
        elif key == Qt.Key.Key_Space:
            if 'bullets' in self.state and not self.space_pressed:
                self.state['bullets'].append([self.state['player_x'] + PLAYER_WIDTH // 2 - 2, self.state['player_y']])
                self.shoot_sound.play()
                self.space_pressed = True
        elif key == Qt.Key.Key_Q:
            QApplication.quit()
        elif key == Qt.Key.Key_R:
            self.worker.running = False
            self.alien_shoot_sound.stop()
            self.shoot_sound.stop()
            self.worker.reset_state()
            self.keys_pressed = {'left': False, 'right': False}
            self.update_key_state()
            self.selecting_difficulty = True
            self.update()
        elif key == Qt.Key.Key_P:
            self.worker.state['paused'] = not self.worker.state.get('paused', False)
        elif key == Qt.Key.Key_L:
            self.worker.state['lives'] += 1
        elif key == Qt.Key.Key_S:
            self.worker.state['score'] += 100
        elif key == Qt.Key.Key_M:
            if self.worker.state.get('mystery_ship') is None:
                start_x = 0 if random.choice([True, False]) else WORLD_W - 60
                direction = 1 if start_x == 0 else -1
                self.worker.state['mystery_ship'] = [start_x, 50]
                self.worker.state['mystery_ship_direction'] = direction
                self.worker.state['mystery_ship_cooldown'] = 1000

        # Difficulty selection
        if self.selecting_difficulty:
            if key in (Qt.Key.Key_E, Qt.Key.Key_M, Qt.Key.Key_H):
                diff = {Qt.Key.Key_E: 'E', Qt.Key.Key_M: 'M', Qt.Key.Key_H: 'H'}[key]
                self.selecting_difficulty = False
                self.worker.start_game(diff)
            return

        self.update_key_state()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        """
        @brief Handle key release events for the player.

        @details
        Stops continuous player movement when arrow keys are released
        and resets the space bar state to allow shooting again.

        Supported keys:
          - Left arrow: Stop moving left.
          - Right arrow: Stop moving right.
          - Space: Reset shooting flag to allow the next shot.

        @param event QKeyEvent containing the key release information.

        @return None
        """
        key = event.key()
        if key == Qt.Key.Key_Left:
            self.keys_pressed['left'] = False
        elif key == Qt.Key.Key_Right:
            self.keys_pressed['right'] = False
        if key == Qt.Key.Key_Space:
            self.space_pressed = False
        self.update_key_state()

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        @brief Render the entire game scene.

        @details
        Draws all game elements, including the background, ground, player, 
        bullets, aliens (animated), alien bullets, mystery ship, HUD, 
        difficulty selection menu, and game over screen with high scores.

        Rendering order:
          1. Background (black)
          2. Ground with linear gradient
          3. Difficulty selection menu (if active)
          4. Player sprite
          5. Player bullets
          6. Aliens with color variants and animation frames
          7. Mystery ship (if present)
          8. Alien bullets
          9. Heads-Up Display (score, lives, level, difficulty)
          10. Game over screen and high scores (if game is over)

        @param event QPaintEvent object containing update region information.
        @return None
        """
        painter = QPainter(self)
        painter.fillRect(0, 0, WORLD_W, WORLD_H, Qt.GlobalColor.black)

        # Draw ground
        grad = QLinearGradient(0, WORLD_H - GROUND_HEIGHT, 0, WORLD_H)
        grad.setColorAt(0, QColor(40, 40, 40))
        grad.setColorAt(1, QColor(20, 20, 20))
        painter.fillRect(0, WORLD_H - GROUND_HEIGHT, WORLD_W, GROUND_HEIGHT, grad)

        # Difficulty selection
        if self.selecting_difficulty:
            image = QPixmap(str(Path(ASSET_DIR/"space-invaders-logo.png").resolve()))
            painter.drawPixmap(0, 0, 1024, 512, image)
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont("Arial", 32))
            painter.drawText(WORLD_W // 2 - 200, WORLD_H // 2 + 150, "Select Difficulty:")
            painter.drawText(WORLD_W // 2 - 150, WORLD_H // 2 + 200, "(E)asy")
            painter.drawText(WORLD_W // 2 - 150, WORLD_H // 2 + 250, "(M)edium")
            painter.drawText(WORLD_W // 2 - 150, WORLD_H // 2 + 300, "(H)ard")
            return

        if not self.state or "player_x" not in self.state:
            return

        # Player
        painter.drawPixmap(self.state['player_x'], self.state['player_y'], self.player_sprite)

        # Bullets
        for b in self.state.get('bullets', []):
            painter.drawPixmap(b[0], b[1], self.bullet_sprite)

        # Aliens
        for alien in self.state.get("aliens", []):
            alien_type = alien.get("type", "squid")
            frame = alien.get("frame", 0)
            color_index = alien.get("color_index", 0)
            sprite = self.alien_sprites[alien_type][color_index][frame]
            painter.drawPixmap(alien["x"], alien["y"], sprite)

        # Mystery Ship
        if self.state.get('mystery_ship'):
            painter.drawPixmap(self.state['mystery_ship'][0],
                               self.state['mystery_ship'][1],
                               self.mystery_ship_sprite)

        # Alien bullets
        painter.setBrush(QColor("blue"))  # Or QColor(0, 0, 255)
        painter.setPen(QColor("blue"))   
        for b in self.state.get('alien_bullets', []):
            painter.drawRect(b[0], b[1], 5, 15)

        # Heads-Up Display (HUD)
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 16))
        if 'score' in self.state:
            difficulty_names = {'E': 'Easy', 'M': 'Medium', 'H': 'Hard'}
            diff_label = difficulty_names.get(self.worker.difficulty, "Unknown")
            painter.drawText(
                10, 20,
                f"Score: {self.state['score']}  "
                f"Lives: {self.state['lives']}  "
                f"Level: {self.state['level']}  "
                f"Difficulty: {diff_label}  "
                f"(Q: Quit, P: Pause)"
            )

        # Game Over Screen
        if self.state.get('game_over', False):
            painter.setFont(QFont("Arial", 36))
            painter.setPen(Qt.GlobalColor.red)
            painter.drawText(WORLD_W // 2 - 120, WORLD_H // 2, "GAME OVER")

            painter.setFont(QFont("Arial", 20))
            painter.setPen(Qt.GlobalColor.white)
            scores = self.highscores.scores
            y_offset = WORLD_H // 2 + 60
            for i, s in enumerate(scores, start=1):
                line = f"{i}. {s['initials']}  {s['score']}"
                painter.drawText(WORLD_W // 2 - 150, y_offset + (i - 1) * 30, line)

            painter.setFont(QFont("Arial", 16))
            painter.drawText(WORLD_W // 2 - 100, WORLD_H // 2 + 250, "Press R to Restart")

    def get_initials(self, score: int) -> None:
        """
        @brief Prompt the player for initials after achieving a high score.

        @details
        Displays a QInputDialog to allow the player to enter up to 3 
        uppercase letters as their initials. Once entered, the initials 
        and score are added to the high score list using the HighScores manager.

        @param score The final score achieved by the player.
        @return None
        """
        initials, ok = QInputDialog.getText(self, "New High Score!", "Enter your initials (3 letters):")
        if ok and initials:
            initials = initials[:3].upper()
            try:
                self.highscores.add_score(initials, score)
            except Exception as e:
                print(f"Warning: Could not save high score: {e}")

def main():
    """
    @brief Main entry point for the Space Invaders application.

    @details
    Initializes the QApplication and main QMainWindow. Creates the 
    SpaceInvadersGame widget, sets it as the central widget, shows 
    the window, and starts the Qt event loop.

    @return None
    """
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Space Invaders")
    game = SpaceInvadersGame(window)
    window.setCentralWidget(game)
    window.show()
    sys.exit(app.exec())

# ---------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    main()

