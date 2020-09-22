# -*- coding: utf-8 -*-
# ?shortcut=Mod1+B

# Restore class fields name and Getters/Setters name from toString() return.
# Author: 22s1mple

import os
import re
from com.pnfsoftware.jeb.client.api import IScript
from com.pnfsoftware.jeb.core.units.code.java import IJavaInstanceField, IJavaElement, IJavaReturn, \
    IJavaArithmeticExpression, IJavaConditionalExpression, IJavaPredicate, IJavaAssignment
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

class RestoreBeanFromtoString(IScript):
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

        for unit in self.JavaSourceUnit:
            clz = unit.getClassElement()
            self.dfs(unit, clz)
            unit.notifyListeners(JebEvent(J.UnitChange))

    def dfs(self, unit, clz):
        innerclzz = clz.getInnerClasses()
        for innerclz in innerclzz:
            self.dfs(unit, innerclz)

        for mtd in clz.getMethods():
            assert isinstance(mtd, IJavaMethod)
            if mtd.getName() == "toString" and str(mtd.getReturnType()) == "java.lang.String":
                print("Find " + mtd.getSignature())
                possibleClzName = self.refactorUseToString(unit, mtd.getBody())
                self.rebuildGetterAndSetters(clz)
                if possibleClzName:
                    self.renameItembySig("Class", clz.getSignature(), possibleClzName)


    def rebuildGetterAndSetters(self, clz):
        assert isinstance(clz, IJavaClass)
        for mtd in clz.getMethods():
            if mtd.getBody().size() != 1: return
            stmt = mtd.getBody().get(0)
            if isinstance(stmt, IJavaReturn):
                rightexp = stmt.getExpression()
                if isinstance(rightexp, IJavaInstanceField):
                    #we find a "getter" method, rename the method name
                    name = rightexp.getField().getName()
                    tagName = rightexp.getField().getTags()["name"]
                    #use tagName generated from toString if applicable, or use original name instead
                    targetName = tagName if tagName else name
                    self.renameItembySig("Method", mtd.getSignature(), "get" + targetName.capitalize())
            elif isinstance(stmt, IJavaAssignment):
                leftexp = stmt.getLeft()
                if isinstance(leftexp, IJavaInstanceField):
                    #we find a "setter" method, rename the method name
                    name = leftexp.getField().getName()
                    tagName = leftexp.getField().getTags()["name"]
                    targetName = tagName if tagName else name
                    self.renameItembySig("Method", mtd.getSignature(), "set" + targetName.capitalize())


    def refactorUseToString(self, junit, block):
        possibleClzName = None
        if block.size() >= 0 and isinstance(block.get(0), IJavaReturn):
            #exp is the return expression
            exp = block.get(0).getExpression()
            assert isinstance(exp, IJavaArithmeticExpression)
            assert isinstance(junit, IJavaSourceUnit)
            while True:
                right = exp.getRight()

                #filter out cases like "test: " + this.d + " ]", remove trailing strings
                #e.g. return "Entity [info="+this.a+"aaa"+"bbb"
                #notice exp.getRight() here returns "bbb", exp.getLeft() returns "Entity [info="+this.a+"aaa"
                while isinstance(right, IJavaConstant):
                    exp = exp.getLeft()
                    # todo check if right is empty str
                    right = exp.getRight()

                right = exp.getRight() # field
                left = exp.getLeft()

                if isinstance(left, IJavaConstant):
                    #we have reached the left end of whole return expression
                    firstFieldName = getUsefulContent(str(left))
                    possibleClzName = getUsefulContent(str(left), False)
                    if possibleClzName == firstFieldName:
                        possibleClzName = None

                    self.renamePossibleExpressionWithStr(right, firstFieldName)
                    break
                else:
                    #doing left traversal
                    #e.g. return {"Entity [info="+this.a+}(left.left)"value="(left.right)+this.b(right)
                    rawstr = str(left.getRight())
                    # print(rawstr) # for debug getUsefulContent e.g. "{\n\n\t\"appId\":\""
                    fieldName = getUsefulContent(rawstr)
                    self.renamePossibleExpressionWithStr(right, fieldName)
                    exp = left.getLeft()

        return possibleClzName


    def renameItembySig(self, codeType, signature, newName):
        x = None
        for cu in self.codeUnits:
            if codeType == "Field":
                x = cu.getField(signature)
            elif codeType == "Method":
                x = cu.getMethod(signature)
            elif codeType == "Class":
                x = cu.getClass(signature)
            else:
                raise Exception("execute renameItembySig with unknown codeType!")
            if x:
                break

        if not x:
            return

        itemId = x.getItemId()
        itemAddress = x.getAddress()
        itemSig = x.getSignature()

        actCntx = ActionContext(cu, Actions.RENAME, itemId, itemAddress)
        actData = ActionRenameData()

        if cu.prepareExecution(actCntx, actData):
            try:
                originalName = actData.getOriginalName()
                getCurrentName = actData.getCurrentName()

                if newName == getCurrentName:
                    return newName
                actData.setNewName(newName)
                bRlt = cu.executeAction(actCntx, actData)
                if not bRlt:
                    print(u'Failure Action %s' % itemAddress)
                else:
                    pass
            except Exception as e:
                print(e)
        return newName

    def renamePossibleExpressionWithStr(self, exp, name):
        if not name: return
        if isinstance(exp, IJavaInstanceField) or isinstance(exp, IJavaStaticField):
            self.renameItembySig("Field", exp.getField().getSignature(), name)
            print("rename from " + exp.getField().getSignature() + " to " + name)
            exp.getField().addTag("name", name)
        elif isinstance(exp, IJavaCall) or isinstance(exp, IJavaConditionalExpression) or isinstance(exp, IJavaPredicate): #consider this.a.toString(), need extract this.a
            targetFields = filter(lambda s: isinstance(s, IJavaInstanceField), exp.getSubElements())
            if len(targetFields) >= 1:
                self.renamePossibleExpressionWithStr(targetFields[0], name)
        else:
            #whoops, what's that
            pass

def getUsefulContent(s, last=True):
    p = r"\w{2,}"
    findObj = re.findall(p, s)
    if findObj:
        if last:
            return findObj[-1]
        else:
            return findObj[0]
    else:
        return None
