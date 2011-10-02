"""
Author: Adam Ginsburg
Created: 3/17/2011
"""
# import parent package
import pyspeckit
from pyspeckit import spectrum
# import local things
import mapplot
import readers
import time
import numpy as np

class Cube(spectrum.Spectrum):

    def __init__(self,filename, x0=0, y0=0, **kwargs):
        """
        Initialize the Cube.  Accepts files in the following formats:
            - .fits

        x0,y0 - initial spectrum to use (defaults to lower-left corner)
        """

        if ".fit" in filename: # allow .fit or .fits
            try: 
                self.cube,self.xarr,self.header,self.fitsfile = readers.open_3d_fits(filename, **kwargs)
                self.data = self.cube[:,y0,x0]
                self.error = None
                self.parse_header(self.header)
            except TypeError as inst:
                print "Failed to read fits file: wrong TYPE."
                print inst
                raise inst
        else:
            raise TypeError('Not a .fits cube - what type of file did you give it?')

        self.fileprefix = filename.rsplit('.', 1)[0]    # Everything prior to .fits or .txt
        self.plotter = spectrum.plotters.Plotter(self)
        self._register_fitters()
        self.specfit = spectrum.fitters.Specfit(self,Registry=self.Registry)
        self.baseline = spectrum.baseline.Baseline(self)
        self.speclines = spectrum.speclines
        # Initialize writers
        self.writer = {}
        for writer in spectrum.writers.writers: self.writer[writer] = spectrum.writers.writers[writer](self)
        self.mapplot = mapplot.MapPlotter(self)

    def plot_spectrum(self, x, y, **kwargs):
        """
        Fill the .data array with a real spectrum and plot it
        """

        self.data = self.cube[:,x,y]

        self.plotter(**kwargs)

    def plot_apspec(self, aperture, coordsys=None, reset_ylimits=True, **kwargs):
        """
        Extract an aperture using cubes.extract_aperture
        (defaults to Cube coordinates)
        """

        self.set_apspec(aperture, coordsys=coordsys)
        self.plotter(reset_ylimits=reset_ylimits, **kwargs)

    def get_spectrum(self, x, y):
        """
        Very simple: get the spectrum at coordinates x,y

        Returns a SpectroscopicAxis instance
        """
        return pyspeckit.Spectrum( xarr=self.xarr.copy(), data = self.cube[:,x,y],
                header=self.header)

    def get_apspec(self, aperture, coordsys=None):
        """
        Extract an aperture using cubes.extract_aperture
        (defaults to Cube coordinates)
        """

        import cubes
        if coordsys is not None:
            return pyspeckit.Spectrum(xarr=self.xarr.copy(), data=cubes.extract_aperture( self.cube, aperture , coordsys=coordsys , wcs=self.mapplot.wcs ), header=self.header)
        else:
            return pyspeckit.Spectrum(xarr=self.xarr.copy(), data=cubes.extract_aperture( self.cube, aperture , coordsys=None), header=self.header)

    def set_apspec(self, aperture, coordsys=None):
        """
        Extract an aperture using cubes.extract_aperture
        (defaults to Cube coordinates)
        """

        import cubes
        if coordsys is not None:
            self.data = cubes.extract_aperture( self.cube, aperture , coordsys=coordsys , wcs=self.mapplot.wcs )
        else:
            self.data = cubes.extract_aperture( self.cube, aperture , coordsys=None)

    def fiteach(self, errspec=None, errmap=None, guesses=(), verbose=True,
            verbose_level=1, quiet=True, signal_cut=3, usemomentcube=False,
            blank_value=0, integral=True, direct=False, **fitkwargs):
        """
        Fit a spectrum to each valid pixel in the cube
        """

        if not hasattr(self.mapplot,'plane'):
            print "Must mapplot before fitting."
            return

        yy,xx = np.indices(self.mapplot.plane.shape)
        if isinstance(self.mapplot.plane, np.ma.core.MaskedArray): 
            OK = (True-self.mapplot.plane.mask)
        else:
            OK = np.isfinite(self.mapplot.plane)
        valid_pixels = zip(xx[OK],yy[OK])

        if usemomentcube:
            npars = self.momentcube.shape[0]
        else:
            npars = len(guesses)

        self.parcube = np.zeros((npars,)+self.mapplot.plane.shape)
        self.errcube = np.zeros((npars,)+self.mapplot.plane.shape) 
        if integral: self.integralmap = np.zeros(self.mapplot.plane.shape)

        t0 = time.time()

        for ii,(x,y) in enumerate(valid_pixels):
            sp = self.get_spectrum(y,x)
            if errspec is not None:
                sp.error = errspec
            elif errmap is not None:
                sp.error = np.ones(sp.data.shape) * errmap[y,x]
            if sp.error is not None and signal_cut > 0:
                max_sn = (sp.data / sp.error).max()
                if max_sn < signal_cut:
                    if verbose_level > 1:
                        print "Skipped %i,%i" % (x,y)
                    continue
            sp.specfit.Registry = self.Registry # copy over fitter registry
            
            if usemomentcube:
                guesses = self.momentcube[:,y,x]

            sp.specfit(guesses=guesses,quiet=True, verbose=False, **fitkwargs)
            self.parcube[:,y,x] = sp.specfit.modelpars
            self.errcube[:,y,x] = sp.specfit.modelerrs
            if integral: self.integralmap[y,x] = sp.specfit.integral(direct=direct)
        
            if blank_value != 0:
                self.errcube[self.parcube == 0] = blank_value
                self.parcube[self.parcube == 0] = blank_value

            if verbose:
                if ii % 10**(3-verbose_level) == 0:
                    print "Finished fit %i.  Elapsed time is %i seconds" % (ii, time.time()-t0)

        if verbose:
            print "Finished final fit %i.  Elapsed time was %i seconds" % (ii, time.time()-t0)


    def momenteach(self, verbose=True, verbose_level=1, **kwargs):
        """
        Return a cube of the moments of each pixel
        """

        yy,xx = np.indices(self.mapplot.plane.shape)
        if isinstance(self.mapplot.plane, np.ma.core.MaskedArray): 
            OK = (True-self.mapplot.plane.mask)
        else:
            OK = np.isfinite(self.mapplot.plane)
        valid_pixels = zip(xx[OK],yy[OK])

        _temp_moment = self.get_spectrum(yy[OK][0],xx[OK][0]).moments(**kwargs)

        self.momentcube = np.zeros((len(_temp_moment),)+self.mapplot.plane.shape)

        t0 = time.time()

        for ii,(x,y) in enumerate(valid_pixels):
            sp = self.get_spectrum(y,x)
            self.momentcube[:,y,x] = sp.moments(**kwargs)
            if verbose:
                if ii % 10**(3-verbose_level) == 0:
                    print "Finished moment %i.  Elapsed time is %i seconds" % (ii, time.time()-t0)

        if verbose:
            print "Finished final moment %i.  Elapsed time was %i seconds" % (ii, time.time()-t0)

