
import numpy as np

import sharppy.sharptab.profile as profile
import sharppy.sharptab.prof_collection as prof_collection
from decoder import Decoder

from StringIO import StringIO
from datetime import datetime

__fmtname__ = "iag"
__classname__ = "IAGDecoder"

class IAGDecoder(Decoder):
    def __init__(self, file_name):
        super(IAGDecoder, self).__init__(file_name)

    def _parse(self):
        file_data = self._downloadFile()
        ## read in the file
        data = np.array([l.strip() for l in file_data.split('\n')])

        ## necessary index points
        start_idx = np.where( data == '<PRE>' )[0]
        finish_idx = np.where(np.char.find(data, '</H3>') > -1)[0]
        time_idx = np.where(np.char.find(data, 'time') > -1)[0][0]
        latitude_idx = np.where(np.char.find(data, 'latitude') > -1)[0][0]

        ## create the plot title and time
        location = data[4].split()[1]
        time = datetime.strptime(data[time_idx].strip().split()[2], '%y%m%d/%H%M')
        latitude = data[latitude_idx].strip().split()[2]
        if time > datetime.utcnow(): #If the strptime accidently makes the sounding the future:
            # If the strptime accidently makes the sounding in the future (like with SARS archive)
            # i.e. a 1957 sounding becomes 2057 sounding...ensure that it's a part of the 20th century
            time = datetime.strptime('19' + data[time_idx].strip().split()[2], '%y%m%d/%H%M')

		## put it all together for StringIO
        data = data[10 : finish_idx][:]
        data_final = []
        max = 0
        for m in data:
            while '  ' in m:
                m = m.replace('  ', ' ')
            if len(m.split(' ')) != 11:
               continue
            if int(float(m.split(' ')[1])) <= max:
               continue
            data_final.append(m)
            max = int(float(m.split(' ')[1]))
        full_data = '\n'.join(data_final)
        while '  ' in full_data:
            full_data = full_data.replace('  ', ' ')
        sound_data = StringIO( full_data.strip() )
        ## read the data into arrays
        p, h, T, Td, rh, mr, wdir, wspd, ta, te, tv = np.genfromtxt( sound_data, delimiter=' ', comments="%", unpack=True )
        #idx = np.argsort(p, kind='mergesort')[::-1] # sort by pressure in case the pressure array is off.

        pres = p #[idx]
        hght = h #[idx]
        tmpc = T #[idx]
        dwpc = Td #[idx]
        wspd = wspd #[idx]
        wdir = wdir #[idx]
        wdir_final = []
        for m in wdir:
            s = '0'
            if int(m) < 360:
                s = m
            wdir_final.append(s)
				
        # Force latitude to be 35 N. Figure out a way to fix this later.
        prof = profile.create_profile(profile='raw', pres=pres, hght=hght, tmpc=tmpc, dwpc=dwpc,
            wdir=wdir_final, wspd=wspd, location=location, date=time, latitude=float(latitude))

        prof_coll = prof_collection.ProfCollection(
            {'':[ prof ]}, 
            [ time ],
        )

        prof_coll.setMeta('loc', location)
        return prof_coll
