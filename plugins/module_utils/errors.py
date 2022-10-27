class SoftwareException(Exception):
    def __init__(self, msg, **context):
        super().__init__(msg)
        self.context = {k: str(v) for k, v in context.items()}
