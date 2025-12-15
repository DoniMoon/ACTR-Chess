(clear-all)
(require-extra "save-model")
(require-extra "blending")

(defparameter *chess-logic-code* "
(defparameter *cell-width* 60) 
(defparameter *board-off-x* 380) 
(defparameter *board-off-y* 380) 
    

(defun loc-to-col-idx (loc)
  (let* ((s (string loc))
         (c (char-code (char (string-downcase s) 0))))
    (- c 96)))

(defun loc-to-row-idx (loc)
  (let* ((s (string loc))
         (c (digit-char-p (char s 1))))
    c))

(defun rel-to-abs-lx (loc)
  (let ((col (if (numberp loc) loc (loc-to-col-idx loc))))
    (+ *board-off-x* (* (- col 1) *cell-width*))))

(defun rel-to-abs-ux (loc)
  (+ (rel-to-abs-lx loc) *cell-width*))

(defun rel-to-abs-ly (loc)
  (let ((row (if (numberp loc) loc (loc-to-row-idx loc))))
    (+ *board-off-y* (* (- row 1) *cell-width*))))

(defun rel-to-abs-uy (loc)
  (+ (rel-to-abs-ly loc) *cell-width*))

(defun rel-to-abs-x (loc)
  (+ (rel-to-abs-lx loc) (/ *cell-width* 2)))

(defun rel-to-abs-y (loc)
  (+ (rel-to-abs-ly loc) (/ *cell-width* 2)))

(defun abs-xy-to-loc (x y)
  (let* ((col-idx (floor (+ (/ (- x *board-off-x*) *cell-width*) 1)))
         (row-idx (floor (+ (/ (- y *board-off-y*) *cell-width*) 1)))
         (col-char (code-char (+ col-idx 96)))) 
    (if (and (>= col-idx 1) (<= col-idx 8)
             (>= row-idx 1) (<= row-idx 8))
        (intern (format nil \"~c~d\" col-char row-idx))
        nil)))

(defun name-to-unicode (name)
  (let ((n (string-downcase (string name))))
    (cond
      ((string= n \"k\") \"♚\")
      ((string= n \"q\") \"♛\")
      ((string= n \"r\") \"♜\")
      ((string= n \"b\") \"♝\")
      ((string= n \"n\") \"♞\")
      ((string= n \"p\") \"♟\")
      (t \"?\"))))

(defun unicode-to-name (uni)
  (let ((u (if (stringp uni) uni (string uni))))
    (cond
      ((or (string= u \"♚\") (string= u \"♔\")) 'k)
      ((or (string= u \"♛\") (string= u \"♕\")) 'q)
      ((or (string= u \"♜\") (string= u \"♖\")) 'r)
      ((or (string= u \"♝\") (string= u \"♗\")) 'b)
      ((or (string= u \"♞\") (string= u \"♘\")) 'n)
      ((or (string= u \"♟\") (string= u \"♙\")) 'p)
      (t nil))))

(defun opposite-color (c)
  (let ((cs (string-downcase (string c))))
    (cond ((string= cs \"white\") 'black)
          ((string= cs \"black\") 'white)
          (t nil))))

(defun get-piece-score (piece-or-uni)
  (let ((s (if (symbolp piece-or-uni) 
               (string-downcase (symbol-name piece-or-uni))
               (string piece-or-uni))))
    (cond
      ((or (string= s \"♚\") (string= s \"k\")) 100)
      ((or (string= s \"♛\") (string= s \"q\")) 9)
      ((or (string= s \"♜\") (string= s \"r\")) 5)
      ((or (string= s \"♝\") (string= s \"b\")) 3)
      ((or (string= s \"♞\") (string= s \"n\")) 3)
      ((or (string= s \"♟\") (string= s \"p\")) 1)
      (t 0))))

;;; Time Management Helpers
(defun get-turn-duration ()
  (let ((g (buffer-read 'goal)))
    (if (and g (chunk-p g))
        (let ((st (chunk-slot-value-fct g 'start-time)))
          (if (numberp st)
              (- (mp-time) st) 
              0))
        0)))

(defun manage-time-pressure (prod-name)
  (let* ((duration (get-turn-duration))
         (threshold 10.0)      
         (base-noise 0.1)      
         (base-utility 3.0))   

    (let ((new-noise (if (> duration threshold)
                         (+ base-noise (* (- duration threshold) 0.05))
                         base-noise)))
      (sgp-fct (list :egs new-noise)))

    (when (> duration threshold)
      (let ((boost (* (- duration threshold) 1.0)))
        (dolist (prod (all-productions)) 
          (when (search \"URGENT\" (symbol-name prod) :test #'string-equal)
            (spp-fct (list prod :u (+ base-utility boost)))))))))

(defun reset-turn-time ()
  (let ((g (buffer-read 'goal)))
    (when g
      (mod-chunk-fct g (list 'start-time (mp-time)))
      (sgp :egs 0.3) 
      (dolist (prod (all-productions))
          (when (search \"URGENT\" (symbol-name prod) :test #'string-equal)
            (spp-fct (list prod :u 3.0)))) 
      )))
")


(defparameter *chess-saver-code* "
(defun restore-custom-functions ()
  (command-output \";; ---------------------------------------------------------\")
  (command-output \";; Recursive Restoration of Custom Functions and Saver Mechanism\")
  (command-output \";; ---------------------------------------------------------\")
  
  (command-output \"(defparameter *chess-logic-code* ~s)\" *chess-logic-code*)
  (command-output \"(defparameter *chess-saver-code* ~s)\" *chess-saver-code*)

   (command-output \"~a\" *chess-logic-code*)
  (command-output \"~a\" *chess-saver-code*)
)

(add-act-r-command \"restore-custom-functions\" 'restore-custom-functions \"Recursively restores functions.\")

(defun save-chess-model (file-name)
  (save-model-file file-name :pre-chunk-type-hook \"restore-custom-functions\"))

(add-act-r-command \"save-chess-model\" 'save-chess-model \"Saves model recursively.\")
")

(defun load-code-string (str)
  (with-input-from-string (s str)
    (loop for form = (read s nil :eof)
          until (eq form :eof)
          do (eval form))))

(load-code-string *chess-logic-code*)
(load-code-string *chess-saver-code*)

; ---------------------------------------------------------

(define-model chess-base-model
  
(sgp :egs 0.3 :v t :esc t :show-focus t :trace-detail high :needs-mouse t :ul t :visual-num-finsts 30 :visual-finst-span 20.0 :do-not-harvest visual-location :auto-attend t :production-hook manage-time-pressure)
  
    (start-hand-at-mouse)  
    (chunk-type game-state
        action       ; multi-purpose field
        rel-plan     ; relation chunk
        target       ; piece chunk (my agent)
        turn         ; t (my turn), nil (opponent turn)
        color        ; w (white), b (black)
        start-time   ; timestamp for turn start
        next-move ; planned best move for this turn.
        con ; current context
        next-move-execute ;if t, discovering planned move
    )
    (chunk-type pic
        n ; name (p,b,r,n,q,k)
        l ; location: a1~h8
        c ; color
    )
    (chunk-type mv
        agent ; piece chunk
        dest ; location: a1~h8
    )
    (chunk-type rel
        r ; relation (a,d,t) - attack, defend, threat
        a ; agent p~k
        ac ; agent color
        ta; target p~k + s(=space)
        tc ; target color
    )
    (chunk-type con ; context
        prev ; previous context
        m-2 ;
        m-1 ;
        m-0 ;
    )
    (chunk-type tac
        rel1 ; relation 1
        rel2 ; relation 2, ignore order
        v ; value
    )
    (chunk-type rlc
        d ; direction (d,c) - diagnoal, cross, L-shape
        o ; one (true, nil) - true, nil. 
        front ; front(true, nil). 상이나 상대각선에서만 true.
        r; right (true, nil): 오른쪽이면 true.
        l; direction of l shape(x,y): 
        agent ; p~k
        target ; p~k + s(=space)
    )
    (chunk-type score 
        m ; 
        s ; int score.
    )
    
  (define-chunks
      (init-white-goal isa game-state action target-find target nil color white turn t)
      (init-black-goal isa game-state action target-find target nil color black turn nil)
      (start-goal isa game-state turn nil)
  )
  
  (goal-focus start-goal)

(p 0-start-my-turn
   =goal>
      isa      game-state
      turn     t
      start-time nil 
==>
   !eval! (reset-turn-time)
   =goal>
      action   target-find
)

(p 1-1-a-1-rel-recall
   =goal>
   isa game-state
   action target-find
   rel-plan =rel-p
   
   ?retrieval>
      state  free
   ==>
   +retrieval> 
   isa rel
)

(p 1-1-a-2-a-rel-agent-check 
   =goal>
   isa game-state
   action target-find
   ?retrieval>
      state  free
      buffer full      
   =retrieval>  
      isa    rel
      a    =agent
      ac   =agent-color
   ==>
   =goal>
   action 1-1-a-2-piece-finding
   +retrieval> 
   isa pic
   n =agent
   c =agent-color 
)

(p 1-1-a-2-b-rel-target-check 
   =goal>
   isa game-state
   action target-find
   ?retrieval>
      state  free
      buffer full      
   =retrieval>  
      isa    rel
      ta    =target
      tc   =target-color
   ==>
   =goal>
   action 1-1-a-2-piece-finding
   +retrieval> 
   isa pic
   n =target
   c =target-color 
)

(p 1-1-a-3-a-set-piece
   =goal>
   isa game-state
   action 1-1-a-2-piece-finding
   ?retrieval>
      state  free
      buffer full      
   =retrieval>
      isa    pic
   ==>
   =retrieval>
   =goal>
       action 1-2-1-recalling
       target =retrieval
)
    
(p 1-1-a-3-b-no-piece
   =goal>
   isa game-state
   action 1-1-a-2-piece-finding
   ?retrieval>
      state  error      
   ==>
   =goal>
       action target-find
       target nil
)
  
(p 1-1-b-1-temp-random-mine
   =goal>
   isa game-state
   action target-find
   color =c
   ==>
   =goal>
   action 1-1-b-random
   +visual-location>
   color =c
)
    
(p 1-1-b-2-move-visual
   =goal>
   action 1-1-b-random
   =visual-location>
   isa visual-location
  ==>
   =visual-location>
   +visual>
      isa        move-attention
      screen-pos =visual-location
   =goal>
      action      1-1-b-2-retrieve
)

(p 1-1-b-3-retrieve-target
   =goal>
   isa game-state
   action 1-1-b-2-retrieve
   =visual-location>
   screen-x =vx
   screen-y =vy
   =visual>
   value =uni
   color =target-c
   !bind! =name (unicode-to-name =uni)
   !bind! =loc-name (abs-xy-to-loc =vx =vy)
   ==>
   =visual-location>
   =goal>
   action 1-1-b-3-retrieved
   +retrieval> 
   isa pic
   n =name
   c =target-c
   l =loc-name
   =visual>
)
    

(p 1-1-b-4-a-recall-fail
   =goal>
   isa game-state
       action 1-1-b-3-retrieved
   ?retrieval>
       state error
   ==>
   =goal>
   action visual-to-imaginal
)

(p 1-1-b-4-b-recall-success
   =goal>
   isa game-state
       action 1-1-b-3-retrieved
   ?retrieval>
       buffer full
   =retrieval>
   ==>
   =retrieval>
   =goal>
   target =retrieval
   action 1-2-1-recalling
)
    
(p 1-1-c-recall-my-any-piece
   =goal>
   isa game-state
   action target-find
   color =my-color
   ?retrieval>
   state free
   ==>
   +retrieval>
   isa pic
   c =my-color
   =goal>
   action 1-1-b-3-retrieved
)
    
(p 1-1-d-1-try-next-mv-urgent
   =goal>
   isa game-state
   action target-find
   color =my-color
   next-move =mv   
   ==>
   +retrieval> =mv
   =goal>
   action 1-1-d-2-mv-find
   next-move-execute t
)
    
(p 1-1-d-2-a-recall-success
   =goal>
   isa game-state
       action 1-1-d-2-mv-find
   ?retrieval>
       buffer full
   =retrieval>
   agent =ag
   ==>
   +retrieval> =ag
   =goal>
   action 1-1-d-2-a-mv-agent-find
)

(p 1-1-d-2-b-recall-fail
   =goal>
   isa game-state
       action 1-1-d-2-mv-find
   ?retrieval>
       state error
   ==>
   =goal>
   next-move nil
   next-move-execute nil
   target nil
   action target-find
)
    
(p 1-1-d-2-a-2-a-recall-success
   =goal>
   isa game-state
       action 1-1-d-2-a-mv-agent-find
   ?retrieval>
       buffer full
   =retrieval>
   ==>
   =retrieval>
   =goal>
   target =retrieval
   action 1-2-1-recalling
)

(p 1-1-d-2-a-2-b-recall-fail
   =goal>
   isa game-state
       action 1-1-d-2-a-mv-agent-find
   ?retrieval>
       state error
   ==>
   =goal>
   next-move nil
   next-move-execute nil
   target nil
   action target-find
)
    
;=========utils for phase 1
    
(p 1-u-visual-to-imaginal
   =goal>
   action visual-to-imaginal
   =visual-location>
       screen-x =vx
       screen-y =vy
   =visual>
       value =uni
       color =target-c
   !bind! =name (unicode-to-name =uni)
   !bind! =correct-loc-name (abs-xy-to-loc =vx =vy)
   ==>
   =visual>
   =goal>
   action representing
   +imaginal> 
       isa pic
       n =name
       l =correct-loc-name
       c =target-c
)

(p 1-u-represent-to-target
   =goal>
       action representing
   =imaginal>
       isa pic
   ==>
   -imaginal>
   =goal>
       action 1-2-1-retrieve-target
       target =imaginal
)
;======util ends    

(p 1-2-1-1-recall-target
   =goal>
       isa game-state
       action 1-2-1-retrieve-target
       target =tar
   ?retrieval>
      state  free
   ==>
   +retrieval> =tar   
   =goal>   
   action 1-2-1-recalling
)

(p 1-2-1-2-a-search-target
   =goal>
       isa game-state
       action 1-2-1-recalling
   ?retrieval>
       state free
       buffer full
   =retrieval>
       isa pic   
       l =loc
       c =color
   ?visual-location>
      state      free
   
   !bind! =lx (rel-to-abs-lx =loc)
   !bind! =ux (rel-to-abs-ux =loc)
   !bind! =ly (rel-to-abs-ly =loc)
   !bind! =uy (rel-to-abs-uy =loc)
   ==>
   =retrieval>
   +visual-location>
      isa        visual-location
      >= screen-x =lx
      <= screen-x =ux
      >= screen-y =ly
      <= screen-y =uy
      color =color
   =goal>
      action found-location
)
    
(p 1-2-1-2-b-fail-search-target-normal
   =goal>
       isa game-state
       action 1-2-1-recalling
       next-move-execute nil
   ?retrieval>
       state error  
   ==>
   =goal>
      action target-find
      target nil
)    

(p 1-2-1-2-c-fail-search-target-was-next-mv
   =goal>
       isa game-state
       action 1-2-1-recalling
       next-move-execute t
   ?retrieval>
       state error  
   ==>
   =goal>
      action target-find
      next-move nil
      next-move-execute nil
      target nil
)    

(p 1-2-1-a-move-eyes
   =goal>
      action      found-location
      target =tar
   =visual-location>
      isa        visual-location
      screen-x   =ax
      screen-y   =ay 
   ?visual>
      state      free
==>
   =visual-location>
   +visual>
      isa        move-attention
      screen-pos =visual-location
   =goal>
      action      1-2-2-consider-target
)
    
(p 1-2-1-b-no-piece
   =goal>
      action      found-location
      target =tar
   ?visual-location>
      state      error
==>
   =goal>
      target nil
      action      target-find
)
    
(p 1-2-2-a-1-not-matched
   =goal>
       isa         game-state
       action      1-2-2-consider-target
       color       =c
       
   ?retrieval>
       state       free
       buffer      full
       
   =retrieval>
       isa         pic
       n           =expected-name
       l           =loc
       c           =c
       
   =visual>
       value       =uni

   ?manual>
       state       free
       
   !bind! =name (unicode-to-name =uni)
   !eval! (not (eq =name =expected-name))

==>  
   +imaginal>
       isa         pic
       n           =name
       l           =loc
       c           =c
   =goal>
       action      refreshing-target
)

(p 1-2-2-a-2-refresh-target
   =goal>
       isa         game-state
       action      refreshing-target 
   =imaginal>
==>
   =goal>
       target      =imaginal
       action      1-2-1-retrieve-target
  -imaginal>
)
    
(p 1-2-2-b-matched
   =goal>
       isa         game-state
       action      1-2-2-consider-target
       color       =c
       
   ?retrieval>
       state       free
       buffer      full
       
   =retrieval>
       isa         pic
       n           =expected-name
       
   =visual>
       value       =uni
       
   ?manual>
       state       free
   !bind! =name (unicode-to-name =uni)
   !eval! (eq =name =expected-name)
==>
   =retrieval>
   =visual>
   =goal>
       action      check-mine  
)

(p 1-2-3-a-click-mine
   =goal>
       turn t
       action      check-mine
       color       =c         
   =visual-location>
       isa         visual-location
       color       =c          

   ?manual>
       state       free

==>
   =goal>
       action      moving-cursor
   =visual-location>    
   +manual>
       isa         move-cursor
       loc         =visual-location
)

(p 1-2-3-b-your-agent
   =visual-location>
       color     =c
   =retrieval>
   isa pic
   n =name
   =goal>
      turn t
       action      check-mine
       - color       =c  
   ?retrieval>
       state free
   ==>
   =visual-location>
   +retrieval>
       isa rel
       a =name
       ac =c
   =goal>
   target nil
   action target-find
)

(p 1-2-3-c-your-target
   =visual-location>
       isa         visual-location
       color     =c
   =retrieval>
   isa pic
   n =name
   =goal>
       action      check-mine
       turn t
       - color       =c  
   ?retrieval>
       state free
   ==>
   +retrieval>
       isa rel
       ta =name
       tc =c
   =goal>
   target nil
   action target-find
)
    
(p 1-2-3-d-not-my-turn
   =goal>
   action check-mine
   turn nil
   ==>
   =goal>
   target nil
   action target-find
)
    
 (p 1-3-click-mouse
     =goal>
        isa         game-state
        action      moving-cursor
     
     ?manual>
        state       free
  ==>
     =goal>
        action      2-specify-move
     +manual>
        cmd         click-mouse
  )
;=========================================================phase 2===========================================================
    
  (p 2-1-recall-move
     =goal>
        isa         game-state
        action      2-specify-move
        target =tar
   ?retrieval>
      state  free 
  ==>
    =goal>
        action      2-recall-move
    +retrieval> 
        isa mv
        agent =tar
)
(p 2-2-a-1-valid-move
   =goal>
   isa game-state
   action 2-recall-move
   =retrieval>
   isa mv
   dest =loc
   !bind! =lx (rel-to-abs-lx =loc)
   !bind! =ux (rel-to-abs-ux =loc)
   !bind! =ly (rel-to-abs-ly =loc)
   !bind! =uy (rel-to-abs-uy =loc)
   ==>
   +visual-location>
      isa        visual-location
      > screen-x =lx
      < screen-x =ux
      > screen-y =ly
      < screen-y =uy
      color gray
   =goal>
   action 2-look-loc
)
    
(p 2-2-a-2-a-gray-exists
   =goal>
   isa game-state
   action 2-look-loc
   
   =visual-location>
   color gray
==>
   =visual-location>
   +visual>
   isa        move-attention
   screen-pos =visual-location
   =goal>
   action 2-recall-score
)
    
(p 2-2-1-2-b-no-gray
   =goal>
   isa game-state
   action 2-look-loc
   ?visual-location>
   state error
   ==>
   =goal>
   action 2-3-find-gray
)
(p 2-2-b-no-move
   =goal>
   action 2-recall-move
   ?retrieval>
   state error
   ==>
   =goal>
   action 2-3-find-gray
)
(p 2-3-find-gray
   =goal>
   action 2-3-find-gray
  ==>   
   =goal>
    action 2-finding-gray
    +visual-location>
    isa         visual-location
    color       gray
)

(p 2-4-a-1-move-recall
   =goal>
   action 2-finding-gray
   target =tar
   =visual-location>   
   isa         visual-location
   screen-x    =vx             
   screen-y    =vy
   color gray
   ?retrieval>
   state free
   !bind! =loc-name (abs-xy-to-loc =vx =vy)
==>
   =visual-location>   
   +visual>
   isa        move-attention
   screen-pos =visual-location
   +retrieval>
       isa mv
       agent =tar
       dest =loc-name
   =goal>
       action 2-try-move-recall
)

(p 2-4-a-2-a-success-move-recall
   =goal>
   action 2-try-move-recall
   =retrieval>
   isa mv
   ==>   
   =retrieval>
   =goal>
   action 2-recall-score
)

(p 2-4-a-2-b-failed-move-recall
   =goal>
   action 2-try-move-recall
   ?retrieval>
   state error
   ==>   
   =goal>
   action 2-6-go-eval
)

(p 2-4-b-search-failed
   =goal>
   action 2-finding-gray
   
   ?visual-location>
       state       error
==>
   =goal>
   action target-find
   target nil
)
(p 2-5-recall-score
   =goal>
   action 2-recall-score
   =retrieval>
==>
   =goal>
   action 2-check-score
   +retrieval>
   isa score
   m =retrieval   
)
(p 2-5-1-a-1-positive-skip-eval
   =goal>
   action 2-check-score
   =retrieval>
   isa score
   > s 0
   ==>
   =retrieval>
   =goal>
   action 4-decide
)
(p 2-5-1-a-1-negative-skip-eval
   =goal>
   action 2-check-score
   =retrieval>
   isa score
   <= s 0
   ==>
   =retrieval>
   =goal>
   action 4-decide
)
(p 2-5-1-b-think-again
   =goal>
   action 2-check-score
   =retrieval>
   isa score
   ==>
   =goal>
   action 2-6-go-eval
)
(p 2-5-2-no-score
   =goal>
   action 2-check-score
   ?retrieval>
   state error
==>
   =goal>
   action 2-6-go-eval
)
(p 2-6-go-eval
   =goal>
   action 2-6-go-eval
   target =tar
   =visual-location>   
   screen-x    =vx             
   screen-y    =vy
   !bind! =loc-name (abs-xy-to-loc =vx =vy)
==>
   +imaginal>
   isa mv
   agent =tar
   dest =loc-name
   =goal>
   action 3-eval
)
;=========================================================phase 3===========================================================
(p 3-0-1-mock
   =goal>
   action 3-eval
   color =c
   =imaginal>
   isa mv
   dest =loc
   !bind! =lx (rel-to-abs-lx =loc)
   !bind! =ux (rel-to-abs-ux =loc)
   !bind! =ly (rel-to-abs-ly =loc)
   !bind! =uy (rel-to-abs-uy =loc)
   !bind! =oc (opposite-color =c)
   ==>
   =imaginal>
   +visual-location>
      isa        visual-location
      > screen-x =lx
      < screen-x =ux
      > screen-y =ly
      < screen-y =uy
      color =oc
   =goal>
   action 3-0-2-get-score
)
(p 3-0-2-a-mock
   =goal>
   action 3-0-2-get-score
   ?visual-location>
   state error
   =imaginal>
   ==>
   +imaginal>
   isa score
   m =imaginal
   s 0
   =goal>
   action 4-eval-move
)
    
(p 3-0-2-b-1-mock
  =goal>
   action 3-0-2-get-score
  ?visual-location>
   buffer full
  =visual-location>
==>   
  +visual>
  isa        move-attention
  screen-pos =visual-location
  =goal>
   action 3-0-2-b-get-visual
)
(p 3-0-2-b-2-mock
   =goal>
   action 3-0-2-b-get-visual
   =visual>
   value =uni
   !bind! =sc (get-piece-score =uni)
   =imaginal>
   ==>
   =visual>
   +imaginal>
   isa score
   m =imaginal
   s =sc
   =goal>
   action 4-eval-move
)
;=========================================================phase 4===========================================================
(p 4-0-skipped-3 
   =goal>
   action 4-decide
   =retrieval>
   ==>
   =retrieval>
   =goal>
   action 4-eval-move 
   +imaginal>
   =retrieval
)    
(p 4-1-a-1-compare-existing
   =goal>
      isa         game-state
      action      4-eval-move    
      next-move   =old-best   
      - next-move nil

   =imaginal>
      isa         score
      m           =new-move
      s           =new-score
      
   ?retrieval>
      state       free
==>
   =imaginal>
   =goal>
      action      4-comparing-scores
   +retrieval>
      isa         score
      m           =old-best
)

(p 4-1-b-first-move-found
   =goal>
      isa         game-state
      action      4-eval-move
      next-move   nil       

   =imaginal>
      isa         score
      m           =new-move
      s           =new-score
==>
   =imaginal>
   =goal>
      action      4-2-consider-candidate
      next-move   =new-move
)

(p 4-1-a-2-a-a-found-better
   =goal>
      isa         game-state
      action      4-comparing-scores
   
   =imaginal>
      isa         score
      m           =new-move
      s           =new-score

   =retrieval>
      isa         score
      s           =old-score
      
   !eval! (> =new-score =old-score) 
==>
   =goal>
      action      4-2-consider-candidate
      next-move   =new-move   ; Best move 
)

(p 4-1-a-2-a-b-keep-old
   =goal>
      isa         game-state
      action      4-comparing-scores
   
   =imaginal>
      isa         score
      s           =new-score

   =retrieval>
      isa         score
      s           =old-score
      
   !eval! (<= =new-score =old-score)
==>
   =goal>
      action      target-find  
      target      nil         
   -imaginal>                
)

(p 4-1-a-2-b-retrieval-failed
   =goal>
      isa         game-state
      action      4-comparing-scores
   =imaginal>
      isa         score
      m           =new-move
   ?retrieval>
      state       error
==>
   =goal>
      action      4-2-consider-candidate
      next-move   =new-move
)

(p 4-3-a-decide-to-move-positive-urgent
   =goal>
      isa         game-state
      action      4-2-consider-candidate
      next-move   =best-move
   
   =imaginal>
      isa         score
      s           =score

   !eval! (> =score 0)
==>
   =imaginal>
   =goal>
      action      5-decide-execute
)

(p 4-3-b-decide-to-move-negative-urgent
   =goal>
      isa         game-state
      action      4-2-consider-candidate
      next-move   =best-move
   
   =imaginal>
      isa         score
      s           =score

   !eval! (<= =score 0)
==>
   =imaginal>
   =goal>
      action      5-decide-execute
)

(p 4-3-c-think-more
   =goal>
      isa         game-state
      action      4-2-consider-candidate
==>
   =goal>
      action      target-find
      target      nil
   -imaginal>
)

(p 5-1-recall-move-details
   =goal>
      isa         game-state
      action      5-decide-execute
   =imaginal>
      m      =move      
   ?retrieval>
      state       free
==>
   =imaginal>
   =goal>
      action      5-2-look-dest
   +retrieval> =move
)

(p 5-2-look-at-dest
   =goal>
      isa         game-state
      action      5-2-look-dest
      
   =retrieval>
      isa         mv
      dest        =loc 
      
   ?visual-location>
      state       free

   !bind! =lx (rel-to-abs-lx =loc)
   !bind! =ux (rel-to-abs-ux =loc)
   !bind! =ly (rel-to-abs-ly =loc)
   !bind! =uy (rel-to-abs-uy =loc)    
==>
   !output! (Looking at =loc X =lx to =ux / Y =ly to =uy)
   =retrieval>
   +visual-location>
      isa         visual-location
      >= screen-x =lx
      <= screen-x =ux
      >= screen-y =ly
      <= screen-y =uy
      
   =goal>
      action      5-3-move-mouse
)

(p 5-3-move-mouse-cursor
   =goal>
      isa         game-state
      action      5-3-move-mouse
      
   =visual-location>
      isa         visual-location
      
   ?manual>
      state       free
==>
   =visual-location>
   +manual>
      isa         move-cursor
      loc         =visual-location
      
   =goal>
      action      5-4-click
)

(p 5-4-click-mouse
   =goal>
      isa         game-state
      action      5-4-click
      
   ?manual>
      state       free
==>
   +manual>
      isa         click-mouse
      
   =goal>
      action      target-find 
      next-move   nil
)
)
