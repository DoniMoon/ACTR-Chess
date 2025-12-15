from utils_chess import PIECE_VALUES, both_sides_material_text, format_material_advantage, get_unicode
import os
import chess
import chess.pgn
import actr
import time
import argparse
import json
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(ROOT_DIR, "save")
MODEL_DIR = os.path.join(SAVE_DIR, "model")
PGN_FILE = os.path.join(SAVE_DIR, "play_record.pgn")
LOG_FILE = os.path.join(SAVE_DIR, "log.json")

SQUARE_SIZE = 60
START_X = 50
START_Y = 50
WINDOW_WIDTH = 780
WINDOW_HEIGHT = 600

SCORE_X = START_X
MY_SCORE_Y = 570
OP_SCORE_Y = 20

INFO_COLOR = 'dark-cyan'
GAME = None

# --- Helper Functions for Save/Load ---

def ensure_directories():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
        print(f"Created directory: {SAVE_DIR}")
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        print(f"Created directory: {MODEL_DIR}")

def get_next_game_id() -> int:
    if not os.path.exists(PGN_FILE):
        return 1

    last_id = 0
    try:
        with open(PGN_FILE, "r", encoding="utf-8") as f:
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                try:
                    gid = int(game.headers.get("ID", last_id))
                    last_id = gid
                except (TypeError, ValueError):
                    pass
    except FileNotFoundError:
        pass
    return last_id + 1

def append_pgn_game(game: chess.pgn.Game, game_id: int) -> None:
    print(f"Saving PGN for Game {game_id} to {PGN_FILE}...")
    try:
        with open(PGN_FILE, "a", encoding="utf-8") as f:
            exporter = chess.pgn.FileExporter(f)
            game.accept(exporter)
            f.write("\n\n")
        print("PGN Saved successfully.")
    except Exception as e:
        print(f"Error saving PGN: {e}")

def log_execution(game_id, model_file, result):
    log_data = {}
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                log_data = json.load(f)
        except json.JSONDecodeError:
            pass
    
    timestamp = datetime.now().isoformat()
    log_entry = {
        "game_id": game_id,
        "model_file": model_file,
        "result": result,
        "timestamp": timestamp
    }
    log_data[timestamp] = log_entry
    
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4)
    except Exception as e:
        print(f"Error saving log: {e}")

# --- Coordinate Helpers ---

def board_to_screen_coords(file_idx: int, rank_idx: int, perspective: chess.Color):
    if perspective == chess.WHITE:
        row = 7 - rank_idx
        col = file_idx
    else:
        row = rank_idx
        col = 7 - file_idx

    x = START_X + col * SQUARE_SIZE
    y = START_Y + row * SQUARE_SIZE
    return x, y

# --- UI Classes ---

