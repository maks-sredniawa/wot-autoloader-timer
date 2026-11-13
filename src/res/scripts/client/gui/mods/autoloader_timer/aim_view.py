from __future__ import division

from gui.mods.gambiter import g_guiFlash
from gui.mods.gambiter.flash import COMPONENT_ALIGN, COMPONENT_EVENT, COMPONENT_TYPE

from . import aim
from .view import dragged_offset, view_offset

# GUIFlash creates battle components in alphabetical order of alias, which is also their stacking order.
_PREFIX = 'maksforgeAimTimer'
OUTLINE = _PREFIX + '0Outline'
TRACK = _PREFIX + '1Track'
LOCKED = _PREFIX + '2Locked'
FILL = _PREFIX + '3Fill'
GAIN = _PREFIX + '4Gain'
LIMIT = _PREFIX + '5Limit'
SECONDS = _PREFIX + '6Seconds'
PERCENT = _PREFIX + '7Percent'
COOLDOWN = _PREFIX + '8Cooldown'
STACKING_ORDER = (OUTLINE, TRACK, LOCKED, FILL, GAIN, LIMIT, SECONDS, PERCENT, COOLDOWN)

TRACK_SIZE = (10, 64)
FILL_WIDTH = 8
FILL_HEIGHT = 62
LIMIT_SIZE = (16, 2)
LABEL_GAP = 10
COOLDOWN_X = 26

