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
        streams = []

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

                    stream = {v.split("=")[0] : v.split("=")[1] for v in stream_infos }
                    stream["playlist"] = stream_playlist
                    stream_ok, segments = StreamPlaylistReader(stream_playlist).process_stream()
                    stream["segments"] = [] if not stream_ok else segments
                    stream["dirname"] = self.directory
                    streams.append(stream)

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
        

class HLSStreamMerger(object):

    def __init__(self, input_stream, ads_and_timestamps):
        self.input_stream = input_stream
        self.ads = ads_and_timestamps
    
    def process_streams(self):
        sorted_ads = sorted(self.ads, key=lambda x: x["timestamp"])
        total_duration: float = 0.0
        final_segments=[]
        for segment in self.input_stream["segments"]:
            ads_to_insert = []
            for ad in sorted_ads:
                
                if total_duration <= ad["timestamp"] <= total_duration+ segment["duration"]:
                    ads_to_insert.append(ad)
                    pp(ad)
                    for ad_segment in ad["stream"]["segments"]:
                        final_segments.append(dict(seg_type="ad", duration=ad_segment["duration"], filename=ad_segment["file_name"], dirpath=ad["stream"]["dirname"]))
                        total_duration+= ad_segment["duration"]

            
            final_segments.append(dict(seg_type="main", duration=segment["duration"], filename=segment["file_name"], dirpath=self.input_stream["dirname"]))
            total_duration += segment["duration"]
        pp (final_segments)

    def export(self, filepath):
        pass



if __name__ == "__main__":
    print(sys.argv)
    playlist_reader = HlsMasterPlaylistReader(filepath=sys.argv[1])
    headers_detected, streams = playlist_reader.process_stream()
    if headers_detected:
        print (sys.argv[1])
        pp(streams)
    else:
        print(sys.argv[1], " is not an HLS stream")


    ad_playlist_reader = HlsMasterPlaylistReader(filepath=sys.argv[2])
    ad_headers_detected, ad_streams = ad_playlist_reader.process_stream()

    if ad_headers_detected:
        print (sys.argv[2])
        pp(ad_streams)
    else:
        print(sys.argv[1], " is not an HLS stream")

    
    for i in range (len (streams)):
        hls_merger = HLSStreamMerger(streams[i], [{"stream":ad_streams[i] , "timestamp": 50.2}])
        hls_merger.process_streams()
        hls_merger.export("filepath")