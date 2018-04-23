from sharppy.sharptab import thermo, utils, interp, params, constants
import sharppy.sharptab as tab
import numpy as np

## Routines implemented in Python by Greg Blumberg - CIMMS and Kelton Halbert (OU SoM)
## wblumberg@ou.edu, greg.blumberg@noaa.gov, kelton.halbert@noaa.gov, keltonhalbert@ou.edu

def wind_chill(prof):
    '''
        Surface Wind Chill Equation

        Computes wind chill at the surface data point in the profile object
        using the equation found at:

        www.nws.noaa.gov/os/windchill/index.shtml

        Parameters
        ----------
        prof : Profile object

        Returns
        -------
        wind_chill : wind chill value in (F)
    '''
    # Needs to be tested

    sfc_temp = thermo.ctof(prof.tmpc[prof.get_sfc()])
    sfc_wspd = utils.KTS2MPH(prof.wspd[prof.get_sfc()])

    wind_chill = 35.74 + (0.6215*sfc_temp) - (35.75*(sfc_wspd**0.16)) + \
                 0.4275 * (sfc_temp) * (sfc_wspd**0.16)
    return wind_chill

def init_phase(prof):
    '''
        Inital Precipitation Phase
        Adapted from SHARP code donated by Rich Thompson (SPC)

        This function determines the initial phase of any precipitation source in the profile.
        It does this either by finding a source of precipitation by searching for the highest 50 mb 
        layer that has a relative humidity greater than 80 percent at the top and the bottom
        of the layer.  This layer may be found either in the lowest 5 km of the profile, and if
        an OMEG profile is specified in the profile object, it will search for the layers with
        upward motion.

        The precipitation type is determined by using a.) the interpolated temperature in the middle
        of the precipitation source layer and b.) set temperature thresholds to determine the 
        precipitation type.  The type may be "Rain", "Freezing Rain", "ZR/S Mix", or "Snow".

        Parameters
        ----------
        prof : Profile object (omega profile optional)

        Returns
        -------
        plevel : the pressure level of the precipitation source (mb)
        phase : the phase type of the precipitation (int)
                phase == 0 for "Rain"
                phase == 1 for "Freezing Rain" or "ZR/S Mix"
                phase == 3 for "Snow"
        tmp : the temperature at the level that is the precipitation source
        st : a string naming the precipitation type

    '''
    # Needs to be tested

    plevel = 0
    phase = -1

    # First, determine whether Upward VVELS are available.  If they are,  
    # use them to determine level where precipitation will develop.
    avail = np.ma.where(prof.omeg < .1)[0]

    hght_agl = interp.to_agl(prof, prof.hght)
    if len(avail) < 5:
        # No VVELS...must look for saturated level 
        # Find the highest near-saturated 50mb layer below 5km agl
        below_5km_idx = np.ma.where((hght_agl < 5000.) &\
                                    (hght_agl >= 0))[0]

    else:
        # Use the VV to find the source of precip.
        below_5km_idx = np.ma.where((hght_agl < 5000.) &\
                                    (hght_agl >= 0) &\
                                    (prof.omeg <= 0))[0]

    # Compute the RH at the top and bottom of 50 mb layers
    rh = thermo.relh(prof.pres, prof.tmpc, prof.dwpc)[below_5km_idx]
    sats = np.ma.where(rh > 80)[0]
    new_pres = prof.pres[below_5km_idx][sats] + 50.
    new_temp = interp.temp(prof, new_pres)
    new_dwpt = interp.dwpt(prof, new_pres)
    rh_plus50 = thermo.relh(new_pres, new_temp, new_dwpt)
    # Find layers where the RH is >80% at the top and bottom
    layers_idx = np.ma.where(rh_plus50 > 80)[0]

    if len(layers_idx) == 0:
        # Found no precipitation source layers
        st = "N/A"
        return prof.missing, phase, prof.missing, st

    # Find the highest layer up via the largest index
    top_most_layer = np.ma.max(layers_idx)
    plevel = new_pres[top_most_layer] - 25.

    # Determine the initial precip type based on the temp in the layer
    tmp = interp.temp(prof, plevel)
    if tmp > 0:
        phase = 0
        st = "Rain"
    elif tmp <= 0 and tmp > -5:
        phase = 1
        st = "Freezing Rain"
    elif tmp <=-5 and tmp > -9:
        phase = 1
        st = "ZR/S Mix"
    elif tmp <= -9:
        phase = 3
        st = "Snow"
    else:
        st = "N/A"

    return plevel, phase, tmp, st

