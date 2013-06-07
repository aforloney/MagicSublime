from magicsubl import ms as MS
import xml.etree.ElementTree as ET
import re
import sublime
import sublime_plugin

# MagicSublime  by Mark Battersby

# Sublime Text API can be found at:
#  http://www.sublimetext.com/docs/2/api_reference.html

# Frequently used and global variables:
#   V = shorthand for self.view, a pointer to the currently active file
#   item = region containing the entity on which the user invoked Magic command
#   settings = a pointer to the MagicSublime settings file


# Global maps
scope = {
    'entity.name.section.macro.title': 'Macro Title',
    'entity.name.function.macro.call': 'Macro Call',
    'variable.other.local': 'Local Variable',
    'storage.temp.data.def': 'Data Definition',
    'support.constant.data.def': 'Data Definition',
    'support.function.npr.macro': 'NPR Macro',
    'entity.function.program.call': 'Procedure'
}

functions = {
    # 'Macro Title': macroTitle,
    # 'Macro Call': macroCall,
    # 'Local Variable': local,
    # 'Data Definition': dataDef,
    # 'NPR Macro': nprMacro,
    # 'Procedure': procedure
}


def findInXML(root, item):
    """Search elements under root for one with the name item."""
    for i in root:
        try:
            name = i.find('name').text
            if name == item:
                return i
        except(NameError, AttributeError):
            print('Warning: Unexpected values in XML file.')


def macroTitle(cursor):
    """Jump to an equivalent macro call.

    When the user invokes the Magic command from a macro call, its position is
    saved in the settings file. If the user jumped to this macro title from
    that saved macro call, jump back to that call. If they didn't jump to this
    title from a call, jump to the first macro call in the procedure."""

    item = V.substr(V.word(cursor))    # The item on which Magic was invoked
    settings = sublime.load_settings('MagicSublime.sublime-settings')

    lastMacro = settings.get('last_macro', sublime.Region(-1))
    if item == V.substr(V.word(lastMacro)):
        jump = sublime.Region(lastMacro,
                              lastMacro + len(item))
    else:
        jump = V.find('@' + item + '[^.]', 0)
        # Find a macro call (@) with a non-period char following it
        if jump is None:
            sublime.status_message("@%s not found") % item
        else:
            jump = V.find(item, jump.begin())

    if jump is not None:
        V.sel().clear()
        V.sel().add(jump)
        V.show_at_center(jump)


def macroCall(cursor):
    """Jump to the macro definition.

    When the user invokes the Magic command from a macro call, its position is
    saved in the settings file (see: macroTitle). This allows it to be quickly
    jumped-back-to once the macro has been reviewed. The macro definition is
    then found and its header highlighted."""

    item = V.substr(V.word(cursor))
    settings = sublime.load_settings('MagicSublime.sublime-settings')
    settings.set('last_macro', int(V.word(cursor).begin()))  # Note pos of call

    try:
        jump = V.find('\n#?' + item + '\n', 0)
        # Macro title will have \n and optional # before, and \n after
        jump = V.find(item, jump.begin())
        # But don't highlight any of those characters

        V.sel().clear()
        V.sel().add(jump)
        V.show_at_center(jump)
        sublime.save_settings('MagicSublime.sublime-settings')
        # If successful, save the macro call position
    except(AttributeError):
        sublime.status_message("@%s not found" % item)


def local(cursor):
    """Show top-of-procedure documentation associated with a local variable.

    If there is documentation for the variable in the procedure header, it
    will be displayed in the footer window frame."""
    pass


