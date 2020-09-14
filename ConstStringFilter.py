# -*- coding: utf-8 -*-
#?shortcut=Mod1+R

# Search & filter constant strings in dex.
# Author: 22s1mple
# Usage:
# - Step 1: Replace <string_filters> with your own implement if needed.
# - Step 2: Press Ctrl/Command + r 


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

import base64
import string
import datetime
import json
import time


class ConstStringFilter(IScript):
    CSF_KEY = 'CONST_STRING_FILTERED'

    def run(self, ctx):
        if ctx.getSoftwareVersion() < Version.create(3, 8):
            print('You need JEB 3.8+ to run this script!')
            return

        if not isinstance(ctx, IGraphicalClientContext):
            print('This script must be run within a graphical client')
            return

        print("Start filtering Constant String in dex . . .")

        prj = ctx.getMainProject()
        csf_json = {}
        cnt = 0
        dexUnits = ctx.getMainProject().findUnits(IDexUnit)

        for dexUnit in dexUnits:
            totalnum = dexUnit.getStringCount()
            unit_id = str(dexUnit.getUid())
            unit_name = dexUnit.getName()
            unit_path = UnitUtil.buildFullyQualifiedUnitPath(dexUnit)
            
            
            for iCodeString in dexUnit.getStrings():
                const_str = iCodeString.getValue()
                real_str = string_filters(const_str)

                if real_str:
                    id = iCodeString.getItemId()
                    ix = iCodeString.getIndex()
                    xrefs = dexUnit.getCrossReferences(DexPoolType.STRING, ix)
                    for xref in xrefs: 
                        addr = xref.getInternalAddress()
                        if addr:
                            ocs_map = csf_json.get(unit_id)
                            if ocs_map == None:
                                ocs_map = {}
                                csf_json[unit_id] = ocs_map

                            ocs_map[cnt] = [const_str, real_str, addr]
                            cnt += 1

        prj.setData(ConstStringFilter.CSF_KEY, json.dumps(csf_json), True)
        print("Search complete. %d string(s) are filtered out." % cnt)
        #print(csf_json)




def check_standard_base64(const_string):
    STANDARD_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
    MESS_SYMBOL_SET = set(string.printable[62:]) 
    result = None

    if len(const_string) % 4 == 0 and set(const_string).issubset(STANDARD_ALPHABET):
        try:
            result = base64.decodestring(const_string).decode("utf-8")
        except:
            return None
    
        if len(const_string) < 9:
            if len(MESS_SYMBOL_SET & set(const_string)) < len(MESS_SYMBOL_SET & set(result)):
                return None
        
        if len(result) < 6 and not "=" in const_string:
            if set(result).issubset(STANDARD_ALPHABET):
                return None

    return result

def string_filters(const_string):
    return check_standard_base64(const_string)