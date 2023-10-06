from typing import List


class HLSMaster:
    filepath: str
    directory: str
    playlists: List
    headers: dict
   

    def __init__(self, filepath, directory, playlists, headers) -> None:
        self.filepath = filepath
        self.directory = directory
        self.playlists = playlists
        self.headers = headers
       


class HLSPlaylist:

    filepath: str
    dirname: str
    resolution: str
    segments: List
    headers :dict


    def __init__(self, filepath: str, resolution: str, segments: List, headers: dict, dirname:str):
        self.filepath = filepath
        self.dirname = dirname
        self.resolution = resolution
        self.segments = segments


    def __init__(self, playlist_infos: dict ):
        self.filepath = playlist_infos.get("playlist")
        self.resolution = playlist_infos.get("RESOLUTION")
        self.dirname = playlist_infos.get("dirname")
    
        self.segments = playlist_infos.get("segments")
        self.headers = dict(bandwidth=playlist_infos.get("BANDWIDTH"))
        
    def __str__(self):
        return self.__dict__.__str__()
    
    def __repr__(self):
        return self.__dict__.__str__()