def posneg_temperature(prof, start=-1):
    '''
        Positive/Negative Temperature profile
        Adapted from SHARP code donated by Rich Thompson (SPC)

        Description:
        This routine calculates the positive (above 0 C) and negative (below 0 C)
        areas of the temperature profile starting from a specified pressure (start).
        If the specified pressure is not given, this routine calls init_phase()
        to obtain the pressure level the precipitation expected to fall begins at.

        This is an routine considers only the temperature profile as opposed to the wet-bulb
        profile.

        Parameters
        ----------
        prof : Profile object
        start : the pressure level the precpitation originates from (found by calling init_phase())

        Returns
        -------
        pos : the positive area (> 0 C) of the temperature profile in J/kg
        neg : the negative area (< 0 C) of the temperature profile in J/kg
        top : the top of the precipitation layer pressure in mb
        bot : the bottom of the precipitation layer pressure in mb

    '''
    # Needs to be tested
    
    # If there is no sounding, don't compute anything
    if utils.QC(interp.temp(prof, 500)) == False and utils.QC(interp.temp(prof, 850)) == False:
        return np.masked, np.masked, np.masked, np.masked

    # Find lowest obs in layer
    lower = prof.pres[prof.get_sfc()]
    lptr  = prof.get_sfc()

    # Find the highest obs in the layer
    if start == -1:
        lvl, phase, st = init_phase(prof)
        if lvl > 0:
            upper = lvl
        else:
            upper = 500.
    else:
        upper = start

    # Find the level where the pressure is just greater than the upper pressure
    idxs = np.where(prof.pres > upper)[0]
    if len(idxs) == 0:
        uptr = 0
    else:
        uptr = idxs[-1]

    # Start with the top layer
    pe1 = upper;
    h1 =  interp.hght(prof, pe1)
    te1 = interp.temp(prof, pe1)
    tp1 = 0

    warmlayer = coldlayer = lyre = totp = totn = tote = ptop = pbot = lyrlast = 0

    for i in np.arange(uptr, lptr-1, -1):
        pe2 = prof.pres[i]
        h2 = prof.hght[i]
        te2 = interp.temp(prof, pe2)
        tp2 = 0
        tdef1 = (0 - te1) / thermo.ctok(te1);
        tdef2 = (0 - te2) / thermo.ctok(te2);
        lyrlast = lyre;
        lyre = 9.8 * (tdef1 + tdef2) / 2.0 * (h2 - h1);

        # Has a warm layer been found yet?
        if te2 > 0:
            if warmlayer == 0:
                warmlayer = 1
                ptop = pe2

        # Has a cold layer been found yet?
        if te2 < 0:
            if warmlayer == 1 and coldlayer == 0:
                coldlayer = 1
                pbot = pe2

        if warmlayer > 0:
            if lyre > 0:
                totp += lyre
            else:
                totn += lyre
            tote += lyre

        pelast = pe1
        pe1 = pe2
        h1 = h2
        te1 = te2
        tp1 = tp2
    
    if warmlayer == 1 and coldlayer == 1:
        pos = totp
        neg = totn
        top = ptop
        bot = pbot
    else:
        neg = 0
        pos = 0
        bot = 0
        top = 0

    return pos, neg, top, bot


