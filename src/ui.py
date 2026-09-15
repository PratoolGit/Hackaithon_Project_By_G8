"""HealthBridge premium desktop UI.

Presentation layer only. Business logic, analytics and persistence stay in the
existing controller/model/storage modules. The UI uses PySide6 as the native
windowing/rendering engine, with optional QtAwesome icons and PyQtGraph for
high-quality data visualization.
"""
from __future__ import annotations

import math
import os
import weakref
from datetime import date
from typing import Callable

from PySide6.QtCore import (
    QEasingCurve, QPoint, QPointF, QPropertyAnimation, QParallelAnimationGroup,
    QSequentialAnimationGroup, QTimer, Qt, Signal, Property, QSettings, QRect, QRectF, QSize,
)
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QRadialGradient, QPainter, QPen, QBrush,
    QPainterPath, QIcon,
)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFrame, QGraphicsOpacityEffect,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QStackedWidget,
    QVBoxLayout, QWidget, QFormLayout, QSlider, QButtonGroup, QToolButton,
)

try:
    from shiboken6 import isValid as _qt_is_valid
except Exception:  # pragma: no cover
    def _qt_is_valid(obj):
        return obj is not None


try:
    from .models import ValidationError
except ImportError:  # pragma: no cover
    from models import ValidationError

try:  # Optional, production-friendly icon layer.
    import qtawesome as qta
except Exception:  # pragma: no cover
    qta = None

try:  # Optional, richer charting; custom fallback remains available.
    import pyqtgraph as pg
except Exception:  # pragma: no cover
    pg = None

BG = "#070A11"
PANEL = "#0C111B"
CARD = "#101826"
CARD_2 = "#151F30"
BORDER = "#243249"
TEXT = "#F5F7FB"
MUTED = "#91A0B5"
ACCENT = "#7B6CFF"
ACCENT_2 = "#2ED6C3"
BLUE = "#59A6FF"
GREEN = "#4BDA8B"
YELLOW = "#F3C85B"
RED = "#FF6B7A"

# Expanded premium background catalogue while retaining the original names.
GRADIENTS = {
    "Aurora": ("#08101D", "#26164B", "#063B3B"),
    "Deep Space": ("#05070D", "#121A2D", "#0A1020"),
    "Midnight": ("#070A12", "#151A31", "#10212D"),
    "Ocean": ("#06131F", "#123C59", "#073C4C"),
    "Purple Nebula": ("#0F081B", "#32145E", "#17103B"),
    "Sunset": ("#180B18", "#4A1F35", "#5A2A12"),
    "Emerald": ("#061510", "#123D34", "#0A2832"),
    "Cyber Blue": ("#050D19", "#0B2C53", "#062D3B"),
    "Soft Professional": ("#111827", "#1D2638", "#13242A"),
    "Dark Glass": ("#070B12", "#111827", "#101923"),
    "Minimal Light": ("#E9EFF7", "#DCE7F5", "#EEF4F6"),
    "Dynamic Aurora": ("#07111D", "#25184E", "#06463D"),
    "Subtle Animated Gradient": ("#0B111A", "#182338", "#10252B"),
}

METRICS = ["sleep_hours", "activity_minutes", "hydration_liters", "wellness_minutes"]
LABELS = {
    "sleep_hours": ("Sleep", "hours", "fa5s.moon"),
    "activity_minutes": ("Activity", "min", "fa5s.walking"),
    "hydration_liters": ("Hydration", "L", "fa5s.tint"),
    "wellness_minutes": ("Wellness", "min", "fa5s.heart"),
}

# Central design tokens. Stylesheet is rebuilt when the appearance mode changes.
THEMES = {
    "dark": dict(bg="#070A11", panel="#0C111B", card="#101826", card2="#151F30", text="#F5F7FB", muted="#91A0B5", border="#243249", field="#0B121D"),
    "light": dict(bg="#F3F7FB", panel="#FFFFFF", card="#FFFFFF", card2="#F7FAFD", text="#172033", muted="#65748B", border="#D9E2EF", field="#FFFFFF"),
}


def icon(name: str, color: str = TEXT, size: int = 16) -> QIcon:
    if qta:
        try:
            return qta.icon(name, color=color)
        except Exception:
            pass
    return QIcon()


def label(text, object_name=None, color=None, size=None, bold=False):
    w = QLabel(text)
    if object_name:
        w.setObjectName(object_name)
    f = w.font()
    if isinstance(size, (int, float)) and size > 0:
        f.setPointSize(int(size))
    f.setBold(bold)
    w.setFont(f)
    if color:
        w.setStyleSheet(f"color:{color};")
    return w


