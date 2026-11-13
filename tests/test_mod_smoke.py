"""Loads the mod against stubbed game modules and renders one frame (run with Python 2.7)."""
import importlib
import os
import shutil
import sys
import tempfile
import types
import unittest

MODS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'res', 'scripts', 'client', 'gui', 'mods')


class _Event(object):

    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.handlers.remove(handler)
        return self

    def __call__(self, *args):
        for handler in list(self.handlers):
            handler(*args)


class FakeGuiFlash(object):

    def __init__(self):
        self.components = {}

    def createComponent(self, alias, compType, props=None, battle=True, lobby=False):
        self.components[alias] = dict(props or {})

    def updateComponent(self, alias, props, params=None):
        self.components[alias].update(props)

    def deleteComponent(self, alias):
        del self.components[alias]


class FakeState(object):

    def __init__(self, left, base):
        self.left, self.base = left, base

    def isReloading(self):
        return self.left > 0

    def getTimeLeft(self):
        return self.left

    def getBaseValue(self):
        return self.base


class FakeAmmo(object):

    def __init__(self):
        self.gun = _Obj(clip=_Obj(size=3), autoReload=_Obj(reloadTime=(12.0, 13.0, 15.0)))
        self.gun.hasAutoReload = lambda: True
        self.gun.hasShellChangeFactor = lambda: True
        self.gun.getShellChangeFactor = lambda: 0.5
        self.gun.isRegularClip = False
        self.gun.getShellDescriptor = lambda _: _Obj(armorDamage=(100.0, 100.0))
        self.shell_change_time = 0.0
        self.shells = (30, 1)
        self.clip_state = FakeState(4.0, 11.7)

    def getGunSettings(self):
        return self.gun

    def getCurrentShellCD(self):
        return 1234

    def getCurrentShells(self):
        return self.shells

    def getPartiallyReloadingClipState(self):
        return self.clip_state

    def getShellChangeTime(self):
        return self.shell_change_time

    def getGunReloadingState(self):
        return FakeState(0.0, 0.0)


