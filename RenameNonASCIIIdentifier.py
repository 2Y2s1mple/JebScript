# -*- coding: utf-8 -*-
# ? shortcut=Shift+N

# Rename non-ASCII identifiers to readable form.
# Author: 22s1mple
# Usage:
# - Position the caret on a method name in decompiled source view.
# - Press Shift+N

import string
import re
import collections
import sys
import urllib
from urlparse import urlparse
from com.pnfsoftware.jeb.client.api import IScript
from com.pnfsoftware.jeb.client.api import IScript, IGraphicalClientContext
from com.pnfsoftware.jeb.core import RuntimeProjectUtil
from com.pnfsoftware.jeb.core.events import JebEvent, J
from com.pnfsoftware.jeb.core.output import AbstractUnitRepresentation, UnitRepresentationAdapter
from com.pnfsoftware.jeb.core.units.code import ICodeUnit, ICodeItem
from com.pnfsoftware.jeb.core.units.code.java import IJavaSourceUnit, IJavaStaticField, IJavaNewArray, IJavaConstant, \
    IJavaCall, IJavaField, IJavaMethod, IJavaClass
from com.pnfsoftware.jeb.core.actions import ActionTypeHierarchyData
from com.pnfsoftware.jeb.core.actions import ActionRenameData
from com.pnfsoftware.jeb.core.util import DecompilerHelper
from com.pnfsoftware.jeb.core.output.text import ITextDocument
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core.actions import ActionOverridesData
from com.pnfsoftware.jeb.core.units import UnitUtil
from com.pnfsoftware.jeb.core.units import UnitAddress
from com.pnfsoftware.jeb.core.actions import Actions, ActionContext, ActionCommentData, ActionRenameData, \
    ActionXrefsData


class RenameNonASCIIIdentifier(IScript):
    def calcItemVal(self, ItemId):
        # @JEB Official: only work for 32-bit numbers, may be disabled in the future
        return str(hex(ItemId & 0xFFFFFFFF))[:-1].lower()

    def methodNameTransform(self, name):
        # Non-ASCII
        try:
            result = bytes(name)
        except UnicodeEncodeError as e:
            result = urllib.quote(name.encode("utf-8")).replace('%', "").lower()
        except Exception as e:
            print(e)

        return result

    def RenameItem(self, itemId, itemAddress, prefix=""):
        actCntx = ActionContext(self.focusUnit, Actions.RENAME, itemId, itemAddress)
        actData = ActionRenameData()

        originalName = ""
        newName = "newName"

        if self.focusUnit.prepareExecution(actCntx, actData):
            try:
                getCurrentName = actData.getCurrentName()

                # 这里的判重逻辑不严谨，先凑合
                if "_" in getCurrentName: return getCurrentName

                originalName = actData.getOriginalName()

                if prefix: prefix += "_"
                newName = prefix + self.methodNameTransform(originalName)
                actData.setNewName(newName)
                bRlt = self.focusUnit.executeAction(actCntx, actData)
                if not bRlt:
                    print(u'Failure Action %s' % itemAddress)
                else:
                    pass
            except Exception as e:
                print(e)
        return newName

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

        self.focusFragment = ctx.getFocusedFragment()
        self.focusUnit = self.focusFragment.getUnit()  # Should be a JavaSourceUnit

        self.activeItem = self.focusFragment.getActiveItem()
        self.activeItemVal = self.calcItemVal(self.activeItem.getItemId())

        if not isinstance(self.focusUnit, IJavaSourceUnit):
            print('This script must be run within IJavaSourceUnit')
            return
        if not self.focusFragment:
            print("You Should pick one method name before run this script.")
            return

        viewMethodSig = self.focusFragment.getActiveAddress()

        self.Traversal(viewMethodSig, self.activeItemVal)

    def Traversal(self, mtdSig, itemId):
        self.codeUnit = RuntimeProjectUtil.findUnitsByType(self.prj, ICodeUnit, False)
        if not self.codeUnit: return None

        for unit in self.codeUnit:
            # Unit已经可以拿全部的identifier，但是太臃肿，也没必要，看哪改哪就够用了
            # for x in unit.getMethods(): print(x)
            # for x in unit.getFields(): print(x)
            if unit.getName().lower() != "bytecode": continue
            classes = unit.getClasses()
            if not classes: continue

            for c in classes:
                cAddr = c.getAddress()
                if not cAddr: continue

                fields = c.getFields()
                # print(c, c.getItemId())  # className重命名要单独并优先做，因为会影响field/method的getName，预期能力 = jadx类名还原 + 老板的jebPlugins，
                for fi in fields:
                    self.RenameItem(fi.getItemId(), fi.getAddress(), fi.getFieldType().getName())

                if mtdSig.find(cAddr) == 0:
                    mtdlist = c.getMethods()
                    if not mtdlist: continue
                    for mtd in mtdlist:
                        self.RenameItem(mtd.getItemId(), mtd.getAddress(), mtd.getReturnType().getName())

        return None