_IMAGE_DIR = 'gui/maps/autoloader_timer/'
_SHADOW = {'color': 0x000000, 'alpha': 0.8, 'blurX': 2, 'blurY': 2, 'strength': 2, 'quality': 2}
_LABEL_OFFSETS = {
    SECONDS: (0, -(TRACK_SIZE[1] // 2 + LABEL_GAP)),
    PERCENT: (0, TRACK_SIZE[1] // 2 + LABEL_GAP),
}
_DRAGGABLE = (TRACK, SECONDS, PERCENT)


def _image(name):
    path = _IMAGE_DIR + name + '.png'
    return {'image': '../../' + path, 'imageAlt': 'img://' + path}


def normal_aim_reached(status):
    return status.percent >= 0.999


def format_seconds(status):
    return None if status.phase == aim.AIMED else '%.1f s' % status.seconds


def format_percent(status):
    return '%d%%' % int(round(status.percent * 100))


def format_cooldown(status):
    return None if not status.locked or status.cooldown is None else '%.1f s' % status.cooldown


class AimBarView(object):

    def __init__(self, settings, on_moved):
        self._settings = settings
        self._on_moved = on_moved
        self._anchor = (0, 0)
        self._view_id = None
        self._shown = {}
        self._status = None
        centered = {'alignX': COMPONENT_ALIGN.CENTER, 'alignY': COMPONENT_ALIGN.CENTER, 'visible': False}
        self._create(OUTLINE, COMPONENT_TYPE.IMAGE, dict(centered, alpha=0.4, width=TRACK_SIZE[0] + 2,
                                                         height=TRACK_SIZE[1] + 2, **_image('light')))
        self._create(TRACK, COMPONENT_TYPE.IMAGE, dict(centered, alpha=0.75, drag=True, width=TRACK_SIZE[0],
                                                       height=TRACK_SIZE[1], **_image('black')))
        self._create(LOCKED, COMPONENT_TYPE.IMAGE, dict(centered, alpha=0.7, width=FILL_WIDTH, **_image('grey')))
        self._create(FILL, COMPONENT_TYPE.IMAGE, dict(centered, width=FILL_WIDTH))
        self._create(GAIN, COMPONENT_TYPE.IMAGE, dict(centered, width=FILL_WIDTH, **_image('cyan')))
        self._create(LIMIT, COMPONENT_TYPE.IMAGE, dict(centered, width=LIMIT_SIZE[0], height=LIMIT_SIZE[1],
                                                       **_image('light')))
        for alias in (SECONDS, PERCENT, COOLDOWN):
            self._create(alias, COMPONENT_TYPE.LABEL, dict(centered, text='', isHtml=True, glowfilter=_SHADOW,
                                                           drag=alias in _DRAGGABLE))
        COMPONENT_EVENT.UPDATED += self._on_component_updated

    def destroy(self):
        COMPONENT_EVENT.UPDATED -= self._on_component_updated
        for alias in list(self._shown):
            g_guiFlash.deleteComponent(alias)
        self._shown = {}

    def set_anchor(self, x, y, view_id=None):
        if ((x, y), view_id) == (self._anchor, self._view_id):
            return
        self._anchor = (x, y)
        self._view_id = view_id
        self.show(self._status)

    def hide(self):
        self.show(None)

    def show(self, status):
        self._status = status
        if status is None:
            for alias in self._shown:
                self._update(alias, {'visible': False})
            return
        cx, cy = self._center()
        bottom = cy + FILL_HEIGHT / 2
        self._update(OUTLINE, {'visible': True, 'x': cx, 'y': cy})
        self._update(TRACK, {'visible': True, 'x': cx, 'y': cy})
        self._show_fill(status, cx, bottom)
        self._show_limit(status, cx, bottom)
        self._show_locked(status, cx, cy, bottom)
        colors = self._settings['colors']
        percent_color = colors['loaded'] if normal_aim_reached(status) else colors['loading']
        self._show_label(SECONDS, format_seconds(status), colors['loading'], self._settings['fontSize'],
                         self._label_position(SECONDS))
        self._show_label(PERCENT, format_percent(status), percent_color, self._settings['fontSize'] - 1,
                         self._label_position(PERCENT))
        locked_middle = (cy - FILL_HEIGHT / 2 + bottom - FILL_HEIGHT * (status.limit or 0)) / 2
        self._show_label(COOLDOWN, format_cooldown(status), colors['shellTime'], self._settings['fontSize'] - 2,
                         (cx + COOLDOWN_X, int(round(locked_middle))))

    def _show_fill(self, status, cx, bottom):
        normal = int(round(FILL_HEIGHT * min(status.fill, status.limit or 1.0)))
        gain = int(round(FILL_HEIGHT * status.fill)) - normal
        self._show_segment(FILL, normal, cx, bottom, 'green' if normal_aim_reached(status) else 'amber')
        self._show_segment(GAIN, gain, cx, bottom - normal)

    def _show_segment(self, alias, height, cx, bottom, image=None):
        if height <= 0:
            self._update(alias, {'visible': False})
            return
        if image is not None:
            self._update(alias, _image(image))
        self._update(alias, {'visible': True, 'x': cx, 'y': int(round(bottom - height / 2)), 'height': height})

    def _show_limit(self, status, cx, bottom):
        if status.limit is None:
            self._update(LIMIT, {'visible': False})
            return
        self._update(LIMIT, {'visible': True, 'x': cx, 'y': int(round(bottom - FILL_HEIGHT * status.limit))})

    def _show_locked(self, status, cx, cy, bottom):
        height = int(round(FILL_HEIGHT * (1 - (status.limit or 1.0))))
        if not status.locked or height <= 0:
            self._update(LOCKED, {'visible': False})
            return
        top = cy - FILL_HEIGHT / 2
        self._update(LOCKED, {'visible': True, 'x': cx, 'y': int(round(top + height / 2)), 'height': height})

    def _show_label(self, alias, text, color, size, position):
        if text is None:
            self._update(alias, {'visible': False})
            return
        html = "<font face='$FieldFont' size='%d' color='#%s'>%s</font>" % (size, color, text)
        self._update(alias, {'visible': True, 'text': html, 'x': position[0], 'y': position[1]})

    def _center(self):
        offset = view_offset(self._settings['aimTimer'], self._view_id)
        return (self._anchor[0] + offset['x'], self._anchor[1] + offset['y'])

    def _label_position(self, alias):
        cx, cy = self._center()
        dx, dy = _LABEL_OFFSETS[alias]
        return (cx + dx, cy + dy)

    def _create(self, alias, component_type, props):
        g_guiFlash.createComponent(alias, component_type, props)
        self._shown[alias] = dict(props)

    def _update(self, alias, props):
        shown = self._shown[alias]
        changed = dict((key, value) for key, value in props.items() if shown.get(key) != value)
        if changed:
            shown.update(changed)
            g_guiFlash.updateComponent(alias, changed)

    def _on_component_updated(self, alias, props):
        if alias not in _DRAGGABLE or 'x' not in props or 'y' not in props:
            return
        dx, dy = _LABEL_OFFSETS.get(alias, (0, 0))
        self._shown[alias].update(x=props['x'], y=props['y'])
        offset = dragged_offset(self._settings['aimTimer'], self._view_id)
        offset['x'] = int(props['x']) - dx - self._anchor[0]
        offset['y'] = int(props['y']) - dy - self._anchor[1]
        self._on_moved()
