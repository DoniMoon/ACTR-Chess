# Base ACT-R Chess Model Specification 

## 1\. Objective & Architecture

This specification details the "Base Model" for a chess-playing ACT-R agent. The model is designed to learn through self-play.

  * **Recursive Self-Play:** The model plays against a copy of itself.
  * **State Persistence:** When a game ends, the winner's declarative memory (chunks) and procedural reinforcements (production utilities) are saved via `save-chess-model`.
  * **Compilation:** The model reloads this saved state for the next match, accumulating experience (DM and Utilities) over generations.

## 2\. Environment Interface

The model interacts with a 2D chess interface.

### 2.1. Coordinate System

  * **Board Dimensions:** 60px per cell.
  * **Offset:** (380, 380).
  * **Coordinate Conversion:** Lisp functions (`loc-to-col-idx`, `abs-xy-to-loc`) convert between algebraic notation (e.g., "e4") and screen coordinates (pixels).

### 2.2. Visual Features

The visual module recognizes specific colors and symbols:

  * **Pieces:** Represented by Unicode characters (♔, ♛, ♜, ♝, ♞, ♟).
  * **Board Colors:** `light-gray`, `dark-gray`.
  * **Legal Moves:** Indicated by **`gray`** dots when a piece is selected.
  * **Check Indicator:** **`red`** highlight.
  * **Last Move:** **`yellow`** highlight.
  * **Player Color:** The model holds a chunk indicating if it plays `white` or `black`.

-----

## 3\. Declarative Memory (Chunks)

The following chunk types are defined in the code:

### 3.1. Game State

Tracks the macro-level state of the current turn.

```lisp
(chunk-type game-state
    action             ; Current sub-goal (e.g., target-find, 2-specify-move)
    rel-plan           ; Current relation strategy being executed
    target             ; The piece currently being attended to (agent)
    turn               ; t (my turn) or nil (opponent turn)
    color              ; white or black
    start-time         ; Timestamp for time pressure calculation
    next-move          ; Best move found so far in decision phase
    con                ; Context
    next-move-execute  ; Flag: t if we are executing a pre-planned move
)
```

### 3.2. Chess Entities

  * **Piece (`pic`):** `n` (name: k,q,r,b,n,p), `l` (location: a1\~h8), `c` (color).
  * **Move (`mv`):** `agent` (piece chunk), `dest` (location).
  * **Score (`score`):** `m` (move chunk), `s` (numeric score).

### 3.3. Relational Knowledge

  * **Relation (`rel`):** Captures dynamic relationships between pieces.
      * `r`: Relation type (attack, defend, threat).
      * `a` / `ac`: Agent piece and color.
      * `ta` / `tc`: Target piece and color.
  * **Tactics (`tac`)**: Combinations of relations (not fully utilized in base code yet).
  * **Relative Location (`rlc`)**: Spatial relationships (L-shape, diagonal, etc.).

-----

## 4\. Procedural Memory (Production Flow)

The model operates in **5 distinct phases**, controlled by the `action` slot in the `game-state` buffer.

### Phase 1: Target Finding (`1-`)

**Goal:** Select a piece to move.

1.  **Turn Initialization:** `0-start-my-turn` resets the `start-time` and enables time-pressure logic.
2.  **Strategy Selection (Competition):**
      * **Relation Recall (`1-1-a`):** Retrieve a `rel` chunk (e.g., "My Knight attacks X") and select that Knight.
      * **Visual Search (`1-1-b`):** Randomly look for pieces of own color on the screen.
      * **Blind Retrieval (`1-1-c`):** Retrieve any piece of own color from DM.
      * **Urgent Plan (`1-1-d`):** If a `next-move` was decided in a previous thought cycle, immediately attempt to retrieve and execute it.
3.  **Verification (`1-2`):**
      * The model looks at the location of the retrieved piece.
      * **Memory Update:** If the piece is not where memory said it was (visual mismatch), the `imaginal` buffer is updated to reflect reality (`1-2-2-a-1`).
      * **Opponent Detection:** If the clicked piece belongs to the opponent, the model generates a `rel` chunk (e.g., "Opponent covers this square") and restarts the search.
4.  **Selection:** Once a valid own piece is confirmed, the model moves the cursor and clicks it (`1-3`), transitioning to Phase 2.

### Phase 2: Move Specification (`2-`)

**Goal:** Determine where to move the selected piece.