def posneg_wetbulb(prof, start=-1):
    '''
        Positive/Negative Wetbulb profile
        Adapted from SHARP code donated by Rich Thompson (SPC)

        Description:
        This routine calculates the positive (above 0 C) and negative (below 0 C)
        areas of the wet bulb profile starting from a specified pressure (start).
        If the specified pressure is not given, this routine calls init_phase()
        to obtain the pressure level the precipitation expected to fall begins at.

        This is an routine considers the wet-bulb profile instead of the temperature profile
        in case the profile beneath the profile beneath the falling precipitation becomes saturated.

        Parameters
        ----------
        prof : Profile object
        start : the pressure level the precpitation originates from (found by calling init_phase())

        Returns
        -------
        pos : the positive area (> 0 C) of the wet-bulb profile in J/kg
        neg : the negative area (< 0 C) of the wet-bulb profile in J/kg
        top : the top of the precipitation layer pressure in mb
        bot : the bottom of the precipitation layer pressure in mb

    '''
    # Needs to be tested

    # If there is no sounding, don't compute anything
    if utils.QC(interp.temp(prof, 500)) == False and utils.QC(interp.temp(prof, 850)) == False:
        return np.masked, np.masked, np.masked, np.masked

    # Find lowest obs in layer
    lower = prof.pres[prof.get_sfc()]
    lptr  = prof.get_sfc()

    # Find the highest obs in the layer
    if start == -1:
        lvl, phase, st = init_phase(prof)
        if lvl > 0:
            upper = lvl
        else:
            upper = 500.
    else:
        upper = start

    # Find the level where the pressure is just greater than the upper pressure
    idxs = np.where(prof.pres > upper)[0]
    if len(idxs) == 0:
        uptr = 0
    else:
        uptr = idxs[-1]

    # Start with the upper layer
    pe1 = upper;
    h1 =  interp.hght(prof, pe1);
    te1 = thermo.wetbulb(pe1, interp.temp(prof, pe1), interp.dwpt(prof, pe1))
    tp1 = 0

    warmlayer = coldlayer = lyre = totp = totn = tote = ptop = pbot = lyrlast = 0

    for i in np.arange(uptr, lptr-1, -1):
        pe2 = prof.pres[i]
        h2 = prof.hght[i]
        te2 = thermo.wetbulb(pe2, interp.temp(prof, pe2), interp.dwpt(prof, pe2))
        tp2 = 0
        tdef1 = (0 - te1) / thermo.ctok(te1);
        tdef2 = (0 - te2) / thermo.ctok(te2);
        lyrlast = lyre;
        lyre = 9.8 * (tdef1 + tdef2) / 2.0 * (h2 - h1);

        # Has a warm layer been found yet?
        if te2 > 0:
            if warmlayer == 0:
                warmlayer = 1
                ptop = pe2

        # Has a cold layer been found yet?
        if te2 < 0:
            if warmlayer == 1 and coldlayer == 0:
                coldlayer = 1
                pbot = pe2

        if warmlayer > 0:
            if lyre > 0:
                totp += lyre
            else:
                totn += lyre
            tote += lyre

        pelast = pe1
        pe1 = pe2
        h1 = h2
        te1 = te2
        tp1 = tp2
    
    if warmlayer == 1 and coldlayer == 1:
        pos = totp
        neg = totn
        top = ptop
        bot = pbot
    else:
        neg = 0
        pos = 0
        bot = 0
        top = 0

    return pos, neg, top, bot

