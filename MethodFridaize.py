# -*- coding: utf-8 -*-
# ? shortcut=Shift+F

# Get the JavaScript template of the method for Frida hook.
# Author: 22s1mple
# Usage:
# - Position the caret on a method name in decompiled source view.
# - Press Shift+F

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
from com.pnfsoftware.jeb.core.units.code import ICodeUnit, ICodeItem, ICodeMethod, ICodeClass, ICodePackage
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

FMT_OBJ_CLZ = 'android hooking watch class {class_path} --dump-args --dump-backtrace --dump-return'
FMT_OBJ_MTD = 'android hooking watch class_method {class_path}{method_name} --dump-args --dump-backtrace --dump-return'
FMT_CLZ = 'var {class_name} = Java.use("{class_path}")'
FMT_SIGNOTE = """// {original_method_sig}
// {mnemonic_method_sig}"""
FMT_MTD = """{class_name}{method_name} // {custom_name}
.overload({param_list}) 
.implementation = function() {{
    return PrintStackAndCallMethod(this, arguments)
}};"""


class MethodFridaize(IScript):
    def calcItemVal(self, ItemId):
        # tricks learned from @JEB Official: only work for 32-bit numbers, may be disabled in the future
        return str(hex(ItemId & 0xFFFFFFFF))[:-1].lower()

    def getItemOriginalName(self, item):
        actCntx = ActionContext(self.focusUnit, Actions.RENAME, item.getItemId(), item.getSignature())
        actData = ActionRenameData()
        originalName = ""
        if self.focusUnit.prepareExecution(actCntx, actData):
            try:
                originalName = actData.getOriginalName()
                assert (item.getName() == actData.getCurrentName())
            except Exception as e:
                print(e)
        return originalName

    def methodNameTransform(self, name, isfrida=True):
        # Non-ASCII
        try:
            if self.isInitMethod or not name:
                result = ".$init"
            else:
                result = "." + bytes(name)
        except UnicodeEncodeError as e:
            # print(sys.version) 看到Jython 还是2.7， 无法import urllib.parse，先用py2写法凑合，后面研究下https://github.com/justfoxing/jfx_bridge_jeb
            result = urllib.quote(name.encode("utf-8"))
            if isfrida:
                result = '[decodeURIComponent("' + result + '")]'
        except Exception as e:
            print(e)

        return result

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
        self.codeUnit = RuntimeProjectUtil.findUnitsByType(self.prj, ICodeUnit, False)

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

        assert isinstance(mtd, ICodeMethod)

        paramList = []
        for x in mtd.getParameterTypes():
            if ";" in str(x.getAddress()):
                argType = self.getRealClassSig(x.getImplementingClass())
            else:
                argType = x.getAddress()
            paramList.append(argType)

        currentClassName = clz.getName()
        currentClassPath = clz.getAddress()[1:-1].replace('/', '.')
        realClassName = self.getItemOriginalName(clz)
        realClassSig = self.getRealClassSig(clz)
        realClassPath = realClassSig[1:-1].replace('/', '.')

        currentMethodName = mtd.getName()
        commentMethodName = self.methodNameTransform(currentMethodName, False)
        realMethodName = self.getItemOriginalName(mtd)


        print(FMT_OBJ_CLZ.format(
            class_path=realClassPath
        ))

        print(FMT_OBJ_MTD.format(
            class_path=realClassPath,
            method_name=self.methodNameTransform(realMethodName)
        ))

        print(FMT_CLZ.format(
            class_name=currentClassName,
            class_path=realClassPath
        ))

        print(FMT_SIGNOTE.format(
            original_method_sig=realClassPath + self.methodNameTransform(realMethodName),
            mnemonic_method_sig=viewMethodSig
        ))

        print(FMT_MTD.format(
            class_name=currentClassName,
            method_name=self.methodNameTransform(realMethodName),
            custom_name=commentMethodName,
            param_list=','.join([self.toFrida(x) for x in paramList]),
        ))

    # @LeadroyaL 大佬这段类型处理足以覆盖90%的日常场景，嵌套数组可以参看下面链接修改，或者直接看frida报错
    # https://github.com/frida/frida-java-bridge/blob/master/lib/types.js
    def toFrida(self, param):
        # input: [I, return: "[I"
        # input: [Ljava/lang/String; return: "[Ljava.lang.String;"
        if param[0] == '[':
            return '"' + param.replace('/', '.') + '"'
        # input: Ljava/lang/String; return: "java.lang.String"
        # input: I, return: "int"
        else:
            if param[-1] == ';':
                return '"' + param[1:-1].replace('/', '.') + '"'
            else:
                return '"' + self.basicTypeMap[param[0]] + '"'

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

    def getRealClassSig(self, icodeClass):
        assert isinstance(icodeClass, ICodeClass)
        OclzSig = str(icodeClass.getSignature())
        realClassNameList = [ self.getItemOriginalName(icodeClass) ]

        while True:
            r = OclzSig.rfind("$")
            if r == -1: break
            OclzSig = OclzSig[:r] + ";"
            ObjClz = self.findClassBySig(OclzSig)
            realClassNameList.append(self.getItemOriginalName(ObjClz))

        P = icodeClass.getPackage()
        assert isinstance(P, ICodePackage)
        realPackageNameList = []
        while not P.isRootPackage():
            realname = self.getItemOriginalName(P)
            realPackageNameList.append(realname)
            P = P.getParentPackage()

        realClassSig = "L" + "/".join(realPackageNameList[::-1]) + "/" + "$".join(realClassNameList[::-1]) + ";"
        return realClassSig

    def findClassBySig(self, OclzSig):
        if not self.codeUnit: return None
        for unit in self.codeUnit:
            Clz = unit.getClass(OclzSig)
            if Clz: return Clz
        return None