def stylesheet(mode="dark") -> str:
    """Centralized HealthBridge design system with accessible dark/light surfaces."""
    t = THEMES.get(mode, THEMES["dark"])
    light = mode == "light"
    sidebar = "rgba(255,255,255,238)" if light else "rgba(7,12,21,238)"
    card = "rgba(255,255,255,232)" if light else "rgba(16,24,38,235)"
    card2 = "rgba(248,251,255,238)" if light else "rgba(21,31,48,235)"
    field = "#FFFFFF" if light else t["field"]
    secondary = "#EEF3FA" if light else "rgba(24,35,52,235)"
    secondary_hover = "#E3EBF6" if light else "#202D42"
    list_bg = "#FFFFFF" if light else "#111925"
    progress_bg = "#DCE5F0" if light else "#0B111B"
    focus = "#5E54E8" if light else ACCENT
    return f"""
    QWidget {{ color:{t['text']}; font-family:'Segoe UI'; font-size:13px; }}
    QMainWindow {{ background:transparent; }}
    QFrame#sidebar {{ background:{sidebar}; border-right:1px solid {t['border']}; }}
    QFrame#card {{ background:{card}; border:1px solid {t['border']}; border-radius:18px; }}
    QFrame#hero {{ background:{card}; border:1px solid {t['border']}; border-radius:26px; }}
    QFrame#glass {{ background:rgba(120,145,180,28); border:1px solid rgba(120,140,175,55); border-radius:16px; }}
    QFrame#statusCard {{ background:{card2}; border:1px solid {t['border']}; border-radius:15px; }}
    QLabel#brand {{ font-size:21px; font-weight:800; }}
    QLabel#eyebrow {{ color:{ACCENT_2}; font-size:10px; font-weight:800; letter-spacing:1.4px; }}
    QLabel#pageTitle {{ font-size:30px; font-weight:800; }}
    QLabel#pageSub {{ color:{t['muted']}; font-size:13px; }}
    QLabel#cardTitle {{ font-size:14px; font-weight:750; }}
    QLabel#metricValue {{ font-size:25px; font-weight:800; }}
    QLabel#muted {{ color:{t['muted']}; }}
    QLabel#badge {{ background:rgba(46,214,195,24); color:{ACCENT_2}; border:1px solid rgba(46,214,195,70); border-radius:11px; padding:6px 10px; font-size:9px; font-weight:800; }}
    QLabel#sectionKicker {{ color:{t['muted']}; font-size:9px; font-weight:800; letter-spacing:1px; }}
    QLabel#statusGood {{ color:{GREEN}; font-weight:750; }}
    QPushButton#nav {{ text-align:left; padding:11px 13px; border:0; border-radius:12px; color:{t['muted']}; background:transparent; font-size:13px; font-weight:650; }}
    QPushButton#nav:hover {{ background:rgba(123,108,255,18); color:{t['text']}; }}
    QPushButton#nav[active="true"] {{ background:rgba(123,108,255,30); color:{focus}; border:1px solid rgba(123,108,255,70); }}
    QPushButton#primary {{ background:{ACCENT}; border:0; border-radius:11px; padding:11px 17px; color:white; font-weight:800; }}
    QPushButton#primary:hover {{ background:#8D80FF; }}
    QPushButton#primary:pressed {{ background:#685AE8; padding-top:12px; padding-bottom:10px; }}
    QPushButton#secondary {{ background:{secondary}; border:1px solid {t['border']}; border-radius:11px; padding:10px 15px; color:{t['text']}; font-weight:700; }}
    QPushButton#secondary:hover {{ background:{secondary_hover}; border-color:#667895; }}
    QPushButton#danger {{ background:rgba(255,107,122,18); border:1px solid rgba(255,107,122,85); border-radius:11px; padding:10px 15px; color:{RED}; font-weight:800; }}
    QPushButton#danger:hover {{ background:rgba(255,107,122,28); border-color:{RED}; }}
    QPushButton:focus, QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QSlider:focus {{ outline:0; border-color:{focus}; }}
    QLineEdit,QSpinBox,QComboBox {{ background:{field}; border:1px solid {t['border']}; border-radius:10px; padding:10px 11px; color:{t['text']}; min-height:20px; selection-background-color:{ACCENT}; }}
    QLineEdit:hover,QSpinBox:hover,QComboBox:hover {{ border-color:#667895; }}
    QComboBox QAbstractItemView {{ background:{list_bg}; color:{t['text']}; selection-background-color:rgba(123,108,255,45); border:1px solid {t['border']}; padding:5px; }}
    QProgressBar {{ background:{progress_bg}; border:0; border-radius:6px; height:8px; text-align:center; color:transparent; }}
    QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACCENT},stop:1 {ACCENT_2}); border-radius:6px; }}
    QSlider::groove:horizontal {{ height:5px; background:{t['border']}; border-radius:2px; }}
    QSlider::handle:horizontal {{ width:16px; margin:-6px 0; border-radius:8px; background:{ACCENT}; border:2px solid {t['bg']}; }}
    QScrollArea {{ border:0; background:transparent; }}
    QScrollBar:vertical {{ width:8px; background:transparent; margin:4px 0; }}
    QScrollBar::handle:vertical {{ background:rgba(145,160,181,80); border-radius:4px; min-height:30px; }}
    QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0; }}
    QToolTip {{ background:#111827; color:#F6F8FC; border:1px solid #34415A; padding:7px 10px; border-radius:8px; }}
    QToolButton {{ border:0; border-radius:10px; padding:8px; }}
    QToolButton:hover {{ background:rgba(123,108,255,18); }}
    """


class FadePage(QWidget):
    def fade(self, duration=260):
        effect = self.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._fade_anim = anim


class HoverCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._base = QPoint()
        self._anim = None
        self.setMouseTracking(True)

    def showEvent(self, event):
        self._base = self.pos()
        super().showEvent(event)

    def enterEvent(self, event):
        self._move(-3)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._move(0)
        super().leaveEvent(event)

    def _move(self, dy):
        if not self._base:
            self._base = self.pos()
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(170)
        anim.setStartValue(self.pos())
        anim.setEndValue(QPoint(self._base.x(), self._base.y() + dy))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._anim = anim


class ClickPulseButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._press_anim = None

    def mousePressEvent(self, event):
        r = self.geometry()
        self._press_anim = QPropertyAnimation(self, b"geometry", self)
        self._press_anim.setDuration(95)
        self._press_anim.setStartValue(r)
        self._press_anim.setEndValue(r.adjusted(1, 1, -1, -1))
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._press_anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        super().mousePressEvent(event)


class ScoreRing(QWidget):
    def __init__(self, value=0, parent=None):
        super().__init__(parent)
        self.setMinimumSize(190, 190)
        self._value = 0.0
        self._anim = QPropertyAnimation(self, b"score", self)
        self._anim.valueChanged.connect(self.update)
        self.animate(value)

    def get_score(self): return self._value
    def set_score(self, value): self._value = float(value); self.update()
    score = Property(float, get_score, set_score)

    def animate(self, value):
        self._anim.stop(); self._anim.setDuration(850); self._anim.setStartValue(self._value)
        self._anim.setEndValue(float(value)); self._anim.setEasingCurve(QEasingCurve.Type.OutCubic); self._anim.start()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = min(self.width(), self.height()) - 30
        c = self.rect().center(); x, y = c.x()-r//2, c.y()-r//2
        p.setPen(QPen(QColor("#263249"), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)); p.drawArc(x,y,r,r,0,360*16)
        g = QLinearGradient(x,y,x+r,y+r); g.setColorAt(0,QColor(ACCENT)); g.setColorAt(1,QColor(ACCENT_2))
        p.setPen(QPen(QBrush(g),12,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap)); p.drawArc(x,y,r,r,90*16,int(-self._value*3.6*16))
        p.setPen(QColor(TEXT)); p.setFont(QFont("Segoe UI",28,QFont.Weight.Bold)); p.drawText(self.rect().adjusted(0,-5,0,-5),Qt.AlignmentFlag.AlignCenter,f"{self._value:.0f}")
        p.setPen(QColor(MUTED)); p.setFont(QFont("Segoe UI",9)); p.drawText(self.rect().adjusted(0,42,0,0),Qt.AlignmentFlag.AlignCenter,"WELLNESS SCORE")


