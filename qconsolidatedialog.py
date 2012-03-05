# -*- coding: utf-8 -*-

#******************************************************************************
#
# QConsolidate
# ---------------------------------------------------------
# Consolidates all layers from current QGIS project into one directory and
# creates copy of current project using this consolidated layers.
#
# Copyright (C) 2012 Alexander Bruy (alexander.bruy@gmail.com), NextGIS
#
# This source is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 2 of the License, or (at your option)
# any later version.
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# A copy of the GNU General Public License is available on the World Wide Web
# at <http://www.gnu.org/licenses/>. You can also obtain it by writing
# to the Free Software Foundation, 51 Franklin Street, Suite 500 Boston,
# MA 02110-1335 USA.
#
#******************************************************************************

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtXml import *

from qgis.core import *
from qgis.gui import *

from ui_qconsolidatedialogbase import Ui_QConsolidateDialog

import glob

databaseLayers = [ "PGeo",
                   "SDE",
                   "IDB",
                   "INGRES",
                   "MySQL",
                   "MSSQLSpatial",
                   "OCI",
                   "ODBC",
                   "OGDI",
                   "PostgreSQL",
                   "SQLite" ] # file or db?

directoryLayers = [ "AVCBin",
                    "GRASS",
                    "UK. NTF",
                    "TIGER" ]

protocolLayers = [ "DODS",
                   "GeoJSON" ]

