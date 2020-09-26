# -*- coding: utf-8 -*-

# Print the decompiled Java abstract syntax tree.
# Author: 22s1mple


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
from com.pnfsoftware.jeb.core.output import AbstractUnitRepresentation, UnitRepresentationAdapter
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

class PrintJavaAST(IScript):
    def run(self, ctx):
        self.ctx = ctx

        if not isinstance(self.ctx, IGraphicalClientContext):
            print ('This script must be run within a graphical client')
            return

        engctx = ctx.getEnginesContext()
        if not engctx:
            print('Back-end engines not initialized')
            return

        projects = engctx.getProjects()
        if not projects:
            print('There is no opened project')

        self.prj = projects[0]

        self.codeUnits = RuntimeProjectUtil.findUnitsByType(self.prj, ICodeUnit, False)
        if not self.codeUnits:
            return

        self.JavaSourceUnit = RuntimeProjectUtil.findUnitsByType(self.prj, IJavaSourceUnit, False)
        self.DexDecompilerUnits = RuntimeProjectUtil.findUnitsByType(self.prj, IDexDecompilerUnit, False)

        self.focusFragment = ctx.getFocusedFragment()
        self.focusUnit = self.focusFragment.getUnit()

        if not isinstance(self.focusUnit, IJavaSourceUnit):
            print ('This script must be run within IJavaSourceUnit')
            return

        clz = self.focusUnit.getClassElement()
        self.dfs(self.focusUnit, clz)


    def dfs(self, unit, clz):
        innerclzz = clz.getInnerClasses()
        for innerclz in innerclzz:
            self.dfs(unit, innerclz)

        for mtd in clz.getMethods():
            assert isinstance(mtd, IJavaMethod)
            print("Method: " + mtd.getSignature())
            block = mtd.getBody()
            for i in range(block.size()):
                self.viewElement(block.get(i), 0)

    def viewElement(self, statement, depth):
        print("    "*depth + repr(statement).strip() + " [" + repr(statement.getElementType()) + "]")
        for sub in statement.getSubElements():
            self.viewElement(sub, depth+1)