class _Obj(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeCrosshair(object):

    def __init__(self):
        self.position = (1280, 625)
        self.onCrosshairPositionChanged = _Event()
        self.onCrosshairSizeChanged = _Event()
        self.onCrosshairScaleChanged = _Event()
        self.onCrosshairViewChanged = _Event()

    def getScaleFactor(self):
        return 1.0

    def getSize(self):
        return (2560, 1440)

    def getDisaredPosition(self):
        return self.position

    def move_to(self, x, y):
        self.position = (x, y)
        self.onCrosshairPositionChanged(x, y)


def _install_stubs(guiflash, ammo, crosshair, player_events, callbacks, mechanics):
    def module(name, **attrs):
        mod = types.ModuleType(name)
        mod.__dict__.update(attrs)
        sys.modules[name] = mod
        return mod

    module('BigWorld', callback=lambda delay, fn: callbacks.append(fn) or len(callbacks),
           cancelCallback=lambda cid: None)
    module('PlayerEvents', g_playerEvents=player_events)
    module('constants', TEMPERATURE_GUN_STATE=_Obj(IDLE=0, HEATING=1, COOLING=2, COOLING_DELAY=3))
    module('items').__path__ = []
    module('items.vehicle_mechanics_types',
           VehicleMechanicKeys=_Obj(OVERHEAT_GUN='overheat', TEMPERATURE_GUN='temperature',
                                                    DUAL_ACCURACY='dualAccuracy'))
    module('vehicles').__path__ = []
    module('vehicles.mechanics').__path__ = []
    module('vehicles.mechanics.mechanic_helpers', getPlayerVehicleMechanicComponent=mechanics.get,
           getMechanicFromMechanicsParams=lambda params, key: params[key])
    module('debug_utils', LOG_CURRENT_EXCEPTION=lambda: (_ for _ in ()).throw(sys.exc_info()[1]),
           LOG_ERROR=lambda *a: None)

    provider = _Obj(shared=_Obj(ammo=ammo, crosshair=crosshair))

    class _Descriptor(object):
        def __init__(self, _):
            pass

        def __get__(self, obj, owner):
            return provider

    module('helpers', dependency=module('helpers.dependency', descriptor=_Descriptor))
    module('skeletons')
    module('skeletons.gui')
    module('skeletons.gui.battle_session', IBattleSessionProvider=object)
    gui = module('gui')
    gui.__path__ = []
    mods = module('gui.mods')
    mods.__path__ = [MODS_DIR]
    gui.mods = mods
    battle_control = module('gui.battle_control', avatar_getter=module(
        'gui.battle_control.avatar_getter', isPlayerOnArena=lambda: True, isVehicleAlive=lambda: True))
    battle_control.__path__ = []
    controllers = module('gui.battle_control.controllers')
    controllers.__path__ = []

    class ChatCommandsController(object):
        sent = []
        cooldown = False
        chat_enabled = True
        broadcast_fails = False

        def sendReloadingCommand(self):
            ChatCommandsController.sent.append('game reload command')

    module('gui.battle_control.controllers.chat_cmd_ctrl', ChatCommandsController=ChatCommandsController)
    module('messenger').__path__ = []
    module('messenger.m_constants', PROTO_TYPE=_Obj(BW_CHAT2=2))
    module('messenger.ext', isBattleChatEnabled=lambda: ChatCommandsController.chat_enabled)

    def broadcast(text, channel):
        if ChatCommandsController.broadcast_fails:
            raise RuntimeError('broadcast failed')
        ChatCommandsController.sent.append((text, channel))

    team_chat = _Obj(isBroadcastInCooldown=lambda: ChatCommandsController.cooldown, broadcast=broadcast)

    class _ProtoGetter(object):
        def __init__(self, _):
            pass

        def __call__(self, fn):
            return property(lambda self: _Obj(arenaChat=team_chat))

    module('messenger.proto', proto_getter=_ProtoGetter)
    gambiter = module('gui.mods.gambiter', g_guiFlash=guiflash)
    gambiter.__path__ = []
    mods.gambiter = gambiter
    module('gui.mods.gambiter.flash',
           COMPONENT_ALIGN=_Obj(CENTER='center'),
           COMPONENT_TYPE=_Obj(LABEL='Label', IMAGE='Image'),
           COMPONENT_EVENT=_Obj(UPDATED=_Event()))
    return provider


class _StubbedGameTest(unittest.TestCase):

    def setUp(self):
        for name in [name for name in sys.modules if name.startswith('gui.mods.')]:
            del sys.modules[name]
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        self.guiflash = FakeGuiFlash()
        self.ammo = FakeAmmo()
        self.events = _Obj(onAvatarReady=_Event(), onAvatarBecomeNonPlayer=_Event())
        self.crosshair = FakeCrosshair()
        self.callbacks = []
        self.mechanics = {}
        self.provider = _install_stubs(self.guiflash, self.ammo, self.crosshair, self.events, self.callbacks,
                                       self.mechanics)
        self.player = _Obj(gunRotator=None, isVehicleAlive=True)
        self.clock = [100.0]
        sys.modules['BigWorld'].player = lambda: self.player
        sys.modules['BigWorld'].time = lambda: self.clock[0]

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp)


