
import logging
# import contextlib
import traceback

from .manager import ChromeRemoteDebugInterface

# @contextlib.contextmanager
class ChromeContext():
	'''
	Context manager for conveniently handling the lifetime of the underlying chromium instance.

	In general, this should be the preferred way to use an instance of `ChromeRemoteDebugInterface`.

	All parameters are forwarded through to the underlying ChromeRemoteDebugInterface() constructor.
	'''
	def __init__(self, *args, **kwargs):
		log = logging.getLogger("Main.ChromeController.ChromeContext")
		self.chrome_created = False
		try:
			chrome_instance = ChromeRemoteDebugInterface(*args, **kwargs)
			self.chrome_created = True
			log.info("Entering chrome context")
			self.instance = chrome_instance
		except Exception as e:
			log.error("Exception in chrome context!")
			for line in traceback.format_exc().split("\n"):
				log.error(line)
			raise e

# 		finally:
# 			log.info("Exiting chrome context")
# 			if chrome_created:
# 				chrome_instance.close()
	def get_instance(self):
		if self.chrome_created:
			return self.instance
		else:
			return None
	def close(self):
		if self.chrome_created:
			self.instance.close()

