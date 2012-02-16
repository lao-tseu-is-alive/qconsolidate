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
    # first create directory for layers
    workDir = QDir( self.leOutputDir.text() )
    if not workDir.exists( "layers" ) and not workDir.mkdir( "layers" ):
      QMessageBox.warning( self, self.tr( "QConsolidate: Error" ),
                           self.tr( "Can't create directory for layers." ) )
      return

    # process layers
    lstLayers = self.iface.legendInterface().layers()
    print "Layer in project:", len( lstLayers )
    for layer in lstLayers:
      layerType = layer.type()
      if layerType == QgsMapLayer.VectorLayer:
        print "found vector layer"
        print layer.storageType()
        print layer.source()
        self.copyVectorLayer( layer.source(), workDir.absolutePath() + "/layers" )
      elif layerType == QgsMapLayer.RasterLayer:
        print "found raster layer"
      else:
        print "This layer type currently not supported: ", layerType

    self.copyAndUpdateProject( workDir.absolutePath() )

  def copyVectorLayer( self, layer, destDir ):
    fi = QFileInfo( layer )
    mask = fi.path() + "/" + fi.baseName() + ".*"
    print "mask", mask
    files = glob.glob( unicode( mask ) )
    print "Files:", files
    fl = QFile()
    for f in files:
      fi.setFile( f )
      fl.setFileName( f )
      print "COPY FROM", f
      print "TO", str( destDir + "/" + fi.fileName() )
      fl.copy( destDir + "/" + fi.fileName() )

  def copyAndUpdateProject( self, destDir ):
    prjPath = QgsProject.instance().fileName()
    print "Project", prjPath
    fi = QFileInfo( prjPath )
    fl = QFile( prjPath )
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

    root = doc.documentElement()