class ModSmokeTest(_StubbedGameTest):

    def label(self):
        return self.guiflash.components.get('maksforgeAutoloaderTimer', {})

    def label_position(self):
        return (self.label()['x'], self.label()['y'])

    def crosshair_handlers(self, crosshair):
        return [crosshair.onCrosshairPositionChanged.handlers, crosshair.onCrosshairSizeChanged.handlers,
                crosshair.onCrosshairScaleChanged.handlers, crosshair.onCrosshairViewChanged.handlers]

    def test_renders_one_line_and_writes_default_config(self):
        mod = importlib.import_module("gui.mods.mod_autoloader_timer")
        mod.init()
        self.events.onAvatarReady()
        text = self.label()['text']
        self.assertTrue(self.label()['visible'])
        self.assertIn("<font color='#D8D8D8'>1/3</font>", text)
        self.assertTrue(text.endswith("<font color='#D8D8D8'>100</font></font>"))
        self.assertIn("<font color='#FCAF1A'>4.0</font>", text)
        self.assertEqual((self.label()['x'], self.label()['y']), (0, -35))
        self.assertIn("<font color='#D8D8D8'>14.8</font>", text)

        self.crosshair.move_to(1280, 720)
        self.assertEqual((self.label()['x'], self.label()['y']), (0, 60))
        self.assertTrue(os.path.isfile(os.path.join('mods', 'configs', 'autoloader_timer', 'config.json')))

        chat_ctrl = sys.modules['gui.battle_control.controllers.chat_cmd_ctrl'].ChatCommandsController
        chat_ctrl().sendReloadingCommand()
        self.assertEqual(chat_ctrl.sent, [('Ready to fire! Magazine 1/3, full in 15 s', 0)])
        chat_ctrl.cooldown = True
        chat_ctrl().sendReloadingCommand()
        self.assertEqual(chat_ctrl.sent[-1], 'game reload command')

        self.ammo.shells = (30, 3)
        self.ammo.clip_state = FakeState(0.0, 0.0)
        self.ammo.shell_change_time = 6.75
        self.callbacks[-1]()
        text = self.label()['text']
        self.assertIn("<font color='#C7FE48'>3/3</font>", text)
        self.assertTrue(text.endswith("<font color='#C7FE48'>300</font></font>"))
        self.assertLess(text.index('>10.8<'), text.index('>11.7<'))
        self.assertLess(text.index('>11.7<'), text.index('>13.5<'))
        chat_ctrl.cooldown = False
        chat_ctrl().sendReloadingCommand()
        self.assertEqual(chat_ctrl.sent[-1], ('Ready to fire! Magazine 3/3', 0))

        self.ammo.gun.hasAutoReload = lambda: False
        self.callbacks[-1]()
        self.assertFalse(self.label()['visible'])
        mod.fini()
        self.assertEqual(self.guiflash.components, {})
        self.assertEqual(self.crosshair_handlers(self.crosshair), [[], [], [], []])

    def test_follows_each_battles_crosshair_and_lets_go_after_it(self):
        mod = importlib.import_module("gui.mods.mod_autoloader_timer")
        mod.init()
        self.events.onAvatarReady()
        old = self.crosshair
        self.events.onAvatarBecomeNonPlayer()
        self.assertEqual(self.crosshair_handlers(old), [[], [], [], []])

        new = FakeCrosshair()
        new.position = (1280, 720)
        self.provider.shared.crosshair = new
        self.events.onAvatarReady()
        self.assertEqual(self.label_position(), (0, 60))
        new.move_to(1300, 720)
        self.assertEqual(self.label_position(), (20, 60))
        old.move_to(1280, 900)
        self.assertEqual(self.label_position(), (20, 60))
        self.assertEqual(self.crosshair_handlers(old), [[], [], [], []])

        mod.fini()
        self.assertEqual(self.crosshair_handlers(new), [[], [], [], []])


def _slots(*states_and_times):
    schedule = sys.modules['gui.mods.autoloader_timer.schedule']
    return [schedule.Slot(number, state, ready_in=ready_in)
            for number, (state, ready_in) in enumerate(states_and_times, 1)]


class ReloadChatTest(_StubbedGameTest):

    def setUp(self):
        super(ReloadChatTest, self).setUp()
        self.reload_chat = importlib.import_module('gui.mods.autoloader_timer.reload_chat')
        self.chat_ctrl = sys.modules['gui.battle_control.controllers.chat_cmd_ctrl'].ChatCommandsController
        self.slots = []
        self.reload_chat.install(lambda: self.slots)

    def press_reload(self):
        self.chat_ctrl().sendReloadingCommand()
        return self.chat_ctrl.sent

    def test_empty_magazine_reports_first_shell_and_full_magazine(self):
        self.slots = _slots(('loading', 8.2), ('queued', 20.0), ('queued', 34.5))
        self.assertEqual(self.press_reload(), [('Reloading! First shell 9 s, full in 35 s', 0)])

    def test_rack_that_cannot_fill_the_magazine_reports_how_far_it_gets(self):
        self.slots = _slots(('loaded', 0.0), ('loading', 8.2), ('no_ammo', 0.0), ('no_ammo', 0.0))
        self.assertEqual(self.press_reload(), [('Ready to fire! Magazine 1/4, 2/4 in 9 s', 0)])

    def test_empty_magazine_with_short_rack_reports_how_far_it_gets(self):
        self.slots = _slots(('loading', 4.0), ('queued', 15.2), ('no_ammo', 0.0))
        self.assertEqual(self.press_reload(), [('Reloading! First shell 4 s, 2/3 in 16 s', 0)])

    def test_out_of_shells_sends_game_command(self):
        self.slots = _slots(('no_ammo', 0.0), ('no_ammo', 0.0), ('no_ammo', 0.0))
        self.assertEqual(self.press_reload(), ['game reload command'])

    def test_chat_disabled_sends_game_command(self):
        self.slots = _slots(('loaded', 0.0), ('loading', 8.2), ('queued', 20.0))
        self.chat_ctrl.chat_enabled = False
        self.assertEqual(self.press_reload(), ['game reload command'])

    def test_error_in_magazine_line_sends_game_command_once(self):
        logged = []
        self.reload_chat.LOG_CURRENT_EXCEPTION = lambda: logged.append(sys.exc_info()[0])
        self.slots = _slots(('loaded', 0.0), ('loading', 8.2), ('queued', 20.0))
        self.chat_ctrl.broadcast_fails = True
        self.assertEqual(self.press_reload(), ['game reload command'])
        self.assertEqual(logged, [RuntimeError])


