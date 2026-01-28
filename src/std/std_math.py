from standard_lib import StdModule
import math

def clamp(x, min_value, max_value):
    if min_value > max_value:
        raise ValueError("min_value cannot be greater than max_value")
    return max(min_value, min(x, max_value))

def isprime(n):
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i+2) == 0:
            return False
        i += 6
    return True

class Vector2:
    __slots__ = ('x','y')
    def __init__(self,x=0,y=0):
        self.x = x
        self.y = y
    def __add__(self,other): return Vector2(self.x+other.x, self.y+other.y)
    def __sub__(self,other): return Vector2(self.x-other.x, self.y-other.y)
    def __mul__(self,val): return Vector2(self.x*val, self.y*val)
    def dot(self,other): return self.x*other.x + self.y*other.y
    def magnitude(self): return math.sqrt(self.x*self.x + self.y*self.y)
    def normalize(self):
        m = self.magnitude()
        return Vector2(self.x/m,self.y/m) if m != 0 else Vector2()
    def __repr__(self): return f"Vector2({self.x},{self.y})"

class Vector3:
    __slots__=('x','y','z')
    def __init__(self,x=0,y=0,z=0):
        self.x=x; self.y=y; self.z=z
    def __add__(self,other): return Vector3(self.x+other.x, self.y+other.y, self.z+other.z)
    def __sub__(self,other): return Vector3(self.x-other.x, self.y-other.y, self.z-other.z)
    def __mul__(self,val): return Vector3(self.x*val, self.y*val, self.z*val)
    def dot(self,other):
        return self.x*other.x + self.y*other.y + self.z*other.z
    def cross(self,other):
        return Vector3(
            self.y*other.z - self.z*other.y,
            self.z*other.x - self.x*other.z,
            self.x*other.y - self.y*other.x
        )
    def magnitude(self): return math.sqrt(self.x*self.x + self.y*self.y + self.z*self.z)
    def normalize(self):
        m = self.magnitude()
        return Vector3(self.x/m,self.y/m,self.z/m) if m != 0 else Vector3()
    def __repr__(self): return f"Vector3({self.x},{self.y},{self.z})"

class Matrix2:
    def __init__(self, rows):
        self.rows = rows
    @staticmethod
    def identity():
        return Matrix2([[1,0],[0,1]])
    def transpose(self):
        return Matrix2([[self.rows[j][i] for j in range(2)] for i in range(2)])
    def __mul__(self,other):
        if isinstance(other,Vector2):
            x = self.rows[0][0]*other.x + self.rows[0][1]*other.y
            y = self.rows[1][0]*other.x + self.rows[1][1]*other.y
            return Vector2(x,y)
        if isinstance(other,Matrix2):
            return Matrix2([
                [
                    sum(self.rows[i][k] * other.rows[k][j] for k in range(2))
                    for j in range(2)
                ]
                for i in range(2)
            ])
        raise TypeError("Unsupported multiply type")

class Matrix3:
    def __init__(self, rows):
        self.rows = rows

    @staticmethod
    def identity():
        return Matrix3([[1,0,0],[0,1,0],[0,0,1]])

    def transpose(self):
        return Matrix3([[self.rows[j][i] for j in range(3)] for i in range(3)])

    def __mul__(self, other):
        if isinstance(other, Vector3):
            x = self.rows[0][0] * other.x + self.rows[0][1] * other.y + self.rows[0][2] * other.z
            y = self.rows[1][0] * other.x + self.rows[1][1] * other.y + self.rows[1][2] * other.z
            z = self.rows[2][0] * other.x + self.rows[2][1] * other.y + self.rows[2][2] * other.z
            return Vector3(x, y, z)

        if isinstance(other, Matrix3):
            return Matrix3([
                [
                    sum(self.rows[i][k] * other.rows[k][j] for k in range(3))
                    for j in range(3)
                ]
                for i in range(3)
            ])

        raise TypeError("Unsupported multiply type")

