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
        ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'
        if set(name).issubset(ALPHABET):
            return name
        else:
            return urllib.quote(name.encode("utf-8")).replace('%', "").lower()

    def RenameItem(self, unit, itemId, itemAddress, prefix=""):
        actCntx = ActionContext(unit, Actions.RENAME, itemId, itemAddress)
        actData = ActionRenameData()

        if unit.prepareExecution(actCntx, actData):
            try:
                getCurrentName = actData.getCurrentName()

                if "_" in getCurrentName: return getCurrentName

                originalName = actData.getOriginalName()

                if prefix: prefix += "_"
                newName = prefix + self.methodNameTransform(originalName)

                if not newName or newName == getCurrentName: return getCurrentName

                actData.setNewName(newName)
                bRlt = unit.executeAction(actCntx, actData)

            except Exception as e:
                print(e)


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

        self.Traversal()

    def Traversal(self):
        self.codeUnit = RuntimeProjectUtil.findUnitsByType(self.prj, ICodeUnit, False)
        if not self.codeUnit: return None

        for unit in self.codeUnit:
            if unit.getName().lower() != "bytecode": continue
            for mtd in unit.getMethods():
                if mtd: self.RenameItem(unit, mtd.getItemId(), mtd.getAddress(), mtd.getReturnType().getName())
            for fi in unit.getFields():
                if fi: self.RenameItem(unit, fi.getItemId(), fi.getAddress(), fi.getFieldType().getName())

        return None