class MagazineDamageTest(_StubbedGameTest):

    def setUp(self):
        super(MagazineDamageTest, self).setUp()
        self.mod = importlib.import_module('gui.mods.mod_autoloader_timer')
        self.mod.init()
        self.addCleanup(self.mod.fini)
        self.events.onAvatarReady()

    def use_regular_magazine(self):
        self.ammo.gun.hasAutoReload = lambda: False
        self.ammo.gun.isRegularClip = True
        self.ammo.gun.clip.size = 6
        self.ammo.gun.getShellDescriptor = lambda _: _Obj(armorDamage=(390.0, 390.0))

    def render(self, total, in_clip):
        self.ammo.shells = (total, in_clip)
        self.callbacks[-1]()
        return self.guiflash.components['maksforgeAutoloaderTimer']

    def test_partial_regular_magazine_shows_count_then_damage_in_grey(self):
        self.use_regular_magazine()
        text = self.render(20, 4)['text']
        self.assertLess(text.index("<font color='#D8D8D8'>4/6</font>"),
                        text.index("<font color='#D8D8D8'>1560</font>"))

    def test_full_regular_magazine_is_green(self):
        self.use_regular_magazine()
        text = self.render(20, 6)['text']
        self.assertIn("<font color='#C7FE48'>6/6</font>", text)
        self.assertIn("<font color='#C7FE48'>2340</font>", text)

    def test_empty_regular_magazine_shows_amber_count_without_damage(self):
        self.use_regular_magazine()
        text = self.render(20, 0)['text']
        self.assertIn("<font color='#FCAF1A'>0/6</font>", text)
        self.assertEqual(text.count('<font color'), 1)

    def test_regular_magazine_with_no_shells_left_hides_the_line(self):
        self.use_regular_magazine()
        self.assertFalse(self.render(0, 0)['visible'])

    def test_hide_when_full_hides_a_full_regular_magazine_only(self):
        self.use_regular_magazine()
        self.mod._timer.settings['hideWhenFull'] = True
        self.assertFalse(self.render(20, 6)['visible'])
        self.assertTrue(self.render(20, 5)['visible'])

    def test_empty_autoreloader_shows_no_damage(self):
        self.ammo.clip_state = FakeState(4.0, 11.7)
        text = self.render(30, 0)['text']
        self.assertTrue(text.endswith("<font color='#D8D8D8'>0/3</font></font>"))

    def test_single_shot_gun_stays_hidden(self):
        self.ammo.gun.hasAutoReload = lambda: False
        self.assertFalse(self.render(30, 1)['visible'])


