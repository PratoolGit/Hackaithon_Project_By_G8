"""HealthBridge - PySide6 application entry point."""

from __future__ import annotations

import sys
import traceback

from PySide6.QtWidgets import QApplication

from .app import HealthBridgeApp
from .ui import HealthBridgeUI


def main() -> int:
    """Create QApplication first, then construct the main window."""
    qt_app = QApplication.instance() or QApplication(sys.argv)
    qt_app.setApplicationName("HealthBridge")
    qt_app.setOrganizationName("HealthBridge")

    try:
        controller = HealthBridgeApp()
        window = HealthBridgeUI(controller)
        window.show()
        return qt_app.exec()
    except Exception:
        print("\n" + "=" * 70)
        print("HEALTHBRIDGE STARTUP ERROR")
        print("=" * 70)
        traceback.print_exc()
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
