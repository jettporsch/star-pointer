#!/bin/bash
# Double-click to start Star Pointer. Plug in the Nucleo USB and 12V first.
# Close this window to stop; the laser switches off on the way out.
cd "$(dirname "$0")"
(sleep 2 && open http://localhost:8000) &
python3 -m app.web
