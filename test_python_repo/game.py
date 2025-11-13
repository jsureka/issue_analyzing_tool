"""
Simple game module for testing Knowledge Base
"""


class Player:
    """Represents a player in the game"""
    
    def __init__(self, name, score=0):
        """Initialize a player with name and score"""
        self.name = name
        self.score = score
    
    def add_points(self, points):
        """Add points to player's score"""
        if points < 0:
            raise ValueError("Points must be positive")
        self.score += points
    
    def get_score(self):
        """Get current player score"""
        return self.score
    
    def reset_score(self):
        """Reset player score to zero"""
        self.score = 0


class GameBoard:
    """Manages the game board state"""
    
    def __init__(self, size=10):
        """Initialize game board with given size"""
        self.size = size
        self.board = [[None for _ in range(size)] for _ in range(size)]
    
    def place_piece(self, x, y, piece):
        """Place a piece on the board at coordinates"""
        if not self._is_valid_position(x, y):
            raise ValueError(f"Invalid position: ({x}, {y})")
        self.board[x][y] = piece
    
    def get_piece(self, x, y):
        """Get piece at given coordinates"""
        if not self._is_valid_position(x, y):
            return None
        return self.board[x][y]
    
    def _is_valid_position(self, x, y):
        """Check if position is within board bounds"""
        return 0 <= x < self.size and 0 <= y < self.size
    
    def clear_board(self):
        """Clear all pieces from the board"""
        self.board = [[None for _ in range(self.size)] for _ in range(self.size)]


def calculate_winner(players):
    """Calculate the winner from a list of players"""
    if not players:
        return None
    
    max_score = max(player.get_score() for player in players)
    winners = [p for p in players if p.get_score() == max_score]
    
    if len(winners) == 1:
        return winners[0]
    return winners  # Multiple winners (tie)


def validate_player_name(name):
    """Validate player name meets requirements"""
    if not name or len(name.strip()) == 0:
        raise ValueError("Player name cannot be empty")
    
    if len(name) > 50:
        raise ValueError("Player name too long (max 50 characters)")
    
    return name.strip()
