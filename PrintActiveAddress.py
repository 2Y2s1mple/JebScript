# -*- coding: utf-8 -*-
#? shortcut=shift+t
# Guess class name from potential Logcat Tag and find possible Logger/LogUtil classes.
# Author: 22s1mple

from com.pnfsoftware.jeb.client.api import IScript, IGraphicalClientContext

class PrintActiveAddress(IScript):
    def run(self, ctx):
        self.ctx = ctx

        engctx = ctx.getEnginesContext()
        if not engctx:
            print('Back-end engines not initialized')
            return

        projects = engctx.getProjects()
        if not projects:
            print('There is no opened project')
            return
        self.prj = projects[0]

        if not isinstance(self.ctx, IGraphicalClientContext):
            print('This script must be run within a graphical client')
            return

        assert isinstance(ctx, IGraphicalClientContext)
        self.focusFragment = ctx.getFocusedFragment()
        self.focusUnit = self.focusFragment.getUnit()


        if not self.focusFragment:
            print("You Should pick one method name before run this script.")
            return

        activeAddress = self.focusFragment.getActiveAddress()
        activeItem = self.focusFragment.getActiveItem()
        activeItemText = self.focusFragment.getActiveItemAsText()
        print(activeAddress)
        print(activeItem)
        print('activeItemText = "' + repr(activeItemText) + '"')


        