1.  **Memory Retrieval (`2-1`):** Attempt to recall a known `mv` (move) associated with this piece.
2.  **Validation (`2-2`):**
      * If a move is retrieved, the model looks at the destination on the board.
      * It checks for the **`gray`** dot (legal move indicator).
3.  **Visual Exploration (`2-3`):**
      * If no move is recalled or the recalled move is illegal, the model visually scans for `gray` dots (legal moves) around the piece.
4.  **Score Retrieval (`2-5`):**
      * Once a move is identified (either by recall or vision), the model attempts to retrieve a `score` chunk for this move.
      * **Heuristic Shortcut:** If a positive score is retrieved immediately, it may skip to Phase 4.
      * **Evaluation Trigger:** If no score exists or the score is neutral/negative, it proceeds to Phase 3 (`3-eval`) to calculate a score.

### Phase 3: Evaluation (`3-`)

**Goal:** Assign a value to the candidate move (Mock/Shallow Search).

  * *Current Implementation:* The base model performs a "Mock" evaluation rather than a full tree search.
  * **Logic:**
    1.  Look at the destination coordinates of the move (`3-0-1-mock`).
    2.  **Empty Square:** Assign Score 0.
    3.  **Capture:** If an opponent piece exists at the destination, assign a score based on material value (`get-piece-score`):
          * King: 100, Queen: 9, Rook: 5, Bishop/Knight: 3, Pawn: 1.
  * **Result:** A `score` chunk is created in the `imaginal` buffer.

### Phase 4: Decision Making (`4-`)

**Goal:** Compare the current candidate against the best "Next-Move".

1.  **Comparison (`4-1`):**
      * The model retrieves the `next-move` stored in the `game-state`.
      * It compares the `imaginal` score (current candidate) with the retrieved score of the `next-move`.
2.  **Update (`4-2`):**
      * If Current Score \> Old Score: Update `next-move` to the current candidate.
      * If Current Score \<= Old Score: Discard current candidate, go back to Phase 1 (find another piece/move).
3.  **Commitment (`4-3`):**
      * **Urgent Productions:** Under time pressure (or high utility), the model will force a decision (`4-3-a/b-decide-to-move...`).
      * **Think More:** Alternatively, it may choose to return to Phase 1 to search for better options.

### Phase 5: Execution (`5-`)

**Goal:** Physically execute the chosen move.

1.  **Recall Details:** Retrieve the precise coordinates of the chosen `mv`.
2.  **Motor Actions:**
      * Look at destination (`5-2`).
      * Move mouse to destination (`5-3`).
      * Click (`5-4`).
3.  **Cleanup:** Reset `action` to `target-find` and clear `next-move`.

-----

## 5\. Cognitive Mechanisms

### 5.1. Time Pressure Management

A custom function `manage-time-pressure` is hooked into the production cycle:

  * **Mechanism:** Tracks `(mp-time) - start-time`.
  * **Threshold:** After **10 seconds**, pressure increases.
  * **Effects:**
    1.  **Noise (`:egs`):** Increases by 0.05 per second. This forces the model to explore less probable paths or make errors as time runs out.
    2.  **Urgency:** Increases the utility (`:u`) of productions containing the keyword "URGENT". This biases the model toward executing a "good enough" move rather than thinking indefinitely.

### 5.2. Visual-Imaginal Interaction

The model heavily relies on aligning visual perception with memory:

  * **Correction:** If `retrieval` (Long-term memory) disagrees with `visual-location` (Reality), `imaginal` is used to synthesize a corrected chunk, which is then committed to DM.

### 5.3. Heuristics

  * **Material Value:** Hardcoded in `get-piece-score`.
  * **Legal Move Scanning:** Relies on the GUI's "gray dot" feature to offload the cognitive load of calculating legal moves.

-----

## 6\. Limitations & Future Work (v1.0)

1.  **Shallow Evaluation:** Phase 3 currently only checks for immediate captures (depth 1). It does not simulate opponent responses (Minimax/DFS).
2.  **Limited Tactics:** While `rel` (Relation) chunks exist, complex tactical patterns (Pins, Forks) are not yet fully implemented in the evaluation logic.
3.  **Dependence on GUI:** The model relies on the interface to determine legal moves (gray dots) rather than calculating them internally.

## 7\. Custom Lisp Functions

  * `save-chess-model`: Saves the model state recursively.
  * `restore-custom-functions`: Restores Lisp definitions upon reloading.
  * `manage-time-pressure`: Adjusts global parameters `:egs` and production utilities dynamically.
