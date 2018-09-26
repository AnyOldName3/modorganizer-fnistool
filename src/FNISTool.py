# This Mod Organizer plugin is released to the pubic under the terms of the GNU GPL version 3, which is accessible from the Free Software Foundation here: https://www.gnu.org/licenses/gpl-3.0-standalone.html

# To use this plugin, place it in the plugins directory of your Mod Organizer install. You will then find a 'Run FNIS' option under the tools menu.

# Intended behaviour:
# * Adds button to tools menu.
# * If FNIS' location isn't known (or isn't valid, e.g. FNIS isn't actually there) when the button is pressed, a file chooser is displayed to find FNIS.
# * `GenerateFNISforUsers.exe RedirectFiles="<some mod path>" InstantExecute=1` is then run within the VFS, with the RedirectFiles option being controlled by other settings (which the user is prompted to fill in if they have not yet been specified).
# * When it exits, if necessary, its return code is used to generate a helpful popup saying whether or not it worked.

# Future behaviour:
# * As in Vortex's FNIS integration, keeps track of mod files which affect FNIS.
# * If they don't match what was there when the last FNIS output was created, uses IPluginDiagnose interface to display a warning
# * This may already be handled by MO's built-in (but disabled) FNIS checker plugin
import os
import pathlib
import sys

from PyQt5.QtCore import QCoreApplication, qCritical, qDebug, QFileInfo
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QFileDialog, QFileSystemModel, QMessageBox

if "mobase" not in sys.modules:
    import mock_mobase as mobase

class FNISMissingException(Exception):
    """Thrown if GenerateFNISforUsers.exe path can't be found"""
    pass

class UnknownOutputPreferenceException(Exception):
    """Thrown if the user hasn't specified whether to output to a separate mod"""
    pass

