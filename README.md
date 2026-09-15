# HealthBridge

**Version 2.5 — International Premium UI**

HealthBridge is a privacy-first desktop wellness tracker for personal habit tracking, school/hackathon demonstrations and product showcases. It records sleep, activity, hydration and wellness time, compares them with personal goals, and produces transparent lifestyle insights.

## ✨ Premium UI 2.5

The application keeps **PySide6/Qt as the production desktop shell** and adds two Qt-compatible Python UI libraries:

- **QtAwesome** — consistent vector iconography with graceful fallback when unavailable.
- **PyQtGraph** — high-performance interactive trend visualization with a native QPainter fallback.

Flet and Dear PyGui are intentionally not embedded into the same process. They use independent window/render/event-loop architectures; mixing them into an existing Qt desktop shell for decoration would add packaging and shutdown complexity without improving the actual product. The result is a more reliable native Windows application.

### Visual system

- Premium dark, light and system appearance modes
- Centralized design tokens for surfaces, text, borders and status colors
- Rounded glass-inspired cards with restrained transparency
- Consistent typography, spacing and hierarchy
- Vector icons for navigation and wellness metrics
- Animated score ring and analytics bars
- Responsive Qt layouts instead of hard-coded page positioning
- Word-wrapped long messages and readable empty states
- Professional hover, press, focus and active states

### 🌌 Advanced ambient background

13 selectable backgrounds are available from Settings:

1. Aurora
2. Deep Space
3. Midnight
4. Ocean
5. Purple Nebula
6. Sunset
7. Emerald
8. Cyber Blue
9. Soft Professional
10. Dark Glass
11. Minimal Light
12. Dynamic Aurora
13. Subtle Animated Gradient

The background uses native `QPainter`, `QLinearGradient`, `QRadialGradient` and lightweight timers. It includes slow ambient light movement, cursor parallax, a restrained particle/constellation field, perspective depth and a cursor halo. It is deliberately subtle so data remains the visual priority.

### Motion & accessibility

Settings now exposes:

- **Full** — normal ambient motion and micro-interactions
- **Reduced** — slower, lower-frequency movement
- **Off** — decorative background animation disabled
- **Animation intensity** — quick accessibility control that maps to the motion mode

Motion is never required to understand information. Controls retain clear text, focus states and status feedback.

### Interaction feedback

- Animated page fade-ins
- Hover elevation for cards
- Button press feedback
- Animated wellness score ring
- Animated progress bars
- Toast notifications for save/delete/settings actions
- Explicit validation errors
- Tooltips on important controls
- Animated navigation active states through Qt styling

## Reliability fixes

The v2.4 onboarding crash was caused by replacing the `QMainWindow` central widget while the application was already using a `QStackedWidget`. Version 2.5 retains one permanent central widget and one permanent page stack. Onboarding is simply another stack page, preventing Qt QObject ownership churn and the previous `QVBoxLayout returned NULL` failure.

The background no longer installs a global application event filter. Cursor tracking is handled directly by the canvas widget, which also removes the shutdown-time `eventFilter()` callback failure seen in the previous build.

## Run

From the project root:

```bash
python -m pip install -r requirements.txt
python -m src.main
```

Windows alternative:

```powershell
py -m pip install -r requirements.txt
py -m src.main
```

## Project structure

```text
src/
├── main.py        # Application entry point
├── app.py         # Controller / application state
├── ui.py          # Premium PySide6 UI, animation, background and widgets
├── analytics.py   # Wellness scoring and suggestions
├── models.py      # User and wellness record models
├── storage.py     # Local JSON persistence
├── sample_data.py # Demo data generator
└── tests.py       # Core unit tests
```

No project source files are added or removed by the UI redesign.

## Analytics model

The wellness score remains transparent and non-medical:

- **Achievement — 70%**
- **Consistency — 20%**
- **Trend — 10%**

The result is capped at 100 and is a lifestyle-tracking score, not a diagnosis or medical assessment.

## Privacy

HealthBridge stores data locally through the existing storage layer. No cloud account or remote health-data service is required.

## Demo flow

1. Launch HealthBridge.
2. Enter a name during onboarding.
3. Open **Settings → Load demo data** for a presentation-ready timeline.
4. Explore **Overview → Trends → Analytics → Report**.
5. Use **Daily log** to enter a real day.
6. Adjust personal targets under **Goals**.
7. Use **Settings → Background** and **Settings → Animation mode** to personalize the presentation.

## Testing

Core behavior is testable without a GUI:

```bash
python -m src.tests -v
```

The UI requires PySide6 and a normal desktop session. PyQtGraph and QtAwesome are optional at runtime because `ui.py` contains graceful fallbacks, but both are included in `requirements.txt` for the full premium experience.


## International competition UI refresh

The current UI release adds a healthcare-specific visual language without introducing a web frontend or external runtime assets. Native Qt painting provides an animated medical-network illustration, ambient backgrounds, restrained motion, accessible focus states, responsive layouts, and a consistent dark/light design-token system. The visual layer remains separate from the controller, analytics and storage layers.

### Product principles

- **Trust first:** readable hierarchy, restrained color, local/private status and explicit non-medical-advice language.
- **Human + technology:** healthcare-network vector graphics connect the product identity to digital health without stock imagery.
- **Motion with purpose:** animation communicates transitions and state; Reduced/Off modes remain fully usable.
- **Offline-ready:** no runtime website, JavaScript frontend, or remote image dependency is required.
- **Competition-ready:** dashboard, onboarding, settings, analytics, history and reports share the same visual system.

### Compatibility note

PySide6 remains the production windowing/rendering framework. QtAwesome and PyQtGraph are optional enhancements that integrate with the Qt event loop and have native fallbacks. Flet and Dear PyGui are not embedded because their independent application/event-loop architectures would increase packaging and lifecycle complexity without improving the native Qt product.
