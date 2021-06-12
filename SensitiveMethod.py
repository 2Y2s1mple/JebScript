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
import collections

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

def init_sd():
    #Sensitive_dict["providerCall"] = ";->call(Ljava/lang/String;Ljava/lang/String;Landroid/os/Bundle;)Landroid/os/Bundle;"
    Sensitive_dict["registerReceiver1"] = "Landroid/content/Context;->registerReceiver(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;)Landroid/content/Intent;"
    Sensitive_dict["registerReceiver2"] = "Landroid/content/Context;->registerReceiver(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;I)Landroid/content/Intent;"
    Sensitive_dict["registerReceiver3"] = "Landroid/content/Context;->registerReceiver(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;Ljava/lang/String;Landroid/os/Handler;)Landroid/content/Intent;"
    Sensitive_dict["registerReceiver4"] = "Landroid/content/Context;->registerReceiver(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;Ljava/lang/String;Landroid/os/Handler;I)Landroid/content/Intent;"
    Sensitive_dict["startService"] = "Landroid/content/Context;->startService(Landroid/content/Intent;)Landroid/content/ComponentName;"
    Sensitive_dict["startServiceAsUser"] = "Landroid/content/Context;->startServiceAsUser(Landroid/content/Intent;Landroid/os/UserHandle;)Landroid/content/ComponentName;"
    Sensitive_dict["startActivity1"] = "Landroid/content/Context;->startActivity(Landroid/content/Intent;)V"
    Sensitive_dict["startActivity2"] = "Landroid/content/Context;->startActivity(Landroid/content/Intent;Landroid/os/Bundle;)V"
    Sensitive_dict["startActivityAsUser1"] = "Landroid/content/Context;->startActivityAsUser(Landroid/content/Intent;Landroid/os/Bundle;Landroid/os/UserHandle;)V"
    Sensitive_dict["startActivityAsUser2"] = "Landroid/content/Context;->startActivityAsUser(Landroid/content/Intent;Landroid/os/UserHandle;)V"
    Sensitive_dict["startActivityForResult"] = "Landroid/content/Context;->startActivityForResult(Ljava/lang/String;Landroid/content/Intent;ILandroid/os/Bundle;)V"
    Sensitive_dict["sendBroadcast1"] = "Landroid/content/Context;->sendBroadcast(Landroid/content/Intent;)V"
    Sensitive_dict["sendBroadcast2"] = "Landroid/content/Context;->sendBroadcast(Landroid/content/Intent;Ljava/lang/String;)V"
    Sensitive_dict["sendBroadcast3"] = "Landroid/content/Context;->sendBroadcast(Landroid/content/Intent;Ljava/lang/String;I)V"
    Sensitive_dict["sendBroadcast4"] = "Landroid/content/Context;->sendBroadcast(Landroid/content/Intent;Ljava/lang/String;Landroid/os/Bundle;)V"
    Sensitive_dict["sendBroadcastAsUser1"] = "Landroid/content/Context;->sendBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;)V"
    Sensitive_dict["sendBroadcastAsUser2"] = "Landroid/content/Context;->sendBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;Ljava/lang/String;)V"
    Sensitive_dict["sendBroadcastAsUser3"] = "Landroid/content/Context;->sendBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;Ljava/lang/String;I)V"
    Sensitive_dict["sendBroadcastAsUser4"] = "Landroid/content/Context;->sendBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;Ljava/lang/String;Landroid/os/Bundle;)V"
    Sensitive_dict["sendBroadcastAsUserMultiplePermissions"] = "Landroid/content/Context;->sendBroadcastAsUserMultiplePermissions(Landroid/content/Intent;Landroid/os/UserHandle;[Ljava/lang/String;)V"
    Sensitive_dict["sendBroadcastMultiplePermissions"] = "Landroid/content/Context;->sendBroadcastMultiplePermissions(Landroid/content/Intent;[Ljava/lang/String;)V"
    Sensitive_dict["sendOrderedBroadcast1"] = "Landroid/content/Context;->sendOrderedBroadcast(Landroid/content/Intent;Ljava/lang/String;)V"
    Sensitive_dict["sendOrderedBroadcast2"] = "Landroid/content/Context;->sendOrderedBroadcast(Landroid/content/Intent;Ljava/lang/String;ILandroid/content/BroadcastReceiver;Landroid/os/Handler;ILjava/lang/String;Landroid/os/Bundle;)V"
    Sensitive_dict["sendOrderedBroadcast3"] = "Landroid/content/Context;->sendOrderedBroadcast(Landroid/content/Intent;Ljava/lang/String;Landroid/content/BroadcastReceiver;Landroid/os/Handler;ILjava/lang/String;Landroid/os/Bundle;)V"
    Sensitive_dict["sendOrderedBroadcast4"] = "Landroid/content/Context;->sendOrderedBroadcast(Landroid/content/Intent;Ljava/lang/String;Landroid/os/Bundle;Landroid/content/BroadcastReceiver;Landroid/os/Handler;ILjava/lang/String;Landroid/os/Bundle;)V"
    Sensitive_dict["sendOrderedBroadcastAsUser1"] = "Landroid/content/Context;->sendOrderedBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;Ljava/lang/String;ILandroid/content/BroadcastReceiver;Landroid/os/Handler;ILjava/lang/String;Landroid/os/Bundle;)V"
    Sensitive_dict["sendOrderedBroadcastAsUser2"] = "Landroid/content/Context;->sendOrderedBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;Ljava/lang/String;ILandroid/os/Bundle;Landroid/content/BroadcastReceiver;Landroid/os/Handler;ILjava/lang/String;Landroid/os/Bundle;)V"
    Sensitive_dict["sendOrderedBroadcastAsUser3"] = "Landroid/content/Context;->sendOrderedBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;Ljava/lang/String;Landroid/content/BroadcastReceiver;Landroid/os/Handler;ILjava/lang/String;Landroid/os/Bundle;)V"
    Sensitive_dict["sendStickyBroadcast"] = "Landroid/content/Context;->sendStickyBroadcast(Landroid/content/Intent;)V"
    Sensitive_dict["sendStickyBroadcastAsUser1"] = "Landroid/content/Context;->sendStickyBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;)V"
    Sensitive_dict["sendStickyBroadcastAsUser2"] = "Landroid/content/Context;->sendStickyBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;Landroid/os/Bundle;)V"
    Sensitive_dict["sendStickyOrderedBroadcast"] = "Landroid/content/Context;->sendStickyOrderedBroadcast(Landroid/content/Intent;Landroid/content/BroadcastReceiver;Landroid/os/Handler;ILjava/lang/String;Landroid/os/Bundle;)V"
    Sensitive_dict["sendStickyOrderedBroadcastAsUser"] = "Landroid/content/Context;->sendStickyOrderedBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;Landroid/content/BroadcastReceiver;Landroid/os/Handler;ILjava/lang/String;Landroid/os/Bundle;)V"
    Sensitive_dict["loadLibrary"] = "Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V"
    Sensitive_dict["load"] = "Ljava/lang/System;->load(Ljava/lang/String;)V"

    Sensitive_dict["getClassLoader"] = "Landroid/content/Context;->getClassLoader()Ljava/lang/ClassLoader;"
    Sensitive_dict["DexClassLoader_init"] = "Ldalvik/system/DexClassLoader;-><init>(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/ClassLoader;)V"
    Sensitive_dict["DexClassLoader_loadClass1"] = "Ldalvik/system/DexClassLoader;->loadClass(Ljava/lang/String;)Ljava/lang/Class;"
    Sensitive_dict["DexClassLoader_loadClass2"] = "Ldalvik/system/DexClassLoader;->loadClass(Ljava/lang/String;Z)Ljava/lang/Class;"


init_sd()
PI = 3
Max_depth = 0
Need_save = True

class SensitiveMethod(IScript):
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

        self.dexunits = RuntimeProjectUtil.findUnitsByType(self.prj, IDexUnit, False)


        activeAddress = "Landroid/content/Context;->sendBroadcastAsUser(Landroid/content/Intent;Landroid/os/UserHandle;)V"
        self.result = []   # for UI table

        for sm_name, sm_address in Sensitive_dict.items():
            activeAddress = sm_address
            dunit, mtd = get_mtd_by_addr(self.dexunits, activeAddress)
            self.xrefs_set = set()

            self.output = []   # for save/print Item

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
            #if any([b in x for b in Black_list2]): continue  #
            if x not in self.xrefs_set:
                self.xrefs_set.add(x)
                out = "-" * PI * level + x
                #print(out)
                self.output.append(out)
                self.result.append([level, sm_name, out, dunit.getUid()])
                du, super_mtd = get_mtd_by_addr(self.dexunits, x)
                self.dfs(sm_name, du, super_mtd, level+1)




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