class FNISTool(mobase.IPluginTool):
    
    def __init__(self):
        super(FNISTool, self).__init__()
        self.__organizer = None
        self.__parentWidget = None

    def init(self, organizer):
        self.__organizer = organizer
        if sys.version_info < (3, 0):
            qCritical(self.__tr("FNISTool plugin requires a Python 3 interpreter, but is running on a Python 2 interpreter."))
            QMessageBox.critical(self.__parentWidget, self.__tr("Incompatible Python version."), self.__tr("This version of the FNIS Integration plugin requires a Python 3 interpreter, but Mod Organizer has provided a Python 2 interpreter. You should check for an updated version, including in the Mod Organizer 2 Development Discord Server."))
            return False
        return True

    def name(self):
        return "FNIS Integration Tool"

    def author(self):
        return "AnyOldName3"

    def description(self):
        return self.__tr("Runs GenerateFNISforUsers.exe so the game can load custom animations.")

    def version(self):
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.prealpha)

    def isActive(self):
        return True

    def settings(self):
        return [
            mobase.PluginSetting("fnis-path", self.__tr("Path to GenerateFNISforUsers.exe"), ""),
            mobase.PluginSetting("output-to-mod", self.__tr("Whether or not to direct the FNIS output to a mod folder."), dict(initialised=False, value=True)),
            mobase.PluginSetting("output-path", self.__tr("When output-to-mod is enabled, the path to the mod to use."), "")
            ]

    def displayName(self):
        return self.__tr("Run FNIS")

    def tooltip(self):
        return self.__tr("Runs GenerateFNISforUsers.exe so the game can load custom animations.")

    def icon(self):
        fnisPath = self.__organizer.pluginSetting(self.name(), "fnis-path")
        if os.path.exists(fnisPath):
            # We can't directly grab the icon from an executable, but this seems like the simplest alternative.
            fin = QFileInfo(fnisPath)
            model = QFileSystemModel()
            model.setRootPath(fin.path())
            return model.fileIcon(model.index(fin.filePath()))
        else:
            # Fall back to where the user might have put an icon manually.
            return QIcon("plugins/FNIS.ico")

    def setParentWidget(self, widget):
        self.__parentWidget = widget
    
    def display(self):
        args = []
        redirectOutput = True
        try:
            redirectOutput = self.__getRedirectOutput()
        except UnknownOutputPreferenceException:
            QMessageBox.critical(self.__parentWidget, self.__tr("Output preference not set"), self.__tr("Whether or not to output to a mod was not specifed. The tool will now exit."))
            return
        if redirectOutput:
            try:
                args.append('RedirectFiles="' + self.__getOutputPath() + '"')
            except UnknownOutputPreferenceException:
                QMessageBox.critical(self.__parentWidget, self.__tr("Output mod not set"), self.__tr("The mod to output to was not specifed. The tool will now exit."))
                return
        args.append('InstantExecute=1')
        try:
            executable = self.__getFNISPath()
        except FNISMissingException:
            QMessageBox.critical(self.__parentWidget, self.__tr("FNIS path not specified"), self.__tr("The path to GenerateFNISforUsers.exe wasn't specified. The tool will now exit."))
            return
        handle = self.__organizer.startApplication(executable, args)
        result, exitCode = self.__organizer.waitForApplication(handle)
        qDebug(str(handle))
        qDebug(str(result))
        qDebug(str(exitCode))
    
    def __tr(self, str):
        return QCoreApplication.translate("FNISTool", str)
    
    def __getRedirectOutput(self):
        redirectOutput = self.__organizer.pluginSetting(self.name(), "output-to-mod")
        if redirectOutput == "":
            QMessageBox.critical(self.__parentWidget, self.__tr("Setting corrupt"), self.__tr("A setting for this plugin has been corrupted. Please restart Mod Organizer to reload the default. The plugin will now crash, but when MO is restarted, everything should be fine."))
        if not redirectOutput['initialised']:
            result = QMessageBox.question(self.__parentWidget, self.__tr("Output to a mod?"), self.__tr("Fore's New Idles in Skyrim can output either to Mod Organizer's VFS (potentially overwriting files from multiple mods) or to a separate mod. Would you like FNIS to output to a separate mod? This setting can be updated in the Plugins tab of the Mod Organizer Settings menu."), QMessageBox.StandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel))
            if result == QMessageBox.Yes:
                redirectOutput['value'] = True
            elif result == QMessageBox.No:
                redirectOutput['value'] = False
            else:
                # the user pressed cancel
                raise UnknownOutputPreferenceException
            
            redirectOutput['initialised'] = True
            self.__organizer.setPluginSetting(self.name(), "output-to-mod", redirectOutput)
        return redirectOutput
    
    def __getOutputPath(self):
        path = self.__organizer.pluginSetting(self.name(), "output-path")
        modDirectory = self.__getModDirectory()
        isAMod = pathlib.Path(path).parent.samefile(modDirectory)
        if not os.path.isdir(path) or not isAMod:
            QMessageBox.information(self.__parentWidget, self.__tr("Choose an output mod"), self.__tr("Please choose an output mod for Fore's New Idles in Skyrim. This must be a directory in Mod Organizer's mods directory, and you can create one if you do not have one already. FNIS will delete any existing contents of this directory when it is run, so do not choose a mod you use for anything else. This setting can be updated in the Plugins tab of the Mod Organizer Settings menu."))
            while not os.path.isdir(path) or not isAMod:
                path = QFileDialog.getExistingDirectory(self.__parentWidget, self.__tr("Choose an output mod"), str(modDirectory), QFileDialog.ShowDirsOnly)
                if not os.path.isdir(path):
                    # cancel was pressed
                    raise UnknownOutputPreferenceException
                isAMod = pathlib.Path(path).parent.samefile(modDirectory)
                if not isAMod:
                    QMessageBox.information(self.__parentWidget, self.__tr("Not a mod..."), self.__tr("The selected directory is not a Mod Organizer managed mod. Please choose a directory within the mods directory."))
            # The user may have created a new mod in the MO mods directory, so we must trigger a refresh
            self.__organizer.refreshModList()
            self.__organizer.setPluginSetting(self.name(), "output-path", path)
        return path
    
    def __getFNISPath(self):
        savedPath = self.__organizer.pluginSetting(self.name(), "fnis-path")
        # FNIS must be installed within the game's data directory, so needs to either be within that or a mod folder
        modDirectory = self.__getModDirectory()
        gameDataDirectory = pathlib.Path(self.__organizer.managedGame().dataDirectory().absolutePath())
        pathlibPath = pathlib.Path(savedPath)
        inGoodLocation = self.__withinDirectory(pathlibPath, modDirectory)
        inGoodLocation |= self.__withinDirectory(pathlibPath, gameDataDirectory)
        if not pathlibPath.is_file() or not inGoodLocation:
            QMessageBox.information(self.__parentWidget, self.__tr("Find FNIS"), self.__tr("Fore's New Idles in Skyrim can't be found using the location saved in Mod Organizer's settings. Please find GenerateFNISforUsers.exe in the file picker. FNIS must be visible within the VFS, so choose an installation either within the game's data directory or within a mod folder. This setting can be updated in the Plugins tab of the Mod Organizer Settings menu."))
            while True:
                path = QFileDialog.getOpenFileName(self.__parentWidget, self.__tr("Locate GenerateFNISforUsers.exe"), str(modDirectory), "FNIS (GenerateFNISforUsers.exe)")[0]
                if path == "":
                    # Cancel was pressed
                    raise FNISMissingException
                pathlibPath = pathlib.Path(path)
                inGoodLocation = self.__withinDirectory(pathlibPath, modDirectory)
                inGoodLocation |= self.__withinDirectory(pathlibPath, gameDataDirectory)
                if pathlibPath.is_file() and inGoodLocation:
                    self.__organizer.setPluginSetting(self.name(), "fnis-path", path)
                    savedPath = path
                    break
                else:
                    QMessageBox.information(self.__parentWidget, self.__tr("Not a compatible location..."), self.__tr("Fore's New Idles in Skyrim only works when within the VFS, so must be installed to the game's data directory or within a mod folder. Please select a different FNIS installation."))
        return savedPath
    
    def __getModDirectory(self):
        modDirectory = None
        modList = self.__organizer.modsSortedByProfilePriority()
        # Get the first managed mod so we can access the mods directory.
        for mod in modList:
            if (self.__organizer.modList().state(mod) & 0x2) != 0:
                modDirectory = pathlib.Path(self.__organizer.getMod(mod).absolutePath()).parent
                break
        return modDirectory
    
    @staticmethod
    def __withinDirectory(innerPath, outerDir):
        for path in innerPath.parents:
            if path.samefile(outerDir):
                return True
        return False
    
def createPlugin():
    return FNISTool()