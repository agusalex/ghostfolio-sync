import colorlog

from EnvironmentConfiguration import EnvironmentConfiguration

envConf = EnvironmentConfiguration()
log_level = envConf.log_level()

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s %(levelname)s:%(filename)s: %(message)s'
    )
)
logger = colorlog.getLogger()
logger.setLevel(log_level)
logger.addHandler(handler)