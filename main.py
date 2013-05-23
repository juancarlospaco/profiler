# -*- coding: utf-8 -*-
# PEP8:OK, LINT:OK, PY3:OK


#############################################################################
## This file may be used under the terms of the GNU General Public
## License version 2.0 or 3.0 as published by the Free Software Foundation
## and appearing in the file LICENSE.GPL included in the packaging of
## this file.  Please review the following information to ensure GNU
## General Public Licensing requirements will be met:
## http:#www.fsf.org/licensing/licenses/info/GPLv2.html and
## http:#www.gnu.org/copyleft/gpl.html.
##
## This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
## WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
#############################################################################


# metadata
' Python Profiler GUI '
__version__ = ' 0.2 '
__license__ = ' GPL '
__author__ = ' juancarlospaco '
__email__ = ' juancarlospaco@ubuntu.com '
__url__ = 'github.com/juancarlospaco'
__date__ = '01/05/2013'
__prj__ = 'profilergui'
__docformat__ = 'html'
__source__ = ''


# imports
import sys
from os import path, remove, getpid, pathsep, access, getenv, X_OK
from tempfile import gettempdir
from pstats import Stats
from re import match
from webbrowser import open_new_tab
from sip import setapi

from PyQt4.QtGui import (QLabel, QPushButton, QFileDialog, QWidget, QVBoxLayout,
    QLineEdit, QBrush, QColor, QDockWidget, QMessageBox, QPalette, QHBoxLayout,
    QProgressDialog, QGroupBox, QGridLayout, QLCDNumber, QTabWidget, QIcon,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTextEdit, QToolBar, QAction,
    QTreeWidgetItem, QSizePolicy, QFrame)

from PyQt4.QtCore import Qt, QProcess, QTimer

try:
    from PyQt4 import Qsci
    QSCI = True
except ImportError:
    QSCI = False

from ninja_ide.core import plugin


# API 2
(setapi(a, 2) for a in ("QDate", "QDateTime", "QString", "QTime", "QUrl",
                        "QTextStream", "QVariant"))


# Constants used to name columns in widgets
TREE_FUNCTION = 0
TREE_NCALLS = 1
TREE_TTIME = 2
TREE_CTIME = 3
STAT_NCALLS = 0
STAT_TTIME = 1
STAT_TPERCALL = 2
STAT_CTIME = 3
STAT_CPERCALL = 4
STAT_FILENAME = 5
STAT_LINE = 6
STAT_FUNCTION = 7
SOURCE_FILENAME = 0
TAB_FUNCTIONSTAT = 0
TAB_SOURCE = 1
# Standard Colors
MATCHED_COLOR = QBrush(QColor("magenta"))
COLORS = [QColor(255, 0, 0), QColor(255, 128, 55), QColor(255, 187, 118),
          QColor(255, 231, 154), QColor(219, 255, 190)]
# Triplet of rate, color and associated from more to the less important
RATECOLORS = [(20.0 / 100, COLORS[0], QBrush(COLORS[0])),
              (10.0 / 100, COLORS[1], QBrush(COLORS[1])),
              (5.0 / 100, COLORS[2], QBrush(COLORS[2])),
              (1.0 / 100, COLORS[3], QBrush(COLORS[3])),
              (1.0 / 500, COLORS[4], QBrush(COLORS[4]))]

profilerPath = ''
for pathz in sys.path:
    profilerPath = path.abspath(path.join(pathz, "profile.py"))
    if path.exists(profilerPath):
        profilerPath = profilerPath
        break

tempPath = path.join(gettempdir(),
                     "ninja-ide-profile-{}.tmp".format(str(getpid())))


###############################################################################


