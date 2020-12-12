# -*- coding: utf-8 -*-
#? shortcut=Mod1+Mod3+f

# Search for Java methods.
# Author: 22s1mple
# Note:
#
import re

from com.pnfsoftware.jeb.client.api import IScript
from com.pnfsoftware.jeb.client.api import IScript, IGraphicalClientContext
from com.pnfsoftware.jeb.core.events import JebEvent, J
from com.pnfsoftware.jeb.core.output import AbstractUnitRepresentation, UnitRepresentationAdapter
from com.pnfsoftware.jeb.core.units.code import ICodeUnit, ICodeItem
from com.pnfsoftware.jeb.core.units.code.java import IJavaSourceUnit, IJavaStaticField, IJavaNewArray, IJavaConstant, IJavaCall, IJavaField, IJavaMethod, IJavaClass
from com.pnfsoftware.jeb.core.actions import ActionTypeHierarchyData
from com.pnfsoftware.jeb.core.actions import ActionRenameData
from com.pnfsoftware.jeb.core.util import DecompilerHelper
from com.pnfsoftware.jeb.core.output.text import ITextDocument
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core.actions import ActionOverridesData
from com.pnfsoftware.jeb.core.units import UnitUtil, IInteractiveUnit
from com.pnfsoftware.jeb.core.units import UnitAddress
from com.pnfsoftware.jeb.core.actions import Actions, ActionContext, ActionCommentData, ActionRenameData, ActionXrefsData
from com.pnfsoftware.jeb.core import RuntimeProjectUtil, IUnitFilter, Version
from com.pnfsoftware.jeb.core.units import IUnit
from com.pnfsoftware.jeb.core.units.code.android.dex import DexPoolType, IDexClass, IDexAnnotationForMethod, \
    IDexAnnotationItem, IDexMethod
from com.pnfsoftware.jeb.client.api import IScript, IconType, ButtonGroupType
from com.pnfsoftware.jeb.core import Version, RuntimeProjectUtil
from com.pnfsoftware.jeb.core.units import UnitUtil

Template = """
Input search type (decimal integer):

1. Java native methods
2. Regex search for methods name
3. JavascriptInterfaces
4. Regex search for method annotations
5. registerReceiver
"""

custom_regex_pattern = None

class SearchJavaMethods(IScript):
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

        self.prj = ctx.getMainProject()
        self.iiunit = self.prj.findUnit(IInteractiveUnit)
        self.dexunits = RuntimeProjectUtil.findUnitsByType(self.prj, IDexUnit, False)

        defaultValue = '3'
        caption = 'Search Java Methods'
        message = Template
        input = ctx.displayQuestionBox(caption, message, defaultValue)
        if input == None:
            return
        try:
            chosen = int(input)
        except Exception as e:
            chosen = 1

        global custom_regex_pattern
        custom_regex_pattern = re.compile("JavascriptInterface")
        if chosen == 2:
            crp_caption = "Search Java methods by name pattern."
        elif chosen == 4:
            crp_caption = "Search Java methods by annotation pattern."

        if chosen in [2, 4]:
            message = "custom_regex_pattern = re.compile(input)"
            input = ctx.displayQuestionBox(crp_caption, message, "")
            if not input: return
            custom_regex_pattern = re.compile(input)

        print("Start search Java methods in dex . . .")

        rows = []
        print(len(self.dexunits))
        for unit in self.dexunits:
            assert isinstance(unit, IDexUnit)
            # print("unit") # for debug potential crash
            if unit.getName() != "Bytecode": continue

            for clazz in unit.getClasses():
                assert isinstance(clazz, IDexClass)
                sourceIndex = clazz.getSourceStringIndex()
                clazzAddress = clazz.getAddress()
                #if "" != clazzAddress: continue
                DexAnnotationsDirectory = clazz.getAnnotationsDirectory()
                if chosen in [1, 2]:
                    for mtd in clazz.getMethods():
                        assert isinstance(mtd, IDexMethod)
                        flag = mtd.getGenericFlags()
                        mtdname = mtd.getName()
                        if chosen == 1 and flag & ICodeItem.FLAG_NATIVE or chosen == 2 and regex_pattern_search(mtdname, custom_regex_pattern):
                            row = [mtd.getSignature(), clazz.getName(), mtd.getName(), unit.getUid()]
                            rows.append(row)
                elif chosen in [3, 4] and DexAnnotationsDirectory:
                    for DexAnnotationForMethod in DexAnnotationsDirectory.getMethodsAnnotations():
                        assert isinstance(DexAnnotationForMethod, IDexAnnotationForMethod)

                        mtdidx = DexAnnotationForMethod.getMethodIndex()
                        mtd = unit.getMethod(mtdidx)

                        for DexAnnotationItem in DexAnnotationForMethod.getAnnotationItemSet():
                            assert isinstance(DexAnnotationItem, IDexAnnotationItem)

                            typeidx = DexAnnotationItem.getAnnotation().getTypeIndex()
                            typename = unit.getType(typeidx).getName()

                            if regex_pattern_search(typename, custom_regex_pattern):
                                row = [mtd.getSignature(), clazz.getName(), mtd.getName(), unit.getUid()]
                                rows.append(row)


        out = list(set([x[0] for x in rows]))
        out.sort()
        for x in out: print(x)

        total = len(out)
        print("Search %d Java methods out." % total)

        headers = ['Address', 'Class', 'Method']
        index = ctx.displayList('Display Java methods search result', None, headers, rows)
        if index < 0:
            return

        sel = rows[index]
        addr, unit_id = sel[0], int(sel[3])

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


def regex_pattern_search(const_string, pattern):
    findObj = pattern.search(const_string)
    if findObj:
        return findObj.group()
    else:
        return None