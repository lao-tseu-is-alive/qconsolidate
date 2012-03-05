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

class ConsolidateThread( QThread ):
  def __init__( self, iface, outputDir, projectFile ):
    QThread.__init__( self, QThread.currentThread() )
    self.mutex = QMutex()
    self.stopMe = 0

    self.iface = iface
    self.outputDir = outputDir
    self.projectFile = projectFile

  def run( self ):
    self.mutex.lock()
    self.stopMe = 0
    self.mutex.unlock()

    interrupted = False

    # read project
    doc = self.loadProject()
    root = doc.documentElement()

    # ensure that relative path used
    e = root.firstChildElement( "properties" )
    e.firstChildElement( "Paths" ).firstChild().firstChild().setNodeValue( "false" )

    # process layers
    layers = self.iface.legendInterface().layers()
    self.emit( SIGNAL( "rangeChanged( int )" ), len( layers ) )
    for layer in layers:
      layerType = layer.type()
      if layerType == QgsMapLayer.VectorLayer:
        print "found vector layer", layer.name()
      elif layerType == QgsMapLayer.RasterLayer:
        print "found raster layer", layer.name()
      else:
        print "found layer", layer.name()

      self.emit( SIGNAL( "updateProgress()" ) )
      self.mutex.lock()
      s = self.stopMe
      self.mutex.unlock()
      if s == 1:
        interrupted = True
        break

    # save updated project

    if not interrupted:
      self.emit( SIGNAL( "processFinished()" ) )
    else:
      self.emit( SIGNAL( "processInterrupted()" ) )

  def stop( self ):
    self.mutex.lock()
    self.stopMe = 1
    self.mutex.unlock()

    QThread.wait( self )

  def loadProject( self ):
    f = QFile( self.projectFile )
    if not f.open( QIODevice.ReadOnly | QIODevice.Text ):
      msg = self.tr( "Cannot read file %1:\n%2." ).arg( self.projectFile ).arg( f.errorString() )
      self.emit( SIGNAL( "processError( PyQt_PyObject )" ), msg )
      return

    doc = QDomDocument()
    setOk, errorString, errorLine, errorColumn = doc.setContent( f, True )
    if not setOk:
      msg = self.tr( "Parse error at line %1, column %2:\n%3" ).arg( errorLine ).arg( errorColumn ).arg( errorString )
      self.emit( SIGNAL( "processError( PyQt_PyObject )" ), msg )
      return

    f.close()
    return doc