class PlayerView:


    def __init__(self, label: str, conn: actr.actr, color: chess.Color, perspective: chess.Color):
        self.label = label
        self.conn = conn
        self.color = color
        self.perspective = perspective
        self.window = None

        self.you_clock_item = None
        self.you_clock_pos = None
        self.opp_clock_item = None
        self.opp_clock_pos = None

    def init_window(self, time_limit_secs: int, you_are_white: bool):

        for rank_idx in range(8):      # 0=1st rank, 7=8th rank (python-chess index)
            for file_idx in range(8):  # 0=a, 7=h
                x, y = board_to_screen_coords(file_idx, rank_idx, self.perspective)

                if self.perspective == chess.WHITE:
                    row = 7 - rank_idx
                    col = file_idx
                else:
                    row = rank_idx
                    col = 7 - file_idx

                color = "light-gray" if (row + col) % 2 == 0 else "dark-gray"

                square = chess.square(file_idx, rank_idx)
                sq_name = chess.square_name(square)
                action_name = f"{self.label}-sq-{sq_name}"

                self.conn.add_button_to_exp_window(
                    self.window,
                    text="",
                    x=x-1, 
                    y=y-1,
                    width=SQUARE_SIZE,
                    height=SQUARE_SIZE,
                    color=color,
                    action=action_name,
                )

        coord_x = START_X + 8 * SQUARE_SIZE + 10
        for i in range(8):
            if self.perspective == chess.WHITE:
                rank_label = 8 - i
            else:
                rank_label = i + 1
            y = START_Y + i * SQUARE_SIZE + 20
            self.conn.add_text_to_exp_window(
                self.window,
                str(rank_label),
                x=coord_x,
                y=y,
                font_size=16,
                color=INFO_COLOR,
            )

        coord_y = START_Y + 8 * SQUARE_SIZE + 10
        for i in range(8):
            if self.perspective == chess.WHITE:
                file_char = chr(ord("a") + i)
            else:
                file_char = chr(ord("h") - i)
            x = START_X + i * SQUARE_SIZE + 23
            self.conn.add_text_to_exp_window(
                self.window,
                file_char,
                x=x,
                y=coord_y,
                font_size=16,
                color=INFO_COLOR,
            )

        time_panel_x = START_X + 9 * SQUARE_SIZE +20
        you_pos = (time_panel_x, START_Y + 4 * SQUARE_SIZE + 20)
        opp_pos = (time_panel_x, START_Y + 4 * SQUARE_SIZE - 40)

        mins = time_limit_secs // 60
        secs = time_limit_secs % 60
        time_str = f"{mins:02d}:{secs:02d}"

        self.conn.add_text_to_exp_window(self.window,"Opponent",x=time_panel_x,y=START_Y + 3 * SQUARE_SIZE -20,font_size=18,color=INFO_COLOR)
        self.conn.add_text_to_exp_window(self.window,"You",x=time_panel_x,y=START_Y + 5 * SQUARE_SIZE,font_size=18,color=INFO_COLOR)
        self.you_clock_item = self.conn.add_text_to_exp_window(
            self.window,
            time_str,
            x=you_pos[0],
            y=you_pos[1],
            font_size=20,
            color=INFO_COLOR,
        )
        self.you_clock_pos = you_pos

        self.opp_clock_item = self.conn.add_text_to_exp_window(
            self.window,
            time_str,
            x=opp_pos[0],
            y=opp_pos[1],
            font_size=20,
            color=INFO_COLOR,
        )
        self.opp_clock_pos = opp_pos

    def clear_pieces(self):
        self.conn.clear_exp_window(self.window)

    def update_clock(self, my_time, opp_time):
        def fmt(t):
            m = int(t) // 60
            s = int(t) % 60
            return f"{m:02d}:{s:02d}"
        
        if self.you_clock_item:
            self.conn.remove_items_from_exp_window(self.window, self.you_clock_item)
        if self.opp_clock_item:
            self.conn.remove_items_from_exp_window(self.window, self.opp_clock_item)
            
        self.you_clock_item = self.conn.add_text_to_exp_window(
            self.window, fmt(my_time), x=self.you_clock_pos[0], y=self.you_clock_pos[1], font_size=20, color=INFO_COLOR
        )
        self.opp_clock_item = self.conn.add_text_to_exp_window(
            self.window, fmt(opp_time), x=self.opp_clock_pos[0], y=self.opp_clock_pos[1], font_size=20, color=INFO_COLOR
        )