class GunCoolingTest(_StubbedGameTest):
    IDLE, HEATING, COOLING, COOLING_DELAY = range(4)

    def setUp(self):
        super(GunCoolingTest, self).setUp()
        self.ammo.gun.hasAutoReload = lambda: False
        self.ammo.gun.mechanicsParams = {'overheat': _Obj(tempOverheatOnThreshold=100.0),
                                         'temperature': _Obj(heatingPerShot=9.0)}
        self.ammo.gun.getShellDescriptor = lambda _: _Obj(armorDamage=(80.0, 80.0))
        self.ammo.shells = (300, 300)
        self.mod = importlib.import_module('gui.mods.mod_autoloader_timer')
        self.mod.init()
        self.addCleanup(self.mod.fini)
        self.events.onAvatarReady()

    def set_gun(self, state, temperature=0.0, cooling_time=-1.0, overheated=False):
        temperature_state = _Obj(state=state, currentTemperature=temperature,
                                 getCoolingTime=lambda target: cooling_time if target == 0.0 else None)
        params = _Obj(coolingDelay=2.0, coolingPerSec=10.0)
        overheat_state = _Obj(isOverheated=overheated)
        self.mechanics['overheat'] = _Obj(getMechanicState=lambda: overheat_state)
        self.mechanics['temperature'] = _Obj(getMechanicState=lambda: temperature_state,
                                             getComponentParams=lambda: params)
        self.callbacks[-1]()
        return self.guiflash.components['maksforgeAutoloaderTimer']

    def test_locked_gun_hides_the_line(self):
        self.set_gun(self.COOLING_DELAY, 40.0, cooling_time=12.4)
        self.assertFalse(self.set_gun(self.COOLING, 90.0, cooling_time=30.0, overheated=True)['visible'])

    def test_warm_gun_shows_time_until_cold_then_damage_of_the_shots_left(self):
        label = self.set_gun(self.COOLING_DELAY, 40.0, cooling_time=12.4)
        self.assertTrue(label['visible'])
        self.assertLess(label['text'].index("<font color='#A8A8A8'>12.4</font>"),
                        label['text'].index("<font color='#D8D8D8'>560</font>"))

    def test_heating_gun_counts_the_delay_and_all_its_heat(self):
        label = self.set_gun(self.HEATING, 50.0)
        self.assertIn("<font color='#A8A8A8'>7.0</font>", label['text'])
        self.assertIn("<font color='#D8D8D8'>480</font>", label['text'])

    def test_cold_gun_shows_full_burst_damage_in_green(self):
        label = self.set_gun(self.IDLE)
        self.assertTrue(label['visible'])
        self.assertIn("<font color='#C7FE48'>960</font>", label['text'])

    def test_last_sliver_of_heat_still_allows_one_shot(self):
        label = self.set_gun(self.COOLING_DELAY, 99.0, cooling_time=20.0)
        self.assertIn("<font color='#D8D8D8'>80</font>", label['text'])

    def test_damage_is_capped_by_the_shells_left(self):
        self.ammo.shells = (3, 3)
        self.assertIn("<font color='#C7FE48'>240</font>", self.set_gun(self.IDLE)['text'])

    def test_hide_when_full_hides_a_cold_gun_only(self):
        self.mod._timer.settings['hideWhenFull'] = True
        self.assertFalse(self.set_gun(self.IDLE)['visible'])
        self.assertTrue(self.set_gun(self.COOLING_DELAY, 40.0, cooling_time=12.4)['visible'])

    def test_no_loaded_shell_on_a_cold_gun_hides_the_line(self):
        self.ammo.getCurrentShellCD = lambda: None
        self.assertFalse(self.set_gun(self.IDLE)['visible'])

    def test_reload_command_stays_the_games_own(self):
        self.set_gun(self.COOLING, 90.0, overheated=True)
        chat_ctrl = sys.modules['gui.battle_control.controllers.chat_cmd_ctrl'].ChatCommandsController
        del chat_ctrl.sent[:]
        chat_ctrl().sendReloadingCommand()
        self.assertEqual(chat_ctrl.sent, ['game reload command'])



class FakeDualAccuracy(object):

    def __init__(self):
        self.active = True

    def isActive(self):
        return self.active

    def getDualAccuracyFactor(self):
        return 0.6


