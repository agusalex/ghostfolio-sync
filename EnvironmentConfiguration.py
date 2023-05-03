import os

from cachetools import TTLCache

cache = TTLCache(maxsize=5, ttl=300)
log_level = os.environ.get("LOG_LEVEL", "INFO")
write_debug_files = os.environ.get("WRITE_DEBUG_FILES", "FALSE")
write_debug_files_location = os.environ.get("FILE_WRITE_LOCATION", "")


class EnvironmentConfiguration:

    def __init__(self):
        pass

    def is_debug_files_enabled(self):
        return write_debug_files

    def debug_file_location(self):
        if len(write_debug_files_location) > 0:
            return write_debug_files_location + os.sep
        return ""

    def log_level(self):
        return log_level