class ChessGameManual:
    def __init__(self, actr1: actr.actr, actr2: actr.actr, game_id: int, time_limit_secs: int = 600):
        self.actr1 = actr1
        self.actr2 = actr2
        self.time_limit_secs = time_limit_secs
        
        self.timer = {chess.WHITE: time_limit_secs, chess.BLACK: time_limit_secs}

        self.board = chess.Board()

        self.actr1_color = chess.WHITE
        self.actr2_color = chess.BLACK

        self.view_actr1 = PlayerView("actr1", actr1, self.actr1_color, self.actr1_color)
        self.view_actr2 = PlayerView("actr2", actr2, self.actr2_color, self.actr2_color)

        self.selected_square = None
        self.legal_targets = set()

        self.highlight_items_actr1 = []
        self.highlight_items_actr2 = []
        
        self.scores = {}

        # PGN
        self.game_id = game_id
        self.pgn_game = chess.pgn.Game()
        self.pgn_game.headers["Event"] = f"ACT-R Self Play {datetime.now().strftime('%Y-%m-%d')}"
        self.pgn_game.headers["ID"] = str(self.game_id)
        self.pgn_game.headers["White"] = "ACT-R 1"
        self.pgn_game.headers["Black"] = "ACT-R 2 (Copy)"
        self.pgn_game.headers["Result"] = "*"
        self.pgn_node = self.pgn_game

        self.finished = False


    def setup_views(self):

        self.view_actr1.window = self.view_actr1.conn.open_exp_window(
            f"Game {self.game_id} - ACT-R 1 (White)",
            visible=True,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
        )
        self.view_actr1.conn.call_command("install-device", self.view_actr1.window)

        self.view_actr2.window = self.view_actr2.conn.open_exp_window(
            f"Game {self.game_id} - ACT-R 2 (Black)",
            visible=True,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
        )
        self.view_actr2.conn.call_command("install-device", self.view_actr2.window)

        self.view_actr1.init_window(
            time_limit_secs=self.time_limit_secs,
            you_are_white=True,
        )
        self.view_actr2.init_window(
            time_limit_secs=self.time_limit_secs,
            you_are_white=False,
        )

        self.redraw_pieces_all()


    def redraw_pieces_for_view(self, view: PlayerView):

        view.conn.clear_exp_window(view.window)
        
        my_time = self.timer[view.color]
        opp_time = self.timer[not view.color]
        
        view.init_window(
            time_limit_secs=int(my_time), 
            you_are_white=(view.color == chess.WHITE),
        )
        view.update_clock(my_time, opp_time)

        for rank_idx in range(8):
            for file_idx in range(8):
                sq = chess.square(file_idx, rank_idx)
                piece = self.board.piece_at(sq)
                if piece is None:
                    continue
                symbol = piece.symbol()
                ch = get_unicode(symbol)
                x, y = board_to_screen_coords(file_idx, rank_idx, view.perspective)
                c = 'black' if symbol == symbol.lower() else 'white'
                view.conn.add_text_to_exp_window(
                    view.window,
                    ch,
                    x=x + 21,
                    y=y + 15,
                    font_size=30,
                    color= c,
                )

    def redraw_pieces_all(self):
        self.redraw_pieces_for_view(self.view_actr1)
        self.redraw_pieces_for_view(self.view_actr2)
        self.redraw_highlights()
        self.redraw_scores()
        
        if self.board.is_game_over():
            self.finished = True
            result = self.board.result()
            self.pgn_game.headers["Result"] = result
            print(f"Game {self.game_id} finished with result {result}")


    def clear_highlights(self):
        if self.highlight_items_actr1:
            self.view_actr1.conn.remove_items_from_exp_window(
                self.view_actr1.window, *self.highlight_items_actr1
            )
        if self.highlight_items_actr2:
            self.view_actr2.conn.remove_items_from_exp_window(
                self.view_actr2.window, *self.highlight_items_actr2
            )
        self.highlight_items_actr1 = []
        self.highlight_items_actr2 = []
    
    def clear_scores(self):
        for k,v in self.scores.items(): 
            if k == 0:
                self.view_actr1.conn.remove_items_from_exp_window(self.view_actr1.window, *v)
            else:
                self.view_actr2.conn.remove_items_from_exp_window(self.view_actr2.window, *v)
        self.scores = {}

    def redraw_scores(self):
        self.clear_scores()
        for turn in [chess.WHITE, chess.BLACK]:    
            score_formatted = format_material_advantage(self.board, turn)
            if not score_formatted:
                continue
            for v_idx, target_view in enumerate([self.view_actr1,self.view_actr2]):
                if v_idx not in self.scores:
                    self.scores[v_idx] = [] 
                is_mine = (target_view.color == turn)
                y_loc = MY_SCORE_Y if is_mine else OP_SCORE_Y
                self.scores[v_idx].append(target_view.conn.add_text_to_exp_window(
                    target_view.window,
                    score_formatted,
                    x=SCORE_X,
                    y=y_loc,
                    color=INFO_COLOR,
                    font_size=14,
                ))
    
    def redraw_highlights(self):
        self.clear_highlights()
        pending = []  # (view, x, y, color)

        def add_circle(view, sq, color):
            file_idx = chess.square_file(sq)
            rank_idx = chess.square_rank(sq)
            x, y = board_to_screen_coords(file_idx, rank_idx, view.perspective)
            if color == "gray":
                pending.append((view, x + 9, y - 6, color,68))
            elif color == "red": 
                pending.append((view, x + 5, y - 14, color,84))
            else:
                pending.append((view, x + 7, y - 10, color,76))

        if self.board.is_check():
            king_sq = self.board.king(self.board.turn)
            if king_sq is not None:
                add_circle(self.view_actr1, king_sq, "red")
                add_circle(self.view_actr2, king_sq, "red")
                
            for attacker_sq in self.board.checkers():
                add_circle(self.view_actr1, attacker_sq, "red")
                add_circle(self.view_actr2, attacker_sq, "red")
                
        if self.board.move_stack:
            last = self.board.move_stack[-1]
            for sq in [last.from_square, last.to_square]:
                add_circle(self.view_actr1, sq, "yellow")
                add_circle(self.view_actr2, sq, "yellow")

        if self.legal_targets:
            for sq in self.legal_targets:
                if self.board.turn == self.view_actr1.color:
                    add_circle(self.view_actr1, sq, "gray")
                else:
                    add_circle(self.view_actr2, sq, "gray")

        for view, x, y, color,size in pending:
            item = view.conn.add_text_to_exp_window(
                view.window,
                "○",
                x=x,
                y=y,
                color=color,
                font_size=size,
            )
            if view is self.view_actr1:
                self.highlight_items_actr1.append(item)
            else:
                self.highlight_items_actr2.append(item)


    def on_square_click(self, side_label: str, square_name: str):
        if self.finished:
            return

        sq = chess.parse_square(square_name)
        turn_color = self.board.turn

        if side_label == "actr1":
            side_color = self.actr1_color
        else:
            side_color = self.actr2_color

        if side_color != turn_color:
            return

        piece = self.board.piece_at(sq)

        if self.selected_square is None:
            if piece is None or piece.color != side_color:
                # print('clicked, not my piece')
                pass
            legal_moves = [m for m in self.board.legal_moves if m.from_square == sq]
            if not legal_moves:
                # print('clicked, but no legal moves')
                return
            self.selected_square = sq
            self.legal_targets = {m.to_square for m in legal_moves}
            self.redraw_highlights()
            return

        if sq == self.selected_square:
            # print('release_select')
            self.selected_square = None
            self.legal_targets.clear()
            self.redraw_highlights()
            return

        if piece is not None and piece.color == side_color and sq not in self.legal_targets:
            legal_moves = [m for m in self.board.legal_moves if m.from_square == sq]
            if not legal_moves:
                self.selected_square = None
                self.legal_targets.clear()
                self.redraw_highlights()
                return
            self.selected_square = sq
            self.legal_targets = {m.to_square for m in legal_moves}
            self.redraw_highlights()
            return

        if sq in self.legal_targets:
            from_sq = self.selected_square
            to_sq = sq
            move = chess.Move(from_sq, to_sq)

            # Promotion always queen
            moving_piece = self.board.piece_at(from_sq)
            if (
                moving_piece is not None
                and moving_piece.piece_type == chess.PAWN
                and (chess.square_rank(to_sq) in (0, 7))
            ):
                move = chess.Move(from_sq, to_sq, promotion=chess.QUEEN)

            if move in self.board.legal_moves:
                self.apply_move(move)

            self.selected_square = None
            self.legal_targets.clear()
            self.redraw_pieces_all()
            return

        self.selected_square = None
        self.legal_targets.clear()
        self.clear_highlights()

    def apply_move(self, move: chess.Move):
        mover = self.board.turn
        captured_piece = None

        if self.board.is_capture(move):
            if self.board.is_en_passant(move):
                cap_sq = chess.square(chess.square_file(move.to_square),
                                      chess.square_rank(move.from_square))
                captured_piece = self.board.piece_at(cap_sq)
            else:
                captured_piece = self.board.piece_at(move.to_square)

        delta = PIECE_VALUES.get(captured_piece)

        self.board.push(move)
        self.pgn_node = self.pgn_node.add_variation(move)
        self.pgn_node.comment = f"[%clk {self.timer[not self.board.turn]:.1f}]"
        
        if delta and delta > 0:
            r = float(delta)

            if mover == chess.WHITE:
                self.actr1.call_command("trigger-reward", r / 100)
                self.actr2.call_command("trigger-reward", -r / 100)
            else:
                self.actr2.call_command("trigger-reward", r / 100)
                self.actr1.call_command("trigger-reward", -r / 100)