class Main(plugin.Plugin):
    " Main Class "
    def initialize(self, *args, **kwargs):
        " Init Main Class "
        super(Main, self).initialize(*args, **kwargs)
        ' GUI main window '

        # Members
        self.scriptPath = ""
        self.scriptArgs = []
        self.profilerPath = profilerPath
        self.tempPath = tempPath
        self.output = " ERROR: FAIL: No output ! "

        # Background process definition
        self.process = QProcess()
        self.process.finished.connect(self.on_process_finished)
        self.process.error.connect(self.on_process_error)

        self.tabWidget = QTabWidget()
        self.stat = QWidget()
        self.vboxlayout1 = QVBoxLayout(self.stat)
        self.hboxlayout1 = QHBoxLayout()
        self.filterTableLabel = QLabel("<b>Type to Search : </b>", self.stat)
        self.hboxlayout1.addWidget(self.filterTableLabel)
        self.filterTableLineEdit = QLineEdit(self.stat)
        self.filterTableLineEdit.setPlaceholderText(' Type to Search . . . ')
        self.hboxlayout1.addWidget(self.filterTableLineEdit)
        self.filterHintTableLabel = QLabel(" ? ", self.stat)
        self.hboxlayout1.addWidget(self.filterHintTableLabel)
        self.vboxlayout1.addLayout(self.hboxlayout1)
        self.tableWidget = QTableWidget(self.stat)
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.setColumnCount(8)
        self.tableWidget.setRowCount(2)
        item = QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(1, item)
        item = QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(2, item)
        item = QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(3, item)
        item = QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(4, item)
        item = QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(5, item)
        item = QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(6, item)
        item = QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(7, item)
        self.tableWidget.itemDoubleClicked.connect(
                                        self.on_tableWidget_itemDoubleClicked)
        self.vboxlayout1.addWidget(self.tableWidget)
        self.tabWidget.addTab(self.stat, " ? ")

        self.source = QWidget()
        self.gridlayout = QGridLayout(self.source)
        self.scintillaWarningLabel = QLabel(
            "QScintilla is not installed!. Falling back to basic text edit!.",
            self.source)
        self.gridlayout.addWidget(self.scintillaWarningLabel, 1, 0, 1, 2)
        self.sourceTreeWidget = QTreeWidget(self.source)
        self.sourceTreeWidget.setAlternatingRowColors(True)
        self.sourceTreeWidget.itemActivated.connect(
                                        self.on_sourceTreeWidget_itemActivated)
        self.sourceTreeWidget.itemClicked.connect(
                                          self.on_sourceTreeWidget_itemClicked)
        self.sourceTreeWidget.itemDoubleClicked.connect(
                                          self.on_sourceTreeWidget_itemClicked)

        self.gridlayout.addWidget(self.sourceTreeWidget, 0, 0, 1, 1)
        self.sourceTextEdit = QTextEdit(self.source)
        self.sourceTextEdit.setReadOnly(True)
        self.gridlayout.addWidget(self.sourceTextEdit, 0, 1, 1, 1)
        self.tabWidget.addTab(self.source, " ? ")

        self.result = QWidget()
        self.vlayout = QVBoxLayout(self.result)
        self.globalStatGroupBox = QGroupBox(self.result)
        self.hboxlayout = QHBoxLayout(self.globalStatGroupBox)
        self.totalTimeLcdNumber = QLCDNumber(self.globalStatGroupBox)
        self.totalTimeLcdNumber.setSegmentStyle(QLCDNumber.Filled)
        self.totalTimeLcdNumber.setNumDigits(7)
        self.totalTimeLcdNumber.display(1000000)
        self.totalTimeLcdNumber.setFrameShape(QFrame.StyledPanel)
        self.totalTimeLcdNumber.setSizePolicy(QSizePolicy.Expanding,
                                              QSizePolicy.Expanding)
        self.hboxlayout.addWidget(self.totalTimeLcdNumber)
        self.tTimeLabel = QLabel("<b>Total Time (Sec)</b>",
                                 self.globalStatGroupBox)
        self.tTimeLabel.setSizePolicy(QSizePolicy.Minimum,
                                      QSizePolicy.Minimum)
        self.hboxlayout.addWidget(self.tTimeLabel)
        self.numCallLcdNumber = QLCDNumber(self.globalStatGroupBox)
        self.numCallLcdNumber.setNumDigits(7)
        self.numCallLcdNumber.display(1000000)
        self.numCallLcdNumber.setSegmentStyle(QLCDNumber.Filled)
        self.numCallLcdNumber.setFrameShape(QFrame.StyledPanel)
        self.numCallLcdNumber.setSizePolicy(QSizePolicy.Expanding,
                                            QSizePolicy.Expanding)
        self.hboxlayout.addWidget(self.numCallLcdNumber)
        self.numCallLabel = QLabel("<b>Number of calls</b>",
                                   self.globalStatGroupBox)
        self.numCallLabel.setSizePolicy(QSizePolicy.Minimum,
                                        QSizePolicy.Minimum)
        self.hboxlayout.addWidget(self.numCallLabel)
        self.primCallLcdNumber = QLCDNumber(self.globalStatGroupBox)
        self.primCallLcdNumber.setSegmentStyle(QLCDNumber.Filled)
        self.primCallLcdNumber.setFrameShape(QFrame.StyledPanel)
        self.primCallLcdNumber.setNumDigits(7)
        self.primCallLcdNumber.display(1000000)
        self.primCallLcdNumber.setSizePolicy(QSizePolicy.Expanding,
                                             QSizePolicy.Expanding)
        self.hboxlayout.addWidget(self.primCallLcdNumber)
        self.primCallLabel = QLabel("<b>Primitive calls (%)</b>",
                                    self.globalStatGroupBox)
        self.primCallLabel.setSizePolicy(QSizePolicy.Minimum,
                                         QSizePolicy.Minimum)
        self.hboxlayout.addWidget(self.primCallLabel)
        self.vlayout.addWidget(self.globalStatGroupBox)
        try:
            from PyKDE4.kdeui import KRatingWidget
            self.rating = KRatingWidget(self.globalStatGroupBox)
            self.rating.setToolTip('Profiling Performance Rating')
        except ImportError:
            pass
        self.tabWidget.addTab(self.result, " Get Results ! ")

        self.resgraph = QWidget()
        self.vlayout2 = QVBoxLayout(self.result)
        self.graphz = QGroupBox(self.resgraph)
        self.graphz.setTitle(" Profile Charts ")
        self.hboxlayout2 = QHBoxLayout(self.graphz)
        try:
            from PyKDE4.kdeui import KLed
            KLed(self.graphz)
        except ImportError:
            pass
        self.hboxlayout2.addWidget(QLabel('''
              <i> Work in Progress </i> '''))
        self.chart = QLabel('')
        # http://chart.googleapis.com/chart?cht=lc&chtt=Ninja_Charts&chg=9,9,2,2&chm=r,FF00004C,0,0.25,0.1&chs=600x200&chd=t:0,69,100&chdl=Calls/Min&chls=5,9,5&chf=c,lg,0,bebebe,0,76A4FB,1&chma=9,9,9,9&chxt=x,y&chxs=0,ff0000,12,0,lt|1,0000ff,10,1,lt
        self.hboxlayout2.addWidget(self.chart)
        self.vlayout2.addWidget(self.graphz)
        self.tabWidget.addTab(self.resgraph, " Graphs and Charts ")

        self.pathz = QWidget()
        self.vlayout3 = QVBoxLayout(self.pathz)
        self.patz = QGroupBox(self.pathz)
        self.patz.setTitle(" Backend Library Configuration ")
        self.hboxlayout3 = QVBoxLayout(self.patz)
        self.profilepath = QLineEdit(profilerPath)
        self.getprofile = QPushButton(QIcon.fromTheme("document-open"), 'Open')
        self.getprofile.setToolTip('Dont touch if you dont know what are doing')
        self.getprofile.clicked.connect(lambda: self.profilepath.setText(str(
            QFileDialog.getOpenFileName(self.patz, ' Open the profile.py file ',
            path.expanduser("~"), ';;(profile.py)'))))
        self.hboxlayout3.addWidget(QLabel(
            '<center><b>Profile.py Python Library Full Path:</b></center>'))
        self.hboxlayout3.addWidget(self.profilepath)
        self.hboxlayout3.addWidget(self.getprofile)

        self.argGroupBox = QGroupBox(self.pathz)
        self.hbxlayout = QHBoxLayout(self.argGroupBox)
        self.argLineEdit = QLineEdit(self.argGroupBox)
        self.argLineEdit.setToolTip('Not touch if you dont know what are doing')
        self.argLineEdit.setPlaceholderText(
            'Dont touch if you dont know what are doing')
        self.hbxlayout.addWidget(QLabel('<b>Additional Profile Arguments:</b>'))
        self.hbxlayout.addWidget(self.argLineEdit)
        self.hboxlayout3.addWidget(self.argGroupBox)

        self.vlayout3.addWidget(self.patz)
        self.tabWidget.addTab(self.pathz, " Paths and Configs ")

        self.outp = QWidget()
        self.vlayout4 = QVBoxLayout(self.outp)
        self.outgro = QGroupBox(self.outp)
        self.outgro.setTitle(" MultiProcessing Output Logs ")
        self.hboxlayout4 = QVBoxLayout(self.outgro)
        self.outputlog = QTextEdit()
        self.outputlog.setText('''
        I do not fear computers, I fear the lack of them.   -Isaac Asimov ''')
        self.hboxlayout4.addWidget(self.outputlog)
        self.vlayout4.addWidget(self.outgro)
        self.tabWidget.addTab(self.outp, " Logs ")

        self.actionNew_profiling = QAction(QIcon.fromTheme("document-new"),
                                           'New Profiling', self)
        self.actionLoad_profile = QAction(QIcon.fromTheme("document-open"),
                                          'Open Profiling', self)
        self.actionClean = QAction(QIcon.fromTheme("edit-clear"), 'Clean', self)
        self.actionClean.triggered.connect(lambda: self.clearContent)
        self.actionAbout = QAction(QIcon.fromTheme("help-about"), 'About', self)
        self.actionAbout.triggered.connect(lambda: QMessageBox.about(self.dock,
            __doc__, ', '.join((__doc__, __license__, __author__, __email__))))
        self.actionSave_profile = QAction(QIcon.fromTheme("document-save"),
                                          'Save Profiling', self)
        self.actionManual = QAction(QIcon.fromTheme("help-contents"),
                                    'Help', self)
        self.actionManual.triggered.connect(lambda:
                    open_new_tab('http://docs.python.org/library/profile.html'))

        self.tabWidget.setCurrentIndex(2)

        self.globalStatGroupBox.setTitle("Global Statistics")
        item = self.tableWidget.horizontalHeaderItem(0)
        item.setText("Number of Calls")
        item = self.tableWidget.horizontalHeaderItem(1)
        item.setText("Total Time")
        item = self.tableWidget.horizontalHeaderItem(2)
        item.setText("Per Call")
        item = self.tableWidget.horizontalHeaderItem(3)
        item.setText("Cumulative Time")
        item = self.tableWidget.horizontalHeaderItem(4)
        item.setText("Per Call")
        item = self.tableWidget.horizontalHeaderItem(5)
        item.setText("Filename")
        item = self.tableWidget.horizontalHeaderItem(6)
        item.setText("Line")
        item = self.tableWidget.horizontalHeaderItem(7)
        item.setText("Function")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.stat),
                                  "Statistics per Function")

        self.sourceTreeWidget.headerItem().setText(0, "Source files")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.source),
                                  "Sources Navigator")
        #######################################################################

        self.dock = QDockWidget()
        self.dock.setFeatures(QDockWidget.DockWidgetFloatable |
                                           QDockWidget.DockWidgetMovable)
        self.dock.setWindowTitle(__doc__)
        self.dock.setStyleSheet('QDockWidget::title{text-align: center;}')
        self.dock.setWidget(self.tabWidget)
        QToolBar(self.dock).addActions((self.actionNew_profiling,
            self.actionClean, self.actionSave_profile, self.actionLoad_profile,
            self.actionManual, self.actionAbout))

        self.actionNew_profiling.triggered.connect(
                                        self.on_actionNew_profiling_triggered)
        self.actionLoad_profile.triggered.connect(
                                        self.on_actionLoad_profile_triggered)
        self.actionSave_profile.triggered.connect(
                                        self.on_actionSave_profile_triggered)

        self.misc = self.locator.get_service('misc')
        self.misc.add_widget(self.dock,
                             QIcon.fromTheme("document-open-recent"), __doc__)

        if QSCI:
            # Scintilla source editor management
            self.scintillaWarningLabel.setText(' QScintilla is Ready ! ')
            layout = self.source.layout()
            layout.removeWidget(self.sourceTextEdit)
            self.sourceTextEdit = Qsci.QsciScintilla(self.source)
            layout.addWidget(self.sourceTextEdit, 0, 1)
            doc = self.sourceTextEdit
            doc.setLexer(Qsci.QsciLexerPython(self.sourceTextEdit))
            doc.setReadOnly(True)
            doc.setEdgeMode(Qsci.QsciScintilla.EdgeLine)
            doc.setEdgeColumn(80)
            doc.setEdgeColor(QColor("#FF0000"))
            doc.setFolding(Qsci.QsciScintilla.BoxedTreeFoldStyle)
            doc.setBraceMatching(Qsci.QsciScintilla.SloppyBraceMatch)
            doc.setCaretLineVisible(True)
            doc.setMarginLineNumbers(1, True)
            doc.setMarginWidth(1, 25)
            doc.setTabWidth(4)
            doc.setEolMode(Qsci.QsciScintilla.EolUnix)
            self.marker = {}
            for color in COLORS:
                mnr = doc.markerDefine(Qsci.QsciScintilla.Background)
                doc.setMarkerBackgroundColor(color, mnr)
                self.marker[color] = mnr
        self.currentSourcePath = None

        # Connect table and tree filter edit signal to unique slot
        self.filterTableLineEdit.textEdited.connect(
                                            self.on_filterLineEdit_textEdited)

        # Timer to display filter hint message
        self.filterHintTimer = QTimer(self)
        self.filterHintTimer.setSingleShot(True)
        self.filterHintTimer.timeout.connect(self.on_filterHintTimer_timeout)

        # Timer to start search
        self.filterSearchTimer = QTimer(self)
        self.filterSearchTimer.setSingleShot(True)
        self.filterSearchTimer.timeout.connect(
                                            self.on_filterSearchTimer_timeout)

        self.tabLoaded = {}
        for i in range(10):
            self.tabLoaded[i] = False
        self.backgroundTreeMatchedItems = {}
        self.resizeWidgetToContent(self.tableWidget)

    def on_actionNew_profiling_triggered(self):
        self.clearContent()
        self.scriptPath = str(QFileDialog.getOpenFileName(self.dock,
            "Choose your script to profile", path.expanduser("~"),
            "Python (*.py *.pyw)"))
        commandLine = [self.profilerPath, "-o", self.tempPath,
                       self.scriptPath] + self.scriptArgs
        commandLine = " ".join(commandLine)
        ##if self.termCheckBox.checkState() == Qt.Checked:
        #termList = ["xterm", "aterm"]
        #for term in termList:
            #termPath = which(term)
            #if termPath:
                #break
        #print((" INFO: OK: Terminal is %s " % termPath))
        #commandLine = """%s -e "%s ; echo 'Press ENTER Exit' ; read" """ \
                      #% (termPath, commandLine)
        print((" INFO: OK: Command line is {} ".format(commandLine)))
        print(" INFO: OK: Working... ")
        self.process.start(commandLine)
        if not self.process.waitForStarted():
            print((" ERROR: {} Failed!".format((str(commandLine)))))
            return

    def on_process_finished(self, exitStatus):
        ' whan the process end '
        print((" INFO: OK: QProcess is {} ".format(self.process.exitCode())))
        self.output = self.process.readAll().data()
        if not self.output:
            self.output = " ERROR: FAIL: No output ! "
        self.outputlog.setText(self.output + str(self.process.exitCode()))
        if path.exists(self.tempPath):
            self.setStat(self.tempPath)
            remove(self.tempPath)
        else:
            self.outputlog.setText(" ERROR: QProcess FAIL: Profiling failed.")
        self.tabWidget.setCurrentIndex(2)

    def on_process_error(self, error):
        ' when the process fail, I hope you never see this '
        print(" ERROR: QProcess FAIL: Profiler Dead, wheres your God now ? ")
        if error == QProcess.FailedToStart:
            self.outputlog.setText(" ERROR: FAIL: Profiler execution failed ")
        elif error == QProcess.Crashed:
            self.outputlog.setText(" ERROR: FAIL: Profiler execution crashed ")
        else:
            self.outputlog.setText(" ERROR: FAIL: Profiler unknown error ")

    def on_actionLoad_profile_triggered(self):
        """Load a previous profile sessions"""
        statPath = str(QFileDialog.getOpenFileName(self.dock,
            "Open profile dump", path.expanduser("~"), "Profile file (*)"))
        if statPath:
            self.clearContent()
            print(' INFO: OK: Loading profiling from {}'.format(statPath))
            self.setStat(statPath)

    def on_actionSave_profile_triggered(self):
        """Save a profile sessions"""
        statPath = str(QFileDialog.getSaveFileName(self.dock,
                "Save profile dump", path.expanduser("~"), "Profile file (*)"))
        if statPath:
            #TODO: handle error case and give feelback to user
            print(' INFO: OK: Saving profiling to {}'.format(statPath))
            self.stat.save(statPath)

    #=======================================================================#
    # Common parts                                                          #
    #=======================================================================#

    def on_tabWidget_currentChanged(self, index):
        """slot for tab change"""
        # Kill search and hint timer if running to avoid cross effect
        for timer in (self.filterHintTimer, self.filterSearchTimer):
            if timer.isActive():
                timer.stop()
        if not self.stat:
            #No stat loaded, nothing to do
            return
        self.populateTable()
        self.populateSource()

    def on_filterLineEdit_textEdited(self, text):
        """slot for filter change (table or tree"""
        if self.filterSearchTimer.isActive():
            # Already runnning, stop it
            self.filterSearchTimer.stop()
        # Start timer
        self.filterSearchTimer.start(300)

    def on_filterHintTimer_timeout(self):
        """Timeout to warn user about text length"""
        print("timeout")
        tab = self.tabWidget.currentIndex()
        if tab == TAB_FUNCTIONSTAT:
            label = self.filterHintTableLabel
        label.setText("Type > 2 characters to search")

    def on_filterSearchTimer_timeout(self):
        """timeout to start search"""
        tab = self.tabWidget.currentIndex()
        if tab == TAB_FUNCTIONSTAT:
            text = self.filterTableLineEdit.text()
            label = self.filterHintTableLabel
            edit = self.filterTableLineEdit
            widget = self.tableWidget
        else:
            print("Unknow tab for filterSearch timeout !")

        print(("do search for %s" % text))
        if not len(text):
            # Empty keyword, just clean all
            if self.filterHintTimer.isActive():
                self.filterHintTimer.stop()
            label.setText(" ? ")
            self.warnUSer(True, edit)
            self.clearSearch()
            return
        if len(text) < 2:
            # Don't filter if text is too short and tell it to user
            self.filterHintTimer.start(600)
            return
        else:
            if self.filterHintTimer.isActive():
                self.filterHintTimer.stop()
            label.setText(" ? ")

        # Search
        self.clearSearch()
        matchedItems = []
        if tab == TAB_FUNCTIONSTAT:
            # Find items
            matchedItems = widget.findItems(text, Qt.MatchContains)
            widget.setSortingEnabled(False)
            matchedRows = [item.row() for item in matchedItems]
            # Hide matched items
            header = widget.verticalHeader()
            for row in range(widget.rowCount()):
                if row not in matchedRows:
                    header.hideSection(row)
            widget.setSortingEnabled(True)
        else:
            print(" Unknow tab for filterSearch timeout ! ")

        print((" INFO: Got {} members... ".format(len(matchedItems))))
        self.warnUSer(matchedItems, edit)
        self.resizeWidgetToContent(widget)

    def resizeWidgetToContent(self, widget):
        """Resize all columns according to content"""
        for i in range(widget.columnCount()):
            widget.resizeColumnToContents(i)

    def clearSearch(self):
        """Clean search result
        For table, show all items
        For tree, remove colored items"""
        tab = self.tabWidget.currentIndex()
        if tab == TAB_FUNCTIONSTAT:
            header = self.tableWidget.verticalHeader()
            if header.hiddenSectionCount():
                for i in range(header.count()):
                    if header.isSectionHidden(i):
                        header.showSection(i)

    def clearContent(self):
        # Clear tabs
        self.tableWidget.clearContents()
        self.sourceTreeWidget.clear()
        # Reset LCD numbers
        for lcdNumber in (self.totalTimeLcdNumber, self.numCallLcdNumber,
                          self.primCallLcdNumber):
            lcdNumber.display(1000000)
        # Reset stat
        self.pstat = None
        # Disable save as menu
        self.actionSave_profile.setEnabled(False)
        # Mark all tabs as unloaded
        for i in range(10):
            self.tabLoaded[i] = False

    def warnUSer(self, result, inputWidget):
        palette = inputWidget.palette()
        if result:
            palette.setColor(QPalette.Normal, QPalette.Base,
                             QColor(255, 255, 255))
        else:
            palette.setColor(QPalette.Normal, QPalette.Base,
                             QColor(255, 136, 138))
        inputWidget.setPalette(palette)
        inputWidget.update()

    def setStat(self, statPath):
        self.stat = Stat(path=statPath)
        # Global stat update
        self.totalTimeLcdNumber.display(self.stat.getTotalTime())
        self.numCallLcdNumber.display(self.stat.getCallNumber())
        self.primCallLcdNumber.display(self.stat.getPrimitiveCallRatio())
        # Refresh current tab
        self.on_tabWidget_currentChanged(self.tabWidget.currentIndex())
        # Activate save as menu
        self.actionSave_profile.setEnabled(True)
        try:
            self.rating.setMaxRating(10)
            self.rating.setRating(
                                int(self.stat.getPrimitiveCallRatio()) / 10 - 1)
        except:
            pass

    #========================================================================#
    # Statistics table                                                      #
    #=======================================================================#

    def populateTable(self):
        row = 0
        rowCount = self.stat.getStatNumber()
        progress = QProgressDialog("Populating statistics table...",
                                         "Abort", 0, 2 * rowCount)
        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setRowCount(rowCount)

        progress.setWindowModality(Qt.WindowModal)
        for (key, value) in self.stat.getStatItems():
            #ncalls
            item = StatTableWidgetItem(str(value[0]))
            item.setTextAlignment(Qt.AlignRight)
            self.tableWidget.setItem(row, STAT_NCALLS, item)
            colorTableItem(item, self.stat.getCallNumber(), value[0])
            #total time
            item = StatTableWidgetItem(str(value[2]))
            item.setTextAlignment(Qt.AlignRight)
            self.tableWidget.setItem(row, STAT_TTIME, item)
            colorTableItem(item, self.stat.getTotalTime(), value[2])
            #per call (total time)
            if value[0] != 0:
                tPerCall = str(value[2] / value[0])
                cPerCall = str(value[3] / value[0])
            else:
                tPerCall = ""
                cPerCall = ""
            item = StatTableWidgetItem(tPerCall)
            item.setTextAlignment(Qt.AlignRight)
            self.tableWidget.setItem(row, STAT_TPERCALL, item)
            colorTableItem(item, 100.0 * self.stat.getTotalTime() /
                           self.stat.getCallNumber(), tPerCall)
            #per call (cumulative time)
            item = StatTableWidgetItem(cPerCall)
            item.setTextAlignment(Qt.AlignRight)
            self.tableWidget.setItem(row, STAT_CPERCALL, item)
            colorTableItem(item, 100.0 * self.stat.getTotalTime() /
                           self.stat.getCallNumber(), cPerCall)
            #cumulative time
            item = StatTableWidgetItem(str(value[3]))
            item.setTextAlignment(Qt.AlignRight)
            self.tableWidget.setItem(row, STAT_CTIME, item)
            colorTableItem(item, self.stat.getTotalTime(), value[3])
            #Filename
            self.tableWidget.setItem(row, STAT_FILENAME,
                                        StatTableWidgetItem(str(key[0])))
            #Line
            item = StatTableWidgetItem(str(key[1]))
            item.setTextAlignment(Qt.AlignRight)
            self.tableWidget.setItem(row, STAT_LINE, item)
            #Function name
            self.tableWidget.setItem(row, STAT_FUNCTION,
                                        StatTableWidgetItem(str(key[2])))
            row += 1
            # Store it in stat hash array
            self.stat.setStatLink(item, key, TAB_FUNCTIONSTAT)
            progress.setValue(row)
            if progress.wasCanceled():
                return

        for i in range(self.tableWidget.rowCount()):
            progress.setValue(row + i)
            for j in range(self.tableWidget.columnCount()):
                item = self.tableWidget.item(i, j)
                if item:
                    item.setFlags(Qt.ItemIsEnabled)

        self.tableWidget.setSortingEnabled(True)
        self.resizeWidgetToContent(self.tableWidget)
        progress.setValue(2 * rowCount)

    def on_tableWidget_itemDoubleClicked(self, item):
        matchedItems = []
        filename = str(self.tableWidget.item(item.row(), STAT_FILENAME).text())
        if not filename or filename.startswith("<"):
            # No source code associated, return immediatly
            return
        function = self.tableWidget.item(item.row(), STAT_FUNCTION).text()
        line = self.tableWidget.item(item.row(), STAT_LINE).text()

        self.on_tabWidget_currentChanged(TAB_SOURCE)  # load source tab
        function = "{} ({})".format(function, line)
        fathers = self.sourceTreeWidget.findItems(filename, Qt.MatchContains,
                                                  SOURCE_FILENAME)
        print((" INFO: Find {} father...".format(len(fathers))))
        for father in fathers:
            findItems(father, function, SOURCE_FILENAME, matchedItems)
        print((" INFO: Find {} items...".format(len(matchedItems))))

        if matchedItems:
            self.tabWidget.setCurrentIndex(TAB_SOURCE)
            self.sourceTreeWidget.scrollToItem(matchedItems[0])
            self.on_sourceTreeWidget_itemClicked(matchedItems[0],
                                                 SOURCE_FILENAME)
            matchedItems[0].setSelected(True)
        else:
            print(" WARNING: Weird: Item found but cannot scroll to it !")

    #=======================================================================#
    # Source explorer                                                      #
    #=====================================================================#

    def populateSource(self):
        items = {}
        for stat in self.stat.getStatKeys():
            source = stat[0]
            function = "{} ({})".format(stat[2], stat[1])
            if source in ("", "profile") or source.startswith("<"):
                continue
            # Create the function child
            child = QTreeWidgetItem([function])
            # Store it in stat hash array
            self.stat.setStatLink(child, stat, TAB_SOURCE)
            if source in items:
                father = items[source]
            else:
                # Create the father
                father = QTreeWidgetItem([source])
                items[source] = father
            father.addChild(child)
        self.sourceTreeWidget.setSortingEnabled(False)
        for value in list(items.values()):
            self.sourceTreeWidget.addTopLevelItem(value)
        self.sourceTreeWidget.setSortingEnabled(True)

    def on_sourceTreeWidget_itemActivated(self, item, column):
        self.on_sourceTreeWidget_itemClicked(item, column)

    def on_sourceTreeWidget_itemClicked(self, item, column):
        line = 0
        parent = item.parent()
        if QSCI:
            doc = self.sourceTextEdit
        if parent:
            pathz = parent.text(column)
            result = match("(.*) \(([0-9]+)\)", item.text(column))
            if result:
                try:
                    function = str(result.group(1))
                    line = int(result.group(2))
                except ValueError:
                    # We got garbage... falling back to line 0
                    pass
        else:
            pathz = item.text(column)
        pathz = path.abspath(str(pathz))
        if self.currentSourcePath != pathz:
            # Need to load source
            self.currentSourcePath == pathz
            try:
                if QSCI:
                    doc.clear()
                    doc.insert(file(pathz).read())
                else:
                    self.sourceTextEdit.setPlainText(file(pathz).read())
            except IOError:
                QMessageBox.warning(self,
                                     "Error", "Source file could not be found",
                                     QMessageBox.Ok)
                return

            if QSCI:
                for function, line in [(i[2], i[1]
                           ) for i in self.stat.getStatKeys() if i[0] == pathz]:
                    # expr, regexp, case sensitive, whole word, wrap, forward
                    doc.findFirst("def", False, True, True, False, True, line,
                                  0, True)
                    end, foo = doc.getCursorPosition()
                    time = self.stat.getStatTotalTime((pathz, line, function))
                    colorSource(doc, self.stat.getTotalTime(), time, line, end,
                                self.marker)
        if QSCI:
            doc.ensureLineVisible(line)


