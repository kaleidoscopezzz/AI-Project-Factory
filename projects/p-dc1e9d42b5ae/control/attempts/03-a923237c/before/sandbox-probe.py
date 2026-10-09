from pathlib import Path
import sys
try:
 Path(sys.argv[1]).write_text("boundary failed")
except PermissionError:
 print("outside-write-denied")
else:
 raise SystemExit("outside-write-allowed")
