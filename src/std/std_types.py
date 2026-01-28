from standard_lib import StdModule

class BaseType:
    def __init__(self, type_name):
        self.thistype = type_name
    
    def __repr__(self):
        return self.thistype
    
    def __str__(self):
        return self.thistype
    
    def __eq__(self, other):
        if isinstance(other, BaseType):
            return self.thistype == other.thistype
        if isinstance(other, str):
            return self.thistype == other
        return False
    
    def __hash__(self):
        return hash(self.thistype)

class StringType(BaseType):
    def __init__(self):
        super().__init__("str")

class IntegerType(BaseType):
    def __init__(self):
        super().__init__("int")

class FloatType(BaseType):
    def __init__(self):
        super().__init__("float")

class LongType(BaseType):
    def __init__(self):
        super().__init__("long")

class DoubleType(BaseType):
    def __init__(self):
        super().__init__("double")

class MapType(BaseType):
    def __init__(self):
        super().__init__("map")

class ListType(BaseType):
    def __init__(self):
        super().__init__("list")

class TupleType(BaseType):
    def __init__(self):
        super().__init__("tuple")

class BoolType(BaseType):
    def __init__(self):
        super().__init__("bool")

class NullType(BaseType):
    def __init__(self):
        super().__init__("null")

class AnyType(BaseType):
    def __init__(self):
        super().__init__("any")

@StdModule.register("kinds")
def std_kinds(interp):
    env = interp.env.new_child_env()
    
    env.define("String", StringType)
    env.define("Integer", IntegerType)
    env.define("Long", LongType)
    env.define("Double", DoubleType)
    env.define("Float", FloatType)
    env.define("Map", MapType)
    env.define("List", ListType)
    env.define("Tuple", TupleType)
    env.define("Bool", BoolType)
    env.define("Null", NullType)
    env.define("Any", AnyType)
    
    return env