class QConsolidateDialog( QDialog, Ui_QConsolidateDialog ):
  def __init__( self, iface ):
    QDialog.__init__( self )
    self.setupUi( self )
    self.iface = iface

    self.workThread = None

    self.btnOk = self.buttonBox.button( QDialogButtonBox.Ok )
    self.btnClose = self.buttonBox.button( QDialogButtonBox.Close )

    QObject.connect( self.btnBrowse, SIGNAL( "clicked()" ), self.setOutDirectory )

  def setOutDirectory( self ):
    outDir = QFileDialog.getExistingDirectory( self,
                                               self.tr( "Select output directory" ),
                                               "." )
    if outDir.isEmpty():
      return

    self.leOutputDir.setText( outDir )

  def accept( self ):
    outputDir = self.leOutputDir.text()
    if outputDir.isEmpty():
      QMessageBox.warning( self,
                           self.tr( "QConsolidate: Error" ),
                           self.tr( "Output directory is not set. Please specify output directory." ) )
      return

    # create directory for layers if not exists
    d = QDir( outputDir )
    if d.exists( "layers" ):
      res = QMessageBox.question( self,
                                  self.tr( "Directory exists" ),
                                  self.tr( "Output directory already contains 'layers' subdirectory. " +
                                           "Maybe this directory was used to consolidate another project. Continue?" ),
                                  QMessageBox.Yes | QMessageBox.No )
      if res == QMessageBox.No:
        return
    else:
      if not d.mkdir( "layers" ):
        QMessageBox.warning( self,
                             self.tr( "QConsolidate: Error" ),
                             self.tr( "Can't create directory for layers." ) )
        return

    # copy project file
    projectFile = QgsProject.instance().fileName()
    f = QFile( projectFile )
    newProjectFile = outputDir + "/" + QFileInfo( projectFile ).fileName()
    f.copy( newProjectFile )

    # start consolidate thread that does all real work
    self.workThread = ConsolidateThread( self.iface, outputDir, newProjectFile )
    QObject.connect( self.workThread, SIGNAL( "rangeChanged( int )" ), self.setProgressRange )
    QObject.connect( self.workThread, SIGNAL( "updateProgress()" ), self.updateProgress )
    QObject.connect( self.workThread, SIGNAL( "processFinished()" ), self.processFinished )
    QObject.connect( self.workThread, SIGNAL( "processInterrupted()" ), self.processInterrupted )

    self.btnClose.setText( self.tr( "Cancel" ) )
    QObject.disconnect( self.buttonBox, SIGNAL( "rejected()" ), self.reject )
    QObject.connect( self.btnClose, SIGNAL( "clicked()" ), self.stopProcessing )

    self.workThread.start()

  def setProgressRange( self, maxValue ):
    self.progressBar.setRange( 0, maxValue )
    self.progressBar.setValue( 0 )

  def updateProgress( self ):
    self.progressBar.setValue( self.progressBar.value() + 1 )

  def processFinished( self ):
    self.stopProcessing()
    self.restoreGui()

  def processInterrupted( self ):
    self.restoreGui()

  def stopProcessing( self ):
    if self.workThread != None:
      self.workThread.stop()
      self.workThread = None

  def restoreGui( self ):
    self.progressBar.setRange( 0, 1 )
    self.progressBar.setValue( 0 )

    QApplication.restoreOverrideCursor()
    QObject.connect( self.buttonBox, SIGNAL( "rejected()" ), self.reject )
    self.btnClose.setText( self.tr( "Close" ) )
    self.btnOk.setEnabled( True )

  def accept_old( self ):
    # first create directory for layers
    workDir = QDir( self.leOutputDir.text() )
    if not workDir.exists( "layers" ) and not workDir.mkdir( "layers" ):
      QMessageBox.warning( self, self.tr( "QConsolidate: Error" ),
                           self.tr( "Can't create directory for layers." ) )
      return

    # process layers
    lstLayers = self.iface.legendInterface().layers()
    #print "Layer in project:", len( lstLayers )
    for layer in lstLayers:
      layerType = layer.type()
      if layerType == QgsMapLayer.VectorLayer:
        #print "found vector layer"
        #print layer.storageType()
        #print layer.source()
        self.copyVectorLayer( layer.source(), workDir.absolutePath() + "/layers" )
      elif layerType == QgsMapLayer.RasterLayer:
        print "found raster layer"
      else:
        print "This layer type currently not supported: ", layerType

    self.copyAndUpdateProject( workDir.absolutePath() )

    QMessageBox.information( self, self.tr( "QConsolidate" ),
                         self.tr( "Completed" ) )

  def copyVectorLayer( self, layer, destDir ):
    fi = QFileInfo( layer )
    mask = fi.path() + "/" + fi.baseName() + ".*"
    #print "mask", mask
    files = glob.glob( unicode( mask ) )
    #print "Files:", files
    fl = QFile()
    for f in files:
      fi.setFile( f )
      fl.setFileName( f )
      #print "COPY FROM", f
      #print "TO", str( destDir + "/" + fi.fileName() )
      fl.copy( destDir + "/" + fi.fileName() )

  def copyAndUpdateProject( self, destDir ):
    prjPath = QgsProject.instance().fileName()
    #print "Project", prjPath
    fi = QFileInfo( prjPath )
    fl = QFile( prjPath )
    newFile = destDir + "/" + fi.fileName()
    fl.copy( destDir + "/" + fi.fileName() )

    fl.setFileName( destDir + "/" + fi.fileName() )
    if not fl.open( QIODevice.ReadOnly | QIODevice.Text ):
      QMessageBox.warning( self, self.tr( "Project loagind error" ),
                           self.tr( "Cannot read file %1:\n%2." )
                           .arg( fi.fileName() )
                           .arg( fl.errorString() ) )
      return

    doc = QDomDocument()
    errorString = None
    errorLine = None
    errorColumn = None

    if not doc.setContent( fl, True ):
      QMessageBox.warning( self, self.tr( "Project loagind error" ),
                           self.tr( "Parse error at line %1, column %2:\n%3" )
                           .arg( errorLine )
                           .arg( errorColumn )
                           .arg( errorString ) )
      return

    fl.close()

    root = doc.documentElement()
    e = root.firstChildElement( "projectlayers" )
    child = e.firstChildElement()
    while not child.isNull():
      ds = child.firstChildElement( "datasource" )
      #print "TEXT", ds.text()
      fi.setFile( ds.text() )
      #print "FILE", fi.fileName()
      p = "./layers/" + fi.fileName()
      #print "NEW", p
      tn = ds.firstChild()
      tn.setNodeValue( p )

      child = child.nextSiblingElement()

    # ensure that we have relative paths
    e = root.firstChildElement( "properties" )
    e.firstChildElement( "Paths" ).firstChild().firstChild().setNodeValue( "false" )

    fi = QFileInfo( newFile )
    fl = QFile( newFile )
    if not fl.open( QIODevice.WriteOnly | QIODevice.Text ):
      QMessageBox.warning( self, self.tr( "Project saving error" ),
                           self.tr( "Cannot write file %1:\n%2." )
                           .arg( fi.fileName() )
                           .arg( fl.errorString() ) )
      return

    out = QTextStream( fl )
    doc.save( out, 4 )
