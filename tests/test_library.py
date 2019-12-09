import os
import unittest

import pykka
from mopidy import core
from mopidy.models import SearchResult, Track

from mopidy_local import actor, storage, translator
from tests import dummy_audio, path_to_data_dir


class LocalLibraryProviderTest(unittest.TestCase):
    config = {
        "core": {"data_dir": path_to_data_dir(""), "max_tracklist_length": 10000},
        "local": {
            "media_dir": path_to_data_dir(""),
            "directories": [],
            "timeout": 10,
            "use_artist_sortname": False,
            "album_art_files": [],
        },
    }

    def setUp(self):
        self.audio = dummy_audio.create_proxy()
        self.backend = actor.LocalBackend.start(
            config=self.config, audio=self.audio
        ).proxy()
        self.core = core.Core.start(
            audio=self.audio, backends=[self.backend], config=self.config
        ).proxy()
        self.library = self.backend.library
        self.storage = storage.LocalStorageProvider(self.config)
        self.storage.load()

    def tearDown(self):  # noqa: N802
        pykka.ActorRegistry.stop_all()
        try:
            os.remove(path_to_data_dir("local/library.db"))
        except OSError:
            pass

    def test_add_noname_ascii(self):
        name = "Test.mp3"
        uri = translator.path_to_local_track_uri(name)
        track = Track(name=name, uri=uri)
        self.storage.begin()
        self.storage.add(track)
        self.storage.close()
        self.assertEqual([track], self.library.lookup(uri).get())

    def test_add_noname_utf8(self):
        name = "Mi\xf0vikudags.mp3"
        uri = translator.path_to_local_track_uri(name.encode("utf-8"))
        track = Track(name=name, uri=uri)
        self.storage.begin()
        self.storage.add(track)
        self.storage.close()
        self.assertEqual([track], self.library.lookup(uri).get())

    def test_clear(self):
        self.storage.begin()
        self.storage.add(Track(uri="local:track:track.mp3"))
        self.storage.close()
        self.storage.clear()
        self.assertEqual(self.storage.load(), 0)

    def test_search_uri(self):
        lib = self.library
        empty = SearchResult(uri="local:search?")
        self.assertEqual(empty, lib.search(uris=None).get())
        self.assertEqual(empty, lib.search(uris=[]).get())
        self.assertEqual(empty, lib.search(uris=["local:"]).get())
        self.assertEqual(empty, lib.search(uris=["local:directory"]).get())
        self.assertEqual(empty, lib.search(uris=["local:directory:"]).get())
        self.assertEqual(empty, lib.search(uris=["foobar:"]).get())