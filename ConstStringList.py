# -*- coding: utf-8 -*-
#? shortcut=Mod1+Mod3+R

# Show Dex Constant String(s) filter result 
# Author: 22s1mple
# Usage:
# - Step 1: Press Ctrl/Command + r to run ConstStringFilter.py once.
# - Step 2: Press Ctrl/Command + Alt + r

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
from com.pnfsoftware.jeb.core.units import UnitUtil
from com.pnfsoftware.jeb.core.units import UnitAddress
from com.pnfsoftware.jeb.core.actions import Actions, ActionContext, ActionCommentData, ActionRenameData, ActionXrefsData
from com.pnfsoftware.jeb.core import RuntimeProjectUtil, IUnitFilter, Version
from com.pnfsoftware.jeb.core.units import IUnit
from com.pnfsoftware.jeb.core.units.code.android.dex import DexPoolType
from com.pnfsoftware.jeb.client.api import IScript, IconType, ButtonGroupType
from com.pnfsoftware.jeb.core import Version, RuntimeProjectUtil
from com.pnfsoftware.jeb.core.units import UnitUtil
from ConstStringFilter import ConstStringFilter

import base64
import string
import datetime
import json
import time


class ConstStringList(IScript):
    def run(self, ctx):
        if ctx.getSoftwareVersion() < Version.create(3, 8):
            print('You need JEB 3.8+ to run this script!')
            return

        if not isinstance(ctx, IGraphicalClientContext):
            print('This script must be run within a graphical client')
            return

        prj = ctx.getMainProject()
        csf_str = prj.getData(ConstStringFilter.CSF_KEY)
        if not csf_str:
            ctx.displayMessageBox(
                'Constant String List', 'No recorded result yet!\nPlease run ConstStringFilter.py first.', IconType.INFORMATION, None)
            return

        csf_json = json.loads(csf_str)
        # print('Current Filter result (%d): %s' % (len(csf_json), csf_json))

        headers = ['Address', 'Constant String', 'Comment']
        rows = []
        for unit_id, ocs_map in csf_json.items():
            for ocs, e in ocs_map.items():
                const_str, real_str, addr = e
                # note we're appended uid, but it won't be displayed (per the header's spec above, which specifies 6 columns - not 7)
                rows.append([addr, const_str, real_str, unit_id]) # e + uid

        index = ctx.displayList('Constant String filter results', 'Note: The <Comment> column may have the corresponding decoded/decrypted result.', headers, rows)
        if index < 0:
            return

        sel = rows[index]
        addr, ocs, cmt, unit_id =  sel[0], sel[1], sel[2], int(sel[3])
        # print('Selected: unit_id=%d,ConstStr=%s,addr=%s' % (uid, ocs, addr))

        unit = RuntimeProjectUtil.findUnitByUid(prj, unit_id)
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
            if not unit.getComment(addr) and cmt: 
                unit.setComment(addr, cmt)

