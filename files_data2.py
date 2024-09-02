from typing import List

class Master:
    filepath: str
    directory: str
    playlists: List
    headers: dict
   

    def __init__(self, filepath, directory, playlists, headers) -> None:
        self.filepath = filepath
        self.directory = directory
        self.playlists = playlists
        self.headers = headers

class Playlist:

    filepath: str
    dirname: str
    resolution: str
    segments: List
    headers :dict
    contentType : str


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
        self.headers = dict(
            bandwidth=playlist_infos.get("BANDWIDTH"),
            contentType=playlist_infos.get("contentType")
        )
        
    def __str__(self):
        return self.__dict__.__str__()
    
    def __repr__(self):
        return self.__dict__.__str__()

class Segment:
    file_name: str
    duration: float
    seg_type: str #ENUM => main | ad

    def __init__(self):
        return


class Resolution:
    width: int
    height: int

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def get_resolution(self):
        return str(self.width)+'x'+str(self.height)