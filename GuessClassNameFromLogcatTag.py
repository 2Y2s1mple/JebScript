# -*- coding: utf-8 -*-

# Guess class name from original source or potential Logcat Tag. And list top 20 possible Logger/LogUtil classes.
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


def checkClassName(rawstr):
    if rawstr and any([c.islower() for c in rawstr]):
        return re.match(r'^[A-Z]+[0-9a-zA-Z]*$', rawstr, flags=0)
    else:
        return None

Black_list = [
    "Ljava/lang/String;",
    "Landroid/text/TextUtils;",
    "Ljavax/net/ssl/SSLContext;",
    "Ljava/util/regex/Pattern;",
]

Conflict_clzname_pool = None
Possible_Logger = None
Possible_Clzname = None

class GuessClassNameFromLogcatTag(IScript):
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

        self.Dexunits = RuntimeProjectUtil.findUnitsByType(self.prj, IDexUnit, False)

        for unit in self.Dexunits:
            assert isinstance(unit, IDexUnit)
            global Conflict_clzname_pool, Possible_Logger, Possible_Clzname
            Possible_Logger = Counter()
            Conflict_clzname_pool = Counter()
            for clz in unit.getClasses():
                assert isinstance(clz, IDexClass)
                clzSig = clz.getSignature()

                sourceIndex = clz.getSourceStringIndex()
                clazzAddress = clz.getAddress()

                if sourceIndex == -1 or '$' in clazzAddress: # Do not rename inner class
                    self.guess_classname_from_logcat_tag(unit, clz)
                    continue

                sourceStr = str(unit.getString(sourceIndex))
                if not sourceStr.strip() or sourceStr.lower() == "proguard" or sourceStr.lower() == "sourcefile":
                    self.guess_classname_from_logcat_tag(unit, clz)
                    continue

                x = sourceStr.rfind(".")
                if x > 0: sourceStr = sourceStr[:x]  # .java .kt
                sourceStr = sourceStr.replace(".", "_").replace("-", "_")

                if clz.getName(True) != sourceStr:
                    self.comment_class(unit, clz, clz.getName(True))  # Backup origin clazz name to comment
                    self.rename_class(unit, clz, sourceStr)  # Rename to source name

            print(u"\nPossible logger class: ")
            for x, t in Possible_Logger.most_common(20):
                print("{:<8d}".format(t) + x)

    def guess_classname_from_logcat_tag(self, unit, clazz):
        if "$" in clazz.getSignature(): return
        global Conflict_clzname_pool, Possible_Logger, Possible_Clzname
        Possible_Clzname = Counter()
        for mtd in clazz.getMethods():
            assert isinstance(mtd, IDexMethod)
            dexCodeItem = mtd.getData().getCodeItem()
            if not dexCodeItem: continue
            insts = dexCodeItem.getInstructions()

            register_map = {}
            for inst in insts:
                assert isinstance(inst, IDalvikInstruction)
                # Get the Dalvik instruction opcode, as defined in DalvikInstructionOpcodes.
                # https://developer.android.com/reference/dalvik/bytecode/Opcodes.html
                # com.pnfsoftware.jeb.core.units.code.android.dex.DalvikInstructionOpcodes
                if inst.getOpcode() in [26, 27]:  # OP_CONST_STRING & OP_CONST_STRING_JUMBO
                    pl = inst.getParameters()
                    idx = pl[1].getValue()
                    register_map[int(pl[0].getValue())] = idx

                if repr(inst) == "invoke-static" and register_map:
                    pl = inst.getParameters()

                    if len(pl) != 3 or pl[1].getType() != 0:
                        register_map = {}
                        continue

                    call_mtd = unit.getMethod(pl[0].getValue())
                    if not call_mtd or any([call_mtd.getSignature().startswith(x) for x in Black_list]):
                        register_map = {}
                        continue

                    u = register_map.get(pl[1].getValue())
                    if not u:
                        register_map = {}
                        continue

                    try:
                        name = str(unit.getString(u))
                    except Exception as e:
                        register_map = {}
                        continue

                    if checkClassName(name):
                        Possible_Clzname.update([name])
                        posslogername = call_mtd.getSignature().split("->")[0]
                        Possible_Logger.update([posslogername])
                    register_map = {}

        for name, times in Possible_Clzname.most_common(1):  # Simply pick the highest frequency one
            suffix = str(Conflict_clzname_pool[name])
            if suffix == "0": suffix = ""
            guess_clz_name = name + suffix
            # print('rename %s to %s success!' % (clazz.getAddress(), guess_clz_name))
            original_name = self.rename_class(unit, clazz, guess_clz_name)
            self.comment_class(unit, clazz, original_name)
            Conflict_clzname_pool.update([name])

    def rename_class(self, unit, originClazz, sourceName):
        actCtx = ActionContext(unit, Actions.RENAME, originClazz.getItemId(), originClazz.getAddress())
        actData = ActionRenameData()
        actData.setNewName(sourceName)

        if unit.prepareExecution(actCtx, actData):
            try:
                originalName = actData.getOriginalName()
                if len(originalName) > 10:  # Skip for general cases: already have meaningful class name
                    return sourceName
                result = unit.executeAction(actCtx, actData)
                if result:
                    print('rename %s to %s success!' % (originalName, originClazz.getAddress()))
                else:
                    print('rename to %s failed!' % sourceName)
            except Exception, e:
                print (Exception, e)

        return originalName

    def comment_class(self, unit, originClazz, commentStr):
        actCtx = ActionContext(unit, Actions.COMMENT, originClazz.getItemId(), originClazz.getAddress())
        actData = ActionCommentData()
        actData.setNewComment(commentStr)

        if unit.prepareExecution(actCtx, actData):
            try:
                result = unit.executeAction(actCtx, actData)
            except Exception, e:
                print (Exception, e)