class AimTimerTest(_StubbedGameTest):

    def setUp(self):
        super(AimTimerTest, self).setUp()
        self.ammo.gun.hasAutoReload = lambda: False
        self.crosshair.position = (1280, 720)
        self.player.gunRotator = _Obj(_VehicleGunRotator__dispersionAngles=[0.4, 0.2, 0.4, 0.2])
        self.player._PlayerAvatar__dispersionInfo = [1.0, 0.0, 0.0, 0.0, 0.0, 2.0]
        self.player._PlayerAvatar__getDetailedVehicleDescriptor = lambda: _Obj(gun=_Obj(shotDispersionAngle=0.2))
        self.player.vehicleTypeDescriptor = _Obj(gun=_Obj(dualAccuracy=_Obj(coolingDelay=4.0)))
        self.mod = importlib.import_module('gui.mods.mod_autoloader_timer')
        self.mod.init()
        self.addCleanup(self.mod.fini)
        self.events.onAvatarReady()

    def part(self, name):
        return self.guiflash.components['maksforgeAimTimer' + name]

    def visible(self, name):
        return self.part(name).get('visible')

    def tick(self, angles=None, at=None):
        if angles is not None:
            self.player.gunRotator._VehicleGunRotator__dispersionAngles = angles
        if at is not None:
            self.clock[0] = at
        self.callbacks[-1]()

    def test_normal_gun_aiming_shows_amber_seconds_half_bar_and_percent(self):
        self.assertIn("color='#FCAF1A'>1.4 s<", self.part('Seconds')['text'])
        self.assertIn("color='#FCAF1A'>50%<", self.part('Percent')['text'])
        self.assertEqual((self.part('Track')['x'], self.part('Track')['y']), (150, 0))
        self.assertEqual(self.part('Fill')['height'], 31)
        self.assertEqual(self.part('Fill')['y'], 16)
        self.assertIn('amber.png', self.part('Fill')['image'])
        self.assertFalse(self.visible('Limit'))
        self.assertFalse(self.visible('Locked'))
        self.assertFalse(self.visible('Cooldown'))

    def test_normal_gun_aimed_hides_seconds_and_turns_green(self):
        self.tick([0.2, 0.2, 0.2, 0.2])
        self.assertFalse(self.visible('Seconds'))
        self.assertIn("color='#C7FE48'>100%<", self.part('Percent')['text'])
        self.assertEqual(self.part('Fill')['height'], 62)
        self.assertIn('green.png', self.part('Fill')['image'])

    def test_type_71_counts_down_the_cooldown_then_aims_the_accurate_circle(self):
        dual = FakeDualAccuracy()
        self.mechanics['dualAccuracy'] = dual
        self.player._PlayerAvatar__getDetailedVehicleDescriptor = lambda: _Obj(gun=_Obj(shotDispersionAngle=0.4))
        self.tick([0.24, 0.24, 0.24, 0.24], at=90.0)
        dual.active = False
        self.tick([0.5, 0.4, 0.5, 0.24], at=100.0)
        self.tick(at=101.0)
        self.assertIn("color='#A8A8A8'>3.0 s<", self.part('Cooldown')['text'])
        self.assertIn("color='#FCAF1A'>80%<", self.part('Percent')['text'])
        self.assertEqual(self.part('Limit')['y'], int(round(31 - 62 * 0.6)))
        self.assertTrue(self.visible('Locked'))
        self.assertEqual(self.part('Locked')['height'], 25)

        dual.active = True
        self.tick([0.4, 0.24, 0.4, 0.24], at=103.5)
        self.assertFalse(self.visible('Locked'))
        self.assertFalse(self.visible('Cooldown'))
        self.assertTrue(self.visible('Limit'))
        self.assertIn("color='#6FD8FF'>", self.part('Percent')['text'])
        self.assertIn('cyan.png', self.part('Fill')['image'])

        dual.active = False
        self.tick([0.5, 0.4, 0.5, 0.24], at=110.0)
        self.tick(at=111.0)
        self.assertIn('>2.5 s<', self.part('Cooldown')['text'])

    def test_driving_tank_is_not_shown_as_aimed(self):
        self.tick([0.8, 0.8, 0.8, 0.8])
        self.assertIn("color='#FCAF1A'>25%<", self.part('Percent')['text'])
        self.assertIn("color='#FCAF1A'>2.8 s<", self.part('Seconds')['text'])

    def test_dead_tank_hides_the_bar(self):
        self.player.isVehicleAlive = False
        self.tick()
        self.assertFalse(any(self.visible(name) for name in ('Track', 'Fill', 'Seconds', 'Percent')))

    def test_bar_follows_the_crosshair_and_saves_where_it_is_dragged(self):
        self.crosshair.move_to(1300, 700)
        self.assertEqual((self.part('Track')['x'], self.part('Track')['y']), (170, -20))
        sys.modules['gui.mods.gambiter.flash'].COMPONENT_EVENT.UPDATED('maksforgeAimTimerPercent',
                                                                       {'x': 200, 'y': 30})
        self.assertEqual(self.mod._timer.settings['aimTimer']['x'], 180)
        self.assertEqual(self.mod._timer.settings['aimTimer']['y'], 8)

    def test_turned_off_creates_no_bar(self):
        self.mod.fini()
        self.mod._timer.settings['aimTimer']['enabled'] = False
        sys.modules['gui.mods.autoloader_timer.config'].save(self.mod._timer.settings)
        self.mod.init()
        self.assertFalse([alias for alias in self.guiflash.components if alias.startswith('maksforgeAimTimer')])


if __name__ == '__main__':
    unittest.main()
