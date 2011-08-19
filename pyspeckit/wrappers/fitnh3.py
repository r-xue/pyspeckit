"""
Wrapper to fit ammonia spectra.  Generates a reasonable guess at the position and velocity using a gaussian fit
"""
import pyspeckit
from matplotlib import pyplot 

def fitnh3tkin(input_dict, dobaseline=True, baselinekwargs={}, crop=False, guessline='twotwo',
        tex=20,tkin=15,column=15.0,fortho=0.66, tau11=None, thin=False, quiet=False, doplot=True, fignum=1,
        guessfignum=2, smooth=False,
        **kwargs): 
    """
    Given a dictionary of filenames and lines, fit them together
    e.g. {'oneone':'G000.000+00.000_nh3_11.fits'}
    """
    spdict = dict([ (linename,pyspeckit.Spectrum(value)) if type(value) is str else (linename,value) for linename, value in input_dict.iteritems() ])
    splist = spdict.values()

    for sp in splist: # required for plotting, cropping
        sp.xarr.convert_to_unit('km/s')

    if dobaseline:
        for sp in splist:
            sp.baseline(**baselinekwargs)

    if crop and len(crop) == 2:
        for sp in splist:
            sp.crop(*crop)

    if smooth and type(smooth) is int:
        for sp in splist:
            sp.smooth(smooth)

    spdict[guessline].specfit(fittype='gaussian',negamp=False)
    ampguess,vguess,widthguess = spdict[guessline].specfit.modelpars
    print "RMS guess: ",spdict[guessline].specfit.errspec.mean()
    print "RMS guess: ",spdict[guessline].specfit.residuals.std()
    errguess = spdict[guessline].specfit.errspec.mean()
    
    for sp in splist:
        sp.error[:] = errguess

    spdict[guessline].plotter(figure=guessfignum)
    spdict[guessline].specfit.plot_fit()

    spectra = pyspeckit.Spectra(splist)

    spectra.specfit(fittype='ammonia',quiet=quiet,multifit=True,guesses=[tkin,tex,column,widthguess,vguess,fortho], thin=thin, **kwargs)

    for sp in splist:
        sp.xarr.convert_to_unit('km/s',quiet=True)
        sp.specfit.fitter = spectra.specfit.fitter
        sp.specfit.modelpars = spectra.specfit.modelpars
        sp.specfit.npeaks = spectra.specfit.npeaks
        sp.specfit.model = pyspeckit.models.ammonia.ammonia(sp.xarr, *spectra.specfit.modelpars)

    if doplot:
        plot_nh3(spdict,spectra,fignum=fignum)

    return spdict,spectra

def plot_nh3(spdict,spectra,fignum=1, show_components=False, residfignum=None, **plotkwargs):
    """
    Plot the results from a multi-nh3 fit
    """ 
    pyplot.figure(fignum)
    pyplot.clf()
    splist = spdict.values()
    if len(splist) == 2:
        axdict = { 'oneone':pyplot.subplot(211), 'twotwo':pyplot.subplot(212) }
    elif len(splist) == 3:
        axdict = { 'oneone':pyplot.subplot(211), 'twotwo':pyplot.subplot(223), 'threethree':pyplot.subplot(224), 'fourfour':pyplot.subplot(224) }
    elif len(splist) == 4:
        axdict = { 'oneone':pyplot.subplot(221), 'twotwo':pyplot.subplot(222), 'threethree':pyplot.subplot(223), 'fourfour':pyplot.subplot(224) }
    for linename,sp in spdict.iteritems():
        sp.plotter(axis=axdict[linename],title=linename, **plotkwargs)
        sp.specfit.selectregion(reset=True)
        sp.specfit.plot_fit(annotate=False, show_components=show_components)
    spdict['oneone'].specfit.annotate(labelspacing=0.05,prop={'size':'small','stretch':'extra-condensed'},frameon=False)

    if residfignum is not None:
        pyplot.figure(residfignum)
        pyplot.clf()
        if len(splist) == 2:
            axdict = { 'oneone':pyplot.subplot(211), 'twotwo':pyplot.subplot(212) }
        elif len(splist) == 3:
            axdict = { 'oneone':pyplot.subplot(211), 'twotwo':pyplot.subplot(223), 'threethree':pyplot.subplot(224), 'fourfour':pyplot.subplot(224) }
        elif len(splist) == 4:
            axdict = { 'oneone':pyplot.subplot(221), 'twotwo':pyplot.subplot(222), 'threethree':pyplot.subplot(223), 'fourfour':pyplot.subplot(224) }
        for linename,sp in spdict.iteritems():
            sp.specfit.plotresiduals(axis=axdict[linename])



def fitnh3(spectrum, vrange=[-100,100], vrangeunits='km/s', quiet=False,
        Tex=20,Tkin=15,column=1e15,fortho=1.0): 

    if vrange:
        spectrum.xarr.convert_to_unit(vrangeunits)
        spectrum.crop(*vrange)

    spectrum.specfit(fittype='gaussian',negamp=False)
    ampguess,vguess,widthguess = spectrum.specfit.modelpars

    spectrum.specfit(fittype='ammonia',quiet=quiet,multifit=True,guesses=[Tex,Tkin,column,widthguess,vguess,fortho])

    return spectrum
