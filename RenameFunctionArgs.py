# -*- coding: utf-8 -*-
#? shortcut=Shift+E

# Get the JavaScript template of the method for Frida hook.
# Author: 22s1mple
# Usage:
# - Position the caret on a method name in decompiled source view.
# - Press Shift+E

import string
import re
import collections
import sys
import urllib
from urlparse import urlparse
from com.pnfsoftware.jeb.client.api import IScript, IGraphicalClientContext, IClientContext
from com.pnfsoftware.jeb.core import RuntimeProjectUtil
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

class RenameFunctionArgs(IScript):
    def run(self, ctx):
        if not isinstance(self.ctx, IGraphicalClientContext):
            print ('This script must be run within a graphical client')
            return

        assert isinstance(ctx, IGraphicalClientContext) # for

        print(type(ctx))
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
             
        self.focusFragment = ctx.getFocusedFragment()
        self.focusUnit = self.focusFragment.getUnit()    # JavaSourceUnit
        if not isinstance(self.focusUnit, IJavaSourceUnit):
            print ('This script must be run within IJavaSourceUnit')
            return   

        self.JavaSourceUnit = RuntimeProjectUtil.findUnitsByType(self.prj, IJavaSourceUnit, False)
        for unit in self.JavaSourceUnit:
            ccllzz = unit.getClassElement()
            print(ccllzz)
            ### print(ccllzz.getSubElements())
            
            self.dfs(unit, ccllzz)
                

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
    
    basicTypeMap2 = {
        'char':'C',
        'byte':'B',
        'double':'D',
        'float':'F',
        'int':'I',
        'long':'J',
        'ClassName':'L',
        'short':'S',
        'boolean':'Z',
    }


    def dfs(self, unit, clz):
        innerclzz = clz.getInnerClasses()
        ### print(innerclzz)
        if innerclzz:
            for innerclz in innerclzz:
                self.dfs(unit, innerclz)

        ### print(mtd) 
        for mtd in clz.getMethods():
            id = 0
            for param in mtd.getParameters():
                ident = param.getIdentifier()
                original_name = ident.getName()
                if original_name != 'this':
                    debug_name = ident.getDebugName() # 没用，基本是None
                    effective_name = unit.getIdentifierName(ident) # 显示的（重命名后）名字
                    ### print('  Parameter: %s (debug name: %s) (effective: %s)' % (param, debug_name, effective_name))  #调试用
                    #if not effective_name and \
                    if not effective_name and \
                       not debug_name and \
                       original_name.startswith('arg'):

                        #if param.getType().isClassOrInterface(): # 过滤基础类型，其实没必要
                        t = str(param.getType())
                        x = t.rfind('.') + 1
                        if t in self.basicTypeMap2:
                            simplename = self.basicTypeMap2[t]
                        else:
                            simplename = t[x].lower() + t[x+1:]
                        
                        # 避免反编译代码中出现类似args0_byte[][v2]这样的歧义，
                        # 将变量名中的括号全部替换，"A" for Array
                        simplename = simplename.replace("[]", "A")

                        effective_name = 'args%d_%s' % (id, simplename)
                        id += 1
                        ### print('  -> Renaming to: %s' % effective_name)
                        unit.setIdentifierName(ident, effective_name) # 官网隐藏API
            