class StatTableWidgetItem(QTableWidgetItem):
    def __lt__(self, item):
        ' function call '
        if not self.text():
            return False
        if not item.text():
            return True
        column = self.column()
        if column in (STAT_NCALLS, STAT_LINE):
            # Int sort
            return (int(self.text()) - int(item.text())) > 0
        elif column in (STAT_TTIME, STAT_TPERCALL, STAT_CTIME, STAT_CPERCALL):
            # float sort
            return (float(self.text()) - float(item.text())) > 0
        else:
            # Standard text sort
            return cmp(self.text(), item.text()) > 0


def findItems(item, text, column, matchedItems):
    if text in item.text(column):
        matchedItems.append(item)
    for i in range(item.childCount()):
        findItems(item.child(i), text, column, matchedItems)


def key2Name(key):
    return "{}:{} {}".format(key[0], key[1], key[2])


def colorTreeItem(item, column, total, value):
    ' give colors '
    if not value:
        value = 0
    for rate, color, bruch in RATECOLORS:
        if float(value) > rate * total:
            item.setBackground(column, bruch)
            break


def colorTableItem(item, total, value):
    if not value:
        value = 0
    for rate, color, bruch in RATECOLORS:
        if float(value) > rate * total:
            item.setBackground(bruch)
            break


