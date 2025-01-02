__kupfer_name__ = "wlroots Window List"
__kupfer_sources__ = ("WlrootsSource",)
__description__ = "All windows on all workspaces"
__version__ = "2025-01-02"
__author__ = "Steffen Klemer <me@sklemer.de>"

from kupfer.obj import Action, Leaf, Source
from kupfer.support import system, weaklib
from wl_framework.loop_integrations import PollIntegration
from wl_framework.network.connection import (
	WaylandConnection,
	WaylandDisconnected
)
from wl_framework.protocols.foreign_toplevel import ForeignTopLevel

class WlCtrl(WaylandConnection):
	EXIT_OK,        \
	EXIT_ARG_ERROR, \
	EXIT_NO_MATCH,  \
	EXIT_MULTIPLE_MATCHES = range(4)

	def __init__(self, eventloop_integration, action, window = None):
		actions = {
				    'list':('list', None),
					'focus': ('activate', None),
				    'activate': ('activate', None),
				    'maximize': ('set_maximize', (True,)),
				    'minimize': ('set_minimize', (True,)),
				  'fullscreen': ('set_fullscreen', (True,)),
				  'unmaximize': ('set_maximize', (False,)),
				  'unminimize': ('set_minimize', (False,)),
				'unfullscreen': ('set_fullscreen', (False,)),
				       'close': ('close', tuple())
		}
		self.action = actions.get(action)
		if window:
			self.target = int(window)
		else:
			self.target = None
		super().__init__(eventloop_integration)
		self.return_code = WlCtrl.EXIT_OK


	def quit(self, data=None):
		self.shutdown()

	def on_initial_sync(self, data):
		super().on_initial_sync(data)
		if self.action[0] == 'activate':
			# As we are subclassing the connection itself
			# we have to patch the action here because
			# the seat is only set in this very function.
			self.action = ('activate', (self.display.seat,))
		self.toplevels = ForeignTopLevel(self)
		# ForeignTopLevel will .bind() in its constructor
		# which will then cause the server to send all of
		# the initial toplevel states. Thus we just wait
		# for that to happen by queueing a callback and
		# then looping over the results.
		self.sync(self.info_done)

	def info_done(self, data):
		if self.action[0] == 'list':
			self.quit()
			return
		func_name, func_args = self.action
		func = getattr(self.toplevels.windows[self.target], func_name)
		func(*func_args)
		# Wait for roundtrip to return before closing the connection
		self.sync(self.quit)

def wlctrl(action='list', window=None):
	loop = PollIntegration()
	app = WlCtrl(loop, action, window)
	try:
		loop.run()
	except WaylandDisconnected:
		pass

	if (action == 'list'):
		return app.toplevels.windows
	return


class WindowAction(Action):
    def __init__(self, name, action, time=False, icon=None):
        super(Action, self).__init__(name)
        self.action = action or name.lower()
        self.icon_name = icon

    def repr_key(self):
        return self.action

    def activate(self, leaf, iobj=None):
        self._perform_action(self.action, leaf)

    @classmethod
    def _perform_action(cls, action_attr, leaf, time=None):
        wlctrl(action_attr, leaf.object)

    def get_icon_name(self):
        if not self.icon_name:
            return super().get_icon_name()

        return self.icon_name

class WindowLeaf(Leaf):
    # object = window xid

    def get_actions(self):
        yield WindowAction(_("Activate"), "activate", time=True)
        yield WindowAction(_("Close"), "close", time=True, icon="window-close")

    def get_description(self):
        return "Some old Window"

    def get_icon_name(self):
        return "kupfer-window"



class WlrootsSource(Source):
    task_update_interval_sec = 5
    source_use_cache = False
    source_prefer_sublevel = True

    def should_sort_lexically(self):
        return True

    def is_dynamic(self):
        return True

    def __init__(self, name="Wlroots Window List"):
        super().__init__(name)

    def get_items(self):
        windows = wlctrl('list')
        for win in windows.values():
            name, app = (win.title, win.app_id)
            if name != app and app not in name:
                name = f"{name} ({app})"

            yield WindowLeaf(win.obj_id, name)

    def get_description(self):
        return "All wlroots windows on all workspaces"

    def get_icon_name(self):
        return "kupfer-window"

    def provides(self):
        yield WindowLeaf
