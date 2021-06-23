# -*- coding: utf-8 -*-
# ? shortcut=Mod1+Mod3+X

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
import json
from collections import Counter
import collections
from collections import OrderedDict

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

Sensitive_dict = collections.OrderedDict()


def init_dx():
    global Sensitive_dict
    sapi_path = os.path.join(os.path.dirname(__file__), "SensitiveApi.json")
    print(sapi_path)
    with open(sapi_path, "r") as jf:
        Sensitive_dict = json.load(jf, object_pairs_hook=OrderedDict)


PI = 3
Max_depth = 0
Need_save = True


class SensitiveMethod(IScript):
    def run(self, ctx):
        init_dx()

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

        self.dexunits = RuntimeProjectUtil.findUnitsByType(self.prj, IDexUnit, False)

        activeAddress = "Landroid/content/Context;->sendBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;)V"
        self.result = []  # for UI table

        for sm_name, sm_address in Sensitive_dict.items():
            activeAddress = sm_address
            dunit, mtd = get_mtd_by_addr(self.dexunits, activeAddress)
            self.xrefs_set = set()

            self.output = []  # for save/print Item

            self.dfs(sm_name, dunit, mtd, 0)
            if self.output:
                print("Cross-references Tree of: " + sm_name)
                for o in self.output: print(o)
                print("\n")

        # not available on 3.17
        # if Need_save:
        #     path = ctx.displayFileSaveSelector("Save output to file:")

        headers = ['Depth', 'Tag', 'Address']
        index = ctx.displayList('List of security sensitive Java methods: ', activeAddress, headers, self.result)
        if index < 0:
            return

        sel = self.result[index]
        depth, tag, addr, unit_id = int(sel[0]), sel[1], sel[2], int(sel[3])
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

    def dfs(self, sm_name, dunit, mtd, level):
        if not dunit or not mtd: return
        if level > Max_depth: return
        xrefs = get_xrefs_by_item(dunit, mtd.getItemId(), mtd.getSignature())
        for x in xrefs:
            if any([x.startswith(b) for b in Black_list]): continue
            # if any([b in x for b in Black_list2]): continue  #
            if x not in self.xrefs_set:
                self.xrefs_set.add(x)
                out = "-" * PI * level + x
                # print(out)
                self.output.append(out)
                self.result.append([level, sm_name, out, dunit.getUid()])
                du, super_mtd = get_mtd_by_addr(self.dexunits, x)
                self.dfs(sm_name, du, super_mtd, level + 1)


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
    if dunit.prepareExecution(ActionContext(dunit, Actions.QUERY_XREFS, itemid, addr), data):  # item.getSignature()
        for xref_addr in data.getAddresses():
            # print(xref_addr)
            result.append(xref_addr)

    return result
