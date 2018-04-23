import numpy as np
from PySide import QtGui, QtCore
from PySide.QtCore import *
from PySide.QtGui import *
import sharppy.sharptab as tab
from sharppy.sharptab.constants import *
import datetime
import platform

## routine written by Kelton Halbert
## keltonhalbert@ou.edu

__all__ = ['backgroundText', 'plotText']

class backgroundText(QtGui.QFrame):
    '''
    Handles drawing the background frame onto a QPixmap.
    Inherits a QtGui.QFrame Object.
    '''
    def __init__(self):
        super(backgroundText, self).__init__()
        self.initUI()

    def initUI(self):
        '''
        Initializes frame variables such as padding,
        width, height, etc, as well as the QPixmap
        that contains the frame drawing.
        '''
        ## set the frame stylesheet
        self.setStyleSheet("QFrame {"
            "  background-color: rgb(0, 0, 0);"
            "  border-width: 1px;"
            "  border-style: solid;"
            "  border-color: #3399CC;}")
        ## set the frame padding
        ## set the height/width variables
        self.lpad = 0; self.rpad = 0
        self.tpad = 5; self.bpad = 0
        self.wid = self.size().width()
        self.hgt = self.size().height()
        self.tlx = self.rpad; self.tly = self.tpad
        self.brx = self.wid; self.bry = self.hgt
        ## do a DPI check to make sure
        ## the text is sized properly!
        fsize = np.floor(.06 * self.hgt)
        self.tpad = np.floor(.03 * self.hgt)
        ## set the font, get the metrics and height of the font
        self.label_font = QtGui.QFont('Helvetica')
        self.label_font.setPixelSize(fsize)
        self.label_metrics = QtGui.QFontMetrics( self.label_font )
        self.label_height = self.label_metrics.xHeight() + self.tpad
        ## the self.ylast variable is used as a running sum for
        ## text placement.
        self.ylast = self.label_height
        ## initialize the QPixmap that will be drawn on.
        self.plotBitMap = QtGui.QPixmap(self.width()-2, self.height()-2)
        self.plotBitMap.fill(QtCore.Qt.black)
        ## plot the background frame
        self.plotBackground()
    
    def draw_frame(self, qp):
        '''
        Draws the background frame and the text headers for indices.
        '''
        ## initialize a white pen with thickness 1 and a solid line
        pen = QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine)
        qp.setPen(pen)
        qp.setFont(self.label_font)
        ## set the horizontal grid to be the width of the frame
        ## divided into 8 spaces
        x1 = self.brx / 8
        y1 = 1
        ## draw the header and the indices using a loop.
        ## This loop is a 'horizontal' loop that will plot
        ## the text for a row, keeping the vertical placement constant.
        count = 0
        titles = ['PCL', 'CAPE', 'CINH', 'NCA', 'LI', 'NCL', 'NE']
        for title in titles:
            rect = QtCore.QRect(x1*count, y1, x1*2, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignCenter, title)
            count += 1
        vspace = self.label_height
        if platform.system() == "Windows":
            vspace += self.label_metrics.descent() + 1
        qp.drawLine(0, vspace, self.brx, vspace)
        self.ylast = vspace
    
    def resizeEvent(self, e):
        '''
        Handles when the window gets resized.
        '''
        self.initUI()

    def plotBackground(self):
        '''
        Handles drawing the text background onto
        the QPixmap.
        '''
        ## initialize a QPainter objext
        qp = QtGui.QPainter()
        qp.begin(self.plotBitMap)
        ## draw the frame
        self.draw_frame(qp)
        qp.end()