def register_actions_for_side(conn: actr.actr, side_label: str):
    def make_handler(slabel: str, sq_name: str):
        def handler():
            if GAME is not None:
                GAME.on_square_click(slabel, sq_name)
            return True
        return handler

    for file_idx in range(8):
        for rank_idx in range(8):
            sq = chess.square(file_idx, rank_idx)
            sq_name = chess.square_name(sq)
            action = f"{side_label}-sq-{sq_name}"
            conn.add_command(action, make_handler(side_label, sq_name))

def initialize_model_state(conn: actr.actr, color_symbol: str, turn: bool):
    if color_symbol == 'white':
        conn.goal_focus('init-white-goal')
    else:
        conn.goal_focus('init-black-goal')

    print(f'init done for {color_symbol}')

def update_turn_signal(conn: actr.actr, is_my_turn: bool):
    turn_val = "t" if is_my_turn else "nil"
    conn.evaluate_single('mod-buffer-chunk', 'goal', ['turn', turn_val, 'action', 'target-find'])

    

def init_model(actr):
    actr.set_parameter_value(":v", True)
    actr.set_parameter_value(":esc", True)
    actr.set_parameter_value(":show-focus", True)
    actr.set_parameter_value(":trace-detail", "high")
    actr.set_parameter_value(":needs-mouse", True)
    actr.set_parameter_value(":ul", True)
    actr.set_parameter_value(":visual-finst-span", 10.0)
    actr.set_parameter_value(":ignore-buffers", ["visual", "goal"])
    actr.start_hand_at_mouse()
    
