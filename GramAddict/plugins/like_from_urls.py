import logging
from os import path
from random import shuffle

from atomicwrites import atomic_write

from GramAddict.core.decorators import run_safely
from GramAddict.core.interaction import do_like
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.utils import open_instagram_with_url, validate_url
from GramAddict.core.views import OpenedPostView

logger = logging.getLogger(__name__)


class LikeFromURLs(Plugin):
    """Likes a post from url. The urls are read from a plaintext file"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Likes a post from url. The urls are read from a plaintext file"
        )
        self.arguments = [
            {
                "arg": "--posts-from-file",
                "nargs": None,
                "help": "full path of plaintext file contains urls to likes",
                "metavar": None,
                "default": None,
                "operation": True,
            }
        ]

    def run(self, device, configs, storage, sessions, plugin):
        class State:
            def __init__(self):
                pass

            is_job_completed = False

        self.args = configs.args
        self.device = device
        self.device_id = configs.args.device
        self.state = None
        self.sessions = sessions
        self.session_state = sessions[-1]
        self.current_mode = plugin

        file_list = [file for file in (self.args.interact_from_file)]
        shuffle(file_list)

        for filename in file_list:
            self.state = State()

            @run_safely(
                device=self.device,
                device_id=self.device_id,
                sessions=self.sessions,
                session_state=self.session_state,
                screen_record=self.args.screen_record,
                configs=configs,
            )
            def job():
                self.process_file(filename, storage)

            job()

    def process_file(self, current_file, storage):
        # TODO: We need to add interactions properly, honor session/source limits, honor filter,
        # etc. Not going to try to do this now, but adding a note to do it later
        if path.isfile(current_file):
            with open(current_file, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if validate_url(url) and "instagram.com/p/" in url:
                        if open_instagram_with_url(url) is True:
                            opened_post_view = OpenedPostView(self.device)
                            username = opened_post_view._getUserName
                            like_succeed = do_like(opened_post_view, self.device)
                            logger.info(
                                "Like for: {}, status: {}".format(url, like_succeed)
                            )
                            if like_succeed:
                                logger.info("Back to profile")
                                storage.add_interacted_user(
                                    username, self.session_state.id, liked=1
                                )
                                self.device.back()
                    else:
                        logger.info("Line in file is blank, skip.")
                remaining = f.readlines()
            if self.args.delete_interacted_users:
                with atomic_write(current_file, overwrite=True, encoding="utf-8") as f:
                    f.writelines(remaining)
        else:
            logger.warning(f"File {current_file} not found.")
            return
