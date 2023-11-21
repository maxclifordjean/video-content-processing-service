import os
import sys
from pprint import pp
from files_data import HLSMaster, HLSPlaylist


class HlsMasterPlaylistReader(object):
    def __init__(self, filepath):
        # We assume, we read a m3u8 file

        if not os.path.exists(filepath) or not filepath.endswith(".m3u8"):
            raise ValueError("not a directory and does not point to a .m3u8 file")
        self.origin_file = filepath
        self.directory = os.path.dirname(filepath)

    def process_stream(self):
        extm3u8_found = False
        ext_x_verion_found = False
        streams = []

        with open(self.origin_file, "r") as input_file:
            count = 0
            file_lines = iter(input_file.readlines())
            stream = {}
            for line in file_lines:
                line = line.replace("\n", "")
                if not line:
                    print(f"line {count} is empty: pass")
                    continue
                extm3u8_found |= line.startswith("#EXTM3U")
                ext_x_verion_found |= line.startswith("#EXT-X-VERSION:")
                if line.startswith("#EXT-X-STREAM-INF"):
                    stream_infos = line.split(":")[-1].split(",")
                    stream_playlist = (
                        self.directory + "/" + next(file_lines).replace("\n", "")
                    )

                    stream.update(
                        {v.split("=")[0]: v.split("=")[1] for v in stream_infos}
                    )
                    stream["playlist"] = stream_playlist
                    stream_ok, segments = StreamPlaylistReader(
                        stream_playlist
                    ).process_stream()
                    stream["segments"] = [] if not stream_ok else segments
                    stream["dirname"] = self.directory

                    streams.append(stream)
            
            return HLSMaster(
                filepath=self.origin_file,
                directory=os.path.dirname(self.origin_file),
                playlists=[HLSPlaylist(playlist_infos=stream) for stream in streams],
                headers={},
            )
           


class StreamPlaylistReader(object):
    def __init__(self, filepath):
        # We assume, we read a m3u8 file
        if not os.path.exists(filepath) or not filepath.endswith(".m3u8"):
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
            file_lines = iter(input_file.readlines())
            for line in file_lines:
                line = line.replace("\n", "")
                if not line:
                    print(f"line {count} is empty: pass")
                    continue
                extm3u8_found |= line.startswith("#EXTM3U")
                ext_x_verion_found |= line.startswith("#EXT-X-VERSION:")
                ext_x_target_duraion_found |= line.startswith("#EXT-X-VERSION:")
                ext_x_media_sequence_found |= line.startswith("#EXT-X-MEDIA-SEQUENCE")
                ext_x_endlist_found |= line.startswith("#EXT-X-ENDLIST")
               

                
               

                if line.startswith("#EXTINF"):
                    duration = line.replace(",", "").split(":")[1]
                    segment = next(file_lines).replace("\n", "")
                    segments.append(dict(file_name=segment, duration=float(duration)))

            all_headers = (
                extm3u8_found
                and ext_x_verion_found
                and ext_x_endlist_found
                and ext_x_target_duraion_found
                and ext_x_media_sequence_found
                and ext_x_endlist_found
                
            )

            return all_headers, segments


class HLSPlaylistMerger(object):
    def __init__(self, input_stream, ads_and_timestamps):
        self.input_stream = input_stream
        self.ads = ads_and_timestamps

    
    def export_main_playlist(self):
        pass

    def process_playlists(self):
        
        input_stream = HlsMasterPlaylistReader(self.input_stream).process_stream()
        
        ads_streams = [[HlsMasterPlaylistReader(ad["filename"]).process_stream(), ad["timestamp"]] for ad in self.ads]
       
        
        for i in range(input_stream.playlists):
            main_stream_video = input_stream.playlists[i]
            ads_streams_videos = [[ad[0].playlists[i],ad[1]] for ad in ads_streams]
            HLSStreamMerger(main_stream_video, ads_streams_videos).process_streams()
            
        
            

class HLSStreamMerger(object):
    def __init__(self, input_stream, ads_and_timestamps):
        self.input_stream = input_stream
        self.ads = ads_and_timestamps

    def process_streams(self):
        sorted_ads = sorted(self.ads, key=lambda x: x["timestamp"])
        total_video_duration: float = 0.0
        total_duration: float = 0.0
        final_segments = []
        for segment in self.input_stream.segments:
            ads_to_insert = []
            for ad in sorted_ads:

                if (
                    total_video_duration
                    <= ad["timestamp"]
                    <= total_video_duration + segment["duration"]
                ):
                    ads_to_insert.append(ad)
                    pp(ad)
                    for ad_segment in ad["stream"].segments:
                        final_segments.append(
                            dict(
                                seg_type="ad",
                                duration=ad_segment["duration"],
                                filename=ad_segment["file_name"],
                                dirpath=ad["stream"].dirname,
                            )
                        )
                        total_duration += ad_segment["duration"]

            final_segments.append(
                dict(
                    seg_type="main",
                    duration=segment["duration"],
                    filename=segment["file_name"],
                    dirpath=self.input_stream.dirname,
                )
            )
            total_video_duration += segment["duration"]
            total_duration += segment["duration"]

        #pp(final_segments)
        # self.export(final_segments, "out.hls")
        return final_segments

    def export(self, segments, output_dir, filename):
        # Create dir
    
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)


        # Create file
        with open(output_dir + os.sep + filename, "w") as output_file:
            # Write Headers
            # So far we have chosen to write with a defined target duration
            output_file.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-ALLOW-CACHE:NO\n#EXT-X-TARGETDURATION:10\n#EXT-X-MEDIA-SEQUENCE:0\n")

            prev_segment = None
            # Write Segments
            for segment in segments:
                pp(segment)
                if prev_segment and (segment['seg_type'] != prev_segment['seg_type']) :
                    output_file.write("#EXT-X-DISCONTINUITY\n")

                output_file.write(f"#EXTINF:{segment['duration']}\n../{segment['dirpath'].split('/')[-1]}/{segment['filename']}\n")

            output_file.write("#EXT-X-ENDLIST\n")

            

if __name__ == "__main__":
    print(sys.argv)
    playlist_reader = HlsMasterPlaylistReader(filepath=sys.argv[1])
    main_video = playlist_reader.process_stream()
    video_streams = main_video.playlists
    


    ad_playlist_reader = HlsMasterPlaylistReader(filepath=sys.argv[2])
    ad_video = ad_playlist_reader.process_stream()
    ad_streams = ad_video.playlists[1:]
    
    
    
    hls_merger = HLSStreamMerger(
        video_streams[0], [{"stream": ad_streams[0], "timestamp": 50.2}]
    )
    segments = hls_merger.process_streams()
    res =  hls_merger.export(segments=segments, output_dir=sys.argv[3], filename="360.m3u8")
