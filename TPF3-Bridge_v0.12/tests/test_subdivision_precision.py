"""Float32 Hermite subdivision regression; independent numerical replay, no game."""
import math
import struct
import unittest

CONTROL={'p0':[-3540.843994140625,-13610.01953125,.9021682739257812],
         'p1':[-3578.908203125,-13708.53515625,.9021682739257812],
         't0':[-35.80976867675781,-99.31127166748047,0],
         't1':[-32.63361740112305,-100.43174743652344,0]}
def f32(x):return struct.unpack('f',struct.pack('f',x))[0]
def value(c,u,derivative=False):
    b=([6*u*u-6*u,3*u*u-4*u+1,-6*u*u+6*u,3*u*u-2*u] if derivative else
       [2*u**3-3*u*u+1,u**3-2*u*u+u,-2*u**3+3*u*u,u**3-u*u])
    result=[]
    for i in range(3):
        x=f32(f32(b[0])*c['p0'][i])
        for coefficient,key in zip(b[1:],('t0','p1','t1')):x=f32(x+f32(f32(coefficient)*c[key][i]))
        result.append(x)
    return result

def near(a,b,c):
    for i in range(3):
        scale=max(abs(a[i]),abs(b[i]),abs(c['p0'][i]),abs(c['p1'][i]));ulp=2**-23
        while scale>=2:scale/=2;ulp*=2
        if abs(a[i]-b[i])>max(.001,4*ulp):return False
    return True

class SubdivisionPrecisionTests(unittest.TestCase):
    def test_translated_float32_subdivision_retains_shape_and_tangent(self):
        c=CONTROL;errors=[];angles=[]
        self.assertEqual(value(c,.375),[-3555.26513671875,-13646.9111328125,.9021682739257812])
        for lo,hi in ((0,.375),(.375,1)):
            split={'p0':value(c,lo),'p1':value(c,hi),
                   't0':[f32(x*(hi-lo)) for x in value(c,lo,True)],
                   't1':[f32(x*(hi-lo)) for x in value(c,hi,True)]}
            for u in (0,.25,.5,.75,1):
                original=value(c,lo+u*(hi-lo));derived=value(split,u)
                errors.append(max(abs(x-y) for x,y in zip(original,derived)))
                self.assertTrue(near(original,derived,c))
                a=value(c,lo+u*(hi-lo),True);b=value(split,u,True)
                dot=sum(a[i]*b[i] for i in (0,1))/(math.hypot(*a[:2])*math.hypot(*b[:2]))
                angles.append(math.degrees(math.acos(max(-1,min(1,dot)))))
        self.assertEqual(max(errors),.001953125)
        self.assertLess(max(angles),.1)
    def test_wrong_geometry_at_large_coordinates_still_fails(self):
        a=value(CONTROL,.5);b=a.copy();b[1]+=.02
        self.assertFalse(near(a,b,CONTROL))
    def test_small_coordinates_keep_millimetre_limit(self):
        c={k:list(v) for k,v in CONTROL.items()}
        for key in ('p0','p1'):
            c[key][0]-=CONTROL['p0'][0];c[key][1]-=CONTROL['p0'][1]
        a=value(c,.5);b=a.copy();b[1]+=.002
        self.assertFalse(near(a,b,c))

if __name__=='__main__':unittest.main()
