# from lxml import etree as ET
import xml.etree.ElementTree as ET #TODO deprecated, use lxml instead!
import re
import time
import os
import sys
import uuid
from pprint import pp
from files_data2 import Master, Playlist, Resolution

def seconds(time):
    s=0
    m=re.search("([0-9.]+)H",time)
    if m: s=s+float(m.group(1))*3600
    m=re.search("([0-9.]+)M",time)
    if m: s=s+float(m.group(1))*60
    m=re.search("([0-9.]+)S",time)
    if m: s=s+float(m.group(1))
    return s

def iso8601(s):
    h=int(s/3600)
    s=s-h*3600
    m=int(s/60)
    s=s-m*60
    return 'PT{0:1g}H{1:1g}M{2:1g}S'.format(h,m,s)

def _ns(tag):
    return "{urn:mpeg:dash:schema:mpd:2011}"+tag

ET.register_namespace('','urn:mpeg:dash:schema:mpd:2011')

def get_format(AdaptationSet, Representation):
    if((Representation.get('mimeType') == 'video/mp4') or (AdaptationSet.get('mimeType') == 'video/mp4') or (AdaptationSet.get('contentType') == 'video')): return 'video'
    if((Representation.get('mimeType') == 'audio/mp4') or (AdaptationSet.get('mimeType') == 'audio/mp4') or (AdaptationSet.get('contentType') == 'audio')): return 'audio'

class DashMasterPlaylistReader(object):
    def __init__(self, filepath):
        # We assume, we read a mpd file

        if not os.path.exists(filepath) or not filepath.endswith(".mpd"):
            raise ValueError("not a directory and does not point to a .mpd file")
        self.origin_file = filepath
        self.directory = os.path.dirname(filepath)

    #determine each stream from the manifest as object
    def process_stream(self):
        streams = []

        with open(self.origin_file, "r") as input_file:

            root=ET.fromstring(input_file.read())
            mediaPresentationDuration = 0
            if 'mediaPresentationDuration' in root.attrib:
                mediaPresentationDuration=seconds(root.attrib["mediaPresentationDuration"])

            Periods=root.findall(_ns("Period"))
            for Period in Periods:
                period_id = str(Period.get('id'))
                period_grp_id = uuid.uuid4()
                period_start = Period.get('start')

                #check & init variant if not exist
                for AdaptationSet in Period.findall(_ns("AdaptationSet")):
                    for Representation in AdaptationSet.findall(_ns("Representation")):
                        representation_id = Representation.get('id')
                        stream = {} #playlist variant (= 1 Representation)
                        stream["playlist"] = self.origin_file #TODO ??
                        stream["dirname"] = self.directory
                        stream['contentType'] = get_format(AdaptationSet, Representation)
                        stream['BANDWIDTH'] = Representation.get('bandwidth')
                        stream['RESOLUTION'] = Resolution(Representation.get('width'), Representation.get('height'))
                        stream['representation_id'] = representation_id
                        stream['segments'] = []

                        #avoid duplicates streams per period
                        pid_stream_is_exist:bool = False
                        for idx in range(len(streams)):
                            for seg in streams[idx]['segments']:
                                if(((stream['contentType'] == 'audio') and ((streams[idx]['BANDWIDTH']==stream['BANDWIDTH']))) and (seg['period_id'] == period_id)):
                                    pid_stream_is_exist = True
                                    continue

                        if(not pid_stream_is_exist):
                            #get segments for current period
                            for SegmentTemplate in Representation.findall(_ns("SegmentTemplate")):
                                timescale = int(SegmentTemplate.get('timescale'))
                                for S in SegmentTemplate.findall(_ns("SegmentTimeline")+"/"+_ns("S")):
                                    if "t" in S.attrib: t=int(S.attrib["t"]) #segment offset in timescale unit
                                    d=int(S.attrib["d"]) #segment duration in timescale unit
                                    r=int(S.attrib["r"]) if "r" in S.attrib else 0 #nb of similar consecutive segments
                                    seg_tl_duration = (d*(r+1))/timescale
                                    seg_tl = dict(
                                        period_grp_id=period_grp_id,
                                        period_id=str(period_id),
                                        period_start=seconds(period_start),
                                        representation_id=representation_id,
                                        timescale=timescale,
                                        timeline=(t,d,r),
                                        duration=seg_tl_duration
                                    )
                                    stream['segments'].append(seg_tl) #TODO segments or segmentsTLs ?? => (seg, seg_tl)

                            #update existing stream with segments or insert complete new stream (video or audio)
                            if len(streams) > 0 :
                                count_update = 0
                                for idx in range(len(streams)):
                                    s = streams[idx]

                                    if(
                                        ((stream['contentType'] == 'video') and ((s['BANDWIDTH']==stream['BANDWIDTH']) and (s['RESOLUTION'].get_resolution()==stream['RESOLUTION'].get_resolution())))
                                        or
                                        ((stream['contentType'] == 'audio') and ((s['BANDWIDTH']==stream['BANDWIDTH'])))
                                    ):
                                        streams[idx]['segments'] = streams[idx]['segments'] + stream['segments'] #add segments over periods into existing stream 
                                        count_update+=1
                                    
                                #insert new stream if not exist
                                if count_update==0:
                                    streams.append(stream)
                            else:
                                streams.append(stream) #init streams with new stream

            # pp("DashMasterPlaylistReader#process_stream#streams : ")
            # pp(streams)
            
            return Master(
                filepath=self.origin_file,
                directory=os.path.dirname(self.origin_file),
                playlists=[Playlist(playlist_infos=stream) for stream in streams],
                headers={
                    'mediaPresentationDuration': mediaPresentationDuration
                },
            )

