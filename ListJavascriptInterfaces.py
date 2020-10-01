# -*- coding: utf-8 -*-

# List methods with @JavascriptInterface annotation
# Author: 22s1mple

# Mutter:
#   If it weren't for the inability to respond click events, which has been confirmed by auditing the code differences
#   between StringsFragment, TableFragment and TreeFragment, StaticTreeDocument/StaticTableDocument should have been
#   used to display the results.
#
#   See also https://groups.google.com/g/jeb-decompiler/c/n1fo3Tid64c/m/0hXxifT7BQAJ

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
    IDexAnnotationItem
from com.pnfsoftware.jeb.client.api import IScript, IconType, ButtonGroupType
from com.pnfsoftware.jeb.core import Version, RuntimeProjectUtil
from com.pnfsoftware.jeb.core.units import UnitUtil


class ListJavascriptInterfaces(IScript):
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
        print('Unit: %s' % self.iiunit)

        self.dexunits = RuntimeProjectUtil.findUnitsByType(self.prj, IDexUnit, False)

        rows = []
        for unit in self.dexunits:
            assert isinstance(unit, IDexUnit)
            for clazz in unit.getClasses():
                assert isinstance(clazz, IDexClass)
                sourceIndex = clazz.getSourceStringIndex()
                clazzAddress = clazz.getAddress()

                DexAnnotationsDirectory = clazz.getAnnotationsDirectory()
                if not DexAnnotationsDirectory: continue
                for DexAnnotationForMethod in DexAnnotationsDirectory.getMethodsAnnotations():
                    assert isinstance(DexAnnotationForMethod, IDexAnnotationForMethod)

                    mtdidx = DexAnnotationForMethod.getMethodIndex()
                    mtd = unit.getMethod(mtdidx)

                    for DexAnnotationItem in DexAnnotationForMethod.getAnnotationItemSet():
                        assert isinstance(DexAnnotationItem, IDexAnnotationItem)

                        typeidx = DexAnnotationItem.getAnnotation().getTypeIndex()
                        typename = unit.getType(typeidx).getName()

                        if "JavascriptInterface" == typename:
                            row = [mtd.getSignature(), clazz.getName(), mtd.getName(), unit.getUid()]
                            rows.append(row)

        total = len(rows)
        print("Find %d methods with @JavascriptInterface annotation" % total)

        headers = ['Address', 'Class', 'Method']
        index = ctx.displayList('List methods with @JavascriptInterface annotation', None, headers, rows)
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
