# -*- coding: utf-8 -*-
#? shortcut=Mod1+Mod3+X

# Display Cross-references Tree of the selected Java method.
# Author: 22s1mple
# Note:
#   With 3 kinds of pruning:
#   1. Max_depth --> Limit the maximum search depth.
#   2. Black_list --> Exclude methods starting with particular custom strings.
#   3. Black_list2 --> Exclude methods that contain specific custom strings.

import os
import re
import sys
from collections import Counter

from com.pnfsoftware.jeb.client.api import IScript
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexMethod, IDalvikInstruction, IDexClass
from com.pnfsoftware.jeb.core.units.code.java import IJavaInstanceField, IJavaElement, IJavaReturn, \
    IJavaArithmeticExpression, IJavaConditionalExpression, IJavaPredicate, IJavaAssignment
from com.pnfsoftware.jeb.client.api import IScript, IGraphicalClientContext, IClientContext
from com.pnfsoftware.jeb.core import RuntimeProjectUtil
from com.pnfsoftware.jeb.core.events import JebEvent, J
from com.pnfsoftware.jeb.core.output import AbstractUnitRepresentation, UnitRepresentationAdapter, \
    AddressConversionPrecision
from com.pnfsoftware.jeb.core.units.code import ICodeUnit, ICodeItem, DecompilationOptions, IDecompilerUnit, \
    DecompilationContext
from com.pnfsoftware.jeb.core.units.code.java import IJavaSourceUnit, IJavaStaticField, IJavaNewArray, IJavaConstant, \
    IJavaCall, IJavaField, IJavaMethod, IJavaClass
from com.pnfsoftware.jeb.core.actions import ActionTypeHierarchyData
from com.pnfsoftware.jeb.core.actions import ActionRenameData
from com.pnfsoftware.jeb.core.util import DecompilerHelper
from com.pnfsoftware.jeb.core.output.text import ITextDocument
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit, IDexDecompilerUnit
from com.pnfsoftware.jeb.core.actions import ActionOverridesData
from com.pnfsoftware.jeb.core.units import UnitUtil
from com.pnfsoftware.jeb.core.units import UnitAddress
from com.pnfsoftware.jeb.core.actions import Actions, ActionContext, ActionCommentData, ActionRenameData, \
    ActionXrefsData

Black_list = [
    "Landroid/support/v4/",
    "Landroidx/",
]

Black_list2 = [
    "->onCreate(Landroid/os/Bundle;)"
]

PI = 3
Max_depth = 3

class ListJavaMethodXrefsTree(IScript):
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
        self.focusUnit = self.focusFragment.getUnit() # JavaSourceUnit

        self.dexunits = RuntimeProjectUtil.findUnitsByType(self.prj, IDexUnit, False)

        if not self.focusFragment:
            print("You Should pick one method name before run this script.")
            return

        caption = 'List Java Method Xrefs Tree'
        message = 'Input recursion depth:'
        global Max_depth
        input = ctx.displayQuestionBox(caption, message, str(Max_depth))
        if input == None:
            return
        try:
            chosen = int(input)
        except Exception as e:
            chosen = Max_depth
        Max_depth = chosen

        activeAddress = self.focusFragment.getActiveAddress(AddressConversionPrecision.FINE)
        activeItem = self.focusFragment.getActiveItem()
        activeItemText = self.focusFragment.getActiveItemAsText()


        dunit, mtd = get_mtd_by_addr(self.dexunits, activeAddress)
        self.xrefs_set = set()
        self.result = []

        print("Cross-references Tree of: " + activeAddress)

        self.dfs(dunit, mtd, 0)
        print("\n")

        headers = ['Depth', 'Address']
        index = ctx.displayList('Cross-references Tree of: ', activeAddress, headers, self.result)
        if index < 0:
            return

        sel = self.result[index]
        depth, addr, unit_id = int(sel[0]), sel[1], int(sel[2])
        addr = addr[depth * PI:]

        unit = RuntimeProjectUtil.findUnitByUid(self.prj, unit_id)
        if not unit:
            print('Unit with uid=%d was not found in the project or no longer exists!' % unit_id)
            return

        if not ctx.openView(unit):
            print('Could not open view for unit!')
        else:
            f = ctx.findFragment(unit, "Disassembly", True)
        if not f:
            print('Fragment Disassembly not found!')
        elif addr:
            f.setActiveAddress(addr)


    def dfs(self, dunit, mtd, level):
        if not dunit or not mtd: return
        if level > Max_depth: return
        xrefs = get_xrefs_by_item(dunit, mtd.getItemId(), mtd.getSignature())
        for x in xrefs:
            if any([x.startswith(b) for b in Black_list]): continue
            #if any([b in x for b in Black_list2]): continue  #
            if x not in self.xrefs_set:
                self.xrefs_set.add(x)
                out = "-" * PI * level + x
                print(out)
                self.result.append([level, out, dunit.getUid()])
                du, super_mtd = get_mtd_by_addr(self.dexunits, x)
                self.dfs(du, super_mtd, level+1)




def get_mtd_by_addr(dunits, addr):
    for dunit in dunits:
        assert isinstance(dunit, IDexUnit)
        dexmtd = dunit.getMethod(addr)
        if dexmtd:
            return dunit, dexmtd

    return None, None


def get_xrefs_by_item(dunit, itemid, addr):
    data = ActionXrefsData()
    result = []
    if dunit.prepareExecution(ActionContext(dunit, Actions.QUERY_XREFS, itemid, addr), data): # item.getSignature()
        for xref_addr in data.getAddresses():
            # print(xref_addr)
            result.append(xref_addr)

    return result



