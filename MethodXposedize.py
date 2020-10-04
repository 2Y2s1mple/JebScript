# -*- coding: utf-8 -*-
#? shortcut=Shift+P

# Get the JavaScript template of the method for Xposed hook.
# Author: 22s1mple
# Usage:
# - Position the caret on a method name in decompiled source view.
# - Press Shift+P

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

FMT_CLZ = 'Class<?> {class_name} = XposedHelpers.findClass("{class_path}", classLoader);'

FMT_NO_PARAMS = """XposedHelpers.findAndHookMethod("%s", classLoader, "%s", new XC_MethodHook() {
    @Override
    protected void beforeHookedMethod(MethodHookParam param) throws Throwable {
        super.beforeHookedMethod(param);
    }
    @Override
    protected void afterHookedMethod(MethodHookParam param) throws Throwable {
        super.afterHookedMethod(param);
    }
});"""

FMT_WITH_PARAMS = """XposedHelpers.findAndHookMethod("%s", classLoader, "%s", %s, new XC_MethodHook() {
    @Override
    protected void beforeHookedMethod(MethodHookParam param) throws Throwable {
        super.beforeHookedMethod(param);
    }
    @Override
    protected void afterHookedMethod(MethodHookParam param) throws Throwable {
        result = param.getResult();
        
        StringBuffer sb = new StringBuffer();
        sb.append("<" + method.getDeclaringClass() + " method=" + MethodDescription(param).toString() + ">\\n");
        try {
            for (int i = 0; i < args.length; i++) {
                sb.append("<Arg index=" + i + ">" + translate(args[i]) + "</Arg>\\n");
            }
        } catch (Throwable e) {
            sb.append("<Error>" + e.getLocalizedMessage() + "</Error>\\n");
        } finally {
            
        }

        try {
            sb.append("<Result>" + translate(result) + "</Result>\\n");
        } catch (Throwable e) {
            sb.append("<Error>" + e.getLocalizedMessage() + "</Error>\\n");
        } finally {
            sb.append("</" + method.getDeclaringClass() + " method=" + MethodDescription(param).toString() + ">\\n");
        }

        XposedBridge.log(sb.toString());
    }
});"""


class MethodXposedize(IScript):
    def calcItemVal(self, ItemId):
        # hack by @JEB Official: only work for 32-bit numbers, may be disabled in the future
        return str(hex(ItemId & 0xFFFFFFFF))[:-1].lower()

    def getItemOriginalName(self, viewName, itemId, viewAddress):
        actCntx = ActionContext(self.focusUnit, Actions.RENAME, itemId, viewAddress)
        actData = ActionRenameData()
        originalName = ""
        if self.focusUnit.prepareExecution(actCntx, actData):
            try:
                originalName = actData.getOriginalName()
                assert (viewName == actData.getCurrentName())
            except Exception as e:
                print(e)
        return originalName

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
        self.focusUnit = self.focusFragment.getUnit()  # JavaSourceUnit

        self.activeItem = self.focusFragment.getActiveItem()
        self.activeItemVal = self.calcItemVal(self.activeItem.getItemId())

        if not isinstance(self.focusUnit, IJavaSourceUnit):
            print('This script must be run within IJavaSourceUnit')
            return
        if not self.focusFragment:
            print("You Should pick one method name before run this script.")
            return

        viewMethodSig = self.focusFragment.getActiveAddress()

        self.isInitMethod = "<init>" in viewMethodSig and self.activeItem.toString().find('cid=CLASS_NAME') != 0

        clz, mtd = self.findMethodByItemId(viewMethodSig, self.activeItemVal)
        if not mtd:
            print('Could not find method: %s' % viewMethodSig)
            return

        paramList = [x.getAddress() for x in mtd.getParameterTypes()]

        currentClassName = clz.getName()
        currentClassPath = clz.getAddress()[1:-1].replace('/', '.')
        realClassName = self.getItemOriginalName(currentClassName, clz.getItemId(), viewMethodSig)
        realClassPath = currentClassPath.replace(currentClassName, realClassName, 1)

        currentMethodName = mtd.getName()

        realMethodName = self.getItemOriginalName(currentMethodName, mtd.getItemId(), viewMethodSig)
        realMethodSig = viewMethodSig.replace(currentMethodName, realMethodName, 1)

        print(FMT_CLZ.format(
            class_name=currentClassName,
            class_path=realClassPath
        ))

        if len(paramList) == 0:
            print FMT_NO_PARAMS % (
                realClassPath,
                realMethodName)
        else:
            print FMT_WITH_PARAMS % (
                realClassPath, realMethodName,
                ', '.join([self.toXposed(x) for x in paramList]))

    # copy from [@LeadroyaL/JebScript](https://github.com/LeadroyaL/JebScript/blob/master/FastXposed.py)
    def toXposed(self, param):
        depth = 0
        while param[depth] == '[':
            depth += 1
        # input: Ljava/lang/String; return: "java.lang.String"
        # input: [Ljava/lang/String; return: "java.lang.String[]"
        if param[-1] == ';':
            return '"' + param[depth + 1:-1].replace('/', '.') + "[]" * depth + '"'
        # input: I, return: int.class
        # input: [I, return: int[].class
        else:
            return self.basicTypeMap[param[depth]] + "[]" * depth + ".class"

    basicTypeMap = {
        'C': u'char',
        'B': u'byte',
        'D': u'double',
        'F': u'float',
        'I': u'int',
        'J': u'long',
        'L': u'ClassName',
        'S': u'short',
        'Z': u'boolean',
        '[': u'Reference',
    }

    def findMethodByItemId(self, mtdSig, itemId):
        self.codeUnit = RuntimeProjectUtil.findUnitsByType(self.prj, ICodeUnit, False)
        if not self.codeUnit: return None

        for unit in self.codeUnit:
            classes = unit.getClasses()
            if not classes: continue
            for c in classes:
                cAddr = c.getAddress()
                if not cAddr: continue
                if mtdSig.find(cAddr) == 0:
                    mtdlist = c.getMethods()
                    if not mtdlist: continue
                    for m in mtdlist:
                        if self.isInitMethod and m.getAddress() == mtdSig:
                            return c, m
                        elif itemId == self.calcItemVal(m.getItemId()):
                            return c, m
        return None