class TrendChart(QWidget):
    """PyQtGraph chart with a native QPainter fallback."""
    def __init__(self, values=None, labels=None, target=None, parent=None):
        super().__init__(parent); self.values=values or []; self.labels=labels or []; self.target=target
        self._plot = None; self._curve = None; self._target_line = None
        if pg:
            self._plot = pg.PlotWidget(self)
            self._plot.setBackground(None); self._plot.hideButtons(); self._plot.showGrid(x=False,y=True,alpha=.12)
            self._plot.getPlotItem().hideAxis('left'); self._plot.getPlotItem().hideAxis('bottom')
            self._plot.setMouseEnabled(x=False,y=False); self._plot.setMenuEnabled(False)
            self._curve = self._plot.plot(pen=pg.mkPen(ACCENT,width=3), symbol='o', symbolSize=7, symbolBrush=ACCENT_2, symbolPen=pg.mkPen(None))
            self._plot.setContentsMargins(12,12,12,12)
            lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(self._plot)
        else: self.setMinimumHeight(250)

    def set_data(self, values, labels, target=None):
        self.values=values or []; self.labels=labels or []; self.target=target
        if self._plot:
            self._curve.setData(list(range(len(self.values))), self.values)
            if self.target is not None:
                if self._target_line is None:
                    self._target_line=pg.InfiniteLine(pos=float(self.target),angle=0,pen=pg.mkPen(ACCENT_2,width=1,style=Qt.PenStyle.DashLine))
                    self._plot.addItem(self._target_line)
                else: self._target_line.setValue(float(self.target))
            self._plot.getPlotItem().enableAutoRange(); self._plot.getPlotItem().setXRange(-.5,max(.5,len(self.values)-.5),padding=0)
        else: self.update()

    def paintEvent(self,event):
        if self._plot: return
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); rect=self.rect().adjusted(32,18,-18,-30); p.fillRect(self.rect(),QColor("#FFFFFF" if self.window() and self.window().property("themeMode")=="light" else CARD))
        if not self.values:
            p.setPen(QColor(MUTED)); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,"No trend data yet — log a day to begin."); return
        maxv=max(max(self.values),self.target or 0,1)*1.15; pts=[]; n=len(self.values)
        p.setPen(QPen(QColor("#202B3D"),1))
        for i in range(5):
            y=rect.bottom()-rect.height()*i/4; p.drawLine(rect.left(),int(y),rect.right(),int(y))
        for i,v in enumerate(self.values):
            x=rect.left()+rect.width()*i/max(n-1,1); y=rect.bottom()-rect.height()*v/maxv; pts.append(QPoint(int(x),int(y)))
        if len(pts)>1:
            path=QPainterPath(QPointF(pts[0])); path.lineTo(QPointF(pts[-1]));
            poly=QPainterPath(); poly.moveTo(pts[0]); [poly.lineTo(pt) for pt in pts[1:]]; poly.lineTo(pts[-1].x(),rect.bottom()); poly.lineTo(pts[0].x(),rect.bottom()); poly.closeSubpath()
            p.fillPath(poly,QColor(123,108,255,32)); p.setPen(QPen(QColor(ACCENT),3,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap));
            for a,b in zip(pts,pts[1:]): p.drawLine(a,b)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(ACCENT_2)); [p.drawEllipse(pt,4,4) for pt in pts]


class GradientBackground(QWidget):
    """Efficient ambient scene with selectable presets and reduced-motion modes."""
    def __init__(self,preset="Aurora",parent=None):
        super().__init__(parent); self.preset=preset if preset in GRADIENTS else "Aurora"; self.setMouseTracking(True)
        self._phase=0.; self._mouse=QPointF(.5,.5); self._target=QPointF(.5,.5); self._closing=False; self._motion="full"; self._intensity=100; self._particles=[]
        for i in range(48): self._particles.append((.03+((i*37)%94)/100,.05+((i*61)%90)/100,1+(i%4)*.55,.45+(i%5)*.13))
        self._timer=QTimer(self); self._timer.setInterval(32); self._timer.timeout.connect(self._tick); self._timer.start()

    def set_motion(self, mode):
        self._motion=mode
        self._apply_timer_interval()
        self.update()

    def set_intensity(self, value):
        self._intensity=max(0,min(100,int(value)))
        self._apply_timer_interval()
        self.update()

    def _apply_timer_interval(self):
        if self._motion=="off":
            interval=500
        else:
            base=68 if self._motion=="reduced" else 30
            # Higher intensity means more frequent updates, while never becoming CPU-heavy.
            factor=1.45-(self._intensity/100.0)*0.45
            interval=max(24,int(base*factor))
        self._timer.setInterval(interval)
    def set_preset(self,preset):
        if preset in GRADIENTS: self.preset=preset; self.update()
    def _tick(self):
        if self._closing or self._motion=="off": return
        self._phase=(self._phase + (.004 if self._motion=="reduced" else .0105))%math.tau
        self._mouse.setX(self._mouse.x()+(self._target.x()-self._mouse.x())*.08); self._mouse.setY(self._mouse.y()+(self._target.y()-self._mouse.y())*.08); self.update()
    def mouseMoveEvent(self,event):
        pos=event.position(); self._target=QPointF(max(0,min(1,pos.x()/max(1,self.width()))),max(0,min(1,pos.y()/max(1,self.height())))); super().mouseMoveEvent(event)
    def leaveEvent(self,event): self._target=QPointF(.5,.5); super().leaveEvent(event)
    def stop(self):
        self._closing=True
        if self._timer.isActive(): self._timer.stop()
    def _light(self,p,cx,cy,radius,color,alpha):
        g=QRadialGradient(cx,cy,radius); c=QColor(color); c.setAlpha(max(0,min(80,int(alpha)))); g.setColorAt(0,c); g.setColorAt(.4,QColor(c.red(),c.green(),c.blue(),int(c.alpha()*.4))); g.setColorAt(1,QColor(c.red(),c.green(),c.blue(),0)); p.setPen(Qt.PenStyle.NoPen); p.setBrush(g); p.drawEllipse(QPointF(cx,cy),radius,radius)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); w,h=max(1,self.width()),max(1,self.height()); a,b,c=GRADIENTS[self.preset]
        base=QLinearGradient(0,0,w,h); base.setColorAt(0,QColor(a)); base.setColorAt(.5,QColor(b)); base.setColorAt(1,QColor(c)); p.fillRect(self.rect(),base)
        if self.preset=="Minimal Light":
            p.fillRect(self.rect(),base); p.setPen(QPen(QColor(255,255,255,55),1));
            for y in range(0,h,72): p.drawLine(0,y,w,y)
            return
        mx,my=self._mouse.x(),self._mouse.y(); dx,dy=(mx-.5)*42,(my-.5)*30; breathe=.5+.5*math.sin(self._phase)
        self._light(p,w*.12+dx,h*.16+dy,250+24*breathe,ACCENT,58); self._light(p,w*.84-dx*.65,h*.23-dy*.5,310+28*(1-breathe),ACCENT_2,52); self._light(p,w*.67+dx*.25,h*.93+dy*.4,360,BLUE,36); self._light(p,w*.5-dx*.15,h*.52-dy*.15,210,"#B58CFF",20)
        if self._motion!="off":
            pts=[]
            for i,(x,y,size,speed) in enumerate(self._particles):
                ang=self._phase*speed+i*.73; px=x*w+math.sin(ang)*(9+i%5*4)+dx*(.06+i%3*.018); py=y*h+math.cos(ang*.83)*(7+i%4*3)+dy*.07; alpha=int(18+24*(.5+.5*math.sin(ang+i))); pts.append(QPointF(px,py)); p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(225,235,255,alpha)); p.drawEllipse(QPointF(px,py),size,size)
            p.setPen(QPen(QColor(180,200,255,8),1));
            for i in range(0,len(pts)-2,3): p.drawLine(pts[i],pts[i+1])
        horizon=int(h*.74+dy*.08); p.setPen(QPen(QColor(255,255,255,7),1))
        for i in range(9): p.drawLine(0,horizon+int((h-horizon)*(i/8)**1.8),w,horizon+int((h-horizon)*(i/8)**1.8))
        cx=w*.5+dx*.22
        for i in range(-9,10): p.drawLine(int(cx),horizon,int(cx+i*(w/9)),h)
        self._light(p,mx*w,my*h,155+22*breathe,"#FFFFFF",24)
        p.end()


