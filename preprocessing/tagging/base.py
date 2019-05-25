import logging
from threading import Thread

OUTPUT_INTERVAL = 30


class BaseTagger(Thread):
    OUTPUT_INTERVAL = 30

    def __init__(self, *args, root_dir=None, translation_dir=None, log_dir=None, config=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_dir = root_dir
        self.translation_dir = translation_dir
        self.log_dir = log_dir
        self.config = config
        self.thread = None
        self.logger = logging.getLogger("preprocessing")
        self.name = self.__class__.__name__

    def prepare(self, resume=False):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def get_progress(self):
        raise NotImplementedError