def dataDef(cursor):
    """Show the ELE documentation for a given data element or segment.

    The source of the documentation is
    MagicSublime/lib/Data Definitions/[app]/[dpm].xml.
    This file is generated via the Z.zcus.export.data.to.xml procedure which
    can be found in the CUS2/IMPPROG56 directory.

    This documentation should be searchable, so that any element or segment
    in it can lead to more documentation."""

    def getDpm(item):
        """Pull the DPM from the item, or infer it from the file path.

        If the selected item doesn't include the DPM, the DPM is the same as
        that of the procedure. This can be pulled from the filepath,
        ie. '/EDM/PAT/depart.npr' should return 'EDM.PAT'

        The only exception to this is the 'Z' DPM, which is the only one that
        doesn't have two parts (...I think)"""
        dpm = re.sub('[a-z]*', '', item).rstrip('.')  # Better way to do this?
        if dpm is '':
            f = str(V.file_name()).split('/')  # \ for Windows?
            if f[len(f) - 2] == 'Z':
                dpm = 'Z'
            else:
                dpm = f[len(f) - 3] + '.' + f[len(f) - 2]
        return dpm

    def generateEleDoc(root):
        """Grab all elements under root and make into pretty documentation."""
        msg = ""
        element = dpm + '.' + root.find('name').text
        local = root.find('local').text
        physical = root.find('').text
        pointer = root.find('pointer').text
        dataType = root.find('type').text
        length = root.find('length').text

        if element is not None:
            msg = msg + "Element        %s\n" % element  # content at col 16
        if local is not None:
            msg = msg + "Local          %s\n" % local
        if physical is not None:
            msg = msg + "Physical       %s\n" % physical
        msg = msg + '\n'
        if pointer is not None:
            msg = msg + "Pointer        %s\n" % pointer
        if dataType is not None:
            msg = msg + "Data Type      %s\n" % dataType
        if length is not None:
            msg = msg + "Length         %s\n" % length
        return msg

    def generateSegDoc(root):
        """Grab all elements under root and make into pretty documentation."""
        pass  # --generate doc for data segment

    item = V.substr(V.word(cursor))
    dpm = getDpm(item)
    item = item.lstrip(dpm)  # If the item contained the DPM, remove it.
    filepath = (sublime.packages_path() +
                '/MagicSublime/lib/Data Definitions' +
                dpm + '.xml')
    root = ET.parse(filepath).getroot()

    # Try first to find a segment with the name item
    seg = findInXML(root, item)
    if seg is not None:
        msg = generateSegDoc(seg)
    else:
        for segment in root:
            elements = segment.find('elements')
            for element in elements:
                ele = findInXML(element, item)
                if ele is not None:
                    msg = generateEleDoc(ele)
                    break
    if msg is not None:
        MS.show_output(msg, 'Packages/Text/Plain text.tmLanguage')
    else:
        sublime.status_message("%s not found" % item)


def nprMacro(cursor):
    """Show NPR Macro documentation.

    The source of the documentation is MagicSublime/lib/npr_macros.xml.

    Its format:
    <macrodb>
        <macro>
            <name></name>
            <etc.../>
        </macro>
    </macrodb>"""

    def generateNprDoc(root):
        """Grab all elements under root and make into pretty documentation."""
        msg = ""
        name = root.find('name').text
        syntax = root.find('stx').text
        description = root.find('dsc').text
        code = root.find('code').text
        comment = root.find('cmt').text

        # Syntax will contain the name and more. Use if it exists, else name
        if syntax is None:
            syntax = '@' + name

        if syntax is not None:
            msg = msg + "Syntax         %s\n" % syntax  # content at col 16
        if description is not None:
            msg = msg + "Description    %s\n" % description
        if code is not None:
            msg = msg + "Code           %s\n" % code
        if comment is not None:
            msg = msg + "Notes\n"
            comment = comment.splitlines()
            for line in comment:
                msg = msg + "  %s\n" % line.rstrip()
        return msg

    item = V.substr(V.word(cursor))
    filepath = (sublime.packages_path() +
                '/MagicSublime/lib/npr_macros.xml')
    root = ET.parse(filepath).getroot()
    macro = findInXML(root, item)
    if macro is not None:
        msg = generateNprDoc(macro)
        MS.show_output(msg, 'Packages/Text/Plain text.tmLanguage')
    else:
        sublime.status_message("@%s not found" % item)


def procedure(cursor):
    """Open the selected procedure in a new tab / Show documentation for
    procedure.

    ...Not sure which yet."""


class MagicCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        """Dispatch of the MagicSublime master hotkey.

        This takes the scope, according to the NPR syntax definition, and
        performs the action specified in the global maps above."""

        global V        # The current view, used by nearly all functions

        V = self.view
        cursor = V.sel()[0].begin()
        scope = MS.scope(self, cursor)

        if scope in functions:
            functions[scope](cursor)
        else:
            sublime.status_message('"%s" function not yet written.' % scope)
