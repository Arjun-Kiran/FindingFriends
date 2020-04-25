import uuid


class BaseComponent(object):
    def __init__(self):
        self._uuid = uuid.uuid4()

    @property
    def uuid(self):
        return str(self._uuid)