class Matrix4:
    def __init__(self, rows):
        self.rows = rows
    @staticmethod
    def identity():
        return Matrix4([
            [1,0,0,0],
            [0,1,0,0],
            [0,0,1,0],
            [0,0,0,1]
        ])
    def transpose(self):
        return Matrix4([[self.rows[j][i] for j in range(4)] for i in range(4)])

def deg2rad(deg):
    return deg * math.pi / 180.0

def rotX(angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return Matrix3([
        [1, 0, 0],
        [0, c, -s],
        [0, s,  c]
    ])

def rotY(angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return Matrix3([
        [ c, 0, s],
        [ 0, 1, 0],
        [-s, 0, c]
    ])

def rotZ(angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return Matrix3([
        [c, -s, 0],
        [s,  c, 0],
        [0,  0, 1]
    ])

def rotX4(angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return Matrix4([
        [1, 0, 0, 0],
        [0, c, -s, 0],
        [0, s,  c, 0],
        [0, 0, 0, 1],
    ])

def rotY4(angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return Matrix4([
        [ c, 0, s, 0],
        [ 0, 1, 0, 0],
        [-s, 0, c, 0],
        [ 0, 0, 0, 1],
    ])

def rotZ4(angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return Matrix4([
        [c, -s, 0, 0],
        [s,  c, 0, 0],
        [0,  0, 1, 0],
        [0,  0, 0, 1],
    ])

def rotateX(v, angle):
    return rotX(angle) * v

def rotateY(v, angle):
    return rotY(angle) * v

def rotateZ(v, angle):
    return rotZ(angle) * v

def lerp(a, b, t):
    return a + (b - a) * t

def remap(x, in_min, in_max, out_min, out_max):
    return out_min + (float(x - in_min) / float(in_max - in_min)) * (out_max - out_min)

def distance2(v1, v2):
    return math.sqrt((v1.x - v2.x)**2 + (v1.y - v2.y)**2)

def distance3(v1, v2):
    return math.sqrt((v1.x - v2.x)**2 + (v1.y - v2.y)**2 + (v1.z - v2.z)**2)

def dot2(a, b):
    return a.x*b.x + a.y*b.y

def dot3(a, b):
    return a.x*b.x + a.y*b.y + a.z*b.z

def angle2(a, b):
    m = a.magnitude() * b.magnitude()
    return math.acos(max(-1, min(1, a.dot(b) / m))) if m != 0 else 0

def angle3(a, b):
    m = a.magnitude() * b.magnitude()
    return math.acos(max(-1, min(1, a.dot(b) / m))) if m != 0 else 0

def rad2deg(rad):
    return rad * 180.0 / math.pi

TAU = math.tau if hasattr(math, "tau") else (math.pi * 2)

class Vector4:
    __slots__ = ('x','y','z','w')
    def __init__(self,x=0,y=0,z=0,w=0):
        self.x=x; self.y=y; self.z=z; self.w=w
    def __add__(self,other): return Vector4(self.x+other.x, self.y+other.y, self.z+other.z, self.w+other.w)
    def __sub__(self,other): return Vector4(self.x-other.x, self.y-other.y, self.z-other.z, self.w-other.w)
    def __mul__(self,val): return Vector4(self.x*val, self.y*val, self.z*val, self.w*val)
    def dot(self,other): return self.x*other.x + self.y*other.y + self.z*other.z + self.w*other.w
    def magnitude(self): return math.sqrt(self.x*self.x + self.y*self.y + self.z*self.z + self.w*self.w)
    def normalize(self):
        m = self.magnitude()
        return Vector4(self.x/m,self.y/m,self.z/m,self.w/m) if m != 0 else Vector4()
    def __repr__(self): return f"Vector4({self.x},{self.y},{self.z},{self.w})"

class Quaternion:
    __slots__=('x','y','z','w')
    def __init__(self, x=0, y=0, z=0, w=1):
        self.x=x; self.y=y; self.z=z; self.w=w

    @staticmethod
    def from_axis_angle(axis, angle):
        s = math.sin(angle/2)
        return Quaternion(axis.x*s, axis.y*s, axis.z*s, math.cos(angle/2))

    def __mul__(self, other):
        if isinstance(other, Quaternion):
            x = self.w*other.x + self.x*other.w + self.y*other.z - self.z*other.y
            y = self.w*other.y - self.x*other.z + self.y*other.w + self.z*other.x
            z = self.w*other.z + self.x*other.y - self.y*other.x + self.z*other.w
            w = self.w*other.w - self.x*other.x - self.y*other.y - self.z*other.z
            return Quaternion(x,y,z,w)

        if isinstance(other, Vector3):
            qvec = Vector3(self.x, self.y, self.z)
            uv = qvec.cross(other)
            uuv = qvec.cross(uv)
            uv = uv * (2.0 * self.w)
            uuv = uuv * 2.0
            return Vector3(other.x + uv.x + uuv.x,
                           other.y + uv.y + uuv.y,
                           other.z + uv.z + uuv.z)

        raise TypeError("Unsupported type for quaternion multiply")

    def normalize(self):
        m = math.sqrt(self.x*self.x + self.y*self.y + self.z*self.z + self.w*self.w)
        return Quaternion(self.x/m,self.y/m,self.z/m,self.w/m) if m != 0 else Quaternion()

    def __repr__(self):
        return f"Quaternion({self.x},{self.y},{self.z},{self.w})"

@StdModule.register("math")
def std_math(interp):
    env = interp.env.new_child_env()

    env.define("sin", math.sin)
    env.define("cos", math.cos)
    env.define("tan", math.tan)
    env.define("asin", math.asin)
    env.define("acos", math.acos)
    env.define("atan", math.atan)
    env.define("sqrt", math.sqrt)
    env.define("abs", abs)
    env.define("min", min)
    env.define("max", max)
    env.define("floor", math.floor)
    env.define("ceil", math.ceil)
    env.define("pow", math.pow)
    env.define("round", round)
    env.define("log", math.log)
    env.define("log2", math.log2)
    env.define("log1p", math.log1p)
    env.define("log10", math.log10)
    env.define("exp", math.exp)
    env.define("atan2", math.atan2)
    env.define("hypot", math.hypot)
    env.define("expm1", math.expm1)
    env.define("factorial", math.factorial)
    env.define("gcd", math.gcd)
    env.define("lcm", math.lcm)
    env.define("isinfinite", math.isfinite)
    env.define("isinf", math.isinf)
    env.define("fmod", math.fmod)
    env.define("nextafter", math.nextafter)
    env.define("copysign", math.copysign)
    env.define("isnan", math.isnan)
    env.define("sinh", math.sinh)
    env.define("cosh", math.cosh)
    env.define("tanh", math.tanh)
    env.define("asinh", math.asinh)
    env.define("acosh", math.acosh)
    env.define("atanh", math.atanh)
    env.define("clamp", clamp)
    env.define("isprime", isprime)
    env.define("nan", math.nan)
    env.define("pi", math.pi)
    env.define("e", math.e)
    env.define("inf", math.inf)

    env.define("Vector2", Vector2)
    env.define("Vector3", Vector3)
    env.define("Matrix2", Matrix2)
    env.define("Matrix3", Matrix3)
    env.define("Matrix4", Matrix4)
    env.define("torad", deg2rad)
    env.define("rotX", rotX)
    env.define("rotY", rotY)
    env.define("rotZ", rotZ)
    env.define("rotX4", rotX4)
    env.define("rotY4", rotY4)
    env.define("rotZ4", rotZ4)
    env.define("rotateX", rotateX)
    env.define("rotateY", rotateY)
    env.define("rotateZ", rotateZ)
    env.define("lerp", lerp)
    env.define("remap", remap)
    env.define("distance2", distance2)
    env.define("distance3", distance3)
    env.define("dot2", dot2)
    env.define("dot3", dot3)
    env.define("angle2", angle2)
    env.define("angle3", angle3)
    env.define("todeg", rad2deg)
    env.define("tau", TAU)
    env.define("Vector4", Vector4)
    env.define("Quaternion", Quaternion)

    return env