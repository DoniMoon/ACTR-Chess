# ACTR-Chess
Chess-playing experiments with ACT-R

# File description

actr.py : modified ACT-R wrapper for multiple agent
experiment.py : chess environment


# How to reproduce
1. Install official ACT-R.
2. Run two ACT-R (default port should be 2650 and 2651) in two seperate window.
```bash
./run-act-r.command
```
if ports are not assigned to 2650 and 2651 , modify actr.py
```python
    actr1 = actr.start(host="127.0.0.1", port=2650)
    actr2 = actr.start(host="127.0.0.1", port=2651)
```
this part.
3. run experiment.py
```bash
python experiment.py
```