def colorSource(item, total, value, begin, end, marker):
    if QSCI:
        for rate, color, bruch in RATECOLORS:
            if float(value) > rate * total:
                for i in range(end - begin):
                    item.markerAdd(begin - 1 + i, marker[color])
                break
        item.setSelection(begin, 0, begin, 0)


###############################################################################


class Stat:
    """manage interface between pstat data and GUI item"""
    def __init__(self, pstat=None, path=None):
        # pStat profile statistics instance
        self.pstat = None
        self.load(pstat, path)
        self.itemArray = {}
        self.itemArray[TAB_FUNCTIONSTAT] = {}
        self.itemArray[TAB_SOURCE] = {}
        # Reference from pstat key to Qt object in the GUI
        self.pStatArray = {}
        self.pStatArray[TAB_FUNCTIONSTAT] = {}
        self.pStatArray[TAB_SOURCE] = {}

    def getTotalTime(self):
        if self.pstat:
            return self.pstat.total_tt
        else:
            return 0

    def getCallNumber(self):
        if self.pstat:
            return self.pstat.total_calls
        else:
            return 0

    def getPrimitiveCallRatio(self):
        if self.pstat:
            return 100.0 * float(self.pstat.prim_calls) / float(
                                                        self.pstat.total_calls)
        else:
            return 0

    def getStatNumber(self):
        if self.pstat:
            return len(self.pstat.stats)
        else:
            return 0

    def getStatItems(self):
        if self.pstat:
            return list(self.pstat.stats.items())

    def getStatKeys(self):
        if self.pstat:
            return list(self.pstat.stats.keys())

    def getCalleesItems(self):
        if self.pstat:
            return list(self.pstat.all_callees.items())

    def getStatTotalTime(self, pstatTriplet):
        if self.pstat:
            try:
                return self.pstat.stats[pstatTriplet][2]
            except KeyError:
                return 0
        else:
            return 0

    def getStatCumulativeTime(self, pstatTriplet):
        if self.pstat:
            try:
                return self.pstat.stats[pstatTriplet][3]
            except KeyError:
                return 0
        else:
            return 0

    def load(self, pstat=None, path=None):
        if pstat and path:
            print('''' Warning : both pstat and path parameter given.
                                 path override pstat !''')
        if pstat:
            self.pstat = pstat
        if path:
            self.pstat = Stats(str(path))
        if self.pstat:
            self.pstat.calc_callees()

    def save(self, path):
        try:
            self.pstat.dump_stats(path)
        except:
            pass

    def setStatLink(self, guiItem, pstatTriplet, target):
        self.itemArray[target][guiItem] = pstatTriplet
        self.pStatArray[target][pstatTriplet] = guiItem

    def getPstatFromGui(self, guiItem, target):
        try:
            return self.itemArray[target][guiItem]
        except KeyError:
            return None

    def getGuiFromPstat(self, pStatTtriplet, target):
        try:
            return self.pStatArray[target][pStatTtriplet]
        except KeyError:
            return None


###############################################################################


def which(progName):
    for directory in getenv("PATH").split(pathsep):
        fullpath = path.join(directory, progName)
        if access(fullpath, X_OK):
                return fullpath
    return None


###############################################################################


if __name__ == "__main__":
    print(__doc__)
