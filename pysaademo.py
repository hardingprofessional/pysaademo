#! /usr/bin/env python3
import os #used to set environment variable
import ctypes as c #module that interacts with DLLs
import pdb

# Python can't set this environment variable for ctypes, so tell the user if
# they need to set it before starting the script
if 'LD_LIBRARY_PATH' not in os.environ:
	print("Set LD_LIBRARY_PATH before running")
	exit()

# DLL Loading follows a split path
#       / TimeFunc -> TLE ->       \
# Main {                            } Sgp4Prop
#       \ EnvConst -> AstroFunc -> /
#
# As such, we will need to init each DLL in this sequence:
# Main, TimeFunc, TLE, EnvConst, AstroFunc, Sgp4Prop

# Init Main
maindll = c.CDLL('libdllmain.so')
# DllMainInit returns a handle which the other DLLs need to communicate with
# each other
maindll.DllMainInit.restype = c.c_int64
maindll_handle = maindll.DllMainInit()
# Open and write to a log file
# If I didn't have this log file, this project would be impossible
# As it is I just guess-and-check based on what ends up here
maindll.OpenLogFile.restype = c.c_int
maindll.OpenLogFile.argtypes = [c.c_char_p]
retcode = maindll.OpenLogFile(b"./run.log")

# Init TimeFunc
timedll = c.CDLL('libtimefunc.so')
timedll.TimeFuncInit.restype = c.c_int
timedll.TimeFuncInit.argtypes = [c.c_int64]
retcode = timedll.TimeFuncInit(maindll_handle)

# Init TLE
tledll  = c.CDLL('libtle.so')
tledll.TleInit.restype = c.c_int
tledll.TleInit.argtypes = [c.c_int64]
retcode = tledll.TleInit(maindll_handle)

# Init EnvConst
envdll = c.CDLL('libenvconst.so')
envdll.EnvInit.restype = c.c_int
envdll.EnvInit.argtypes = [c.c_int64]
retcode = envdll.EnvInit(maindll_handle)

# Init Astro
astrodll = c.CDLL('libastrofunc.so')
astrodll.AstroFuncInit.restype = c.c_int
astrodll.AstroFuncInit.argtypes = [c.c_int64]
retcode = astrodll.AstroFuncInit(maindll_handle)

# Init SGP4
sgp4dll = c.CDLL('libsgp4prop.so')
# Gotta get that license file
sgp4dll.Sgp4SetLicFilePath.argtypes = [c.c_char_p]
sgp4dll.Sgp4SetLicFilePath(c.c_char_p(b"./libdll/"))
# Init the DLL
sgp4dll.Sgp4Init.restype = c.c_int
sgp4dll.Sgp4Init.argtypes = [c.c_int64]
retcode = sgp4dll.Sgp4Init(maindll_handle)

# demonstrate how sgp4dll uses pointer activity to replace variables
# The parameter is a 512 character long byte string (probably ASCII)
# The function locates and writes to it
# Yes, this means that the path to the license is limited to 512 characters
sgp4dll.Sgp4GetLicFilePath.argtypes = [c.c_char_p]
byte512 = c.c_char*512
path = byte512()
sgp4dll.Sgp4GetLicFilePath(path)
print('-'*20)
print('SAA Licence Path:')
print(path.value)
print('-'*20)

# use TleAddSatFrLines to create a TLE object from strings from TLE file
# return is a "satkey" number which can be used throughout the DLLs to 
# identify this particular instance of the satellite TLE
tledll.TleAddSatFrLines.restype = c.c_int64
tledll.TleAddSatFrLines.argtypes = [c.c_char_p, c.c_char_p]
line1 = c.c_char_p(b"1 90001U SGP4-VAL 93 51.47568104  .00000184      0 0  00000-4   814")
line2 = c.c_char_p(b"2 90001   0.0221 182.4922 0000720  45.6036 131.8822  1.00271328 1199")
SatKey = tledll.TleAddSatFrLines(line1, line2)

# init an Sgp4InitSat object, must be done before propagation
sgp4dll.Sgp4InitSat.restype = c.c_int
sgp4dll.Sgp4InitSat.argtypes = [c.c_int64]
retcode = sgp4dll.Sgp4InitSat(SatKey)

# Set up to propagate the TLE
vector = c.c_double * 3
r_ECI = vector()
v_ECI = vector()
llh = vector()
ds50UTC = c.c_double()
sgp4dll.Sgp4PropMse.restype = c.c_int
sgp4dll.Sgp4PropMse.argtypes = [c.c_int64, c.c_double, c.POINTER(c.c_double), vector, vector, vector]

def printvector(name, vector):
	print("{:5} = < {:13.7f}, {:14.7f}, {:14.7f} >".format(name, vector[0], vector[1], vector[2]))

# Do one run at 0 minutes past Epoch
mse = c.c_double(0)
retcode = sgp4dll.Sgp4PropMse(SatKey, mse, c.byref(ds50UTC), r_ECI, v_ECI, llh)
print('Sgp4PropMse Return Code: {:d}'.format(retcode))
print("ds50UTC: {0:.7f}".format(ds50UTC.value))
printvector('r_ECI', r_ECI)
printvector('v_ECI', v_ECI)
printvector('llh', llh)
print('-'*20)

# Do one run at 2700 minutes past Epoch
mse = c.c_double(2700)
retcode = sgp4dll.Sgp4PropMse(SatKey, mse, c.byref(ds50UTC), r_ECI, v_ECI, llh)
print('Sgp4PropMse Return Code: {:d}'.format(retcode))
print("ds50UTC: {0:.7f}".format(ds50UTC.value))
printvector('r_ECI', r_ECI)
printvector('v_ECI', v_ECI)
printvector('llh', llh)
print('-'*20)