class DashMerger():
    def __init__(self, input, ads_and_timestamps):
        self.input = input
        self.ads = ads_and_timestamps

    #FOR NOW WE GO WITH SEG TIMELINE APPROACH, THE IDEA IS TO INSERT AD STREAM SEGS BASED ON PERIOD POSITION ONLY
    #TODO MAYBE NEXT, WITH SEG PLAYLIST, be able to insert ads based on segments position also ??
    def process_streams(self):
        sorted_ads = sorted(self.ads, key=lambda x: x["timestamp"])
        output_streams = dict(
            video=[],
            audio=[]
        )

        for main_stream in self.input.playlists:
                content_type = main_stream.headers.get('contentType')
                period_grp_id = None
                seq:int = 0
                period_start: float = 0.0
                total_content_duration: float = 0.0 #result main video segments duration
                total_duration: float = 0.0 #result main video & ad segments duration
                final_segments = []
      
                for main_seg in main_stream.segments:      
                    #detect period changes in main_video
                    if(period_grp_id != main_seg['period_grp_id']):
                        period_grp_id = main_seg['period_grp_id']
                        period_start = total_duration

                    for ad in sorted_ads:
                        #check if we are at ad insertion position
                        if (
                            total_content_duration
                            <= ad["timestamp"]
                            <= total_content_duration + main_seg['duration']
                        ):
                            for ad_stream in ad['master'].playlists:
                                #take only ad_stream which match with main_stream formats (contentType, BW, resolution)
                                if(
                                    ((ad_stream.headers.get('contentType') == 'video') and (main_stream.headers.get('contentType') == 'video') and ((main_stream.headers.get('bandwidth')==ad_stream.headers.get('bandwidth') and (main_stream.resolution.get_resolution()==ad_stream.resolution.get_resolution()))))
                                    or
                                    ((ad_stream.headers.get('contentType') == 'audio') and ((main_stream.headers.get('bandwidth')==ad_stream.headers.get('bandwidth'))))
                                ):
                                    #Insert AD Period
                                    for ad_seg in ad_stream.segments:
                                        ad_seg['period_start'] = period_start
                                        ad_seg['seg_type'] = 'ad'
                                        final_segments.append(ad_seg)
                                        total_duration += ad_seg['duration'] #total duration augmented with ad seg duration

                                    period_start = total_duration

                    main_seg['period_start'] = period_start
                    main_seg['seg_type'] = 'main'

                    #Insert Main seg
                    final_segments.append(main_seg)

                    total_content_duration += main_seg['duration']
                    total_duration += main_seg['duration']

                #update each seg period_id sequence order
                prev_seg = final_segments[0]
                for i in range(len(final_segments)):
                    if(final_segments[i]['period_grp_id'] != prev_seg['period_grp_id']):
                        seq+=1
                    final_segments[i]['period_id'] = seq
                    prev_seg = final_segments[i]

                output = dict(
                    content_type=content_type,
                    total_content_duration=total_content_duration,
                    total_duration=total_duration,
                    segments=final_segments
                )

                output_streams[content_type].append(output)
        
        print('output_streams: ')
        pp(output_streams)

    def export(self):
        #set output or return String manifest
        return

# v = seconds("PT0H1M59.89S")
# print('PT0H1M59.89S', v, type(v))
# print('119.89', iso8601(v))

##Video Content merge with Periodic Ads placement##
#video content manifest (multi periods)
print('read main video dash MPD...')
dmPlist = DashMasterPlaylistReader('./video-storage/dash/my_video/index.mpd').process_stream()
print('\n')

#ad video manifest
print('read ad dash MPD...')
ADdmPlist = DashMasterPlaylistReader('./video-storage/dash/vast_intro/ad.mpd').process_stream()
print('\n')
#merge main content with ads
print('proceed merge...')
merged_manifests = DashMerger(dmPlist,[{"master": ADdmPlist, "timestamp": 31.033}]).process_streams()

#TODO THEN => Personalized Manifest: Export/Write obj -> mpd + Calcul (mediaPresentationDuration,...)
#personalized_master = merged_manifests.export()

#NOTE => for now the main goal is to be able to parse mpd with segmentsTLs and insert ADs based on period instead of segment partial duration, so no calcul required based on segs. In the case we evolve based on segments partials maybe we could transcode video mezzanine into segments playlists as HLS
