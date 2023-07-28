from os import path
import sys
from pprint import pp

class HlsMasterPlaylistReader(object):


    def __init__(self, filepath):
        # We assume, we read a m3u8 file
        
        if not path.exists(filepath) or not filepath.endswith(".m3u8"):
            raise ValueError("not a directory and does not point to a .m3u8 file")
        self.origin_file = filepath
        self.directory = path.dirname(filepath)

    def process_stream(self):
        extm3u8_found = False
        ext_x_verion_found = False
        streams = {}

        with open(self.origin_file, "r") as input_file:
            count = 0
            file_lines=iter(input_file.readlines())
            for line in file_lines:
                line = line.replace("\n","")
                if not line:
                    print(f"line {count} is empty: pass")
                    continue
                extm3u8_found |= line.startswith("#EXTM3U")
                ext_x_verion_found |= line.startswith("#EXT-X-VERSION:")
                if line.startswith("#EXT-X-STREAM-INF"):
                    stream_infos = line.split(':')[-1].split(',')
                    stream_playlist = self.directory +"/"+next(file_lines).replace("\n","")
            
                    streams[stream_playlist] = {v.split("=")[0] : v.split("=")[1] for v in stream_infos }
                    stream_ok, segments = StreamPlaylistReader(stream_playlist).process_stream()
                    streams[stream_playlist]["segments"] = [] if not stream_ok else segments
                    streams[stream_playlist]["dirname"] = self.directory

            return (extm3u8_found and ext_x_verion_found), streams
        


class StreamPlaylistReader(object):
    def __init__(self, filepath):
        # We assume, we read a m3u8 file
        
        if not path.exists(filepath) or not filepath.endswith(".m3u8"):
            raise ValueError("not a directory and does not point to a .m3u8 file")
        self.origin_file = filepath


    def process_stream(self):
        extm3u8_found = False
        ext_x_verion_found = False
        ext_x_target_duraion_found = False
        ext_x_media_sequence_found = False
        ext_x_endlist_found = False
        segments = []

        with open(self.origin_file, "r") as input_file:
            count = 0
            file_lines=iter(input_file.readlines())
            for line in file_lines:
                line = line.replace("\n","")
                if not line:
                    print(f"line {count} is empty: pass")
                    continue
                extm3u8_found |= line.startswith("#EXTM3U")
                ext_x_verion_found |= line.startswith("#EXT-X-VERSION:")
                ext_x_target_duraion_found |= line.startswith("#EXT-X-VERSION:")
                ext_x_media_sequence_found |=  line.startswith('#EXT-X-MEDIA-SEQUENCE')
                ext_x_endlist_found |= line.startswith("#EXT-X-ENDLIST")
                if line.startswith("#EXTINF"):
                    duration = line.replace(",","").split(":")[1]
                    segment = next(file_lines).replace("\n","")
                    segments.append(dict(file_name= segment, duration=float(duration))) 
            
            all_headers =(extm3u8_found
                        and ext_x_verion_found 
                        and ext_x_endlist_found 
                        and ext_x_target_duraion_found
                        and ext_x_media_sequence_found
                        and ext_x_endlist_found
            )
            return all_headers, segments

if __name__ == "__main__":
    playlist_reader = HlsMasterPlaylistReader(filepath=sys.argv[1])
    headers_detected, streams = playlist_reader.process_stream()
    if headers_detected:
        print (sys.argv[1])
        pp(streams)
    else:
        print(sys.argv[1], " is not an HLS stream")


    ad_playlist_reader = HlsMasterPlaylistReader(filepath=sys.argv[2])
    ad_headers_detected, streams = ad_playlist_reader.process_stream()

    if ad_headers_detected:
        print (sys.argv[2])
        pp(streams)
    else:
        print(sys.argv[1], " is not an HLS stream")