# HealthBridge — Technical & UX Documentation

**Release: v2.5 — International Premium UI**

## 1. Purpose

HealthBridge is a desktop-first wellness tracking application. The goal is to make everyday habit data understandable without presenting it as medical advice.

Tracked dimensions:

- Sleep (hours)
- Activity (minutes)
- Hydration (liters)
- Personal wellness time (minutes)

## 2. Architecture

```text
                 ┌─────────────────────────┐
                 │     PySide6 MainWindow   │
                 │  one permanent shell     │
                 └────────────┬────────────┘
                              │
                    QStackedWidget pages
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
   Premium presentation                     Qt-compatible
   background / widgets                     enhancement libs
          │                                  QtAwesome / PyQtGraph
          └───────────────────┬───────────────────┘
                              ▼
                     HealthBridgeApp
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                  Models            Analytics
                    │                   │
                    └─────────┬─────────┘
                              ▼
                       Local JSON Storage
```

The UI does not implement scoring formulas or directly manipulate the JSON file. `main.py` creates `QApplication` before constructing the window. `app.py` remains the controller between UI, models, analytics and storage.

## 3. Production UI design system

### Design tokens

`src/ui.py` centralizes the primary visual values through `THEMES` and the shared constants for accent/status colors. This prevents the interface from accumulating unrelated hard-coded colors.

The main surfaces are:

- Background
- Sidebar/panel
- Card
- Elevated card
- Text primary
- Text secondary
- Border
- Input field
- Accent
- Success
- Warning
- Error
- Informational accent

### Typography

The interface uses a restrained Segoe UI hierarchy for:

- Product/brand name
- Page title
- Page subtitle
- Section/card title
- Metric numbers
- Labels
- Secondary descriptions
- Status badges

Layouts use Qt spacing and margins consistently and avoid fixed-position UI elements.

### Icon system

QtAwesome provides Font Awesome vector icons for navigation and metric cards. The UI checks whether QtAwesome is available and falls back safely instead of making the application unlaunchable when an optional icon dependency is absent.

## 4. Advanced background engine

`GradientBackground` is a custom QWidget painted with native Qt APIs.

### Rendering layers

1. **Base gradient** — three-stop preset-specific atmospheric background.
2. **Ambient light fields** — radial gradients that breathe slowly.
3. **Cursor parallax** — pointer position is interpolated before influencing light positions.
4. **Particle field** — deterministic lightweight particles drift using trigonometric motion.
5. **Constellation layer** — sparse low-alpha links add depth without becoming a wallpaper.
6. **Perspective floor** — restrained horizon and converging lines provide spatial depth.
7. **Cursor bloom** — a soft local highlight follows the pointer.

The background is presentation-only and never changes records, calculations or storage.

### Performance

The animation timer runs at a controlled frequency rather than repainting as fast as possible. Reduced mode lowers the update frequency and motion rate; Off mode stops decorative animation updates. Cursor tracking is local to the background widget, avoiding the previous global `QApplication` event filter and its shutdown hazards.

## 5. Motion architecture

The UI uses Qt-native animation primitives:

- `QPropertyAnimation` for opacity, score progress, progress bars, hover movement and button feedback.
- `QParallelAnimationGroup` / `QSequentialAnimationGroup` remain available for future composite motion without changing the shell architecture.
- `QGraphicsOpacityEffect` provides page/toast fades.
- `QTimer` controls the ambient scene.

Animations communicate state rather than decorate every interaction. Reduced-motion and Off modes are available for accessibility and lower resource usage.

## 6. Data visualization

The Trends page uses **PyQtGraph** when installed. It provides efficient native Qt plotting, mouse-disabled presentation mode, a smooth line series and a target reference line.

A QPainter chart remains as a fallback, so the application can still render trends when PyQtGraph is unavailable.

Charts are used only where they communicate actual logged data.

## 7. Interaction feedback

The interface uses a reusable `Toast` component for lightweight feedback:

- Success
- Information
- Warning
- Error

Toasts have a clear accent, readable text wrapping, close control, fade entrance and automatic dismissal. Critical confirmations such as deleting or resetting data continue to use Qt confirmation dialogs.

## 8. Main screens

### Overview

Greeting, seven-day score, quick action, smart insight, four metric cards and recent activity.

### Daily log

Create or update one record by date. Numeric validation remains in the existing model/controller layer.

### History

Newest-first record list with demo/logged status and deletion.

### Trends

Metric selector plus recent-record chart and personal target reference.

### Analytics

Achievement, consistency and trend components shown separately so the score is explainable.

### Goals

Personal targets that feed the existing scoring and suggestion engine.

### Report

Seven-day averages, score, suggestions and the existing non-medical disclaimer.

### Settings

Profile, appearance, background preset, animation mode/intensity, demo data and local reset.

## 9. Reliability architecture

