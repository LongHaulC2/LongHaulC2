# compilation


## Server:
`nuitka --standalone --onefile --include-package=server   --include-package-data=limits run.py` (one binary, extracts to ./tmp)
Alternatively, can get rid of "--onefile" to have it all in one folder in current location

- note - this I think still reqs file paths of certain items, so the templates being wherever they need to be (/var/lib, or whatever, etc.). Works fine though so far. 
- note 2: This is with dev server func, not gunicorn. test with gunicorn as well, should work, but still.

So, idea for goign forward:

 - Modify "make deploy" to use the .bin instead of installing python deps. This gives us the following:
   - 1. IP protection
   - 2. Room for licensing/limitations in the future (make server source private, only release bin + setup)
   - 3. Less dependency BS. 

 - Not sure when to do this. options:
   - [THIS] have source public during beta, then close it off when out of beta. Ship releases with compiled version, and modified make deploy
   - Close off server code now. 

- 0 issues with client being open source, etc. 
- I want to leave the implant open though, allows for modification.