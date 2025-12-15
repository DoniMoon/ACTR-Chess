# ACTR-Chess

![Chess Playing Demo](playing_demo.gif)
Chess-playing experiments with ACT-R

# File description

- actr.py: modified ACT-R wrapper for multiple agents
- experiment.py: chess environment
- base-model.lisp: ACT-R model file.
- Description.md: Simple documentation of base-model.lisp


# How to reproduce
1. Install official ACT-R.
2. Clone this repo, and execute
```bash
pip install -r requirements.txt
```
3. Run two ACT-R (default port should be 2650 and 2651) in two separate windows.
```bash
./run-act-r.command
```
if ports are not assigned to 2650 and 2651, modify actr.py
```python
    actr1 = actr.start(host="127.0.0.1", port=2650)
    actr2 = actr.start(host="127.0.0.1", port=2651)
```
this part.
4. run experiment.py
```bash
python experiment.py
```
