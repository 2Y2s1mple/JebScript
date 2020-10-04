# -*- coding: utf-8 -*-
#? shortcut=Mod1+r

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
from com.pnfsoftware.jeb.core import RuntimeProjectUtil, IUnitFilter, Version
from com.pnfsoftware.jeb.core.units import IUnit
from com.pnfsoftware.jeb.core.units.code.android.dex import DexPoolType

import base64
import string
import datetime
import json
import time
import re

Template = """
Input filter flag (decimal integer):

001 - 0x01. Completely URI 
002 - 0x02. Bundle name
004 - 0x04. File Path
008 - 0x08. URL parameters
016 - 0x10. Standard Base64
032 - 0x20. Common infos
064 - 0x30. Input regex pattern  
128 - 0x40. All constant Strings
"""

custom_regex_pattern = None
class ConstStringFilter(IScript):
    CSF_KEY = 'CONST_STRING_FILTERED'

    def run(self, ctx):
        if ctx.getSoftwareVersion() < Version.create(3, 8):
            print('You need JEB 3.8+ to run this script!')
            return

        if not isinstance(ctx, IGraphicalClientContext):
            print('This script must be run within a graphical client')
            return

        defaultValue = '4'
        caption = 'Input filter Flag:'
        message = Template
        input = ctx.displayQuestionBox(caption, message, defaultValue)
        if input == None:
            return
        try:
            choose = int(input)
        except Exception as e:
            choose = 1

        global custom_regex_pattern
        if choose & 64:
            crp_caption = "Input your regex pattern for filter."
            message = "custom_regex_pattern = re.compile(input)"
            input = ctx.displayQuestionBox(crp_caption, message, "")
            if not input: return
            custom_regex_pattern = re.compile(input)

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
                real_str = string_filters(choose, const_str)

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
        print("Search complete. %d string(s) are filtered out. Press Ctrl + Alt + r show result." % cnt)
        # print(csf_json)


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


completely_url_pattern = re.compile(r'\w*://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
bundle_name_pattern = re.compile(r'[a-zA-Z]+[0-9a-zA-Z_]*(\.[a-zA-Z]+[0-9a-zA-Z_]*)*\.[a-zA-Z]+[0-9a-zA-Z_]*(\$[a-zA-Z]+[0-9a-zA-Z_]*)*')
file_path_pattern = re.compile(r"\/(\w+\/?)+")
url_parameter_pattern = re.compile(r"(&?(\w+)=(\w*))+")

log_comment_pattern = re.compile(r"[\u4E00-\u9FA5A-Za-z0-9_]+")
phone_pattern = re.compile(r"(13[0-9]|14[5|7]|15[0|1|2|3|5|6|7|8|9]|18[0|1|2|3|5|6|7|8|9])\d{8}")
ip_pattern = re.compile(r"\d+\.\d+\.\d+\.\d+")




def regex_pattern_search(const_string, pattern):
    findObj = pattern.search(const_string)
    if findObj:
        return findObj.group()
    else:
        return None

def common_infos_search(const_string):
    ps = [
        log_comment_pattern,
        phone_pattern,
        ip_pattern
    ]
    for p in ps:
        findObj = p.search(const_string)
        if findObj:
            return findObj.group()

    return None

def string_filters(flag, const_string):
    """
    Input filter flag (decimal integer):
    001 - 0x01. Completely URI
    002 - 0x02. Bundle name
    004 - 0x04. File Path
    008 - 0x08. URL parameters
    016 - 0x10. Standard Base64
    032 - 0x20. Common infos
    064 - 0x30. Input regex pattern
    128 - 0x40. All constant Strings
    """
    result = None
    if flag & 128:
        return const_string

    global custom_regex_pattern

    if not result and flag & 1:
        result = regex_pattern_search(const_string, completely_url_pattern)
    elif not result and flag & 2:
        result = regex_pattern_search(const_string, bundle_name_pattern)
    elif not result and flag & 4:
        result = regex_pattern_search(const_string, file_path_pattern)
    elif not result and flag & 8:
        result = regex_pattern_search(const_string, url_parameter_pattern)
    elif not result and flag & 16:
        result = check_standard_base64(const_string)
    elif not result and flag & 32:
        result = common_infos_search(const_string)
    elif not result and flag & 64:
        result = regex_pattern_search(const_string, custom_regex_pattern)
    else:
        result = None

    return result