class Toast(QFrame):
    """Short-lived notification that owns its animation lifecycle safely."""
    def __init__(self,title,message,kind="success",parent=None):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setMinimumWidth(330)
        self.setMaximumWidth(480)
        self._closing = False
        accent={"success":GREEN,"error":RED,"warning":YELLOW,"info":BLUE}.get(kind,ACCENT_2)
        self.setStyleSheet(f"QFrame#toast{{background:rgba(12,18,29,245);border:1px solid rgba(255,255,255,20);border-left:4px solid {accent};border-radius:14px;}}")
        row=QHBoxLayout(self); row.setContentsMargins(14,11,10,11); row.setSpacing(10)
        mark=QLabel("✓" if kind=="success" else "!" if kind in ("error","warning") else "i")
        mark.setStyleSheet(f"color:{accent};font-size:15px;font-weight:900;")
        row.addWidget(mark,alignment=Qt.AlignmentFlag.AlignTop)
        col=QVBoxLayout(); col.setSpacing(2)
        col.addWidget(label(title,color=accent,size=9,bold=True))
        body=label(message,color=TEXT,size=10); body.setWordWrap(True); body.setMinimumWidth(240); col.addWidget(body)
        row.addLayout(col,1)
        close=QToolButton(); close.setText("×"); close.clicked.connect(self.close_animated); row.addWidget(close,alignment=Qt.AlignmentFlag.AlignTop)
        self._effect=QGraphicsOpacityEffect(self); self.setGraphicsEffect(self._effect); self._effect.setOpacity(0)

    def show_animated(self):
        self.show(); self.adjustSize()
        a=QPropertyAnimation(self._effect,b"opacity",self); a.setDuration(220); a.setStartValue(0); a.setEndValue(1); a.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._in=a; a.start()
        QTimer.singleShot(3600,self.close_animated)

    def close_animated(self):
        if self._closing or not _qt_is_valid(self): return
        self._closing=True
        if not self.isVisible():
            self.deleteLater(); return
        a=QPropertyAnimation(self._effect,b"opacity",self); a.setDuration(180); a.setStartValue(self._effect.opacity()); a.setEndValue(0); a.setEasingCurve(QEasingCurve.Type.InCubic)
        a.finished.connect(self._finish_close)
        self._out=a; a.start()

    def _finish_close(self):
        if _qt_is_valid(self):
            self.hide()
            self.deleteLater()