The previous onboarding failure came from replacing the `QMainWindow` central widget while a `QStackedWidget` was still owned by the original widget tree. The current implementation has exactly one permanent central `GradientBackground` and exactly one permanent `QStackedWidget`.

Onboarding is inserted into that same stack. `build_shell()` only changes visibility and rebuilds pages inside the existing stack. It never calls `setCentralWidget()` again.

The background also no longer registers a global application event filter. This removes a class of teardown-time callback failures.

## 10. Accessibility

The UI provides:

- Readable contrast in dark and light modes
- Visible focus borders on form controls
- Tooltips on important controls
- Keyboard-friendly Qt widgets
- Word wrapping for long descriptions and notifications
- Reduced-motion and Off animation modes
- Status text in addition to color accents
- Responsive layouts for smaller windows

## 11. Framework strategy

HealthBridge is intentionally a **native Qt application**, not a mixture of competing GUI frameworks.

### Why QtAwesome and PyQtGraph

Both libraries are designed to work with Qt/PySide6 and therefore improve icons and data visualization without introducing a second windowing/event-loop architecture.

### Why not embed Flet + Dear PyGui

Flet and Dear PyGui are capable Python GUI frameworks, but they are not drop-in widget libraries for an existing PySide6 widget tree. Embedding all three merely to create visual effects would complicate event loops, ownership, packaging and Windows shutdown behavior. The production design therefore uses compatible Qt extensions and native Qt rendering instead.

## 12. Analytics

```text
Final score = Achievement × 0.70
            + Consistency × 0.20
            + Trend × 0.10
```

Each metric is compared with the user's own target. The resulting score is capped at 100. It is explicitly not a medical score.

## 13. Installation

Recommended Python: 3.10+

Install the full UI stack:

```bash
python -m pip install -r requirements.txt
```

Run:

```bash
python -m src.main
```

Test:

```bash
python -m src.tests -v
```

## 14. Validation performed for this release

The available execution environment does not provide network access, so external GUI wheels could not be installed here. The following checks were completed locally:

- Every Python module in `src/` compiles successfully with `py_compile`.
- All **38 existing core tests** pass.
- The controller, model, analytics and storage APIs were preserved.
- No new project source files were introduced and no existing project files were removed.

A final Windows GUI smoke test should be run after installing the requirements on the target Windows machine because PySide6 itself is platform/runtime dependent.

## 2.5.1 Runtime stability notes

The notification system uses weak references plus `shiboken6.isValid()` checks so Python does not call methods on Qt objects whose underlying C++ objects have already been deleted. Toasts now finish their fade-out before `deleteLater()` and the close button follows the same lifecycle.

The shared label helper also rejects non-positive point sizes before calling `QFont.setPointSize()`. This prevents invalid font-size requests from being forwarded to Qt while preserving the normal inherited font when no explicit size is supplied.

These safeguards are presentation-layer changes only; scoring, validation, persistence, navigation targets and controller behavior are unchanged.

### Verification

The existing test suite contains 38 tests covering analytics, controller flows, storage and validation. The suite passes after the UI repair. Python compilation also succeeds for every module in `src/`.


## Settings page — v2.5 UI repair

The Settings screen now uses a scrollable, sectioned layout so controls remain usable on smaller windows and high-DPI displays. Profile, appearance, motion/accessibility, and local-data controls are visually separated with descriptive helper text. Theme and background changes preview immediately, while profile data remains explicitly saved with **Save profile**. Animation intensity is persisted locally and is applied to the ambient background without changing wellness calculations or application data.


## UI/UX release notes — international competition refresh

### Visual architecture
The interface now uses centralized design tokens for surfaces, borders, text, status colors, controls and focus states. Dark and light appearances update the complete widget stylesheet instead of leaving isolated dark-only controls. System appearance resolves from the native Qt palette.

### Healthcare graphics
The UI includes a lightweight vector `HealthNetworkGraphic` painted with Qt. It combines a medical cross, connected care nodes, a pulsing data path and ambient halo. It requires no image file and stops its timer during window shutdown.

### Motion and performance
Ambient background motion uses a bounded QTimer and supports Full, Reduced and Off modes. Decorative healthcare graphics also use a bounded timer. Closing the window stops animation timers. The UI avoids web views and continuously running background workers for decorative effects.

### Accessibility
Controls retain text labels, tooltips, visible focus states and keyboard-friendly operation. Reduced/Off motion does not remove information. Long text uses word wrapping and scrollable settings/history layouts.

### Reliability
The release preserves the single central widget and single page-stack architecture. Toast objects are lifecycle-safe, font helpers reject non-positive point sizes, and Qt size arguments use the correct `QSize` type.

### v2.6.1 runtime hotfix
- Fixed missing `QRectF` import used by the native HealthBridge network graphic paint event.
- Prevents the paint-event exception that could cascade into `QPaintDevice: Cannot destroy paint device that is being painted`.