def best_guess_precip(prof, init_phase, init_lvl, init_temp, tpos, tneg):
    '''
        Best Guess Precipitation type
        Adapted from SHARP code donated by Rich Thompson (SPC)

        Description:
        This algorithm utilizes the output from the init_phase() and posneg_temperature()
        functions to make a best guess at the preciptation type one would observe
        at the surface given a thermodynamic profile.

        Precipitation Types Supported:
        - None
        - Rain
        - Snow
        - Sleet and Snow
        - Sleet
        - Freezing Rain/Drizzle
        - Unknown

        Parameters
        ----------
        prof : Profile object
        init_phase : the initial phase of the precipitation (int) (see 2nd value returned from init_phase())
        init_lvl : the inital level of the precipitation source (mb) (see 1st value returned from init_phase())
        init_temp : the inital level of the precipitation source (C) (see 3rd value returned from init_phase())
        tpos : the positive area (> 0 C) in the temperature profile (J/kg)

        Returns
        -------
        precip_type : a string containing the best guess precipitation type
    '''
    # Needs to be tested

    precip_type = None

    # Case: No precip
    if init_phase < 0:
        precip_type = "None."

    # Case: Always too warm - Rain
    elif init_phase == 0 and tneg >=0 and prof.tmpc[prof.get_sfc()] > 0:
        precip_type = "Rain."

    # Case: always too cold
    elif init_phase == 3 and tpos <= 0 and prof.tmpc[prof.get_sfc()] <= 0:
        precip_type = "Snow."

    # Case: ZR too warm at sfc - Rain
    elif init_phase == 1 and tpos <= 0 and prof.tmpc[prof.get_sfc()] > 0:
        precip_type = "Rain."

    # Case: non-snow init...always too cold - Initphase & sleet
    elif init_phase == 1 and tpos <= 0 and prof.tmpc[prof.get_sfc()] <= 0:
        #print interp.to_agl(prof, interp.hght(prof, init_lvl))
        if interp.to_agl(prof, interp.hght(prof, init_lvl)) >= 3000:
            if init_temp <= -4:
                precip_type = "Sleet and Snow."
            else:
                precip_type = "Sleet."
        else:
            precip_type = "Freezing Rain/Drizzle."

    # Case: Snow...but warm at sfc
    elif init_phase == 3 and tpos <= 0 and prof.tmpc[prof.get_sfc()] > 0:
        if prof.tmpc[prof.get_sfc()] > 4:
            precip_type = "Rain."
        else:
            precip_type = "Snow."
   
    # Case: Warm layer.
    elif tpos > 0:
        x1 = tpos
        y1 = -tneg
        y2 = (0.62 * x1) + 60.0
        if y1 > y2:
            precip_type = "Sleet."
        else:
            if prof.tmpc[prof.get_sfc()] <= 0:
                precip_type = "Freezing Rain."
            else:
                precip_type = "Rain."
    else:
        precip_type = "Unknown."

    return precip_type

def precip_type(prof):
    '''
        OLD PROPOSED FUNCTION
    '''
    #
    # This function looks at the current SHARPPY profile (prof)
    # and makes a single guess of the precipitation type associated with
    # that profile.
    #
    # it would be nice to produce probabilites of the preciptation type using
    # different methods, but it's 12 AM now.
    #
    # it would also be nice to have BUFKIT's precpitation intensity and type algorithm

    # Step 1: Check for ice in a cloud (is there a cloud with temps of -10 to -18 C?)

    # if no ice in cloud, check surface temp
    # if surface temp > 0 C, it's rain
    # if surface temp < 0 C, it's freezing rain

    # if there is ice in the cloud, what are the temperatures below it?
    # if the temperature below is less than 0.5 C, it's snow, but ony if T_w <= 0 C
    # otherwise if T_w > 0 C in the lowest 100 meters, and sfc T_w > 33 F, it's rain

    # if the temperatures below the ice cloud are between 0.5 to 3 C, there will be melting
    # if T_w or T are <= 0C, it's a mix (if warm layer is near 1 C) or sleet ( if warm layer is near 3 C)
    # if T_w >= 0 C in lowest 100 m and T_w > 33F, it's rain or drizzle

    # if the temperatures below the ice cloud are > 3 C, there's total melting
    # if minimum cold layer temp is > -12 C and sfc_T <= 0 C, it's freezing rain
    # if minimum cold layer temp is > -12 C and sfc_T > 0 C, it's rain.
    # if minimum cold layer temp is < -12 C and sfc_T_w < 33 F, it's snow and sleet
    return

