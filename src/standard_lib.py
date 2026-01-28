class StdModule:
    registry = {}

    @staticmethod
    def register(name):
        def decorator(func):
            StdModule.registry[name] = func
            return func
        return decorator

    @staticmethod
    def load(name, interpreter):
        if name not in StdModule.registry:
            raise Exception(f"ImportError: Built-in module '{name}' not found")
        return StdModule.registry[name](interpreter)