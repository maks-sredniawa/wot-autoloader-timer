import math

from debug_utils import LOG_CURRENT_EXCEPTION
from gui.battle_control import avatar_getter
from gui.battle_control.controllers.chat_cmd_ctrl import ChatCommandsController
from messenger.ext import isBattleChatEnabled
from messenger.m_constants import PROTO_TYPE
from messenger.proto import proto_getter

from . import schedule

TEAM_CHANNEL = 0


class _TeamChat(object):

    @proto_getter(PROTO_TYPE.BW_CHAT2)
    def proto(self):
        return None

    def try_send(self, text):
        arena_chat = self.proto.arenaChat
        if not isBattleChatEnabled() or arena_chat.isBroadcastInCooldown():
            return False
        arena_chat.broadcast(text, TEAM_CHANNEL)
        return True


def _seconds(value):
    return int(math.ceil(max(0.0, value)))


def _last_shell_text(slots, loaded, pending):
    seconds = _seconds(schedule.full_in(slots))
    reachable = loaded + len(pending)
    if reachable == len(slots):
        return 'full in %d s' % seconds
    return '%d/%d in %d s' % (reachable, len(slots), seconds)


def magazine_text(slots):
    loaded = sum(1 for slot in slots if slot.state == schedule.LOADED)
    pending = [slot for slot in slots if slot.state in (schedule.LOADING, schedule.QUEUED)]
    if loaded == 0:
        if not pending:
            return None
        return 'Reloading! First shell %d s, %s' % (_seconds(pending[0].ready_in),
                                                     _last_shell_text(slots, loaded, pending))
    text = 'Ready to fire! Magazine %d/%d' % (loaded, len(slots))
    if pending:
        text += ', ' + _last_shell_text(slots, loaded, pending)
    return text


def install(get_slots):
    original = ChatCommandsController.sendReloadingCommand
    team_chat = _TeamChat()

    def send_magazine_status():
        if not avatar_getter.isPlayerOnArena() or not avatar_getter.isVehicleAlive():
            return False
        slots = get_slots()
        text = magazine_text(slots) if slots else None
        return bool(text) and team_chat.try_send(text)

    def sendReloadingCommand(self):
        try:
            if send_magazine_status():
                return
        except Exception:
            LOG_CURRENT_EXCEPTION()
        original(self)

    ChatCommandsController.sendReloadingCommand = sendReloadingCommand
