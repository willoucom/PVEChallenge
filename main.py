"""Entry point of the distributed executable.

Nuitka compiles this file, not `pvechallenge/gui.py`: a package module
compiled as a script no longer belongs to its package, and its relative
imports fail. The absolute import below lets Nuitka follow the whole
package from the root.
"""

from pvechallenge.gui import main

raise SystemExit(main())
