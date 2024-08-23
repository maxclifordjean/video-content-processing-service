from typing import List

#Master => index.m3u8 as object
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

# Example =>    
# {
#     filepath: 'video-storage/hls/my_video/index.m3u8'
#     directory: 'video-storage/hls/my_video'
#     playlists:[
#       HLSPlaylist,
#       HLSPlaylist,
#       ...
#     ],
#     headers:{
#
#     }
# }

#Variant *.ts as object
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

# Example =>
# {
#     'filepath': 'video-storage/hls/my_video/360p.m3u8', 
#     'resolution': '640x360', 
#     'dirname': 'video-storage/hls/my_video', 
#     'segments': [
#         {'file_name': '360p_000.ts', 'duration': 16.666667}, 
#         {'file_name': '360p_001.ts', 'duration': 8.333333}, 
#         {'file_name': '360p_002.ts', 'duration': 5.033333}
#     ], 
#     'headers': {'bandwidth': '800000'}
# }

class Segment:
    file_name: str,
    duration: float,
    seg_type: str, #ENUM => main | ad
    

    def __init__(self):
        return


class Resolution:
    width: int,
    height: int,

    def __init__(self):
        return

    def get_resolution(self):
        return str(self.width)+'x'+str(self.height)