class plotText(backgroundText):
    updatepcl = Signal(tab.params.Parcel)

    '''
    Handles plotting the indices in the frame.
    Inherits a backgroundText Object that contains
    a QPixmap with the frame drawn on it. All drawing
    gets done on this QPixmap, and then the QPixmap
    gets rendered by the paintEvent function.
    '''
    def __init__(self, pcl_types):
        '''
        Initialize the data from a Profile object passed to 
        this class. It then takes the data it needs from the
        Profile object and converts them into strings that
        can be used to draw the text in the frame.
        
        Parameters
        ----------
        prof: a Profile Object
        
        '''
        ## get the parcels to be displayed in the GUI
        super(plotText, self).__init__()

        self.prof = None;
        self.pcl_types = pcl_types
        self.parcels = {}
        self.bounds = np.empty((4,2))
        self.setDefaultParcel()

        self.w = SelectParcels(self.pcl_types, self)

    def setDefaultParcel(self):
        idx = np.where(np.asarray(self.pcl_types) == "MU")[0]
        if len(idx) == 0:
            self.skewt_pcl = 0
        else:
            self.skewt_pcl = idx

    def mouseDoubleClickEvent(self, e):
        self.w.show()

    def setParcels(self, prof):
        self.parcels["SFC"] = prof.sfcpcl # Set the surface parcel
        self.parcels["ML"] = prof.mlpcl
        self.parcels["FCST"] = prof.fcstpcl
        self.parcels["MU"] = prof.mupcl
        self.parcels["EFF"] = prof.effpcl
        self.parcels["USER"] = prof.usrpcl

    def setProf(self, prof):
        self.ylast = self.label_height
        self.setParcels(prof)
        self.prof = prof;

        ## either get or calculate the indices, round to the nearest int, and
        ## convert them to strings.
        ## K Index
        self.k_idx = tab.utils.INT2STR( prof.k_idx )
        ## precipitable water
        self.pwat = tab.utils.FLOAT2STR( prof.pwat, 2 )
        ## 0-3km agl lapse rate
        self.lapserate_3km = tab.utils.FLOAT2STR( prof.lapserate_3km, 1 )
        ## 3-6km agl lapse rate
        self.lapserate_3_6km = tab.utils.FLOAT2STR( prof.lapserate_3_6km, 1 )
        ## 850-500mb lapse rate
        self.lapserate_850_500 = tab.utils.FLOAT2STR( prof.lapserate_850_500, 1 )
        ## 700-500mb lapse rate
        self.lapserate_700_500 = tab.utils.FLOAT2STR( prof.lapserate_700_500, 1 )
        ## convective temperature
        self.convT = tab.utils.INT2STR( prof.convT )
        ## sounding forecast surface temperature
        self.maxT = tab.utils.INT2STR( prof.maxT )
        #fzl = str(int(self.sfcparcel.hght0c))
        ## 100mb mean mixing ratio
        self.mean_mixr = tab.utils.FLOAT2STR( prof.mean_mixr, 1 )
        ## 150mb mean rh
        self.low_rh = tab.utils.INT2STR( prof.low_rh )
        self.mid_rh = tab.utils.INT2STR( prof.mid_rh )
        ## calculate the totals totals index
        self.totals_totals = tab.utils.INT2STR( prof.totals_totals )
        self.dcape = tab.utils.INT2STR( prof.dcape )
        self.drush = tab.utils.INT2STR( prof.drush )
        self.sigsevere = tab.utils.INT2STR( prof.sig_severe )
        self.mmp = tab.utils.FLOAT2STR( prof.mmp, 2 )
        self.esp = tab.utils.FLOAT2STR( prof.esp, 1 )
        self.wndg = tab.utils.FLOAT2STR( prof.wndg, 1 )
        self.tei = tab.utils.INT2STR( prof.tei )

        self.clearData()
        self.plotBackground()
        self.plotData()
        self.update()

    def resizeEvent(self, e):
        '''
        Handles when the window is resized.
        
        Parametes
        ---------
        e: an Event Object
        '''
        super(plotText, self).resizeEvent(e)
        self.plotData()
    
    def paintEvent(self, e):
        '''
        Handles when the window gets painted.
        This renders the QPixmap that the backgroundText
        Object contians. For the actual drawing of the data,
        see the plotData function.
        
        Parametes
        ---------
        e: an Event Object
        
        '''
        super(plotText, self).paintEvent(e)
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.drawPixmap(1, 1, self.plotBitMap)
        qp.end()

    def plotData(self):
        '''
        Handles the drawing of the text onto the QPixmap.
        This is where the actual data gets plotted/drawn.
        '''
        if self.prof is None:
            return

        ## initialize a QPainter object
        qp = QtGui.QPainter()
        qp.begin(self.plotBitMap)
        ## draw the indices
        self.drawConvectiveIndices(qp)
        self.drawIndices(qp)
        self.drawSevere(qp)
        qp.end()

    def clearData(self):
        '''
        Handles the clearing of the pixmap
        in the frame.
        '''
        self.plotBitMap = QtGui.QPixmap(self.width(), self.height())
        self.plotBitMap.fill(QtCore.Qt.black)
    
    def drawSevere(self, qp):
        '''
        This handles the severe indices, such as STP, sig hail, etc.
        
        Parameters
        ----------
        qp: QtGui.QPainter object
        
        '''
        ## initialize a pen to draw with.
        pen = QtGui.QPen(QtCore.Qt.yellow, 1, QtCore.Qt.SolidLine)
        qp.setFont(self.label_font)
        color_list = [QtGui.QColor(CYAN), QtGui.QColor(DBROWN), QtGui.QColor(LBROWN), QtGui.QColor(WHITE), QtGui.QColor(YELLOW), QtGui.QColor(RED), QtGui.QColor(MAGENTA)]
        ## needs to be coded.
        x1 = self.brx / 8
        y1 = self.ylast + self.tpad
        ship = tab.utils.FLOAT2STR( self.prof.ship, 1 )
        stp_fixed = tab.utils.FLOAT2STR( self.prof.stp_fixed, 1 )
        stp_cin = tab.utils.FLOAT2STR( self.prof.stp_cin, 1 )
        right_scp = tab.utils.FLOAT2STR( self.prof.right_scp, 1 )

        # Coloring provided by Rich Thompson (SPC)
        labels = ['Superceldas: ', 'Tornado (cin): ', 'Tornado (fix): ', 'Granizo: ']
        indices = [right_scp, stp_cin, stp_fixed, ship]
        for label, index in zip(labels,indices):
            rect = QtCore.QRect(x1*5 - 8, y1, x1*8, self.label_height)
            ## Cambios para el hemisferio sur JP JP
            if self.prof.latitude < 0:
                if label != labels[3]:
                    index = tab.utils.FLOAT2STR(-float(index), 1)

            if label == labels[0]: # STP uses a different color scale
                if float(index) >= 19.95:
                    pen = QtGui.QPen(color_list[6], 1, QtCore.Qt.SolidLine)
                elif float(index) >= 11.95:
                    pen = QtGui.QPen(color_list[5], 1, QtCore.Qt.SolidLine)
                elif float(index) >= 1.95:
                    pen = QtGui.QPen(color_list[3], 1, QtCore.Qt.SolidLine)
                elif float(index) >= .45:
                    pen = QtGui.QPen(color_list[2], 1, QtCore.Qt.SolidLine)
                elif float(index) >= -.45:
                    pen = QtGui.QPen(color_list[1], 1, QtCore.Qt.SolidLine)
                elif float(index) < -.45:
                    pen = QtGui.QPen(color_list[0], 1, QtCore.Qt.SolidLine)
            elif label == labels[1]: # STP effective
                if float(index) >= 8:
                    pen = QtGui.QPen(color_list[6], 1, QtCore.Qt.SolidLine)
                elif float(index) >= 4:
                    pen = QtGui.QPen(color_list[5], 1, QtCore.Qt.SolidLine)
                elif float(index) >= 2:
                    pen = QtGui.QPen(color_list[4], 1, QtCore.Qt.SolidLine)
                elif float(index) >= 1:
                    pen = QtGui.QPen(color_list[3], 1, QtCore.Qt.SolidLine)
                elif float(index) >= .5:
                    pen = QtGui.QPen(color_list[2], 1, QtCore.Qt.SolidLine)
                elif float(index) < .5:
                    pen = QtGui.QPen(color_list[1], 1, QtCore.Qt.SolidLine)
            elif label == labels[2]: # STP fixed
                if float(index) >= 7:
                    pen = QtGui.QPen(color_list[6], 1, QtCore.Qt.SolidLine)
                elif float(index) >= 5:
                    pen = QtGui.QPen(color_list[5], 1, QtCore.Qt.SolidLine)
                elif float(index) >= 2:
                    pen = QtGui.QPen(color_list[4], 1, QtCore.Qt.SolidLine)
                elif float(index) >= 1:
                    pen = QtGui.QPen(color_list[3], 1, QtCore.Qt.SolidLine)
                elif float(index) >= .5:
                    pen = QtGui.QPen(color_list[2], 1, QtCore.Qt.SolidLine)
                else:
                    pen = QtGui.QPen(color_list[1], 1, QtCore.Qt.SolidLine)
            elif label == labels[3]: # SHIP
                if float(index) >= 5:
                    pen = QtGui.QPen(color_list[6], 1, QtCore.Qt.SolidLine)
                elif float(index) >= 2:
                    pen = QtGui.QPen(color_list[5], 1, QtCore.Qt.SolidLine)
                elif float(index) >= 1:
                    pen = QtGui.QPen(color_list[4], 1, QtCore.Qt.SolidLine)
                elif float(index) >= .5:
                    pen = QtGui.QPen(color_list[3], 1, QtCore.Qt.SolidLine)
                else:
                    pen = QtGui.QPen(color_list[1], 1, QtCore.Qt.SolidLine)

            if self.prof.latitude < 0:
                if label != labels[3]:
                    index = tab.utils.FLOAT2STR(-float(index), 1)
            qp.setPen(pen)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignLeft, label + index)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent()
            y1 += vspace
    
    def drawIndices(self, qp):
        '''
        Draws the non-parcel indices.
        
        Parameters
        ----------
        qp: QtGui.QPainter object
        
        '''
        qp.setFont(self.label_font)
        ## make the initial x point relatice to the width of the frame.
        x1 = self.brx / 10
        rpad = 5
        tpad = 5

        ## Now we have all the data we could ever want. Time to start drawing
        ## them on the frame.
        ## This starts with the left column.
        pwat = float(self.pwat) * 25.4
        if pwat > 50:
            color = QtGui.QColor('#00EE00')
        elif pwat > 40:
            color = QtGui.QColor('#00AA00')
        else:
            color = QtGui.QColor('#FFFFFF')

        ## draw the first column of text using a loop, keeping the horizontal
        ## placement constant.
        y1 = self.ylast + self.tpad
        colors = [color, QtGui.QColor(WHITE), QtGui.QColor(WHITE), QtGui.QColor(WHITE), QtGui.QColor(WHITE), QtGui.QColor(WHITE)]
        texts = ['PWat = ', 'MeanW = ', 'LowRH = ', 'MidRH = ', 'DCAPE = ', 'DownT = ']
        indices = [tab.utils.FLOAT2STR(pwat, 1) + 'mm', self.mean_mixr + 'g/Kg', self.low_rh + '%', self.mid_rh + '%', self.dcape, self.drush + 'F']
        for text, index, c in zip(texts, indices, colors):
            rect = QtCore.QRect(rpad, y1, x1*4, self.label_height)
            pen = QtGui.QPen(c, 1, QtCore.Qt.SolidLine)
            qp.setPen(pen)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignLeft, text + index)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace

        ## middle-left column
        y1 = self.ylast + self.tpad
        texts = ['K = ', 'TT = ', 'ConvT = ', 'maxT = ', 'ESP = ', 'MMP = ']
        indices = [self.k_idx, self.totals_totals, self.convT + 'F', self.maxT + 'F', self.esp, self.mmp]
        for text, index in zip(texts, indices):
            rect = QtCore.QRect(x1*3.5, y1, x1*4, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignLeft, text + index)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace

        ## middle-right column
        y1 = self.ylast + self.tpad
        texts = ['WNDG = ', 'TEI = ', '3CAPE = ', 'MBurst = ', '', 'SigSvr = ']
        indices = [self.wndg, self.tei, tab.utils.INT2STR(self.prof.mlpcl.b3km), tab.utils.INT2STR(self.prof.mburst), '', self.sigsevere + ' m3/s3']
        for text, index in zip(texts, indices):
            rect = QtCore.QRect(x1*6, y1, x1*4, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignLeft, text + index)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace
            self.ylast = y1
        qp.drawLine(0, y1+2, self.brx, y1+2)
        qp.drawLine(x1*6-5, y1+2, x1*6-5, self.bry )
        
        ## lapserate window
        y1 = self.ylast + self.tpad
        texts = ['Sup-3km AGL LR = ', '3-6km AGL LR = ', '850-500mb LR = ', '700-500mb LR = ']
        indices = [self.lapserate_3km + ' C/km', self.lapserate_3_6km + ' C/km', self.lapserate_850_500 + ' C/km', self.lapserate_700_500 + ' C/km']
        for text, index in zip(texts, indices):
            rect = QtCore.QRect(rpad, y1, x1*8, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignLeft, text + index)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace


    def drawConvectiveIndices(self, qp):
        '''
        This handles the drawing of the parcel indices.
        
        Parameters
        ----------
        qp: QtGui.QPainter object
        
        '''
        ## initialize a white pen with thickness 2 and a solid line
        pen = QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine)
        qp.setPen(pen)
        qp.setFont(self.label_font)
        ## make the initial x pixel coordinate relative to the frame
        ## width.
        x1 = self.brx / 8
        y1 = self.ylast + self.tpad
        ## get the indices rounded to the nearest int, conver to strings
        ## Start with the surface based parcel.
        capes = np.empty(4, dtype="S10") # Only allow 4 parcels to be displayed
        cins = np.empty(4, dtype="S10")
        lcls = np.empty(4, dtype="S10")
        lis = np.empty(4, dtype="S10")
        lfcs = np.empty(4, dtype="S10")
        els = np.empty(4, dtype="S10")
        texts = self.pcl_types
        for i, key in enumerate(texts):
            parcel = self.parcels[key]
            capes[i] = tab.utils.INT2STR(parcel.bplus) # Append the CAPE value
            cins[i] = tab.utils.INT2STR(parcel.bminus)
            lcls[i] = tab.utils.INT2STR(parcel.lclhght)
            lis[i] = tab.utils.INT2STR(parcel.li5)
            lfcs[i] = tab.utils.INT2STR(parcel.lfchght)
            els[i] = tab.utils.INT2STR(parcel.elhght)
        ## Now that we have all the data, time to plot the text in their
        ## respective columns.
        
        ## PCL type
        pcl_index = 0
        for i, text in enumerate(texts):
            self.bounds[i,0] = y1
            if text == self.pcl_types[self.skewt_pcl]:
                pen = QtGui.QPen(QtCore.Qt.cyan, 1, QtCore.Qt.SolidLine)
                qp.setPen(pen)
                pcl_index = i
            else:
                pen = QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine)
                qp.setPen(pen)
            rect = QtCore.QRect(0, y1, x1*2, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignCenter, text)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace
            self.bounds[i,1] = y1
        ## CAPE
        y1 = self.ylast + self.tpad
        for i, text in enumerate(capes):
            try:
                if pcl_index == i and int(text) >= 4000:
                    color = QtCore.Qt.magenta
                elif pcl_index == i and int(text) >= 3000:
                    color=QtCore.Qt.red
                elif pcl_index == i and int(text) >= 2000:
                    color=QtCore.Qt.yellow
                else:
                    color=QtCore.Qt.white
            except:
                color=QtCore.Qt.white
            pen = QtGui.QPen(color, 1, QtCore.Qt.SolidLine)
            qp.setPen(pen)
            rect = QtCore.QRect(x1*1, y1, x1*2, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignCenter, text)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace
        ## CINH
        y1 = self.ylast + self.tpad
        for i, text in enumerate(cins):
            try:
                if int(capes[i]) > 0 and pcl_index == i and int(text) >= -50:
                    color = QtCore.Qt.green
                elif int(capes[i]) > 0 and pcl_index == i and int(text) >= -100:
                    color=QtGui.QColor('#996600')
                elif int(capes[i]) > 0 and pcl_index == i and int(text) < -100:
                    color=QtGui.QColor('#993333')
                else:
                    color=QtCore.Qt.white
            except:
                color=QtCore.Qt.white
            pen = QtGui.QPen(color, 1, QtCore.Qt.SolidLine)
            qp.setPen(pen)
            rect = QtCore.QRect(x1*2, y1, x1*2, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignCenter, text)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace

        ## LCL
        y1 = self.ylast + self.tpad
        for i, text in enumerate(lcls):
            try:
                if int(text) < 1000 and pcl_index == i and texts[i] == "ML":
                    color = QtCore.Qt.green
                elif int(text) < 1500 and pcl_index == i and texts[i] == "ML":
                    color=QtGui.QColor('#996600')
                elif int(text) < 2000 and pcl_index == i and texts[i] == "ML":
                    color=QtGui.QColor('#993333')
                else:
                    color=QtCore.Qt.white
            except:
                color=QtCore.Qt.white
            pen = QtGui.QPen(color, 1, QtCore.Qt.SolidLine)
            qp.setPen(pen)
            rect = QtCore.QRect(x1*3, y1, x1*2, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignCenter, text)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace

        pen = QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine)
        qp.setPen(pen)
        ## LI
        y1 = self.ylast + self.tpad
        for text in lis:
            rect = QtCore.QRect(x1*4, y1, x1*2, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignCenter, text)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace
        ## LFC
        y1 = self.ylast + self.tpad
        for text in lfcs:
            rect = QtCore.QRect(x1*5, y1, x1*2, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignCenter, text)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace
        ## EL
        y1 = self.ylast + self.tpad
        for text in els:
            rect = QtCore.QRect(x1*6, y1, x1*2, self.label_height)
            qp.drawText(rect, QtCore.Qt.TextDontClip | QtCore.Qt.AlignCenter, text)
            vspace = self.label_height
            if platform.system() == "Windows":
                vspace += self.label_metrics.descent() + 1
            y1 += vspace
            self.ylast = y1
        qp.drawLine(0, y1+2, self.brx, y1+2)
        color=QtGui.QColor('#996633')
        pen = QtGui.QPen(color, .5, QtCore.Qt.SolidLine)
        qp.setPen(pen)
        qp.drawLine(2, self.bounds[self.skewt_pcl,0]-1, x1*6 + x1*2 - 1, self.bounds[self.skewt_pcl,0]-1)
        qp.drawLine(2, self.bounds[self.skewt_pcl,0]-1, 2, self.bounds[self.skewt_pcl,1])
        qp.drawLine(2, self.bounds[self.skewt_pcl,1], x1*6 + x1*2 - 1, self.bounds[self.skewt_pcl,1])
        qp.drawLine(x1*6 + x1*2 -1 , self.bounds[self.skewt_pcl,0]-1, x1*6 + x1*2 -1, self.bounds[self.skewt_pcl,1])


    def mousePressEvent(self, e):
        pos = e.pos()
        for i, bound in enumerate(self.bounds):
            if bound[0] < pos.y() and bound[1] > pos.y():
                self.skewt_pcl = i
                self.ylast = self.label_height
                pcl_to_pass = self.parcels[self.pcl_types[self.skewt_pcl]]
                self.updatepcl.emit(pcl_to_pass)
                self.clearData()
                self.plotBackground()
                self.plotData()
                self.update()
                self.parentWidget().setFocus()
                break

