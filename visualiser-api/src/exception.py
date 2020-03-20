
class MetaflowException(Exception):

    def __init__(self, http_code, message):

        self.http_code = http_code
        self.message = message