def possible_watch(prof):
    '''
        Possible Weather/Hazard/Watch Type
        
        This function generates a list of possible significant weather types
        one can expect given a Profile object. (Currently works only for ConvectiveProfile.)

        These possible weather types are computed via fuzzy logic through set thresholds that
        have been found through a.) analyzing ingredients within the profile and b.) combining those ingredients
        with forecasting experience to produce a suggestion of what hazards may exist.  Some of the logic is 
        based on experience, some of it is based on actual National Weather Service criteria.

        This function has not been formally verified and is not meant to be comprehensive nor
        a source of strict guidance for weather forecasters.  As always, the raw data is to be 
        consulted.

        This code base is currently under development.

        Wx Categories (ranked in terms of severity):
        - PDS TOR
        - TOR
        - MRGL TOR
        - SVR
        - MRGL SVR
        - FLASH FLOOD
        - BLIZZARD
        - WINTER STORM
        - WIND CHILL
        - FIRE WEATHER
        - EXCESSIVE HEAT
        - FREEZE
    
        Suggestions for severe/tornado thresholds were contributed by Rich Thompson - NOAA Storm Prediction Center

        Parameters
        ----------
        prof : ConvectiveProfile object

        Returns
        -------
        watch_types :  a list of strings containing the weather types in code
        colors : a list of the HEX colors corresponding to each weather type
    '''
        
    watch_types = []
    colors = []
    
    lr1 = params.lapse_rate( prof, 0, 1000, pres=False )
    stp_eff = prof.stp_cin
    stp_fixed = prof.stp_fixed
    srw_4_6km = utils.mag(prof.srw_4_6km[0],prof.srw_4_6km[1])
    sfc_8km_shear = utils.mag(prof.sfc_8km_shear[0],prof.sfc_8km_shear[1])
    right_esrh = prof.right_esrh[0]
    srh1km = prof.srh1km[0]
    right_scp = prof.right_scp
    ## Cambios para el hemisferio sur JP JP
    if prof.latitude < 0:
        srh1km = -srh1km
        stp_eff = -stp_eff
        stp_fixed = -stp_fixed
        right_scp = -prof.left_scp
        right_esrh = -prof.left_esrh[0]
    if stp_eff >= 3 and stp_fixed >= 3 and srh1km >= 200 and right_esrh >= 200 and srw_4_6km >= 15.0 and \
        sfc_8km_shear > 45.0 and prof.sfcpcl.lclhght < 1000. and prof.mlpcl.lclhght < 1200 and lr1 >= 5.0 and \
        prof.mlpcl.bminus >= -50 and prof.ebotm == 0:
        watch_types.append("SPP TOR")
        colors.append(constants.MAGENTA)
    elif (stp_eff >= 3 or stp_fixed >= 4) and prof.mlpcl.bminus >= -125. and prof.ebotm == 0:
        watch_types.append("TOR")
        colors.append("#FF0000")
    elif (stp_eff >= 1 or stp_fixed >= 1) and (srw_4_6km >= 15.0 or sfc_8km_shear >= 40) and \
        prof.mlpcl.bminus >= -50 and prof.ebotm == 0:
        watch_types.append("TOR")
        colors.append("#FF0000")
    elif (stp_eff >= 1 or stp_fixed >= 1) and ((prof.low_rh + prof.mid_rh)/2. >= 60) and lr1 >= 5.0 and \
        prof.mlpcl.bminus >= -50 and prof.ebotm == 0:
        watch_types.append("TOR")
        colors.append("#FF0000")
    elif (stp_eff >= 1 or stp_fixed >= 1) and prof.mlpcl.bminus >= -150 and prof.ebotm == 0.:
        watch_types.append("MRGL TOR")
        colors.append("#FF0000")
    elif (stp_eff >= 0.5 and prof.right_esrh >= 150) or (stp_fixed >= 0.5 and srh1km >= 150) and \
        prof.mlpcl.bminus >= -50 and prof.ebotm == 0.:
        watch_types.append("MRGL TOR")
        colors.append("#FF0000")
    #t1 = tab.utils.FLOAT2STR(stp_eff, 1)
    #t2 = tab.utils.FLOAT2STR(stp_fixed, 1)
    #t3 = tab.utils.FLOAT2STR(srw_4_6km, 1)
    #t4 = tab.utils.INT2STR(sfc_8km_shear)
    #t5 = tab.utils.INT2STR(prof.mlpcl.bminus)
    #t6 = tab.utils.INT2STR(prof.ebotm)
    #with open('C:\\temp.txt', 'a') as f:
    #    f.write(t1 + ',' + t2 + ',' + t3 + ',' + t4 + ',' + t5 + ',' + t6 + '\n')

    #SVR LOGIC
    if (stp_fixed >= 1.0 or right_scp >= 4.0 or stp_eff >= 1.0) and prof.mupcl.bminus >= -50:
        colors.append("#FFFF00")
        watch_types.append("SVR")
    elif right_scp >= 2.0 and (prof.ship >= 1.0 or prof.dcape >= 750) and prof.mupcl.bminus >= -50:
        colors.append("#FFFF00")
        watch_types.append("SVR")
    elif prof.sig_severe >= 30000 and prof.mmp >= 0.6 and prof.mupcl.bminus >= -50:
        colors.append("#FFFF00")
        watch_types.append("SVR")
    elif prof.mupcl.bminus >= -75.0 and (prof.wndg >= 0.5 or prof.ship >= 0.5 or right_scp >= 0.5):
        colors.append("#0099CC")
        watch_types.append("MRGL SVR")
    
    # Flash Flood Watch PWV is larger than normal and cloud layer mean wind speeds are slow
    # This is trying to capture the ingredients of moisture and advection speed, but cannot
    # handle precipitation efficiency or vertical motion
    pw_climo_flag = prof.pwv_flag
    pwat = prof.pwat
    upshear = utils.comp2vec(prof.upshear_downshear[0],prof.upshear_downshear[1])
    if pw_climo_flag >= 2 and upshear[1] < 25:
        watch_types.append("INUND REPENT")
        colors.append("#5FFB17")
    #elif pwat > 1.3 and upshear[1] < 25:
    #    watch_types.append("FLASH FLOOD")
    #    colors.append("#5FFB17")
    
    # Blizzard if sfc winds > 35 mph and precip type detects snow 
    # Still needs to be tied into the 
    sfc_wspd = utils.KTS2MPH(prof.wspd[prof.get_sfc()])
    if sfc_wspd > 35. and prof.tmpc[prof.get_sfc()] <= 0 and "Snow" in prof.precip_type:
        watch_types.append("TORM NIEVE")
        colors.append("#3366FF")
    
    # Wind Chill (if wind chill gets below -20 F)
    if wind_chill(prof) < -20.:
        watch_types.append("ST VIENTO")
        colors.append("#3366FF")
    
    # Fire WX (sfc RH < 30% and sfc_wind speed > 15 mph) (needs to be updated to include SPC Fire Wx Indices)
    if sfc_wspd > 15. and thermo.relh(prof.pres[prof.get_sfc()], prof.tmpc[prof.get_sfc()], prof.tmpc[prof.get_sfc()]) < 30. :
        watch_types.append("INCENDIOS")
        colors.append("#FF9900")
    
    # Excessive Heat (if Max_temp > 105 F and sfc dewpoint > 75 F)
    if thermo.ctof(prof.dwpc[prof.get_sfc()]) > 75. and thermo.ctof(params.max_temp(prof)) >= 105.:
        watch_types.append("CALOR INTENSO")
        colors.append("#CC33CC")
    
    # Freeze (checks to see if wetbulb is below freezing and temperature isn't and wind speeds are low)
    # Still in testing.
    if thermo.ctof(prof.dwpc[prof.get_sfc()]) <= 32. and thermo.ctof(prof.wetbulb[prof.get_sfc()]) <= 32 and prof.wspd[prof.get_sfc()] < 5.:
        watch_types.append("HELADAS")
        colors.append("#3366FF")
    
    watch_types.append("NINGUNA")
    colors.append("#FFCC33")
    
    return np.asarray(watch_types), np.asarray(colors)