class SelectParcels(QWidget):
    def __init__(self, parcel_types, parent):
        QWidget.__init__(self)
        self.thermo = parent
        self.parcel_types = parcel_types
        self.max_pcls = 4
        self.pcl_count = 0
        self.initUI()

    def initUI(self):

        self.sb = QtGui.QCheckBox('Parcela de superficie', self)
        self.sb.move(20, 20)
        if "SFC" in self.parcel_types:
            self.sb.toggle()
            self.pcl_count += 1
        self.sb.stateChanged.connect(self.changeParcel)

        self.ml = QtGui.QCheckBox('Parcela de mezcla (100 hPa)', self)
        self.ml.move(20, 40)
        if "ML" in self.parcel_types:
            self.ml.toggle()
            self.pcl_count += 1
        self.ml.stateChanged.connect(self.changeParcel)

        self.fcst = QtGui.QCheckBox('Parcela de sup. pronost.', self)
        self.fcst.move(20, 60)
        if "FCST" in self.parcel_types:
            self.fcst.toggle()
            self.pcl_count += 1
        self.fcst.stateChanged.connect(self.changeParcel)

        self.mu = QtGui.QCheckBox('Parcela mas inestable', self)
        self.mu.move(20, 80)
        if "MU" in self.parcel_types:
            self.mu.toggle()
            self.pcl_count += 1
        self.mu.stateChanged.connect(self.changeParcel)

        self.eff = QtGui.QCheckBox('Parcela de afluencia efectiva', self)
        self.eff.move(20, 100)
        if "EFF" in self.parcel_types:
            self.eff.toggle()
            self.pcl_count += 1
        self.eff.stateChanged.connect(self.changeParcel)

        self.usr = QtGui.QCheckBox('Parcela personalizada', self)
        self.usr.move(20, 120)
        if "USER" in self.parcel_types:
            self.usr.toggle()
            self.pcl_count += 1
        self.usr.stateChanged.connect(self.changeParcel)


        self.setGeometry(300, 300, 250, 180)
        self.setWindowTitle('Ver parcelas')
        self.ok = QtGui.QPushButton('Ok', self)
        self.ok.move(20,150)
        self.ok.clicked.connect(self.okPushed)

        #cb.stateChanged.connect(self.changeTitle)
    #cb.stateChanged.connect(

    def changeParcel(self, state):
        if state == QtCore.Qt.Checked:
            self.pcl_count += 1
        else:
            self.pcl_count -= 1

    def okPushed(self):
        if self.pcl_count > self.max_pcls:
            msgBox = QMessageBox()
            msgBox.setText("You can only show 4 parcels at a time.\nUnselect some parcels.")
            msgBox.exec_()
        elif self.pcl_count != self.max_pcls:
            msgBox = QMessageBox()
            msgBox.setText("You need to select 4 parcels to show.  Select some more.")
            msgBox.exec_()
        else:
            self.parcel_types = []
            if self.sb.isChecked() is True:
                self.parcel_types.append('SFC')
            if self.ml.isChecked() is True:
                self.parcel_types.append('ML')
            if self.fcst.isChecked() is True:
                self.parcel_types.append('FCST')
            if self.mu.isChecked() is True:
                self.parcel_types.append('MU')
            if self.eff.isChecked() is True:
                self.parcel_types.append('EFF')
            if self.usr.isChecked() is True:
                self.parcel_types.append('USER')

            self.thermo.pcl_types = self.parcel_types
            self.thermo.skewt_pcl = 0
            self.thermo.ylast = self.thermo.label_height
            pcl_to_pass = self.thermo.parcels[self.thermo.pcl_types[self.thermo.skewt_pcl]]
            self.thermo.updatepcl.emit(pcl_to_pass)
            self.thermo.clearData()
            self.thermo.plotBackground()
            self.thermo.plotData()
            self.thermo.update()
            self.thermo.parentWidget().setFocus()
            self.hide()
