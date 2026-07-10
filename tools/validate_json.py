import json, sys
for p in sys.argv[1:]:
    json.load(open(p)); print('PASS', p)