def main():
    global GAME

    parser = argparse.ArgumentParser(description='ACT-R Chess Self-Play')
    parser.add_argument('--continue_game', type=int, help='Game ID to continue from', default=0)
    args = parser.parse_args()

    ensure_directories()

    actr1 = actr.start(host="127.0.0.1", port=2650)
    actr2 = actr.start(host="127.0.0.1", port=2651)

    start_game_id = args.continue_game
    if start_game_id == 0:
        start_game_id = get_next_game_id()
    
    current_game_id = start_game_id

    try:
        while True:
            
            print(f"\n=== Starting Game {current_game_id} ===")
            
            model_to_load = "base-model.lisp" 
            
            prev_model_path = os.path.join(MODEL_DIR, f"{current_game_id - 1}.lisp")
            if current_game_id > 1 and os.path.exists(prev_model_path):
                model_to_load = prev_model_path
            
            if current_game_id == start_game_id and args.continue_game > 0:
                 arg_model_path = os.path.join(MODEL_DIR, f"{args.continue_game}.lisp")
                 if os.path.exists(arg_model_path):
                     model_to_load = arg_model_path
            
            full_model_path = os.path.join(ROOT_DIR, model_to_load).replace("\\", "/")
            print(f"Loading model from: {full_model_path}")
            
            actr1.call_command("reset")
            actr2.call_command("reset")
            
            actr1.call_command("load-act-r-model", full_model_path)
            actr2.call_command("load-act-r-model", full_model_path)
            init_model(actr1)
            init_model(actr2)    
            GAME = ChessGameManual(actr1, actr2, game_id=current_game_id, time_limit_secs=600)
            register_actions_for_side(actr1, "actr1")
            register_actions_for_side(actr2, "actr2")
            
            GAME.setup_views() 

            initialize_model_state(actr1, "white", True)
            initialize_model_state(actr2, "black", False)

            last_turn = chess.WHITE
            last_second = int(actr1.call_command("mp-time"))
            time.sleep(2)
            print("Game Started.")
            while not GAME.finished:
                actr1.call_command("run", 0.1)
                actr2.call_command("run", 0.1)
                # time.sleep(0.1)

                current_time_val = actr1.call_command("mp-time")
                current_time = float(current_time_val) if current_time_val is not None else 0
                
                if int(current_time) > last_second:
                    last_second = int(current_time)
                    if GAME.board.turn == chess.WHITE:
                        GAME.timer[chess.WHITE] -= 1
                    else:
                        GAME.timer[chess.BLACK] -= 1
                    
                    if GAME.timer[chess.WHITE] <= 0 or GAME.timer[chess.BLACK] <= 0:
                        GAME.finished = True
                        print("Time Over")
                        if GAME.timer[chess.WHITE] <= 0:
                            GAME.pgn_game.headers["Result"] = "0-1"
                        else:
                            GAME.pgn_game.headers["Result"] = "1-0"
                    
                    GAME.view_actr1.update_clock(GAME.timer[chess.WHITE], GAME.timer[chess.BLACK])
                    GAME.view_actr2.update_clock(GAME.timer[chess.BLACK], GAME.timer[chess.WHITE])

                if GAME.board.turn != last_turn:
                    last_turn = GAME.board.turn
                    is_white_turn = (GAME.board.turn == chess.WHITE)
                    print('turn changed!!', ('white turn' if is_white_turn else 'black turn.'))
                    update_turn_signal(actr1, is_white_turn)
                    update_turn_signal(actr2, not is_white_turn)

            print(f"Game {current_game_id} Ended. Result: {GAME.pgn_game.headers['Result']}")
            
            result = GAME.pgn_game.headers["Result"]
            reward = -5 
            if result == "1-0": 
                reward = 100
            elif result == "0-1": 
                reward = -100
            
            actr1.call_command("eval", "(mod-buffer-chunk 'goal '(action review))")
            actr1.call_command("trigger-reward", reward / 100)
            
            print("Reviewing (Compilation) for 10 seconds...")
            actr1.call_command("run", 10)
            time.sleep(3)

            append_pgn_game(GAME.pgn_game, current_game_id)        
            save_filename = f"{current_game_id}.lisp"
            save_path = os.path.join(MODEL_DIR, save_filename)
            
            if os.path.exists(save_path):
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_filename = f"{current_game_id}_{timestamp_str}.lisp"
                save_path = os.path.join(MODEL_DIR, save_filename)
            
            # abs path
            save_path_lisp = save_path.replace("\\", "/")
            
            print(f"Saving model to: {save_path_lisp}")
            try:
                actr1.call_command("save-chess-model", save_path_lisp)
                print(f"- Model saved to: {save_path_lisp}")
                                
         
            except Exception as e:
                print(f"Error calling save-model-file: {e}")

            # log history
            log_execution(current_game_id, save_filename, result)
            
            current_game_id += 1

    except KeyboardInterrupt:
        print("\nExiting loop by user interrupt.")

if __name__ == "__main__":
    main()