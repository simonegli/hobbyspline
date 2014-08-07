## Metapolator's Hobby Spline as Robofont plugin
## Contributors: Juraj Sukop, Lasse Fister, Simon Egli

import vanilla

from math import atan2, degrees, pi, sin, cos, radians 
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.extensions import getExtensionDefault, setExtensionDefault
from cmath import e, sqrt

from mojo.UI import UpdateCurrentGlyphView
from mojo.glyphPreview import GlyphPreview
from mojo.events import addObserver, removeObserver

from MojoDrawingToolsPen import MojoDrawingToolsPen
from mojo.drawingTools import save, restore, stroke, fill, strokeWidth
from vanilla import *


extensionID = "com.metapolator"
        
def arg(x): # phase
    return atan2(x.imag, x.real)
    
def hobby(theta, phi):
    st, ct = sin(theta), cos(theta)
    sp, cp = sin(phi), cos(phi)
    return \
            (2 + sqrt(2) * (st - 1/16*sp) * (sp - 1/16*st) * (ct - cp)) / \
            (3 * (1 + 0.5*(sqrt(5) - 1) * ct + 0.5*(3 - sqrt(5)) * cp))
        
def controls(z0, w0, alpha, beta, w1, z1):
    theta = arg(w0 / (z1 - z0))
    phi = arg((z1 - z0) / w1)
    u = z0 + e**(0+1j * theta) * (z1 - z0) * hobby(theta, phi) / alpha
    v = z1 - e**(0-1j * phi) * (z1 - z0) * hobby(phi, theta) / beta
    return u, v
        
        
class metapolator(BaseWindowController):
    
    def __init__(self):

        
        addObserver(self, "_curvePreview", "draw")
        addObserver(self, "_curvePreview", "drawInactive")
        addObserver(self, "_currentGlyphChanged", "currentGlyphChanged")
                
        self.methods = {
            0: "fl",
            4: "free",
        }
        
        self.methodNames = [
            "Tension:"
        ]
        
        
        height = 80
        
        self.w = vanilla.FloatingWindow((300, height), "Hobby's Spline")
        
        y = -200
        self.w.hobbyMethodSelector = vanilla.RadioGroup((10, y, -10, 108),
            titles = "Circle",
            callback=self._changeMethod,
            sizeStyle="small"
        )
        
        y = 10
        
        self.w.HobbySlider = Slider((15, y, -15, 25),
            tickMarkCount=4,

            callback=self._changetension,
            minValue=0.5,
            maxValue=1.0,
            sizeStyle="small",
            continuous=True
        )
        
        y = height - 32
        self.w.hobbycurveButton = vanilla.Button((60, y , -60, 25), "transform selected curves",
            callback=self._hobbycurve,
            sizeStyle="small",
        )
        
        self.w.hobbyMethodSelector.set(getExtensionDefault("%s.%s" %(extensionID, "method"), 0))
        self.method = self.methods[self.w.hobbyMethodSelector.get()]
        self._checkSecondarySelectors()
        
        self.w.HobbySlider.set(getExtensionDefault("%s.%s" %(extensionID, "tension"), 0.5))
        self.tension = self.w.HobbySlider.get()
  
        self.tmp_glyph = RGlyph()
        UpdateCurrentGlyphView()
        
        self.setUpBaseWindowBehavior()
        self.w.open()
        
        
    def _changeMethod(self, sender):
        choice = sender.get()
        self.method = self.methods[choice]
        self._checkSecondarySelectors()
        UpdateCurrentGlyphView()

    def _changeCurvature(self, sender):
        choice = sender.get()
        self.curvature = self.curvatures[choice]
        UpdateCurrentGlyphView()
    
    def _changetension(self, sender):
        self.tension = sender.get()
        UpdateCurrentGlyphView()
    
    def _currentGlyphChanged(self, sender):
        UpdateCurrentGlyphView()

    def _checkSecondarySelectors(self):
 
        if self.method == "free":
            self.w.HobbySlider.enable(True)

    def _curvePreview(self, info):
        _doodle_glyph = info["glyph"]

        if _doodle_glyph is not None and len(_doodle_glyph.components) == 0 and _doodle_glyph.selection != []:
            self.tmp_glyph.clear()
            self.tmp_glyph.appendGlyph(_doodle_glyph)
            self._hobbycurve()
            pen = MojoDrawingToolsPen(self.tmp_glyph, _doodle_glyph.getParent())
            save()
            stroke(0, 0, 0, 0.5)
            fill(1, 0, 0, 0.9)
            strokeWidth(info["scale"])
            self.tmp_glyph.draw(pen)
            pen.draw()
            restore()
            UpdateCurrentGlyphView()


    def spline(self, p0, p1, p2, p3, curvature=1.75):
        delta0 = complex(p1.x, p1.y) - complex(p0.x, p0.y)  
        rad0 = atan2(delta0.real, delta0.imag)
        w0 = complex(sin(rad0), cos(rad0))
        delta1 = complex(p3.x, p3.y) - complex(p2.x, p2.y) 
        rad1 = atan2(delta1.real, delta1.imag)
        w1 = complex(sin(rad1), cos(rad1))
        alpha, beta = 1 * curvature, 1 * curvature
        u, v = controls(complex(p0.x, p0.y), w0, alpha, beta, w1, complex(p3.x, p3.y))
        p1.x, p1.y = u.real, u.imag
        p2.x, p2.y = v.real, v.imag
        return p1, p2
                    
    def _hobbycurve(self, sender=None):
        reference_glyph = CurrentGlyph()

        if reference_glyph.selection != []:
            if sender is None:
                modify_glyph = self.tmp_glyph
            else:
                modify_glyph = reference_glyph
                reference_glyph.prepareUndo(undoTitle="spline /%s" % reference_glyph.name)
            for contourIndex in range(len(reference_glyph.contours)):
                reference_contour = reference_glyph.contours[contourIndex]
                modify_contour = modify_glyph.contours[contourIndex]
                for i in range(len(reference_contour.segments)):
                    reference_segment = reference_contour[i]
                    modify_segment = modify_contour[i]
                    if reference_segment.selected and reference_segment.type == "curve":
                        # last point of the previous segment
                        p0 = modify_contour[i-1][-1]
                        p1, p2, p3 = modify_segment.points

                        p1, p2 = self.spline(p0, p1, p2, p3, self.tension)

                        if sender is not None:
                            p1.round()
                            p2.round()
            reference_glyph.update()
            if sender is not None:
                reference_glyph.performUndo()    
 
    
    def windowCloseCallback(self, sender):
        removeObserver(self, "draw")
        removeObserver(self, "drawInactive")
        removeObserver(self, "currentGlyphChanged")
        setExtensionDefault("%s.%s" % (extensionID, "tension"), self.w.HobbySlider.get())
        super(metapolator, self).windowCloseCallback(sender)
        UpdateCurrentGlyphView()
     

OpenWindow(metapolator)