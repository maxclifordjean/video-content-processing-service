# from lxml import etree as ET
import xml.etree.ElementTree as ET #TODO deprecated, use lxml instead!
import re
import time
import os
import sys
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
                pId = Period.get('id')
                pStart = Period.get('start')

                #check & init variant if not exist
                for AdaptationSet in Period.findall(_ns("AdaptationSet")):
                    for Representation in AdaptationSet.findall(_ns("Representation")):
                        stream = {} #playlist variant (= 1 Representation)
                        stream["playlist"] = self.directory + "/" + self.origin_file #TODO ??
                        stream["dirname"] = self.directory
                        stream['contentType'] = get_format(AdaptationSet, Representation)
                        stream['BANDWIDTH'] = Representation.get('bandwidth')
                        stream['RESOLUTION'] = Resolution(Representation.get('width'), Representation.get('height'))
                        stream['segments'] = []

                        #get segments for current period
                        for SegmentTemplate in Representation.findall(_ns("SegmentTemplate")):
                            timescale = float(SegmentTemplate.get('timescale'))
                            for S in SegmentTemplate.findall(_ns("SegmentTimeline")+"/"+_ns("S")):
                                if "t" in S.attrib: t=int(S.attrib["t"]) #segment offset in timescale unit
                                d=int(S.attrib["d"]) #segment duration in timescale unit
                                r=int(S.attrib["r"]) if "r" in S.attrib else 0 #nb of similar consecutive segments
                                seg_tl_duration = (d*(r+1))/timescale
                                seg_tl = ((pId, seconds(pStart)), Representation.get('id'), timescale, t,d,r, seg_tl_duration)
                                stream['segments'].append(seg_tl) #TODO segments or segmentsTLs ?? => (seg, seg_tl)

                        #update existing stream with segments or insert complete new stream (video or audio)
                        if len(streams) > 0 :
                            count_update = 0
                            for idx in range(len(streams)):
                                #update existing stream
                                s = streams[idx]
                                if(
                                    ((stream['contentType'] == 'video') and ((s['BANDWIDTH']==stream['BANDWIDTH']) and (s['RESOLUTION'].get_resolution()==stream['RESOLUTION'].get_resolution()))) 
                                    or 
                                    ((stream['contentType'] == 'audio') and ((s['BANDWIDTH']==stream['BANDWIDTH'])))
                                ):
                                    streams[idx]['segments'] = streams[idx]['segments'] + stream['segments'] #add segments into existing stream
                                    count_update+=1
                            
                            #insert new stream
                            if count_update==0:
                                streams.append(stream)
                        else:
                            streams.append(stream) #init streams with new stream

            pp("DashMasterPlaylistReader#process_stream#streams : ")
            pp(streams)
            
            return Master(
                filepath=self.origin_file,
                directory=os.path.dirname(self.origin_file),
                playlists=[Playlist(playlist_infos=stream) for stream in streams],
                headers={},
            )
    
    def set_media_presentation_duration(self):
        return

# v = seconds("PT0H1M59.89S")
# print('PT0H1M59.89S', v, type(v))
# print('119.89', iso8601(v))

dmPlist = DashMasterPlaylistReader('./video-storage/dash/my_video/index.mpd').process_stream()
#TODO NEXT => Video Content merge with Periodic Ads placement
#TODO THEN => Personalized Manifest: Export/Write obj -> mpd + Calcul (mediaPresentationDuration,...)

#NOTE => for now the main goal is to be able to parse mpd with segmentsTLs and insert ADs based on period instead of segment partial duration, so no calcul required based on segs. In the case we evolve based on segments partials maybe we could transcode video mezzanine into segments playlists as HLS
