# utils_chess.py

import os
import chess.pgn
import chess

PGN_FILE = "play_record.pgn"
SAVE_DIR = "saved_models"

PIECE_VALUES = {
    chess.PAWN:   1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK:   5,
    chess.QUEEN:  9,
}

UNICODE_WHITE = {
    chess.PAWN:   "♙",
    chess.KNIGHT: "♘",
    chess.BISHOP: "♗",
    chess.ROOK:   "♖",
    chess.QUEEN:  "♕",
}

UNICODE_BLACK = {
    chess.PAWN:   "♟",
    chess.KNIGHT: "♞",
    chess.BISHOP: "♝",
    chess.ROOK:   "♜",
    chess.QUEEN:  "♛",
}


PIECE_UNICODE = {
    "K": "♔",
    "Q": "♕",
    "R": "♖",
    "B": "♗",
    "N": "♘",
    "P": "♙",
    "k": "♚",
    "q": "♛",
    "r": "♜",
    "b": "♝",
    "n": "♞",
    "p": "♟",
}

def get_unicode(s:str) -> str:
    return PIECE_UNICODE[s.lower()]
def count_material(board: chess.Board) -> dict:
    counts = {
        chess.WHITE: {pt: 0 for pt in PIECE_VALUES.keys()},
        chess.BLACK: {pt: 0 for pt in PIECE_VALUES.keys()},
    }

    for square, piece in board.piece_map().items():
        pt = piece.piece_type
        if pt in PIECE_VALUES:
            counts[piece.color][pt] += 1

    return counts

def compute_material_advantage(
    board: chess.Board,
    perspective: chess.Color,
) -> tuple[list[tuple[int, int]], int]:
    counts = count_material(board)
    mine = counts[perspective]
    opp  = counts[not perspective]

    extra = []
    total_score = 0

    order = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]

    for pt in order:
        diff = mine[pt] - opp[pt]

        extra.append((pt, diff))
        total_score += diff * PIECE_VALUES[pt]

    return extra, total_score


def format_material_advantage(
    board: chess.Board,
    perspective: chess.Color,
) -> str:
    extra, score = compute_material_advantage(board, perspective)
    if not extra:
        return ""

    glyphs = UNICODE_WHITE if perspective == chess.BLACK else UNICODE_BLACK

    order = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]

    piece_str_parts = []
    for pt in order:
        # 해당 pt의 diff를 extra 리스트에서 찾기
        diff = next((cnt for (ppt, cnt) in extra if ppt == pt), 0)
        if diff > 0:
            piece_str_parts.append(glyphs[pt] * diff)

    pieces_str = "".join(piece_str_parts)
    return f"{pieces_str} + {score}" if score > 0 else pieces_str

def both_sides_material_text(board: chess.Board):
    return {
        chess.WHITE: format_material_advantage(board, chess.WHITE),
        chess.BLACK: format_material_advantage(board, chess.BLACK),
    }

def ensure_dirs():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

def get_next_game_id():
    """
    play_record.pgn을 읽어서 마지막 게임 ID를 찾고 +1 반환.
    파일 없으면 1 시작.
    """
    if not os.path.exists(PGN_FILE):
        return 1

    last_id = 0
    with open(PGN_FILE, "r") as f:
        for line in f:
            if line.startswith("[ID "):
                try:
                    last_id = int(line.split('"')[1])
                except:
                    pass
    return last_id + 1


def save_pgn_game(game):
    """
    PGN 하나 append
    """
    with open(PGN_FILE, "a") as f:
        exporter = chess.pgn.FileExporter(f)
        game.accept(exporter)
        f.write("\n\n")   # 다음 게임과 구분


def save_actr_state(game_id):
    """
    나중에 ACT-R state 덤프할 때 쓸 자리. 지금은 빈 shell.
    """
    ensure_dirs()
    filename = os.path.join(SAVE_DIR, f"chess_actr_{game_id}.lisp")
    with open(filename, "w") as f:
        f.write(";; ACT-R state placeholder\n")
        
        