class HealthNetworkGraphic(QWidget):
    """Small vector healthcare network illustration; no external image assets required."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(230, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._phase = (self._phase + 0.035) % math.tau
        self.update()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w * .52, h * .53
        # Soft central halo.
        halo = QRadialGradient(cx, cy, min(w, h) * .42)
        halo.setColorAt(0, QColor(46, 214, 195, 38))
        halo.setColorAt(1, QColor(46, 214, 195, 0))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(halo); p.drawEllipse(QPointF(cx, cy), min(w,h)*.42, min(w,h)*.42)
        nodes = [
            QPointF(w*.18,h*.27), QPointF(w*.25,h*.73), QPointF(w*.77,h*.22),
            QPointF(w*.84,h*.68), QPointF(w*.52,h*.12), QPointF(w*.52,h*.86),
        ]
        center = QPointF(cx, cy)
        p.setPen(QPen(QColor(130,165,205,42), 1.2))
        for n in nodes:
            p.drawLine(center, n)
        for i in range(len(nodes)):
            for j in range(i+1,len(nodes)):
                if (nodes[i]-nodes[j]).manhattanLength() < min(w,h)*.55:
                    p.drawLine(nodes[i], nodes[j])
        # Animated pulse travels around the center ring.
        radius = min(w,h)*.22
        pulse_a = self._phase
        pulse = QPointF(cx + math.cos(pulse_a)*radius, cy + math.sin(pulse_a)*radius)
        p.setPen(QPen(QColor(123,108,255,90), 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(center, radius, radius)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(123,108,255,190)); p.drawEllipse(pulse, 5, 5)
        # Central medical cross inside a rounded badge.
        badge = QRectF(cx-31, cy-31, 62, 62)
        p.setBrush(QColor(12,20,32,225)); p.setPen(QPen(QColor(46,214,195,120),1.5)); p.drawRoundedRect(badge,18,18)
        p.setBrush(QColor(46,214,195,225)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(cx-5,cy-18,10,36),4,4); p.drawRoundedRect(QRectF(cx-18,cy-5,36,10),4,4)
        # Node dots.
        for i,n in enumerate(nodes):
            glow = 0.5 + .5*math.sin(self._phase*1.7+i)
            p.setBrush(QColor(89,166,255,int(90+70*glow))); p.drawEllipse(n,5,5)
        p.end()


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__(); self.app=app; self.setWindowTitle("HealthBridge • Personal Wellness"); self.resize(1280,820); self.setMinimumSize(980,650)
        self.settings=QSettings("HealthBridge","HealthBridge"); self.mode=getattr(app,"theme","dark") if getattr(app,"theme","") in set(THEMES) | {"system"} else "dark"; self.mode=self._resolve_theme(self.mode)
        self.gradient_name=self.settings.value("background_gradient","Aurora"); self.gradient_name=self.gradient_name if self.gradient_name in GRADIENTS else "Aurora"
        self.motion=self.settings.value("animation_mode","full"); self.motion=self.motion if self.motion in ("full","reduced","off") else "full"
        self.intensity=int(self.settings.value("animation_intensity",100) or 100); self.intensity=max(0,min(100,self.intensity))
        self.setStyleSheet(stylesheet(self.mode)); self.setProperty("themeMode", self.mode)
        self.nav_buttons={}; self.pages={}; self._toasts=[]
        self.canvas=GradientBackground(self.gradient_name); self.canvas.setObjectName("appBackground"); self.canvas.set_motion(self.motion); self.canvas.set_intensity(self.intensity); self.setCentralWidget(self.canvas)
        self.shell=QHBoxLayout(self.canvas); self.shell.setContentsMargins(0,0,0,0); self.shell.setSpacing(0)
        self.sidebar=self._build_sidebar(); self.content=QWidget(); self.content.setStyleSheet("background:transparent;"); cl=QVBoxLayout(self.content); cl.setContentsMargins(28,24,28,22); self.stack=QStackedWidget(); self.stack.setObjectName("pageStack"); cl.addWidget(self.stack)
        self.shell.addWidget(self.sidebar); self.shell.addWidget(self.content,1)
        if self.app.onboarded: self.show_page("dashboard")
        else: self.show_onboarding()

    def _resolve_theme(self, mode):
        if mode in THEMES:
            return mode
        palette = QApplication.instance().palette() if QApplication.instance() else QApplication.palette()
        return "light" if palette.window().color().lightness() > 150 else "dark"

    def _build_sidebar(self):
        s=QFrame(); s.setObjectName("sidebar"); s.setFixedWidth(238); lay=QVBoxLayout(s); lay.setContentsMargins(17,23,17,17); lay.setSpacing(4)
        brand=QHBoxLayout(); mark=QLabel(); mark.setPixmap(icon("fa5s.heartbeat",ACCENT_2,20).pixmap(22,22) if not icon("fa5s.heartbeat",ACCENT_2,20).isNull() else QIcon().pixmap(1,1)); brand.addWidget(mark); brand.addWidget(label("HealthBridge","brand")); lay.addLayout(brand); lay.addSpacing(25)
        sections=[("YOUR HEALTH",[("dashboard","Overview","fa5s.home"),("log","Daily log","fa5s.plus-circle"),("history","History","fa5s.history")]),("INSIGHTS",[("trends","Trends","fa5s.chart-line"),("analytics","Analytics","fa5s.chart-pie"),("goals","Goals","fa5s.bullseye"),("report","Report","fa5s.file-alt")])]
        for title,items in sections:
            lay.addWidget(label(title,color=MUTED,size=8,bold=True)); lay.addSpacing(4)
            for key,textv,ic in items:
                b=QPushButton(textv); b.setObjectName("nav"); b.setIcon(icon(ic,"#AEB9CB",15)); b.setIconSize(QSize(16,16)); b.setProperty("active",False); b.setToolTip(textv); b.clicked.connect(lambda checked=False,k=key:self.show_page(k)); self.nav_buttons[key]=b; lay.addWidget(b)
            lay.addSpacing(12)
        lay.addStretch(); settings=QPushButton("Settings"); settings.setObjectName("nav"); settings.setIcon(icon("fa5s.sliders-h","#AEB9CB",15)); settings.clicked.connect(lambda:self.show_page("settings")); lay.addWidget(settings); lay.addWidget(label("●  LOCAL • PRIVATE",color=MUTED,size=8,bold=True)); return s

    def _header(self,title,subtitle):
        box=QWidget(); row=QHBoxLayout(box); row.setContentsMargins(0,0,0,18); left=QVBoxLayout(); left.setSpacing(4); left.addWidget(label(title,"pageTitle")); sub=label(subtitle,"pageSub"); sub.setWordWrap(True); left.addWidget(sub); row.addLayout(left,1); badge=label("●  LOCAL & PRIVATE","badge"); row.addWidget(badge,alignment=Qt.AlignmentFlag.AlignTop); return box

    def show_page(self,key):
        if key not in {"dashboard","log","history","trends","analytics","goals","report","settings"}: key="dashboard"
        old=self.pages.pop(key,None)
        if old:
            self.stack.removeWidget(old); old.deleteLater()
        page=getattr(self,f"{key}_page")(); self.pages[key]=page; self.stack.addWidget(page); self.stack.setCurrentWidget(page)
        for k,b in self.nav_buttons.items(): b.setProperty("active",k==key); b.style().unpolish(b); b.style().polish(b)
        if self.motion!="off": page.fade(260)

    def clear_stack(self):
        while self.stack.count():
            w=self.stack.widget(0); self.stack.removeWidget(w); w.deleteLater()
        self.pages.clear()

    def show_onboarding(self):
        self.clear_stack(); self.sidebar.setVisible(False)
        page=FadePage(); outer=QHBoxLayout(page); outer.setContentsMargins(30,20,30,20); outer.addStretch()
        card=QFrame(); card.setObjectName("hero"); card.setMaximumWidth(700); grid=QGridLayout(card); grid.setContentsMargins(42,38,42,38); grid.setHorizontalSpacing(36)
        left=QVBoxLayout(); left.setSpacing(10); left.addWidget(label("HEALTHBRIDGE • PERSONAL WELLNESS","eyebrow")); title=label("A calmer, clearer way to understand your everyday habits.",size=30,bold=True); title.setWordWrap(True); left.addWidget(title); sub=label("Track sleep, movement, hydration and personal wellness time. Your data stays on this computer.",color=MUTED,size=12); sub.setWordWrap(True); left.addWidget(sub); left.addSpacing(12)
        trust=QFrame(); trust.setObjectName("glass"); tl=QVBoxLayout(trust); tl.setContentsMargins(14,12,14,12); tl.addWidget(label("DESIGNED FOR CLARITY",color=ACCENT_2,size=9,bold=True)); tl.addWidget(label("Transparent scoring • Private local storage • No cloud account required",color=TEXT,size=10)); left.addWidget(trust); grid.addLayout(left,0,0)
        visual=HealthNetworkGraphic(); visual.setMinimumWidth(220); grid.addWidget(visual,0,1)
        form=QVBoxLayout(); form.setSpacing(8); form.addWidget(label("GET STARTED",color=MUTED,size=9,bold=True)); name=QLineEdit(); name.setPlaceholderText("Your name"); age=QLineEdit(); age.setPlaceholderText("Age (optional)"); form.addWidget(name); form.addWidget(age); go=ClickPulseButton("Enter HealthBridge  →"); go.setObjectName("primary"); form.addSpacing(5); form.addWidget(go)
        def start():
            if not name.text().strip(): self.notify("Name required","Please enter your name to continue.","warning"); return
            try:
                self.app.complete_onboarding(name.text().strip(),age.text().strip() or None,{}); self.build_shell(); self.show_page("dashboard")
            except Exception as exc: self.notify("Could not start",str(exc),"error")
        go.clicked.connect(start); grid.addLayout(form,1,0,1,2); outer.addWidget(card); outer.addStretch(); self.stack.addWidget(page); self.stack.setCurrentWidget(page); page.fade(420)

    def build_shell(self):
        self.sidebar.setVisible(True); self.content.setVisible(True); self.clear_stack()

    def notify(self,title,message,kind="success"):
        self._prune_toasts()
        toast=Toast(title,message,kind,self.canvas)
        self._toasts.append(weakref.ref(toast))
        toast.adjustSize()
        margin=24; x=self.canvas.width()-toast.width()-margin; y=24
        for ref in self._toasts[:-1]:
            t=ref()
            if t is not None and _qt_is_valid(t) and t.isVisible():
                y=t.y()+t.height()+10
        toast.move(max(20,x),y)
        toast.show_animated()
        QTimer.singleShot(3800,self._prune_toasts)

    def _prune_toasts(self):
        alive=[]
        for ref in self._toasts:
            t=ref() if callable(ref) else ref
            if t is not None and _qt_is_valid(t):
                alive.append(weakref.ref(t))
        self._toasts=alive

    def form_row(self,parent,text,widget):
        field=QVBoxLayout(); field.setSpacing(5); field.addWidget(label(text,color=MUTED,size=9,bold=True)); field.addWidget(widget)
        if isinstance(parent,QGridLayout):
            count=parent.property("_count"); count=int(count) if count is not None else 0; parent.addLayout(field,count//2,count%2); parent.setProperty("_count",count+1)
        else: parent.addLayout(field)

    def dashboard_page(self):
        page=FadePage(); root=QVBoxLayout(page); root.setSpacing(16); root.addWidget(self._header(f"Good to see you, {self.app.user.name}.","Your seven-day wellness snapshot, built from the habits you choose to track."))
        top=QHBoxLayout(); top.setSpacing(16); hero=QFrame(); hero.setObjectName("hero"); hl=QHBoxLayout(hero); hl.setContentsMargins(22,18,22,18); score=self.app.report.wellness_score(7); ring=ScoreRing(score); hl.addWidget(ring); visual=HealthNetworkGraphic(); visual.setMinimumWidth(220); hl.addWidget(visual); copy=QVBoxLayout(); copy.setSpacing(6); copy.addWidget(label("WELLNESS SNAPSHOT","eyebrow")); copy.addWidget(label("Small habits. Clear signals.",size=20,bold=True)); copy.addWidget(label("Your score combines achievement, consistency and trend. It is a lifestyle-tracking signal, not a medical metric.",color=MUTED,size=10)); action=ClickPulseButton("Log today  →"); action.setObjectName("primary"); action.clicked.connect(lambda:self.show_page("log")); copy.addSpacing(6); copy.addWidget(action,alignment=Qt.AlignmentFlag.AlignLeft); hl.addLayout(copy,1); top.addWidget(hero,1)
        insight=HoverCard(); il=QVBoxLayout(insight); il.setContentsMargins(18,18,18,18); il.addWidget(label("SMART INSIGHT","eyebrow")); weakest=self.app.report.weakest_metric(7); il.addWidget(label("Your next best step",size=18,bold=True)); text="Start logging a few days to unlock personalized suggestions." if not self.app.records else f"Focus on {LABELS[weakest][0].lower()} this week. Small, consistent improvements matter more than perfect days."; body=label(text,color=MUTED,size=10); body.setWordWrap(True); il.addWidget(body); top.addWidget(insight,1); root.addLayout(top)
        grid=QGridLayout(); grid.setSpacing(14); avgs=self.app.report.averages(7)
        for i,m in enumerate(METRICS):
            c=HoverCard(); l=QVBoxLayout(c); l.setContentsMargins(16,15,16,15); head=QHBoxLayout(); ic=QLabel(); ico=icon(LABELS[m][2],ACCENT_2,14); ic.setPixmap(ico.pixmap(16,16) if not ico.isNull() else QIcon().pixmap(1,1)); head.addWidget(ic); head.addWidget(label(LABELS[m][0],"cardTitle")); head.addStretch(); head.addWidget(label(f"target {self.app.user.goals[m]:g}",color=MUTED,size=8)); l.addLayout(head); l.addWidget(label(f"{avgs[m]:.1f} {LABELS[m][1]}","metricValue")); bar=QProgressBar(); bar.setValue(0); l.addWidget(bar); val=min(100,int(avgs[m]/max(self.app.user.goals[m],.001)*100)); anim=QPropertyAnimation(bar,b"value",bar); anim.setDuration(700); anim.setStartValue(0); anim.setEndValue(val); anim.setEasingCurve(QEasingCurve.Type.OutCubic); anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped); bar._anim=anim; grid.addWidget(c,i//2,i%2)
        root.addLayout(grid); recent=QFrame(); recent.setObjectName("card"); rl=QVBoxLayout(recent); rl.setContentsMargins(18,15,18,15); rh=QHBoxLayout(); rh.addWidget(label("Recent activity","cardTitle")); rh.addStretch(); rh.addWidget(label(f"{len(self.app.records)} logged days",color=MUTED,size=9)); rl.addLayout(rh)
        for r in self.app.sorted_records()[:3]: rl.addWidget(label(f"{r.date}   •   Sleep {r.sleep_hours:g}h   •   Activity {r.activity_minutes:g}m   •   Hydration {r.hydration_liters:g}L",color=MUTED,size=10))
        if not self.app.records: rl.addWidget(label("No records yet. Your first log will appear here.",color=MUTED,size=10))
        root.addWidget(recent); root.addStretch(); return page

    def log_page(self):
        page=FadePage(); root=QVBoxLayout(page); root.addWidget(self._header("Daily log","Capture one day of sleep, movement, hydration and personal wellness time.")); card=QFrame(); card.setObjectName("card"); form=QVBoxLayout(card); form.setContentsMargins(22,20,22,22); form.setSpacing(14)
        date_edit=QLineEdit(date.today().isoformat()); date_edit.setPlaceholderText("YYYY-MM-DD"); form.addWidget(label("DATE",color=MUTED,size=9,bold=True)); form.addWidget(date_edit)
        fields={m:QLineEdit() for m in METRICS}; existing=self.app.find_record(date_edit.text())
        if existing:
            for m in METRICS: fields[m].setText(str(getattr(existing,m)))
        grid=QGridLayout(); grid.setSpacing(12)
        for m in METRICS: self.form_row(grid,f"{LABELS[m][0].upper()} • {LABELS[m][1].upper()}",fields[m])
        form.addLayout(grid); note=label("Tip: enter realistic values for the selected date. HealthBridge validates relationships between daily metrics.",color=MUTED,size=9); note.setWordWrap(True); form.addWidget(note); save=ClickPulseButton("Save daily record  ✓"); save.setObjectName("primary")
        def submit():
            try:
                self.app.add_or_update_record(date_edit.text().strip(),*(float(fields[m].text()) for m in METRICS)); self.notify("Record saved","Your daily wellness entry is safely stored locally."); self.show_page("dashboard")
            except Exception as exc: self.notify("Could not save",str(exc),"error")
        save.clicked.connect(submit); form.addWidget(save,alignment=Qt.AlignmentFlag.AlignLeft); root.addWidget(card); root.addStretch(); return page

    def history_page(self):
        page=FadePage(); root=QVBoxLayout(page); root.addWidget(self._header("History","Your saved wellness timeline, newest first.")); scroll=QScrollArea(); scroll.setWidgetResizable(True); body=QWidget(); l=QVBoxLayout(body); l.setContentsMargins(2,2,8,2); l.setSpacing(10)
        for r in self.app.sorted_records():
            c=HoverCard(); row=QHBoxLayout(c); row.setContentsMargins(15,12,12,12); info=QVBoxLayout(); info.addWidget(label(r.date,"cardTitle")); info.addWidget(label(f"Sleep {r.sleep_hours:g}h  •  Activity {r.activity_minutes:g}m  •  Hydration {r.hydration_liters:g}L  •  Wellness {r.wellness_minutes:g}m",color=MUTED,size=10)); row.addLayout(info,1); tag=label("DEMO" if r.is_demo else "LOGGED"); tag.setStyleSheet(f"color:{ACCENT_2 if not r.is_demo else YELLOW};background:rgba(255,255,255,7);padding:5px 8px;border-radius:8px;font-size:8px;font-weight:800;"); row.addWidget(tag); delete=ClickPulseButton("Delete"); delete.setObjectName("secondary"); delete.clicked.connect(lambda checked=False,d=r.date:self.delete_record(d)); row.addWidget(delete); l.addWidget(c)
        if not self.app.records: l.addWidget(label("No records yet. Start with Daily log.",color=MUTED,size=11)); l.addStretch()
        scroll.setWidget(body); root.addWidget(scroll,1); return page

    def delete_record(self,d):
        if QMessageBox.question(self,"Delete record",f"Delete the record for {d}?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            if self.app.delete_record(d): self.notify("Record deleted","The selected local record was removed.","info"); self.show_page("history")

    def trends_page(self):
        page=FadePage(); root=QVBoxLayout(page); root.addWidget(self._header("Trends","See how each habit is moving across your recent records.")); card=QFrame(); card.setObjectName("card"); l=QVBoxLayout(card); l.setContentsMargins(18,18,18,18); controls=QHBoxLayout(); controls.addWidget(label("METRIC",color=MUTED,size=9,bold=True)); combo=QComboBox(); combo.addItems([LABELS[m][0] for m in METRICS]); controls.addWidget(combo); controls.addStretch(); l.addLayout(controls); chart=TrendChart(); l.addWidget(chart,1)
        def refresh():
            m=METRICS[combo.currentIndex()]; recs=sorted(self.app.records,key=lambda r:r.date_obj); vals=[getattr(r,m) for r in recs[-14:]]; labs=[r.date[5:] for r in recs[-14:]]; chart.set_data(vals,labs,self.app.user.goals.get(m))
        combo.currentIndexChanged.connect(refresh); refresh(); root.addWidget(card,1); return page

    def analytics_page(self):
        page=FadePage(); root=QVBoxLayout(page); root.addWidget(self._header("Analytics","A transparent breakdown of your lifestyle-tracking score.")); report=self.app.report; grid=QGridLayout(); grid.setSpacing(14)
        for i,(name,v) in enumerate((("Achievement",report.achievement_score(7)),("Consistency",report.consistency_score(7)),("Trend",report.trend_score(7)))):
            c=HoverCard(); l=QVBoxLayout(c); l.setContentsMargins(18,16,18,16); l.addWidget(label(name,"cardTitle")); l.addWidget(label(f"{v:.1f}","metricValue")); bar=QProgressBar(); bar.setValue(0); l.addWidget(bar); anim=QPropertyAnimation(bar,b"value",bar); anim.setDuration(800); anim.setStartValue(0); anim.setEndValue(int(v)); anim.setEasingCurve(QEasingCurve.Type.OutCubic); anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped); bar._anim=anim; l.addWidget(label({"Achievement":"70% of score","Consistency":"20% of score","Trend":"10% of score"}[name],color=MUTED,size=9)); grid.addWidget(c,0,i)
        root.addLayout(grid); disc=QFrame(); disc.setObjectName("card"); dl=QVBoxLayout(disc); dl.setContentsMargins(18,16,18,16); dl.addWidget(label("How it works","cardTitle")); text=label("Achievement compares logged values with your own goals. Consistency considers stability across logged days. Trend compares earlier and recent records. The final score is capped at 100 and is not a medical metric.",color=MUTED,size=10); text.setWordWrap(True); dl.addWidget(text); root.addWidget(disc); root.addStretch(); return page

    def goals_page(self):
        page=FadePage(); root=QVBoxLayout(page); root.addWidget(self._header("Goals","Set personal targets that shape your score and suggestions.")); card=QFrame(); card.setObjectName("card"); l=QVBoxLayout(card); l.setContentsMargins(22,20,22,22); grid=QGridLayout(); grid.setSpacing(12); fields={}
        for m in METRICS: fields[m]=QLineEdit(str(self.app.user.goals.get(m,""))); self.form_row(grid,f"{LABELS[m][0].upper()} • {LABELS[m][1].upper()}",fields[m])
        l.addLayout(grid); save=ClickPulseButton("Save goals"); save.setObjectName("primary")
        def submit():
            try: self.app.update_goals({m:float(fields[m].text()) for m in METRICS}); self.notify("Goals updated","Your personal targets are now active."); self.show_page("goals")
            except Exception as exc: self.notify("Could not save goals",str(exc),"error")
        save.clicked.connect(submit); l.addWidget(save,alignment=Qt.AlignmentFlag.AlignLeft); root.addWidget(card); root.addStretch(); return page

    def report_page(self):
        page=FadePage(); root=QVBoxLayout(page); root.addWidget(self._header("Weekly report","A compact summary you can review or present.")); r=self.app.report; card=QFrame(); card.setObjectName("card"); l=QVBoxLayout(card); l.setContentsMargins(22,20,22,22); score=label(f"Wellness score • {r.wellness_score(7):.1f}/100","metricValue"); l.addWidget(score); l.addWidget(label("Seven-day averages","cardTitle")); av=r.averages(7)
        for m in METRICS: l.addWidget(label(f"{LABELS[m][0]}: {av[m]:.1f} {LABELS[m][1]}  •  target {self.app.user.goals[m]:g}",color=MUTED,size=10))
        l.addSpacing(10); l.addWidget(label("Suggestions","cardTitle"));
        for tip in r.suggestions(7): l.addWidget(label("• "+tip,color=MUTED,size=10))
        l.addSpacing(10); l.addWidget(label("This report is for personal wellness tracking only and is not medical advice.",color=YELLOW,size=9)); root.addWidget(card); root.addStretch(); return page

    def settings_page(self):
        page=FadePage()
        root=QVBoxLayout(page); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(self._header("Settings","Shape your HealthBridge experience, accessibility and local data controls."))

        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body=QWidget(); body_l=QVBoxLayout(body); body_l.setContentsMargins(2,0,10,20); body_l.setSpacing(14)

        def section(title_text, description):
            card=QFrame(); card.setObjectName("card")
            lay=QVBoxLayout(card); lay.setContentsMargins(20,18,20,20); lay.setSpacing(12)
            lay.addWidget(label(title_text,"cardTitle"))
            d=label(description,color=MUTED,size=9); d.setWordWrap(True); lay.addWidget(d)
            return card,lay

        # Profile
        card,l=section("Profile","Keep your personal details accurate. HealthBridge stores these values locally on this device.")
        profile_grid=QGridLayout(); profile_grid.setHorizontalSpacing(14); profile_grid.setVerticalSpacing(8)
        name=QLineEdit(self.app.user.name); name.setPlaceholderText("Your name"); name.setClearButtonEnabled(True)
        age=QLineEdit(str(self.app.user.age or "")); age.setPlaceholderText("Optional"); age.setClearButtonEnabled(True)
        self.form_row(profile_grid,"NAME",name); self.form_row(profile_grid,"AGE",age); l.addLayout(profile_grid)
        profile_status=label("Changes are saved only when you press Save profile.",color=MUTED,size=9); l.addWidget(profile_status)
        save=ClickPulseButton("Save profile  ✓"); save.setObjectName("primary")
        def save_profile():
            try:
                self.app.update_profile(name.text().strip(),age.text().strip() or None)
                profile_status.setText("Saved locally • Your profile is up to date."); profile_status.setStyleSheet(f"color:{GREEN};")
                self.notify("Profile updated","Your profile changes are saved locally.")
            except Exception as exc:
                profile_status.setText("Please check the highlighted values and try again."); profile_status.setStyleSheet(f"color:{RED};")
                self.notify("Could not save profile",str(exc),"error")
        save.clicked.connect(save_profile); l.addWidget(save,alignment=Qt.AlignmentFlag.AlignLeft)
        body_l.addWidget(card)

        # Appearance
        card,l=section("Appearance","Preview visual changes immediately. Your choices are remembered between launches.")
        grid=QGridLayout(); grid.setHorizontalSpacing(16); grid.setVerticalSpacing(12)
        theme=QComboBox(); theme.addItems(["Dark","Light","System"]); theme.setCurrentText({"dark":"Dark","light":"Light","system":"System"}.get(getattr(self.app,"theme","dark"),"Dark")); theme.setToolTip("Choose the overall application appearance.")
        gradient=QComboBox(); gradient.addItems(list(GRADIENTS)); gradient.setCurrentText(self.gradient_name); gradient.setToolTip("Choose the ambient background style.")
        self.form_row(grid,"THEME",theme); self.form_row(grid,"BACKGROUND",gradient); l.addLayout(grid)
        appearance_note=label(f"Active background • {self.gradient_name}",color=ACCENT_2,size=9,bold=True); l.addWidget(appearance_note)
        theme.currentTextChanged.connect(self.change_theme)
        gradient.currentTextChanged.connect(lambda value:(self.change_gradient(value), appearance_note.setText(f"Active background • {value}")))
        body_l.addWidget(card)

        # Motion & accessibility
        card,l=section("Motion & accessibility","Tune visual movement to your comfort level. Reduced and Off modes also reduce background work.")
        motion=QComboBox(); motion.addItems(["Full","Reduced","Off"]); motion.setCurrentText(self.motion.title()); motion.setToolTip("Full = expressive motion, Reduced = calmer motion, Off = decorative animation disabled.")
        l.addWidget(label("ANIMATION MODE",color=MUTED,size=9,bold=True)); l.addWidget(motion)
        intensity_row=QHBoxLayout(); intensity_row.setSpacing(12); intensity_row.addWidget(label("Animation intensity",color=TEXT,size=10)); intensity_value=label(f"{self.intensity}%",color=ACCENT_2,size=10,bold=True); intensity_row.addWidget(intensity_value); intensity_row.addStretch(); l.addLayout(intensity_row)
        intensity=QSlider(Qt.Orientation.Horizontal); intensity.setRange(0,100); intensity.setValue(self.intensity); intensity.setSingleStep(5); intensity.setPageStep(10); intensity.setToolTip("Adjust animation intensity from subtle to expressive."); l.addWidget(intensity)
        motion_note=label("Keyboard-friendly focus states remain available even when animation is off.",color=MUTED,size=9); motion_note.setWordWrap(True); l.addWidget(motion_note)
        def apply_motion(value):
            self.change_motion(value); intensity.setValue(0 if value=="Off" else 45 if value=="Reduced" else max(self.intensity,75))
        motion.currentTextChanged.connect(apply_motion)
        def apply_intensity(value):
            self.intensity=value; intensity_value.setText(f"{value}%"); self.settings.setValue("animation_intensity",value); self.canvas.set_intensity(value)
            if value==0 and self.motion!="off":
                motion.blockSignals(True); motion.setCurrentText("Off"); motion.blockSignals(False); self.change_motion("Off")
            elif value>10 and self.motion=="off":
                mode="reduced" if value<60 else "full"; motion.blockSignals(True); motion.setCurrentText(mode.title()); motion.blockSignals(False); self.change_motion(mode.title())
        intensity.valueChanged.connect(apply_intensity)
        body_l.addWidget(card)

        # Local data
        card,l=section("Local data","HealthBridge is designed around local-first wellness tracking. Use these controls carefully.")
        data_grid=QGridLayout(); data_grid.setHorizontalSpacing(10); data_grid.setVerticalSpacing(10)
        demo=ClickPulseButton("Load demo data"); demo.setObjectName("secondary"); demo.setToolTip("Add presentation-ready sample records without replacing your own records.")
        clear=ClickPulseButton("Clear demo data"); clear.setObjectName("secondary"); clear.setToolTip("Remove only records marked as demo data.")
        reset=ClickPulseButton("Reset all local data"); reset.setObjectName("danger")
        reset.setToolTip("Permanently remove local HealthBridge data and return to onboarding.")
        demo.clicked.connect(self.load_demo); clear.clicked.connect(self.clear_demo); reset.clicked.connect(self.reset_all)
        data_grid.addWidget(demo,0,0); data_grid.addWidget(clear,0,1); data_grid.addWidget(reset,1,0,1,2); l.addLayout(data_grid)
        privacy=label("LOCAL • PRIVATE  ·  No cloud account is required for the core application.",color=ACCENT_2,size=9,bold=True); privacy.setWordWrap(True); l.addWidget(privacy)
        body_l.addWidget(card)

        footer=label("HealthBridge • Personal wellness tracking • Changes apply immediately unless explicitly saved.",color=MUTED,size=9); footer.setWordWrap(True); body_l.addWidget(footer); body_l.addStretch()
        scroll.setWidget(body); root.addWidget(scroll,1)
        return page

    def change_theme(self,value):
        theme={"Dark":"dark","Light":"light","System":"system"}.get(value,"dark"); self.app.set_theme(theme); self.mode=self._resolve_theme(theme); self.setStyleSheet(stylesheet(self.mode)); self.setProperty("themeMode", self.mode); self.notify("Appearance updated",f"{value} theme is active.","info")
    def change_gradient(self,value):
        if value in GRADIENTS: self.gradient_name=value; self.settings.setValue("background_gradient",value); self.canvas.set_preset(value); self.notify("Background updated",f"{value} is now active.","info")
    def change_motion(self,value):
        self.motion={"Full":"full","Reduced":"reduced","Off":"off"}.get(value,"full"); self.settings.setValue("animation_mode",self.motion); self.canvas.set_motion(self.motion); self.notify("Motion updated",f"Animation mode: {value}.","info")
    def change_intensity(self,value):
        self.intensity=max(0,min(100,int(value))); self.settings.setValue("animation_intensity",self.intensity); self.canvas.set_intensity(self.intensity)
        if self.intensity<=10: mode="off"
        elif self.intensity<60: mode="reduced"
        else: mode="full"
        if mode!=self.motion:
            self.motion=mode; self.settings.setValue("animation_mode",mode); self.canvas.set_motion(mode)
    def load_demo(self): self.app.load_demo_data(); self.notify("Demo data loaded","Presentation-ready sample records are available."); self.show_page("dashboard")
    def clear_demo(self): self.app.clear_demo_data(); self.notify("Demo data cleared","Only demo records were removed.","info"); self.show_page("dashboard")
    def reset_all(self):
        if QMessageBox.question(self,"Reset everything","This removes all locally stored HealthBridge data. Continue?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.app.reset_all(); self.show_onboarding()
    def closeEvent(self,event):
        try:
            self.canvas.stop()
            for graphic in self.findChildren(HealthNetworkGraphic):
                graphic.stop()
        finally: super().closeEvent(event)


HealthBridgeUI = MainWindow


def launch_preview():
    from .app import HealthBridgeApp
    app=QApplication.instance() or QApplication([]); w=MainWindow(HealthBridgeApp()); w.show(); app.exec()


if __name__=="__main__": launch_preview()
